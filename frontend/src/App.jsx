
import { useState } from "react"; 
import { Copy, Code2, ExternalLink, LoaderCircle, Sparkles } from "lucide-react";
import "./App.css"; 

const API_URL = "http://127.0.0.1:8000/generate-test"; 

function App() {
  const [url, setUrl] = useState("");
  const [requirement, setRequirement] = useState(""); 
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null); 
  const [error, setError] = useState(""); 
  const [copied, setCopied] = useState(false); 

  async function handleGenerate(event) {
    event.preventDefault(); 
    setLoading(true); 
    setResult(null); 
    setError(""); 
    setCopied(false); 
    try {
      const response = await fetch(API_URL, {
        method: "POST", 
        headers: { "Content-Type": "application/json" }, 
        body: JSON.stringify({
          url: url.trim(), 
          requirement: requirement.trim(),
        }),
      });

      const data = await response.json();

      if (!response.ok || data.status !== "success") {
        const details = data.details;
        const detailMessage =
          details?.message ||
          details?.validation?.message ||
          data.message;

        throw new Error(detailMessage || "Test generation failed."); 
      }

      const validatedCode = data.validation?.test_code;

      if (!validatedCode || data.validation?.syntax_valid !== true) {
        throw new Error("The backend did not return syntactically validated code.");
      }

      setResult({
        code: validatedCode,
        language: data.generated_code?.language || "python", 
        framework: data.generated_code?.framework || "playwright",
        assumptions: data.generated_code?.assumptions || [], 
        limitations: data.generated_code?.limitations || [], 
        validation: data.validation, 
        url: data.url, 
      });
    } catch (err) {
      setError(
        err instanceof TypeError
          ? "Cannot connect to the backend. Ensure FastAPI is running on port 8000."
          : err.message || "Something went wrong."
      ); 
    } finally {
      setLoading(false); 
    }
  }

  async function handleCopy() {
    if (!result?.code) return; 

    try {
      await navigator.clipboard.writeText(result.code); 
      setCopied(true); 
      window.setTimeout(() => setCopied(false), 2000); 
    } catch {
      setError("Clipboard access failed. Please select and copy the code manually."); 
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="TestPilot AI home">
          <span className="brand-icon"><Code2 size={21} /></span>
          <span>TestPilot<span className="brand-accent"> AI</span></span>
        </a>
        <span className="phase-label"><span className="status-dot" /> AI Test Generator</span>
      </header>

      <section className="hero">
        <div className="eyebrow"><Sparkles size={15} /> FROM REQUIREMENT TO AUTOMATION</div>
        <h1>Turn your requirements into <span>test code.</span></h1>
        <p className="hero-description">
          Describe what you want to test. TestPilot AI explores the application
          and generates syntactically validated Playwright code.
        </p>
      </section>

      <section className="workspace">
        <form className="input-panel" onSubmit={handleGenerate}>
          <div className="panel-heading">
            <span className="step-number">01</span>
            <div>
              <h2>Configure your test</h2>
              <p>Tell us where to test and what to verify.</p>
            </div>
          </div>

          <label htmlFor="app-url">Application URL</label>
          <input
            id="app-url"
            type="url"
            placeholder="https://your-application.com"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            required
          />

          <label htmlFor="requirement">Testing requirement</label>
          <textarea
            id="requirement"
            placeholder={"Example: Log in using TEST_USERNAME and TEST_PASSWORD, then verify successful login."}
            value={requirement}
            onChange={(event) => setRequirement(event.target.value)}
            rows={7}
            required
          />

          <div className="form-note">
            <span className="status-dot" />
            Syntax validation and repair included
          </div>

          <button className="generate-button" type="submit" disabled={loading}>
            {loading ? (
              <>
                <LoaderCircle className="spin" size={18} />
                Generating your test...
              </>
            ) : (
              <>
                <Sparkles size={18} />
                Generate test code
              </>
            )}
          </button>

          {loading && (
            <p className="loading-note">
              Inspecting the application and generating code. This may take a minute or longer.
            </p>
          )}
        </form>

        <section className="output-panel">
          <div className="panel-heading output-heading">
            <span className="step-number">02</span>
            <div>
              <h2>Generated output</h2>
              <p>Your test code and generation details.</p>
            </div>
          </div>

          {error && (
            <div className="error-box" role="alert">
              <strong>Generation failed</strong>
              <p>{error}</p>
            </div>
          )}

          {!result && !error && (
            <div className="empty-state">
              <div className="empty-icon"><Code2 size={30} /></div>
              <h3>Your code will appear here</h3>
              <p>Enter an application URL and testing requirement to get started.</p>
            </div>
          )}

          {result && (
            <div className="result-content">
              <div className="result-toolbar">
                <div className="file-label">
                  <Code2 size={16} />
                  <span>test_generated.py</span>
                </div>
                <button className="copy-button" type="button" onClick={handleCopy}>
                  <Copy size={15} />
                  {copied ? "Copied!" : "Copy code"}
                </button>
              </div>

              <div className="code-meta">
                <span>{result.language}</span>
                <span>{result.framework}</span>
                <span className="valid-label">✓ Syntax valid</span>
              </div>

              <pre className="code-viewer"><code>{result.code}</code></pre>

              <div className="result-details">
                <div className="detail-heading">
                  <ExternalLink size={16} />
                  <h3>Target application</h3>
                </div>
                <a href={result.url} target="_blank" rel="noreferrer" className="target-link">
                  {result.url}
                </a>

                <h3>Assumptions</h3>
                {result.assumptions.length ? (
                  <ul>{result.assumptions.map((item, index) => <li key={index}>{item}</li>)}</ul>
                ) : <p className="muted-text">No assumptions provided.</p>}

                <h3>Limitations</h3>
                {result.limitations.length ? (
                  <ul>{result.limitations.map((item, index) => <li key={index}>{item}</li>)}</ul>
                ) : <p className="muted-text">No limitations provided.</p>}

                <p className="disclaimer">
                  Syntax validated. Runtime behavior and successful authentication are not verified by this result.
                </p>
              </div>
            </div>
          )}
        </section>
      </section>

      <footer className="footer">
        TestPilot AI <span>·</span> Requirement-driven test automation <span>·</span> Made with <span className="heart">♥</span> by <a href="https://www.linkedin.com/in/rohan-dhangar-02bb131b9/" target="_blank" style={{ textDecoration: 'none', color: '#a5b4fc' }}>Rohan Dhangar</a>
      </footer>
    </main>
  );
}

export default App;