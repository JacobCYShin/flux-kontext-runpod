import gradio as gr
import runpod

from config import RUNPOD_API_KEY, ratios
from inference import generate

# --- Gradio UI ---

def create_ui():
    """Creates and returns the Gradio UI."""
    with gr.Blocks(css="""
        .container { max-width: 800px; margin: auto; padding-top: 2rem; }
        .gr-button { background-color: #4CAF50; color: white; }
        .gr-button:hover { background-color: #45a049; }
    """) as demo:
        with gr.Column(elem_classes="container"):
            gr.Markdown("# Flux Kontext Experiment Tool")
            
            with gr.Row():
                with gr.Column(scale=1):
                    execution_env = gr.Radio(
                        choices=["runpod", "local"], 
                        value="runpod", 
                        label="Execution Environment",
                        info="Choose 'runpod' for cloud-based generation or 'local' to use your own GPU (requires setup)."
                    )
                    image_input = gr.Image(type="filepath", label="Upload Image")
                    prompt_input = gr.Textbox(lines=2, label="Prompt", placeholder="e.g., make it a watercolor painting")
                    ratio_input = gr.Radio(choices=ratios, label="Aspect Ratio", value="Original")
                    generate_button = gr.Button("Generate", variant="primary")

                with gr.Column(scale=1):
                    status_output = gr.Textbox(label="Status", interactive=False)
                    image_output = gr.Image(label="Generated Image", interactive=False)

            async def wrapped_generate(execution_env, image_path, prompt, ratio):
                """A wrapper to handle UI updates like button disabling and spinners."""
                # Disable the button at the start of any generation attempt.
                yield {generate_button: gr.Button(interactive=False)}

                # Variables to store the final state
                final_image = None
                final_status = ""

                # Stream results from the underlying generator.
                async for image, status in generate(execution_env, image_path, prompt, ratio):
                    # Store the current state
                    final_image = image
                    final_status = status
                    
                    # Check for final status keywords to determine if the spinner should be shown.
                    is_complete = any(keyword in status.lower() for keyword in 
                                      ["complete", "failed", "cancelled", "error", "not available", "upload an image"])

                    # Update UI elements. The spinner is prepended if not complete.
                    yield {
                        image_output: image,
                        status_output: status if is_complete else f"⚙️ {status}",
                    }

                # After the loop finishes, re-enable the button while preserving the final state.
                yield {
                    image_output: final_image,
                    status_output: final_status,
                    generate_button: gr.Button(interactive=True)
                }


            generate_button.click(
                fn=wrapped_generate,
                inputs=[execution_env, image_input, prompt_input, ratio_input],
                outputs=[image_output, status_output, generate_button]
            )
    return demo

# --- Main Execution ---

if __name__ == "__main__":
    if not RUNPOD_API_KEY:
        print("ERROR: RUNPOD_API_KEY environment variable is not set.")
        print("Please create a .env file and add your RunPod API key to it.")
        print("Example .env file content:")
        print("RUNPOD_API_KEY=YOUR_RUNPOD_API_KEY_HERE")
    else:
        runpod.api_key = RUNPOD_API_KEY
        app = create_ui()
        app.launch(
            server_name="0.0.0.0",
            server_port=7860,
         
        )