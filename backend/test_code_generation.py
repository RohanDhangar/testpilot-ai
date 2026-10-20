
import asyncio  # What: async execution support; Why: हमारी services async हैं; How: main coroutine चलाने में मदद करता है।
import json  # What: readable JSON output; Why: generated result inspect करना है; How: dictionary को formatted JSON text में बदलता है।

from app.services.code_generation import code_genration  # What: generation service import; Why: इसी phase को test करना है; How: existing async function reuse करता है।
from app.services.requirement_analysis import requirement_analysis  # What: requirement service import; Why: actual test plan बनाना है; How: existing async function reuse करता है।

async def main():  # What: test workflow define करता है; Why: दोनों services क्रम में चलानी हैं; How: async function के अंदर await इस्तेमाल करते हैं।
    user_requirement = (  # What: initial user request; Why: पूरे backend workflow को test करना है; How: natural-language requirement pass करते हैं।
    "Open the application at https://qk.peoplestrong.com/ and check whether "  # What: target URL और task बताता है; Why: application login test करनी है; How: URL और objective specify करता है।
    "a user can log in successfully using credentials stored in environment "  # What: credential source बताता है; Why: real login test चाहिए; How: environment variables से credentials लेने को कहता है।
    "variables TEST_USERNAME and TEST_PASSWORD. Generate a Playwright test "  # What: expected test framework और variables बताता है; Why: generated code सही होना चाहिए; How: Playwright और variable names specify करता है।
    "that fills in the username and password, clicks Continue, and verifies "  # What: login actions बताता है; Why: केवल page open होना पर्याप्त नहीं; How: form submission और verification माँगता है।
    "whether login succeeded. Do not invent credentials or bypass CAPTCHA/MFA."  # What: safety और correctness constraints; Why: fake success और security bypass से बचना है; How: explicit boundaries देता है।
)  # What: requirement string complete करता है; Why: यही analysis का input होगा; How: multiline string को close करता है।
 # What: sample requirement; Why: simple scenario से generation test करना है; How: string को analysis service में भेजेंगे।
    analysis_result = await requirement_analysis(user_requirement)  # What: test plan generate करता है; Why: Code Generation को required structured input चाहिए; How: analysis function का result await करता है।
    print("\nREQUIREMENT ANALYSIS RESULT:\n")  # What: output heading; Why: phases के results अलग दिखाने हैं; How: terminal पर heading print करता है।
    print(json.dumps(analysis_result, indent=2, ensure_ascii=False))  # What: analysis result दिखाता है; Why: structure inspect करना है; How: dictionary को formatted JSON में बदलता है।

    if analysis_result.get("status") != "success":  # What: analysis status check; Why: failed plan पर generation नहीं करनी; How: status field compare करता है।
        print("\nStopping because requirement analysis failed.")  # What: failure message; Why: कारण स्पष्ट करना है; How: terminal पर message print करता है।
        return  # What: function रोकता है; Why: आगे की phase के लिए valid input नहीं है; How: main से बाहर निकलता है।

    result = await code_genration("https://qk.peoplestrong.com/", analysis_result)  # What: generation service call; Why: real snapshot और requirement से code generate करना है; How: URL और analysis result pass करता है।
    print("\nCODE GENERATION RESULT:\n")  # What: output heading; Why: generated phase का result अलग देखना है; How: terminal पर heading print करता है।
    print(json.dumps(result, indent=2, ensure_ascii=False))  # What: complete result दिखाता है; Why: generated code और limitations inspect करनी हैं; How: response को readable JSON में print करता है।

if __name__ == "__main__":  # What: direct execution check; Why: import करने पर test auto-run नहीं होना चाहिए; How: Python के __name__ value को check करता है।
    asyncio.run(main())  # What: async workflow start करता है; Why: coroutine execute करनी है; How: event loop के जरिए main चलाता है।
