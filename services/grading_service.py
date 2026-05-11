import json


def grade_exercise(exercise, user_answer):
    etype = exercise.get("type", "multiple_choice")
    score = 0
    correct = False
    feedback = ""

    if etype == "multiple_choice":
        try:
            user_idx = int(user_answer)
        except (ValueError, TypeError):
            user_idx = -1
        correct = (user_idx == exercise["answer"])
        score = 10 if correct else 0
        feedback = "回答正确！" if correct else f"回答错误。正确答案是：{exercise['options'][exercise['answer']]}"

    elif etype == "true_false":
        user_bool = str(user_answer).strip().lower()
        if user_bool in ("true", "1", "yes", "对", "正确"):
            user_bool = True
        elif user_bool in ("false", "0", "no", "错", "错误"):
            user_bool = False
        else:
            user_bool = None
        correct = (user_bool == exercise["answer"])
        score = 10 if correct else 0
        answer_text = "正确" if exercise["answer"] else "错误"
        feedback = "回答正确！" if correct else f"回答错误。正确答案是：{answer_text}"

    elif etype == "code_fill":
        user_ans = str(user_answer).strip()
        expected = str(exercise.get("answer", "")).strip()
        if isinstance(exercise.get("answer"), list):
            correct = any(user_ans.lower() == str(a).strip().lower() for a in exercise["answer"])
        else:
            correct = (user_ans.lower() == expected.lower())
        score = 10 if correct else 0
        feedback = "代码填写正确！" if correct else f"不正确。正确答案是：\n```\n{expected}\n```"

    elif etype == "programming":
        user_ans = str(user_answer).strip()
        ref_answer = str(exercise.get("answer", "")).strip()
        similarity = _text_similarity(user_ans, ref_answer)
        if similarity > 0.9:
            correct = True
            score = 10
            feedback = "代码基本正确！"
        elif similarity > 0.6:
            correct = True
            score = 7
            feedback = "代码思路正确，但与参考答案有差异，请查看解析。"
        elif similarity > 0.3:
            correct = False
            score = 4
            feedback = "部分正确，但核心逻辑有偏差。"
        else:
            correct = False
            score = 0
            feedback = "代码不正确，请参考解析重新尝试。"

    return {
        "correct": correct,
        "score": score,
        "feedback": feedback
    }


def _text_similarity(a, b):
    a_lines = {line.strip() for line in a.split("\n") if line.strip()}
    b_lines = {line.strip() for line in b.split("\n") if line.strip()}
    if not a_lines or not b_lines:
        return 0
    intersection = a_lines & b_lines
    union = a_lines | b_lines
    return len(intersection) / len(union)
