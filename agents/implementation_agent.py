import os

DEBUG = False
class ImplementationAgent:
    def __init__(self, name, client, prompt="", gen_kwargs=None):
        self.name = name
        self.client = client
        self.prompt = prompt
        self.gen_kwargs = gen_kwargs or {
            "model": "gpt-4o",
            "temperature": 0.2
        }
        self.prompt = """\
You are a software developer, tasked with implementing the plan described below.
"""

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
    async def execute(self, message_history):
        import os

        # Update the prompt with the plan content
        self.prompt += """
            The Markdown will indicate which steps are incomplete and which are complete.Implement the first step in the plan from the markdown file that has not been completed yet. 
            Implement the step and update the plan.md file by marking the step as complete. The implementation should output html and css files.
            Once you have the updated plan.md, html and css files, call the updateArtifacts function once for each file, each call should have the file name and contents of that file only.
            
            """
        sys_prompt = self._build_system_prompt()
        # Print the system prompt
        if DEBUG:
            print("System Prompt:")
            print(sys_prompt)
        # Call the parent class's execute method
        return sys_prompt