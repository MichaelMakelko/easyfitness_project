# model/llama_model.py
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import torch
import os
from config import MODEL_PATH

class LlamaBot:
    def __init__(self):
        os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )

        print("Lade Llama-3.1-8B 4-Bit – einen Moment...")
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True)
        self.tokenizer.pad_token = self.tokenizer.eos_token
        self.tokenizer.padding_side = "left"

        self.model = AutoModelForCausalLM.from_pretrained(
            MODEL_PATH,
            device_map="auto",
            quantization_config=quant_config,
            dtype=torch.float16,
            max_memory={0: "7.6GiB", "cpu": "96GiB"},
            offload_folder="offload",
            local_files_only=True,
        )
        print("Max ist wach und fit!")

    def generate(self, messages):
        tokenized = self.tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_attention_mask=True,
            return_tensors="pt",
            truncation=True,
            max_length=8192
        )

        if isinstance(tokenized, dict):
            input_ids = tokenized["input_ids"].to("cuda")
            attention_mask = tokenized["attention_mask"].to("cuda")
        else:
            input_ids = tokenized.to("cuda")
            attention_mask = None

        with torch.no_grad():
            output = self.model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_new_tokens=300,
                temperature=0.8,
                top_p=0.9,
                do_sample=True,
                repetition_penalty=1.2,
                pad_token_id=self.tokenizer.eos_token_id,
            )

        reply = self.tokenizer.decode(output[0], skip_special_tokens=True)
        return reply.split("assistant")[-1].strip()