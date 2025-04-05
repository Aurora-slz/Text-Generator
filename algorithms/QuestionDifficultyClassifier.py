import json
import os
import pandas as pd
from utils import LocalModelGenerator, APIGenerator_aisuite, APIGenerator_request
from utils.Prompts import QuestionCategoryPrompt

class QuestionCategoryClassifier:
    def __init__(self, config):
        """
        Initialize the QuestionCategoryClassifier with the provided configuration.
        """
        self.config = config
        self.prompts = QuestionCategoryPrompt()

        # Ensure the necessary configuration keys are provided
        self.input_file = self.config.get("input_file")
        self.output_file = self.config.get("output_file")
        self.input_key = self.config.get("input_key", "question")  # default key for question input
        self.output_key = self.config.get("output_key", "classification_result")  # default output key

        # Validate that input_file and output_file are provided
        if not self.input_file or not self.output_file:
            raise ValueError("Both input_file and output_file must be specified in the config.")

        # Initialize the model
        self.model = self.__init_model__()

    def __init_model__(self):
        """
        Initialize the model generator based on the configuration.
        """
        generator_type = self.config.get("generator_type", "local").lower()
        
        if generator_type == "local":
            return LocalModelGenerator(self.config)
        elif generator_type == "aisuite":
            return APIGenerator_aisuite(self.config)
        elif generator_type == "request":
            return APIGenerator_request(self.config)
        else:
            raise ValueError(f"Invalid generator type: {generator_type}")

    def _reformat_prompt(self, dataframe):
        """
        Reformat the prompts in the dataframe to generate questions.
        """
        # Check if input_key is in the dataframe
        if self.input_key not in dataframe.columns:
            key_list = dataframe.columns.tolist()
            raise ValueError(f"input_key: {self.input_key} not found in the dataframe. Available keys: {key_list}")

        formatted_prompts = []
        for text in dataframe[self.input_key]:
            used_prompt = self.prompts.question_synthesis_prompt(text)
            formatted_prompts.append(used_prompt.strip())

        return formatted_prompts

    def run(self):
        """
        Run the question category classification process.
        """
        try:
            # Read the input file
            dataframe = pd.read_json(self.input_file, lines=True)

            # Reformat the prompts for classification
            formatted_prompts = self._reformat_prompt(dataframe)

            # Generate responses using the model
            responses = self.model.generate_text_from_input(formatted_prompts)

            # Parse and store the classification results
            for idx, (row, classification_str) in enumerate(zip(dataframe.iterrows(), responses)):
                try:
                    classification = json.loads(classification_str) if classification_str else {}

                    dataframe.at[idx, "primary_category"] = classification.get("primary_category", "")
                    dataframe.at[idx, "secondary_category"] = classification.get("secondary_category", "")

                except json.JSONDecodeError:
                    print(f"[警告] JSON 解析失败，收到的分类数据: {classification_str}")
                except Exception as e:
                    print(f"[错误] 解析分类结果失败: {e}")

            # Ensure output_key doesn't already exist in the dataframe
            if self.output_key in dataframe.columns:
                raise ValueError(f"Found {self.output_key} in the dataframe, which would overwrite an existing column. Please use a different output_key.")

            # Ensure output directory exists
            output_dir = os.path.dirname(self.output_file)
            os.makedirs(output_dir, exist_ok=True)

            # Save DataFrame to the output file
            dataframe.to_json(self.output_file, orient="records", lines=True, force_ascii=False)

            print(f"Classification results saved to {self.output_file}")

        except Exception as e:
            print(f"[错误] 处理过程中发生异常: {e}")
