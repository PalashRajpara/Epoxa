import uuid
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.knowledge_repo import knowledge_repo
from app.repositories.ticket_repo import ticket_repo
from app.repositories.customer_repo import customer_repo
from app.repositories.voice_repo import voice_repo
from app.schemas.ticket import TicketCreate
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.core.logging import logger

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Searches verified company policies, return rules, and FAQs to answer customer inquiries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query keywords regarding policy, product, or service rules."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_support_ticket",
            "description": "Creates an official support ticket when an issue requires manual agent investigation or customer follow-up.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Short descriptive title of the issue"},
                    "description": {"type": "string", "description": "Detailed explanation of customer problem"},
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "urgent"],
                        "description": "Ticket priority level"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["general", "technical", "billing", "escalation"],
                        "description": "Problem category"
                    }
                },
                "required": ["title", "description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_customer_details",
            "description": "Captures customer contact details (name, phone, email) to link their profile to this support session.",
            "parameters": {
                "type": "object",
                "properties": {
                    "display_name": {"type": "string", "description": "Customer's full name"},
                    "phone_number": {"type": "string", "description": "Contact phone number"},
                    "email": {"type": "string", "description": "Contact email address"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "request_supervisor_escalation",
            "description": "Requests an immediate live takeover by an online human supervisor.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Specific reason caller requires human supervisor intervention"}
                },
                "required": ["reason"]
            }
        }
    }
]

class AgentToolExecutor:
    """Executes validated tool calls with server-enforced tenant boundaries."""

    async def execute_tool(
        self,
        db: AsyncSession,
        tool_name: str,
        arguments: Dict[str, Any],
        org_id: uuid.UUID,
        session_id: uuid.UUID,
        customer_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        logger.info("Executing agent tool", tool_name=tool_name, org_id=str(org_id), session_id=str(session_id))

        if tool_name == "search_knowledge_base":
            query = arguments.get("query", "")
            results = await knowledge_repo.search_chunks(db, org_id=org_id, query=query, limit=3)
            if not results:
                return {
                    "found": False,
                    "message": "No matching knowledge base documents found for this query."
                }
            chunks_text = "\n---\n".join([f"[{c.document.title}]: {c.chunk_content}" for c, score in results])
            return {
                "found": True,
                "context": chunks_text
            }

        elif tool_name == "create_support_ticket":
            data = TicketCreate(
                title=arguments.get("title", "Voice Support Inbound Issue"),
                description=arguments.get("description", "Ticket created via voice agent"),
                priority=arguments.get("priority", "medium"),
                category=arguments.get("category", "general"),
                customer_id=customer_id,
                call_session_id=session_id
            )
            ticket = await ticket_repo.create_ticket(db, org_id=org_id, data=data)
            return {
                "success": True,
                "ticket_number": ticket.ticket_number,
                "status": ticket.status,
                "message": f"Support ticket {ticket.ticket_number} created successfully."
            }

        elif tool_name == "update_customer_details":
            name = arguments.get("display_name")
            phone = arguments.get("phone_number")
            email = arguments.get("email")

            # Check if customer already linked or exists
            if customer_id:
                cust = await customer_repo.get_by_id(db, customer_id=customer_id, org_id=org_id)
                if cust:
                    await customer_repo.update(db, cust, CustomerUpdate(display_name=name, phone_number=phone, email=email))
                    return {"success": True, "message": "Customer profile updated successfully."}

            # Create new customer record
            new_cust = await customer_repo.create(db, org_id=org_id, data=CustomerCreate(
                display_name=name,
                phone_number=phone,
                email=email
            ))
            # Link to session
            call = await voice_repo.get_session_by_id(db, session_id=session_id, org_id=org_id)
            if call:
                call.customer_id = new_cust.id
                await db.flush()

            return {
                "success": True,
                "customer_id": str(new_cust.id),
                "message": "Customer details recorded and linked to session."
            }

        elif tool_name == "request_supervisor_escalation":
            reason = arguments.get("reason", "Customer requested supervisor assistance")
            # Update call session state
            await voice_repo.update_status(db, session_id=session_id, status="escalated", handoff_state="requested")
            # Create escalation record
            esc = await ticket_repo.create_escalation(db, org_id=org_id, session_id=session_id, reason=reason)
            # Log event
            await voice_repo.add_event(db, session_id=session_id, event_type="escalation_requested", actor="ai_agent", payload={"reason": reason})

            return {
                "escalated": True,
                "state": "pending",
                "message": "An alert has been dispatched to human supervisors on duty."
            }

        else:
            return {"error": f"Unknown tool: {tool_name}"}

tool_executor = AgentToolExecutor()
