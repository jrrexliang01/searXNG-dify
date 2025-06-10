from typing import Any
import requests
import json
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin import Tool


class SearXNGSearchTool(Tool):
    """
    Tool for performing a search using SearXNG engine.
    """

    def _invoke(self, tool_parameters: dict[str, Any]) -> ToolInvokeMessage | list[ToolInvokeMessage]:
        """
        Invoke the SearXNG search tool.

        Args:
            tool_parameters (dict[str, Any]): The parameters for the tool invocation.

        Returns:
            ToolInvokeMessage | list[ToolInvokeMessage]: The result of the tool invocation.
        """
        host = self.runtime.credentials.get("searxng_base_url")
        if not host:
            raise Exception("SearXNG api is required")
        
        try:
            response = requests.get(
                host,
                params={
                    "q": tool_parameters.get("query"),
                    "time_range": tool_parameters.get("time_range", "day"),
                    "format": "json",
                    "categories": tool_parameters.get("search_type", "general"),
                },
                timeout=30  # 添加超时设置
            )
            
            if response.status_code != 200:
                return self.create_text_message(f"Error {response.status_code}: {response.text}")
            
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                return self.create_text_message(f"Invalid JSON response: {response.text}")
            
            res = response_data.get("results", [])
            if not res:
                return self.create_text_message(f"No results found for query: {tool_parameters.get('query')}")
            
            # 修复：安全地创建消息列表
            messages = []
            for i, item in enumerate(res):
                try:
                    # 验证item是否为有效字典
                    if not isinstance(item, dict):
                        messages.append(self.create_text_message(f"Result {i+1}: {str(item)}"))
                        continue
                    
                    # 清理和验证字典内容
                    cleaned_item = {}
                    for key, value in item.items():
                        # 确保键值对都是可序列化的
                        if isinstance(value, (str, int, float, bool, list, dict)) or value is None:
                            cleaned_item[key] = value
                        else:
                            cleaned_item[key] = str(value)
                    
                    # 创建JSON消息
                    json_message = self.create_json_message(cleaned_item)
                    messages.append(json_message)
                    
                except Exception as e:
                    # 降级处理：如果JSON消息创建失败，使用文本消息
                    error_msg = f"Result {i+1} (JSON creation failed): {str(item)[:200]}..."
                    messages.append(self.create_text_message(error_msg))
            
            return messages
            
        except requests.RequestException as e:
            return self.create_text_message(f"Request failed: {str(e)}")
        except Exception as e:
            return self.create_text_message(f"Unexpected error: {str(e)}")

