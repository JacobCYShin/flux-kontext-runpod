import asyncio
import aiohttp
import os
import runpod
from runpod import AsyncioEndpoint, AsyncioJob
import base64

from dotenv import load_dotenv
load_dotenv()

runpod.api_key = os.getenv("RUNPOD_API_KEY")


async def main():
    async with aiohttp.ClientSession() as session:
        input_payload = {
            "prompt": "make it green color",
            "image": "https://cdn.dyp.ai/gen-img/b06d06e1-2d30-42bb-bb1b-6e558ac1d72e/3059152d-075f-4d37-afdd-ef391d4da7b1/image.png"
        }
        endpoint = AsyncioEndpoint("93szmi2k95ybv8", session)
        job: AsyncioJob = await endpoint.run(input_payload)

        # Polling job status
        while True:
            status = await job.status()
            
            print(f"Current job status: {status}")
            if status == "COMPLETED":
                output = await job.output()
                print("Job output:", output)
                break  # Exit the loop once the job is completed.
            elif status in ["FAILED"]:
                print("Job failed or encountered an error.")

                break
            else:
                if status == "IN_PROGRESS":
                    data = await job._fetch_job()
                    if "output" in data and isinstance(data.get("output"), dict) and "step" in data["output"] and "image" in data["output"]:
                        try:
                            image_b64 = data["output"]["image"]
                            step = data["output"]["step"]
                            image_data = base64.b64decode(image_b64)
                            
                            filename = f"{step}.png"
                            
                            with open(filename, "wb") as f:
                                f.write(image_data)
                            print(f"Saved intermediate image: {filename}")
                        except Exception as e:
                            print(f"Could not process and save image: {e}")

                print("Job in queue or processing. Waiting 3 seconds...")
                await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())