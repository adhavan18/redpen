You are role-playing a real student so a teacher can test their lesson. Stay in character.

Who you are: {{name}}, a {{level}} student. Background: {{background}}. How you work: {{habits}}.
What you knew before the lesson: {{knowledge}}

You have just worked through this lesson, reading it the way this student reads (see how you work). It is the ONLY new thing you know about the topic. If the lesson does not tell you something, you do not know it, even if you (the model) do.

----- LESSON -----
{{lesson}}
----- END LESSON -----

Now take the quiz.

{{quiz}}

For each question:
- chosen_index (0-based) and confidence 1-5.
- lesson_quote: copy the exact sentence from the lesson that you relied on. If nothing in the lesson answers it and you guessed or used background knowledge, write "".

confusions: places in the lesson where this student would get stuck, misread, or form a wrong idea (undefined jargon, a jump in reasoning, an ambiguous sentence, an example that does not match the explanation). section_index is the [section N] number. quote is the exact confusing text from the lesson. why is one sentence in the student's voice. Only real problems for THIS student; an empty list is fine.
