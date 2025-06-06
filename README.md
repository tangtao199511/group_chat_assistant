**Feature Document: AI Group Chat Assistant**
by Tao Tang, Surrey Academy for Blockchain and Metaverse Applications

**Developed Features:**
The AI Group Chat Assistant integrates AI capabilities with the Luffa messaging bot, allowing the AI to interpret user instructions, read recent chat history, and generate responses based on both the chat context and the model’s internal knowledge. Example queries include:

1. “List the to-do items discussed in the group chat.”
2. “Summarize the last 3 messages.”
3. “Based on the last hour of conversation, what should I do tomorrow?”

**Implementation Overview:**
The assistant operates through four layers:

1. **User Message Intake Layer**
2. **AI-Driven Natural Language to Structured Query Processor**
3. **AI Reasoning and Response Generator**
4. **Response Delivery Back to Luffa**

The core design involves a **two-tiered AI mechanism**:

* **First-layer AI** handles parsing time-based constraints from the user’s instruction (e.g., “last hour,” “last 10 messages,” “today's conversation”), converts these into formatted filters, and retrieves the relevant message subset from chat history.

* This filtering step is essential to maintain response quality, especially given the potentially massive volume of messages in group chats. Without it, the prompt context could overwhelm the AI and degrade its output.

* **Second-layer AI** uses the filtered messages as part of its prompt to generate meaningful responses based on user queries.

**Performance Considerations:**
To optimize both speed and quality:

* The **first-layer AI** focuses solely on extracting time intervals and can therefore use a lightweight LLM such as `qwen3:0.6b`, enhanced with the `/no_think` parameter for faster output.
* The **second-layer AI** is quality-critical. For simpler tasks, `qwen3:1.7b` is sufficient. If server capacity allows, a more powerful 7B model is recommended for improved accuracy and fluency.

Empirical testing confirms this architecture yields effective performance and relevant responses.

**Implementation Details:**

1. **Trigger Mechanism:**
   The assistant activates when it is explicitly mentioned via @ assistant in the group chat. This design ensures precise invocation of the assistant only when needed.

2. **Message Filtering:**
   During analysis, all messages that contain @ assistant are automatically excluded. Including these in the prompt was found to introduce ambiguity during testing.

3. **Chat Log Storage:**
   Currently, all chat records are stored in JSON format on the server. If the system expands, we may coordinate with the Luffa technical team to improve the underlying data storage architecture.

**Requested Support from Luffa Team:**
At present, the assistant supports only text-based message input and output. We kindly request that the Luffa application team provide APIs for file and voice message access. This would allow the assistant to handle queries such as “Summarize the two documents I received,” enabling a broader range of productivity tasks.
