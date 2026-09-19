import { useEffect, useState } from "react";
import axios from "axios";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const API = "http://127.0.0.1:8000";

const emptyStats = {
  total_feedback: 0,
  active_insights: 0,
  high_priority: 0,
  strong_signals: 0,
  sources: 0,
};

function App() {
  const [stats, setStats] = useState(emptyStats);
  const [insights, setInsights] = useState([]);
  const [timeline, setTimeline] = useState([]);

  const [file, setFile] = useState(null);
  const [filename, setFilename] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [selectedInsight, setSelectedInsight] =
    useState(null);

  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    loadCurrentState();
  }, []);

  async function loadCurrentState() {
    try {
      const [statsResponse, insightsResponse, timelineResponse] =
        await Promise.all([
          axios.get(`${API}/api/stats`),
          axios.get(`${API}/api/insights`),
          axios.get(`${API}/api/timeline`),
        ]);

      setStats(
        statsResponse.data || emptyStats
      );

      setInsights(
        insightsResponse.data?.insights || []
      );

      setTimeline(
        timelineResponse.data?.timeline || []
      );

      if (
        insightsResponse.data?.dataset_loaded
      ) {
        setLoaded(true);
        setFilename(
          insightsResponse.data.filename
        );
      }
    } catch {
      setError(
        "Backend is not running. Start the FastAPI server."
      );
    }
  }

  function handleFileChange(event) {
    const selected = event.target.files?.[0];

    if (!selected) {
      return;
    }

    setFile(selected);
    setError("");
  }

  async function uploadFile() {
    if (!file) {
      setError("Please select a file first.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const formData = new FormData();

      formData.append("file", file);

      const response = await axios.post(
        `${API}/api/upload`,
        formData
      );

      const data = response.data;

      setStats(
        data.stats || emptyStats
      );

      setInsights(
        data.insights || []
      );

      setTimeline(
        data.timeline || []
      );

      setFilename(
        data.filename || file.name
      );

      setLoaded(true);

    } catch (err) {

      console.error(err);

      setError(
        err.response?.data?.detail ||
        "Upload failed."
      );

    } finally {
      setLoading(false);
    }
  }

  function getPriorityClass(priority) {
    const value =
      String(priority || "").toLowerCase();

    if (value === "high") {
      return "priority-high";
    }

    if (value === "medium") {
      return "priority-medium";
    }

    return "priority-low";
  }

  function getSignalClass(signal) {
    const value =
      String(signal || "").toLowerCase();

    if (
      value === "strong" ||
      value === "high"
    ) {
      return "signal-strong";
    }

    return "signal-normal";
  }

  return (
    <div className="app">

      {/* HEADER */}

      <header className="header">

        <div>
          <h1>VoC-Miner</h1>

          <p>
            Voice-of-Customer Intelligence
          </p>
        </div>

        <div className="header-status">
          <span
            className={
              loaded
                ? "status-dot active"
                : "status-dot"
            }
          />

          {loaded
            ? "Dataset loaded"
            : "Waiting for dataset"}
        </div>

      </header>


      <main className="container">

        {/* UPLOAD */}

        <section className="upload-section">

          <div className="upload-title">

            <h2>
              Analyze Customer Feedback
            </h2>

            <p>
              Upload customer feedback in CSV,
              Excel, JSON, TXT, DOCX or PDF format.
            </p>

          </div>

          <div className="upload-controls">

            <label className="file-input">

              <input
                type="file"
                accept=".csv,.xlsx,.xls,.json,.txt,.docx,.pdf"
                onChange={handleFileChange}
              />

              <span>
                {file
                  ? file.name
                  : "Choose feedback file"}
              </span>

            </label>

            <button
              className="upload-button"
              onClick={uploadFile}
              disabled={!file || loading}
            >
              {loading
                ? "Analyzing..."
                : "Analyze Feedback"}
            </button>

          </div>

          <div className="supported-formats">
            Supported:
            <span>CSV</span>
            <span>XLSX</span>
            <span>JSON</span>
            <span>TXT</span>
            <span>DOCX</span>
            <span>PDF</span>
          </div>

          {error && (
            <div className="error">
              {error}
            </div>
          )}

        </section>


        {/* EMPTY STATE */}

        {!loaded && !loading && (
          <section className="empty-state">

            <div className="empty-icon">
              ◇
            </div>

            <h2>
              No feedback dataset loaded
            </h2>

            <p>
              Upload a customer feedback file
              to discover recurring problems,
              evidence strength and priority.
            </p>

          </section>
        )}


        {/* DASHBOARD */}

        {loaded && (

          <>

            {/* DATASET INFO */}

            <section className="dataset-banner">

              <div>
                <span className="label">
                  CURRENT DATASET
                </span>

                <strong>
                  {filename}
                </strong>
              </div>

              <div>
                <span className="label">
                  FEEDBACK ENTRIES
                </span>

                <strong>
                  {stats.total_feedback}
                </strong>
              </div>

            </section>


            {/* STATS */}

            <section className="stats-grid">

              <div className="stat-card">

                <span className="stat-label">
                  FEEDBACK
                </span>

                <strong>
                  {stats.total_feedback}
                </strong>

                <small>
                  analyzed entries
                </small>

              </div>


              <div className="stat-card">

                <span className="stat-label">
                  INSIGHTS
                </span>

                <strong>
                  {stats.active_insights}
                </strong>

                <small>
                  recurring patterns
                </small>

              </div>


              <div className="stat-card">

                <span className="stat-label">
                  HIGH PRIORITY
                </span>

                <strong>
                  {stats.high_priority}
                </strong>

                <small>
                  requiring attention
                </small>

              </div>


              <div className="stat-card">

                <span className="stat-label">
                  STRONG SIGNALS
                </span>

                <strong>
                  {stats.strong_signals}
                </strong>

                <small>
                  supported by evidence
                </small>

              </div>


              <div className="stat-card">

                <span className="stat-label">
                  SOURCES
                </span>

                <strong>
                  {stats.sources}
                </strong>

                <small>
                  feedback channels
                </small>

              </div>

            </section>


            {/* TIMELINE */}

            {timeline.length > 0 && (

              <section className="panel">

                <div className="panel-header">

                  <div>
                    <h2>
                      Feedback Timeline
                    </h2>

                    <p>
                      Volume of customer feedback
                      across the uploaded dataset.
                    </p>
                  </div>

                </div>

                <div className="chart">

                  <ResponsiveContainer
                    width="100%"
                    height={280}
                  >

                    <BarChart
                      data={timeline}
                    >

                      <CartesianGrid
                        strokeDasharray="3 3"
                      />

                      <XAxis
                        dataKey="date"
                      />

                      <YAxis
                        allowDecimals={false}
                      />

                      <Tooltip />

                      <Bar
                        dataKey="count"
                        name="Feedback"
                      />

                    </BarChart>

                  </ResponsiveContainer>

                </div>

              </section>
            )}


            {/* INSIGHTS */}

            <section className="insights-section">

              <div className="section-heading">

                <div>
                  <h2>
                    Customer Pain Points
                  </h2>

                  <p>
                    Recurring problems discovered
                    from the uploaded feedback.
                  </p>
                </div>

                <span className="count-badge">
                  {insights.length}
                </span>

              </div>


              {insights.length === 0 ? (

                <div className="no-insights">
                  No recurring insights were detected
                  in this dataset.
                </div>

              ) : (

                <div className="insights-grid">

                  {insights.map(
                    (insight, index) => (

                      <article
                        className="insight-card"
                        key={
                          insight.cluster ??
                          index
                        }
                      >

                        <div className="insight-top">

                          <span
                            className={
                              `priority-badge ${
                                getPriorityClass(
                                  insight.priority
                                )
                              }`
                            }
                          >
                            {insight.priority ||
                              "LOW"}
                          </span>

                          <span
                            className={
                              `signal-badge ${
                                getSignalClass(
                                  insight.signal_strength
                                )
                              }`
                            }
                          >
                            {insight.signal_strength ||
                              "NORMAL"}
                          </span>

                        </div>


                        <h3>
                          {insight.problem_summary ||
                            insight.problem ||
                            "Customer issue"}
                        </h3>


                        <p className="pattern">
                          {insight.observed_pattern ||
                            ""}
                        </p>


                        <div className="impact">

                          <strong>
                            Customer impact
                          </strong>

                          <p>
                            {insight.customer_impact ||
                              "Potential negative customer experience."}
                          </p>

                        </div>


                        <div className="evidence-grid">

                          <div>
                            <span>
                              Evidence
                            </span>

                            <strong>
                              {insight.evidence_count ??
                                0}
                            </strong>
                          </div>

                          <div>
                            <span>
                              Negative
                            </span>

                            <strong>
                              {insight.negative_ratio != null
                                ? `${(
                                    insight.negative_ratio *
                                    100
                                  ).toFixed(0)}%`
                                : "—"}
                            </strong>
                          </div>

                          <div>
                            <span>
                              Sources
                            </span>

                            <strong>
                              {insight.source_count ??
                                insight.sources?.length ??
                                0}
                            </strong>
                          </div>

                          <div>
                            <span>
                              Priority
                            </span>

                            <strong>
                              {insight.priority_score != null
                                ? Number(
                                    insight.priority_score
                                  ).toFixed(2)
                                : "—"}
                            </strong>
                          </div>

                        </div>


                        <div className="insight-footer">

                          <span>
                            {insight.first_seen ||
                              "—"}
                            {" → "}
                            {insight.last_seen ||
                              "—"}
                          </span>

                          <button
                            onClick={() =>
                              setSelectedInsight(
                                insight
                              )
                            }
                          >
                            View Evidence →
                          </button>

                        </div>

                      </article>

                    )
                  )}

                </div>

              )}

            </section>

          </>

        )}

      </main>


      {/* EVIDENCE MODAL */}

      {selectedInsight && (

        <div
          className="modal-overlay"
          onClick={() =>
            setSelectedInsight(null)
          }
        >

          <div
            className="modal"
            onClick={(event) =>
              event.stopPropagation()
            }
          >

            <div className="modal-header">

              <div>

                <span className="modal-label">
                  TRACEABLE EVIDENCE
                </span>

                <h2>
                  {selectedInsight.problem_summary ||
                    selectedInsight.problem}
                </h2>

              </div>

              <button
                className="close-button"
                onClick={() =>
                  setSelectedInsight(null)
                }
              >
                ×
              </button>

            </div>


            <div className="modal-summary">

              <div>
                <span>
                  Evidence score
                </span>

                <strong>
                  {selectedInsight.evidence_score != null
                    ? Number(
                        selectedInsight.evidence_score
                      ).toFixed(2)
                    : "—"}
                </strong>
              </div>

              <div>
                <span>
                  Severity
                </span>

                <strong>
                  {selectedInsight.severity ||
                    "—"}
                </strong>
              </div>

              <div>
                <span>
                  Sources
                </span>

                <strong>
                  {selectedInsight.sources?.join(
                    ", "
                  ) || "—"}
                </strong>
              </div>

            </div>


            <div className="evidence-list">

              <h3>
                Supporting customer feedback
              </h3>

              {(
                selectedInsight.supporting_feedback ||
                []
              ).map(
                (feedback, index) => (

                  <div
                    className="feedback-item"
                    key={index}
                  >

                    <div className="feedback-meta">

                      <span>
                        {feedback.source ||
                          "unknown"}
                      </span>

                      <span>
                        {feedback.date ||
                          ""}
                      </span>

                    </div>

                    <p>
                      {feedback.text ||
                        feedback}
                    </p>

                  </div>

                )
              )}

            </div>

          </div>

        </div>

      )}

    </div>
  );
}

export default App;