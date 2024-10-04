import os
import chainlit as cl

DEBUG = False

class Agent:
    """
    Base class for all agents.
    """

    tools = [
        {
            "type": "function",
            "function": {
                "name": "updateArtifact",
                "description": "Update an artifact file which is HTML, CSS, or markdown with the given contents.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "The name of the file to update.",
                        },
                        "contents": {
                            "type": "string",
                            "description": "The markdown, HTML, or CSS contents to write to the file.",
                        },
                    },
                    "required": ["filename", "contents"],
                    "additionalProperties": False,
                },
            }
        },
        {
            "type": "function",
            "function": {
                "name": "callAgent",
                "description": "Instantiates an agent with a given name. For example, for implementation_agent, call callAgent(agent_name='implementation_agent')",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "agent_name": {
                            "type": "string",
                            "description": "The name of the Agent to instantiate.",
                        }
                    },
                    "required": ["agent_name"],
                    "additionalProperties": False,
                },
            }
        }
    ]

    def __init__(self, name, client, prompt="", gen_kwargs=None, implementation_agent=None):
        self.name = name
        self.client = client
        self.prompt = prompt
        self.gen_kwargs = gen_kwargs or {
            "model": "gpt-4o",
            "temperature": 0.2
        }
        self.implementation_agent = implementation_agent
        if DEBUG:
            print("DEBUG: implementation_agent:")
            print("type:", type(self.implementation_agent))
            print("value:", self.implementation_agent)   
    
    async def call_agent(self, agent_name, message_history):
        """
        Calls another agent with the given name and message history.
        """
        # Create a new message history for the called agent
        called_agent_message_history = message_history.copy()
        if DEBUG:
            print("DEBUG: agent_name:")
            print("agent_name:", agent_name)
        if agent_name == "implementation_agent":
            print("DEBUG: icalling mplementation_prompt:")
            implementation_prompt = await self.implementation_agent.execute(called_agent_message_history)
            message_history.append({
            "role": "system",
            "content": implementation_prompt
            })
            if DEBUG:
                print("DEBUG: callign execute for implementation_agent")
            return await self.execute(message_history)

    async def execute(self, message_history):
        """
        Executes the agent's main functionality.

        Note: probably shouldn't couple this with chainlit, but this is just a prototype.
        """
        copied_message_history = message_history.copy()

        # Check if the first message is a system prompt
        if copied_message_history and copied_message_history[0]["role"] == "system":
            # Replace the system prompt with the agent's prompt
            copied_message_history[0] = {"role": "system", "content": self._build_system_prompt()}
        else:
            # Insert the agent's prompt at the beginning
            copied_message_history.insert(0, {"role": "system", "content": self._build_system_prompt()})

        response_message = cl.Message(content="")
        await response_message.send()

        stream = await self.client.chat.completions.create(messages=copied_message_history, stream=True, tools=self.tools, tool_choice="auto", **self.gen_kwargs)

        function_name = ""
        arguments = ""
        function_calls = {}
        async for part in stream:
            if part.choices[0].delta.tool_calls:
                for tool_call in part.choices[0].delta.tool_calls:
                    if tool_call.index is not None:
                        if tool_call.index not in function_calls:
                            function_calls[tool_call.index] = {"name": "", "arguments": ""}
                        
                        if tool_call.function.name:
                            function_calls[tool_call.index]["name"] += tool_call.function.name
                        
                        if tool_call.function.arguments:
                            function_calls[tool_call.index]["arguments"] += tool_call.function.arguments
 
            if token := part.choices[0].delta.content or "":
                await response_message.stream_token(token)        
        # Print function_calls
        if DEBUG:
            print("DEBUG: function_calls:")
            print("type:", type(function_calls))
            print("value:", function_calls)
        for index, function_call in function_calls.items():
            function_name = function_call["name"]
            arguments = function_call["arguments"]
            if DEBUG:
                print("DEBUG: function_name:")
                print("type:", type(function_name))
                print("value:", function_name)
                print("DEBUG: arguments:")
                print("type:", type(arguments))
                print("value:", arguments)
            
            if function_name == "updateArtifact":
                import json
                
                arguments_dict = json.loads(arguments)
                filename = arguments_dict.get("filename")
                contents = arguments_dict.get("contents")
                
                if filename and contents:
                    os.makedirs("artifacts", exist_ok=True)
                    with open(os.path.join("artifacts", filename), "w") as file:
                        file.write(contents)
                    
                    # Add a message to the message history
                    message_history.append({
                        "role": "system",
                        "content": f"The artifact '{filename}' was updated."
                    })

                    stream = await self.client.chat.completions.create(messages=message_history, stream=True, **self.gen_kwargs)
                    async for part in stream:
                        if token := part.choices[0].delta.content or "":
                            await response_message.stream_token(token)  
                
            elif function_name == "callAgent":
                import json
                arguments_dict = json.loads(arguments)
                agent_name = arguments_dict.get("agent_name")
                    
                if agent_name:
                    await self.call_agent(agent_name, message_history)

        else:
            if DEBUG:
                print("No tool call")

        await response_message.update()

        return response_message.content

    def _build_system_prompt(self):
        """
        Builds the system prompt including the agent's prompt and the contents of the artifacts folder.
        """
        artifacts_content = "<ARTIFACTS>\n"
        artifacts_dir = "artifacts"

        if os.path.exists(artifacts_dir) and os.path.isdir(artifacts_dir):
            for filename in os.listdir(artifacts_dir):
                file_path = os.path.join(artifacts_dir, filename)
                if os.path.isfile(file_path):
                    with open(file_path, "r") as file:
                        file_content = file.read()
                        artifacts_content += f"<FILE name='{filename}'>\n{file_content}\n</FILE>\n"
        
        artifacts_content += "</ARTIFACTS>"

        return f"{self.prompt}\n{artifacts_content}"