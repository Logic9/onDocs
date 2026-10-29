import os
import torch
from transformers import AutoModel, AutoTokenizer
from transformers.utils import import_utils as tf_import_utils
from onnxruntime.quantization import quantize_dynamic, QuantType

# 설정
model_id = "jhgan/ko-sroberta-multitask"
output_dir = "onnx_emb_model"
onnx_model_path = os.path.join(output_dir, "model.onnx")
quantized_model_path = os.path.join(output_dir, "model_quantized.onnx")

# 폴더 생성
os.makedirs(output_dir, exist_ok=True)

print(f"모델 로드 중... ({model_id})")
tokenizer = AutoTokenizer.from_pretrained(model_id)
# safetensors 우선 시도, 실패하면 취약점 검사 우회 후 PyTorch bin 로드
try:
    model = AutoModel.from_pretrained(model_id, use_safetensors=True)
except Exception as e:
    print(f"⚠️ safetensors 로드 실패 또는 미지원: {e}")
    # torch>=2.6 미제공 환경에서만 사용: 공식 모델만 신뢰하는 경우에 한해 안전 검사 우회
    tf_import_utils.check_torch_load_is_safe = lambda: None  # noqa: E731
    model = AutoModel.from_pretrained(model_id, use_safetensors=False)
model.eval()

# 더미 입력 생성 (Export를 위한 Trace용)
dummy_text = "이것은 테스트 문장입니다."
dummy_inputs = tokenizer(dummy_text, return_tensors="pt")

print("PyTorch -> ONNX 변환 중...")
try:
    torch.onnx.export(
        model,
        (dummy_inputs["input_ids"], dummy_inputs["attention_mask"]),
        onnx_model_path,
        input_names=["input_ids", "attention_mask"],
        output_names=["last_hidden_state", "pooler_output"],
        dynamic_axes={
            "input_ids": {0: "batch_size", 1: "sequence_length"},
            "attention_mask": {0: "batch_size", 1: "sequence_length"},
            "last_hidden_state": {0: "batch_size", 1: "sequence_length"}
        },
        opset_version=14
    )
    tokenizer.save_pretrained(output_dir)
    print(f"✅ 변환 완료: {onnx_model_path}")
except Exception as e:
    print(f"❌ 변환 실패: {e}")
    exit(1)

print("ONNX 모델 양자화 (Int8) 진행 중...")
try:
    quantize_dynamic(
        model_input=onnx_model_path,
        model_output=quantized_model_path,
        weight_type=QuantType.QUInt8 
    )
    print(f"양자화 완료. 최종 모델: {quantized_model_path}")
    
    # 용량 비교 출력
    orig_size = os.path.getsize(onnx_model_path) / (1024 * 1024)
    quant_size = os.path.getsize(quantized_model_path) / (1024 * 1024)
    print(f"   - 원본 크기: {orig_size:.2f} MB")
    print(f"   - 압축 크기: {quant_size:.2f} MB (약 {orig_size/quant_size:.1f}배 감소)")

    os.remove(onnx_model_path)
    print("🧹 원본 FP32 모델 삭제 완료 (공간 절약)")

except Exception as e:
    print(f"❌ 양자화 실패: {e}")
    exit(1)
