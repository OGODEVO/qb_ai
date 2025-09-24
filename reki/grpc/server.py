import asyncio
import grpc
from concurrent import futures

from reki.grpc import reki_agent_pb2
from reki.grpc import reki_agent_pb2_grpc
from reki.agent1.agent import handle_chat_completion
from reki.agent1.short_term_memory import ShortTermMemory

class RekiAgentServicer(reki_agent_pb2_grpc.RekiAgentServicer):
    async def Chat(self, request_iterator, context):
        print("Chat session started")
        short_term_memory = ShortTermMemory()

        async for request in request_iterator:
            print(f"Received message from {request.actor_id}: {request.message}")
            short_term_memory.add_message("user", request.message)

            async for chunk in handle_chat_completion(short_term_memory, "grok-3-fast", True):
                if chunk.choices[0].delta.content:
                    print(f"Sending message to {request.actor_id}: {chunk.choices[0].delta.content}")
                    yield reki_agent_pb2.ChatResponse(
                        actor_id=request.actor_id,
                        message=chunk.choices[0].delta.content
                    )

async def serve():
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    reki_agent_pb2_grpc.add_RekiAgentServicer_to_server(RekiAgentServicer(), server)
    server.add_insecure_port('[::]:50051')
    print("gRPC server started on port 50051")
    await server.start()
    await server.wait_for_termination()

if __name__ == '__main__':
    asyncio.run(serve())
