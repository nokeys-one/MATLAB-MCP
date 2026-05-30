import base64
from pathlib import Path


class ClientAdapter:
    def __init__(self, client_vision: bool = True, context_limit: int = 200000):
        self.client_vision = client_vision
        self.context_limit = context_limit

    def get_capabilities(self) -> dict:
        return {
            "client_vision": self.client_vision,
            "context_limit": self.context_limit,
        }

    def truncate_output(self, output: str, max_length: int | None = None) -> str:
        limit = max_length or self.context_limit
        if len(output) <= limit:
            return output
        return output[:limit] + f"\n... (truncated, {len(output) - limit} chars omitted)"

    def adapt_image_response(self, response: dict, image_path: str) -> dict:
        if self.client_vision:
            try:
                img_path = Path(image_path)
                if img_path.exists() and img_path.stat().st_size < 10 * 1024 * 1024:
                    with open(img_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")
                    response["image_base64"] = b64
                    response["image_format"] = img_path.suffix.lstrip(".")
            except Exception:
                pass
            return response
        else:
            response.pop("image_base64", None)
            response["instruction"] = (
                "请调用 execute_matlab_script 编写 imread 代码，利用 MATLAB 后台提取特征"
            )
            return response

    def adapt_data_response(self, response: dict, element_count: int,
                            full_data_threshold: int = 100) -> dict:
        if element_count > full_data_threshold:
            response["data_truncated"] = True
            response["suggestion"] = "数据量较大，已返回统计摘要。使用绘图工具可视化完整数据。"
        return response
