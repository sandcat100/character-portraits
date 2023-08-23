from __future__ import annotations

import io
import os
import time
import re
import base64
import json
from pathlib import Path
from fastapi.responses import Response

from modal import Image, Secret, Stub, method, web_endpoint

stub = Stub("stable-diffusion-cli")

model_id = 'runwayml/stable-diffusion-v1-5'
cache_path = "/vol/cache"

def download_image_models():
	import diffusers
	import torch

	hugging_face_token = os.environ["HUGGINGFACE_TOKEN"]

	# Instantiate a Scheduler class from a pre-defined JSON configuration file inside a directory or Hub repo
	scheduler = diffusers.DPMSolverMultistepScheduler.from_pretrained(
		model_id,
		subfolder='scheduler',
		use_auth_token=hugging_face_token,
		cache_dir=cache_path
	)

	# Save a scheduler configuration object to the directory save_directory, so that it can be re-loaded using the from_pretrained() class method
	scheduler.save_pretrained(cache_path, safe_serialization=True)

	# Downloads all other models
	pipe = diffusers.StableDiffusionPipeline.from_pretrained(
		model_id,
		use_auth_token=hugging_face_token,
		revision="fp16",
		torch_dtype=torch.float16,
		cache_dir=cache_path
	)
	pipe.save_pretrained(cache_path, safe_serialization=True)

def download_language_models():
	from huggingface_hub import snapshot_download
	# Download LLM files (but not into memory!)
	snapshot_download(
		"meta-llama/Llama-2-13b-chat-hf",
		local_dir=cache_path,
		token=os.environ["HUGGINGFACE_TOKEN"]
	)

# This builds an image with the scheduler and model defined above
image_model_image = (
	Image.debian_slim(python_version="3.10")
	.pip_install(
		"accelerate",
		"diffusers[torch]>=0.15.1",
		"ftfy",
		"torchvision",
		"transformers~=4.25.1",
		"triton",
		"safetensors"
	)
	.pip_install(
		"torch==2.0.1+cu117",
		find_links="https://download.pytorch.org/whl/torch_stable.html",
	)
	.pip_install("xformers", pre=True)
	.run_function(
		download_image_models,
		secrets=[Secret.from_name("my-huggingface-secret")]
	)
)

language_model_image = (
	Image.from_dockerhub("nvcr.io/nvidia/pytorch:22.12-py3")
	.pip_install(
		"torch==2.0.1", index_url="https://download.pytorch.org/whl/cu118"
	)
	.pip_install(
		"vllm @ git+https://github.com/vllm-project/vllm.git@bda41c70ddb124134935a90a0d51304d2ac035e8"
	)
	.pip_install("hf-transfer~=0.1")
	.env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
	.run_function(
		download_language_models,
		secret=Secret.from_name("my-huggingface-secret"),
		timeout=60 * 20,
	)
)

@stub.cls(gpu='A10g', image=image_model_image)
class StableDiffusion:
	def __enter__(self):
		import diffusers
		import torch

		torch.backends.cuda.matmul.allow_tf32 = True

		#Loading scheduler that's saved in cache_path
		scheduler = diffusers.DPMSolverMultistepScheduler.from_pretrained(
			cache_path,
			subfolder="scheduler",
			solver_order=2,
			prediction_type="epsilon",
			thresholding=False,
			algorithm_type="dpmsolver++",
			solver_type="midpoint",
			denoise_final=True,
			low_cpu_mem_usage=True,
			device_map="auto",
		)

		#Loading model that's saved in cache_path
		self.pipe = diffusers.StableDiffusionPipeline.from_pretrained(
			cache_path,
			scheduler=scheduler,
			low_cpu_mem_usage=True,
			device_map="auto",
		)
		self.pipe.enable_xformers_memory_efficient_attention()

	@method()
	def run_inference(
		self, prompt: str, steps: int = 20, batch_size: int = 4
	) -> list[bytes]:

		import torch

		with torch.inference_mode():
			with torch.autocast("cuda"):
				images = self.pipe( # This is the saved model/pipeline being called for inference
					[prompt] * batch_size,
					num_inference_steps=steps,
					guidance_scale=8.0,
				).images

		# Convert to PNG bytes
		image_output = []
		for image in images:
			with io.BytesIO() as buf:
				image.save(buf, format="PNG")
				# this is appending bytes--the output of .getvalue() is <class 'bytes'>
				image_output.append(buf.getvalue())
		return image_output

@stub.cls(gpu="A100", image=language_model_image)
class LanguageModel:

	# Interesting, this isn't called again even if I call llm_entrypoint via the endpoint twice in succession.
	# Only called when new container is started.
	def __enter__(self):
		from vllm import LLM
		self.llm = LLM(cache_path)
		self.template = """SYSTEM: You are a helpful assistant. USER: {} ASSISTANT: """

	@method()
	def run_inference(self, user_questions):
		from vllm import SamplingParams

		prompts = [self.template.format(q) for q in user_questions]
		sampling_params = SamplingParams(
			temperature=0.3, # "creativity" of the response, value from 0 to 1
			top_p=1, # choosing from possible tokens whose probabilities sum up to this value
			max_tokens=200, # max response length
			presence_penalty=0, # penalizes tokens that have already appeared in preceding text
		)
		result = self.llm.generate(prompts, sampling_params)
		num_tokens = 0
		for output in result:
			num_tokens += len(output.outputs[0].token_ids)
			print(output.prompt, output.outputs[0].text, "\n\n", sep="")
		print(f"Generated {num_tokens} tokens")
		return output.outputs[0].text

@stub.function()
@web_endpoint(method="POST")
def stable_diffusion_entrypoint(
	parameters: dict
):
	prompt = parameters['prompt']
	samples = parameters['samples']
	steps = parameters['steps']
	batch_size = parameters['batch_size']

	print(
		f"prompt => {prompt}, steps => {steps}, samples => {samples}, batch_size => {batch_size}"
	)

	dir = Path("/tmp/stable-diffusion")
	if not dir.exists():
		dir.mkdir(exist_ok=True, parents=True)

	sd = StableDiffusion()
	for i in range(samples):
		t0 = time.time()
		images = sd.run_inference.call(prompt, steps, batch_size)
		total_time = time.time() - t0
		print(
			f"Sample {i} took {total_time:.3f}s ({(total_time)/len(images):.3f}s / image)."
		)
		image_bytes_array = []
		for j, image_bytes in enumerate(images):
			output_path = dir / f"output_{j}_{i}.png"
			print(f"Saving it to {output_path}")
			# with open(output_path, "wb") as f:
			# 	f.write(image_bytes)
			image_bytes_array.append(base64.b64encode(image_bytes).decode('utf8'))
	return Response(content=json.dumps(image_bytes_array))


@stub.function()
@web_endpoint()
def llm_entrypoint(book, character):
	llm = LanguageModel()
	question_template = """Describe what {} ({} character) looks like. The response is a comma-separated list of SHORT, concrete phrases describing the character's gender, age, physical appearance and how they dress. The response is 20-30 words. Put quotes around the response. Example of response format: "tall, imposing man with a rugged and weathered appearance, square head, dark unkempt hair, strong hands, broad shoulders, no-nonsense demeanor, plain and practical clothing" """
	question = question_template.format(character, book)
	questions = [question]
	answer = llm.run_inference.call(questions)
	char_description = re.findall(r'"([^"]*)"', answer)[0]
	return char_description

@stub.local_entrypoint()
def run(book: str="Remains of the Day", character: str="Stevens"):
	char_description = llm_entrypoint.call(book, character)
	char_prompt = "Portrait of " + char_description + ", by Greg Rutkowski, digital painting"
	stable_diffusion_entrypoint.call({"prompt":char_prompt, "samples":1, "steps": 20, "batch_size":5})