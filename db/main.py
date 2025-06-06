import asyncio
import traceback
import yaml
from agents import (
    Agent, ModelSettings, ModelProvider, OpenAIChatCompletionsModel,
    set_tracing_disabled, RunConfig, Runner
)
from agents.mcp import MCPServerStdio
from openai import AsyncOpenAI


API_KEY = ""
BASE_URL = "" 
MODEL_NAME = "" 

set_tracing_disabled(True)
client = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)

class DkModelProvider(ModelProvider):
    def get_model(self, model_name: str):
        return OpenAIChatCompletionsModel(model=model_name or MODEL_NAME, openai_client=client)

model_provider = DkModelProvider()

# 2. 连接本地MCP数据库工具
async def main():

    db_mcp_server = MCPServerStdio(
    name="dbutils",
    params={
        "command": "python",
        "args": [
            "-m", "src.mcp_dbutils",
            "--config",
            "examples/config.yaml"
        ],
        "env": {}
    },
    cache_tools_list=True
)

    try:
        print("正在连接本地MCP数据库工具服务...")
        await db_mcp_server.connect()
        print("连接成功！")

        tools = await db_mcp_server.list_tools()
        print(f"数据库MCP服务可用工具（共{len(tools)}个）：")
        # for tool in tools:
        #     print(f"- 工具名称: {tool['name']}")
        #     print(f"  描述: {tool.get('description', '无')}")
        #     print(f"  输入参数: {tool.get('parameters', {})}")
        #     print("-" * 40)
        for tool in tools:
            print(f"- 工具名称: {tool.name}")
            print(f"  描述: {getattr(tool, 'description', '无')}")
            print(f"  输入参数: {getattr(tool, 'parameters', {})}")
            print("-" * 40)

        # 3. 构建智能数据库分析Agent
        db_agent = Agent(
            name="DBSmartAgent",
            instructions="""
你是数据库分析专家。用户会用自然语言描述需求，你需要调用数据库MCP工具完成如下任务：
1. 自动分析数据库结构（如列出所有表、字段、主键等）。
2. 根据用户需求自动生成只读SQL，并调用MCP工具执行。
3. 以结构化、易懂的中文解释查询结果。
4. 不允许任何写操作。
""",
            mcp_servers=[db_mcp_server],
            model=model_provider.get_model(MODEL_NAME),
            model_settings=ModelSettings(
                temperature=0.2,
                top_p=0.9,
                tool_choice="auto"
            )
        )

        # 4. 命令行交互
        while True:
            user_query = input("\n请输入数据库分析/查询需求（quit退出）：").strip()
            if user_query.lower() in ["quit", "exit"]:
                print("感谢使用，再见！")
                break
            if not user_query:
                print("输入不能为空")
                continue

            print("正在分析并执行，请稍候...")
            result = await Runner.run(
                db_agent,
                input=user_query,
                max_turns=10,
                run_config=RunConfig(trace_include_sensitive_data=False)
            )
            print("\n【分析结果】")
            print(result.final_output if hasattr(result, "final_output") else result)

    except Exception as e:
        print(f"发生异常: {e}")
        traceback.print_exc()
    finally:
        await db_mcp_server.cleanup()
        print("MCP数据库工具服务已关闭。")

if __name__ == "__main__":
    with open("examples/config.yaml", "r", encoding="utf-8") as f:
        print(yaml.safe_load(f))
    asyncio.run(main())

# 所有数据库相关工具调用，必须显式传递 config.yaml 中的连接名（如 localhost_3306），参数类型要与工具描述一致。


# 否列出我数据库中 的所有表？
# users表的结构是什么？

# 过去近三年有多少客户进行了存款？

# UserID为4。通过近一年的存款和取款行为，UserID为4的消费潜力怎么样

# log 趋势，这个月和上个月内存实际情况变化+