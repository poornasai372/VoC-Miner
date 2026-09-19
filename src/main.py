import pandas as pd
import numpy as np
import re

from sentence_transformers import SentenceTransformer
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity
from transformers import pipeline


# ==========================================
# 1. Load customer feedback
# ==========================================

def analyze_feedback(csv_path="data/feedback.csv"):

    df = pd.read_csv(csv_path)

    df["date"] = pd.to_datetime(df["date"])

    print("Number of feedback entries:", len(df))


    # ==========================================
    # 2. Sentiment analysis
    # ==========================================

    print("\nLoading sentiment model...")

    sentiment_model = pipeline(
        "sentiment-analysis",
        model="distilbert-base-uncased-finetuned-sst-2-english"
    )

    sentiment_results = sentiment_model(
        df["text"].tolist()
    )

    df["sentiment"] = [
        result["label"].lower()
        for result in sentiment_results
    ]

    df["sentiment_score"] = [
        result["score"]
        for result in sentiment_results
    ]


    # ==========================================
    # 3. Create semantic embeddings
    # ==========================================

    print("\nCreating embeddings...")

    embedding_model = SentenceTransformer(
        "all-MiniLM-L6-v2"
    )

    embeddings = embedding_model.encode(
        df["text"].tolist(),
        normalize_embeddings=True
    )

    print("Embedding shape:", embeddings.shape)


    # ==========================================
    # 4. Semantic clustering
    # ==========================================

    cluster_model = DBSCAN(
        eps=0.35,
        min_samples=2,
        metric="cosine"
    )

    df["cluster"] = cluster_model.fit_predict(
        embeddings
    )


    # ==========================================
    # 5. Severity detection
    # ==========================================

    high_severity_words = [
        "crash",
        "crashes",
        "crashing",
        "freeze",
        "freezes",
        "freezing",
        "cannot",
        "can't",
        "unable",
        "failure",
        "fails",
        "failed",
        "broken",
        "unreliable"
    ]

    medium_severity_words = [
        "slow",
        "painfully",
        "frustrating",
        "difficult",
        "confusing",
        "extremely",
        "forever",
        "too many",
        "too long",
        "takes too long"
    ]


    def detect_severity(text):

        text_lower = text.lower()

        # HIGH: functional failure
        for word in high_severity_words:

            if word in text_lower:
                return "HIGH", 1.0

        # HIGH: measurable delay
        if re.search(
            r"\b\d+\s*(day|days|week|weeks|hour|hours)\b",
            text_lower
        ):
            return "HIGH", 1.0

        if "several days" in text_lower:
            return "HIGH", 1.0

        if "almost a week" in text_lower:
            return "HIGH", 1.0

        if "days" in text_lower:
            return "HIGH", 1.0

        if "weeks" in text_lower:
            return "HIGH", 1.0

        # MEDIUM: strong inconvenience
        for word in medium_severity_words:

            if word in text_lower:
                return "MEDIUM", 0.6

        # LOW
        return "LOW", 0.3


    severity_results = [
        detect_severity(text)
        for text in df["text"]
    ]

    df["severity"] = [
        result[0]
        for result in severity_results
    ]

    df["severity_score"] = [
        result[1]
        for result in severity_results
    ]


    # ==========================================
    # 6. Insight explanation
    # ==========================================

    def generate_problem_summary(cluster_feedback):

        texts = cluster_feedback["text"].tolist()

        combined_text = " ".join(texts).lower()


        # --------------------------------------
        # Document upload problem
        # --------------------------------------

        if (
            "upload" in combined_text
            and (
                "pdf" in combined_text
                or "document" in combined_text
            )
            and (
                "crash" in combined_text
                or "freeze" in combined_text
            )
        ):
            return (
                "PDF and document uploads are causing "
                "the application to crash or freeze."
            )


        # --------------------------------------
        # Application loading problem
        # --------------------------------------

        if (
            (
                "load" in combined_text
                or "opening" in combined_text
                or "start" in combined_text
            )
            and "slow" in combined_text
        ):
            return (
                "Customers are experiencing slow "
                "application startup and loading times."
            )


        # --------------------------------------
        # Support response problem
        # --------------------------------------

        if (
            "support" in combined_text
            and (
                "days" in combined_text
                or "week" in combined_text
                or "reply" in combined_text
                or "response" in combined_text
            )
        ):
            return (
                "Customers are experiencing long "
                "customer-support response times."
            )


        # --------------------------------------
        # Report export problem
        # --------------------------------------

        if (
            (
                "export" in combined_text
                or "download" in combined_text
            )
            and (
                "fail" in combined_text
                or "failure" in combined_text
                or "cannot" in combined_text
                or "unable" in combined_text
                or "error" in combined_text
                or "crash" in combined_text
            )
        ):
            return (
                "Customers are experiencing failures "
                "when exporting or downloading reports."
            )


        # --------------------------------------
        # Generic fallback
        # --------------------------------------

        return (
            "Customers are repeatedly reporting "
            "a similar product problem."
        )


    def generate_observed_pattern(cluster_feedback):

        sources = sorted(
            cluster_feedback["source"]
            .unique()
            .tolist()
        )

        texts = cluster_feedback["text"].tolist()

        combined_text = " ".join(texts).lower()

        source_text = ", ".join(sources)


        # Document upload

        if (
            "upload" in combined_text
            and (
                "crash" in combined_text
                or "freeze" in combined_text
            )
        ):
            return (
                f"The problem repeatedly appears during "
                f"document/PDF uploads and is reported across "
                f"{source_text}."
            )


        # Application loading

        if (
            "slow" in combined_text
            and (
                "load" in combined_text
                or "opening" in combined_text
                or "start" in combined_text
            )
        ):
            return (
                f"The same startup performance problem appears "
                f"repeatedly across {source_text}."
            )


        # Customer support

        if (
            "support" in combined_text
            and (
                "days" in combined_text
                or "week" in combined_text
                or "response" in combined_text
                or "reply" in combined_text
            )
        ):
            return (
                f"Customers report delayed support responses "
                f"across {source_text}."
            )


        # Report exports

        if (
            (
                "export" in combined_text
                or "download" in combined_text
            )
            and (
                "fail" in combined_text
                or "failure" in combined_text
                or "cannot" in combined_text
                or "unable" in combined_text
                or "error" in combined_text
                or "crash" in combined_text
            )
        ):
            return (
                f"Report export or download failures "
                f"recur across {source_text}."
            )


        return (
            f"Similar feedback is recurring across "
            f"{source_text}."
        )


    def generate_customer_impact(cluster_feedback):

        texts = cluster_feedback["text"].tolist()

        combined_text = " ".join(texts).lower()


        # Upload failures

        if (
            "upload" in combined_text
            and (
                "crash" in combined_text
                or "freeze" in combined_text
            )
        ):
            return (
                "Customers may be unable to reliably "
                "upload their documents."
            )


        # Loading

        if (
            "slow" in combined_text
            and (
                "load" in combined_text
                or "opening" in combined_text
                or "start" in combined_text
            )
        ):
            return (
                "Customers experience delays before they "
                "can begin using the application."
            )


        # Support

        if (
            "support" in combined_text
            and (
                "days" in combined_text
                or "week" in combined_text
                or "response" in combined_text
            )
        ):
            return (
                "Customers may have to wait several days "
                "before receiving assistance."
            )


        # Report exports

        if (
            (
                "export" in combined_text
                or "download" in combined_text
            )
            and (
                "fail" in combined_text
                or "failure" in combined_text
                or "cannot" in combined_text
                or "unable" in combined_text
                or "error" in combined_text
                or "crash" in combined_text
            )
        ):
            return (
                "Customers may be unable to successfully "
                "export or download completed reports."
            )


        return (
            "The recurring issue is creating friction "
            "for customers."
        )


    # ==========================================
    # 7. Analyze pain points
    # ==========================================

    pain_points = []


    for cluster_id in sorted(df["cluster"].unique()):

        # Ignore noise
        if cluster_id == -1:
            continue

        cluster_feedback = df[
            df["cluster"] == cluster_id
        ].copy()

        total_count = len(cluster_feedback)


        # ======================================
        # Negative evidence
        # ======================================

        negative_count = (
            cluster_feedback["sentiment"] == "negative"
        ).sum()

        negative_ratio = (
            negative_count / total_count
        )

        # Ignore positive-only clusters
        if negative_count == 0:
            continue


        # ======================================
        # Frequency score
        # ======================================

        all_cluster_sizes = (
            df[df["cluster"] != -1]
            .groupby("cluster")
            .size()
        )

        max_frequency = all_cluster_sizes.max()

        frequency_score = (
            total_count / max_frequency
        )


        # ======================================
        # Source diversity
        # ======================================

        source_count = (
            cluster_feedback["source"]
            .nunique()
        )

        total_source_types = (
            df["source"].nunique()
        )

        source_diversity = (
            source_count / total_source_types
        )


        # ======================================
        # Temporal recurrence
        # ======================================

        first_seen = (
            cluster_feedback["date"].min()
        )

        last_seen = (
            cluster_feedback["date"].max()
        )

        time_span_days = (
            last_seen - first_seen
        ).days

        dataset_span = (
            df["date"].max()
            - df["date"].min()
        ).days

        if dataset_span > 0:

            temporal_score = (
                time_span_days / dataset_span
            )

        else:

            temporal_score = 0


        # ======================================
        # Average severity
        # ======================================

        severity_score = (
            cluster_feedback["severity_score"]
            .mean()
        )


        # ======================================
        # Evidence score
        # ======================================

        evidence_score = (
            0.25 * frequency_score
            + 0.25 * negative_ratio
            + 0.15 * source_diversity
            + 0.15 * temporal_score
            + 0.20 * severity_score
        )


        # ======================================
        # Signal strength
        # ======================================

        if evidence_score >= 0.70:

            signal_strength = "STRONG SIGNAL"

        else:

            signal_strength = "WEAK SIGNAL"


        # ======================================
        # Priority score
        # ======================================

        priority_score = (
            0.50 * evidence_score
            + 0.50 * severity_score
        )


        # ======================================
        # Priority level
        # ======================================

        if priority_score >= 0.80:

            priority = "HIGH"

        elif priority_score >= 0.60:

            priority = "MEDIUM"

        else:

            priority = "LOW"


        # ======================================
        # Representative statement
        # ======================================

        cluster_indices = (
            cluster_feedback.index.tolist()
        )

        cluster_embeddings = embeddings[
            cluster_indices
        ]

        centroid = np.mean(
            cluster_embeddings,
            axis=0
        )

        similarities = cosine_similarity(
            cluster_embeddings,
            centroid.reshape(1, -1)
        ).flatten()

        best_position = np.argmax(
            similarities
        )

        representative_index = (
            cluster_indices[best_position]
        )

        representative_text = df.loc[
            representative_index,
            "text"
        ]


        # ======================================
        # Supporting feedback IDs
        # ======================================

        supporting_ids = (
            cluster_feedback["id"]
            .tolist()
        )


        # ======================================
        # Supporting feedback
        # ======================================

        supporting_feedback = []

        for _, row in cluster_feedback.iterrows():

            supporting_feedback.append({
                "id": row["id"],
                "source": row["source"],
                "date": row["date"].date().isoformat(),
                "text": row["text"],
                "sentiment": row["sentiment"],
                "severity": row["severity"]
            })


        # ======================================
        # Source list
        # ======================================

        sources = sorted(
            cluster_feedback["source"]
            .unique()
            .tolist()
        )


        # ======================================
        # Generate explanation
        # ======================================

        problem_summary = (
            generate_problem_summary(
                cluster_feedback
            )
        )

        observed_pattern = (
            generate_observed_pattern(
                cluster_feedback
            )
        )

        customer_impact = (
            generate_customer_impact(
                cluster_feedback
            )
        )


        # ======================================
        # Create structured insight
        # ======================================

        insight = {

            "cluster":
                cluster_id,

            "problem":
                representative_text,

            "problem_summary":
                problem_summary,

            "observed_pattern":
                observed_pattern,

            "customer_impact":
                customer_impact,

            "signal_strength":
                signal_strength,

            "priority":
                priority,

            "priority_score":
                round(
                    priority_score,
                    3
                ),

            "severity":
                cluster_feedback["severity"]
                .value_counts()
                .idxmax(),

            "severity_score":
                round(
                    severity_score,
                    3
                ),

            "evidence_score":
                round(
                    evidence_score,
                    3
                ),

            "evidence_count":
                total_count,

            "negative_evidence":
                negative_count,

            "negative_ratio":
                round(
                    negative_ratio,
                    3
                ),

            "sources":
                sources,

            "source_count":
                source_count,

            "first_seen":
                first_seen.date().isoformat(),

            "last_seen":
                last_seen.date().isoformat(),

            "time_span_days":
                time_span_days,

            "supporting_feedback_ids":
                supporting_ids,

            "supporting_feedback":
                supporting_feedback
        }


        pain_points.append(insight)


    # ==========================================
    # 8. Sort by priority
    # ==========================================

    pain_points = sorted(
        pain_points,
        key=lambda x: x["priority_score"],
        reverse=True
    )

    return pain_points


# ==========================================
# 9. Standalone execution
# ==========================================

if __name__ == "__main__":

    pain_points = analyze_feedback()

    for insight in pain_points:

        print("=" * 70)

        print(
            f"\nPRIORITY: "
            f"{insight['priority']}"
        )

        print(
            f"\nProblem:\n"
            f"  {insight['problem_summary']}"
        )

        print(
            f"\nObserved pattern:\n"
            f"  {insight['observed_pattern']}"
        )

        print(
            f"\nCustomer impact:\n"
            f"  {insight['customer_impact']}"
        )

        print(
            f"\nPriority score:"
            f" {insight['priority_score']:.3f}"
        )

        print(
            f"Signal strength:"
            f" {insight['signal_strength']}"
        )

        print(
            f"Severity:"
            f" {insight['severity']}"
        )

        print(
            f"Evidence count:"
            f" {insight['evidence_count']}"
        )

        print(
            f"Negative evidence:"
            f" {insight['negative_evidence']}/"
            f"{insight['evidence_count']}"
        )

        print(
            f"Sources:"
            f" {', '.join(insight['sources'])}"
        )

        print(
            f"First seen:"
            f" {insight['first_seen']}"
        )

        print(
            f"Last seen:"
            f" {insight['last_seen']}"
        )

        print(
            f"Time span:"
            f" {insight['time_span_days']} days"
        )

        print(
            f"\nSupporting feedback IDs:"
            f" {insight['supporting_feedback_ids']}"
        )

        print("\nCustomer Evidence:")

        for feedback in insight["supporting_feedback"]:

            print(
                f"  [{feedback['id']}] "
                f"{feedback['source']} | "
                f"{feedback['severity']} | "
                f"{feedback['text']}"
            )

        print()