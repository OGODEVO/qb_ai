import asyncio
import grpc
from reki.grpc import reki_agent_pb2
from reki.grpc import reki_agent_pb2_grpc

async def run():
    async with grpc.aio.insecure_channel('localhost:50051') as channel:
        stub = reki_agent_pb2_grpc.RekiAgentStub(channel)
        
        async def request_generator():
            yield reki_agent_pb2.ChatRequest(actor_id="test_actor", message="Hello, agent!")
            await asyncio.sleep(1)

        response_iterator = stub.Chat(request_generator())
        
        async for response in response_iterator:
            print(f"Received message from agent: {response.message}")

if __name__ == '__main__':
    asyncio.run(run())
