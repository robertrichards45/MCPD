from app.services import orders_ingestion


def test_extract_link_pairs_reads_anchor_text():
    html = """
    <html><body>
      <a href="/News/Messages/Messages-Display/Article/12345/maradmin-123-24/">MARADMIN 123/24</a>
      <a href="https://www.marines.mil/Portals/1/Publications/MCO%205500.6H.pdf">MCO 5500.6H</a>
    </body></html>
    """
    pairs = orders_ingestion._extract_link_pairs(html, "https://www.marines.mil/")
    urls = [url for url, _ in pairs]
    labels = [label for _, label in pairs]
    assert any("messages-display" in url.lower() for url in urls)
    assert any("mco 5500.6h" in label.lower() for label in labels)


def test_candidate_text_detects_order_terms():
    assert orders_ingestion._is_candidate_text("MARADMIN 123/24 policy update")
    assert orders_ingestion._is_candidate_text("MCO 5500.6H")
    assert not orders_ingestion._is_candidate_text("Photo gallery and social media post")


def test_extract_order_number_from_text_and_url():
    text = "This publication references MCO 5500.6H for law enforcement guidance."
    code = orders_ingestion._extract_order_number(text, "https://www.marines.mil")
    assert code == "MCO 5500.6H"

    code2 = orders_ingestion._extract_order_number("", "https://www.marines.mil/News/Messages/Messages-Display/Article/999/maradmin-431-24/")
    assert code2 == "MARADMIN 431/24"


def test_topic_tags_for_common_policy_queries():
    sample = "Haircut grooming and appearance standards plus leave and barracks guidance."
    tags = orders_ingestion._topic_tags_for_text(sample)
    assert "grooming" in tags
    assert "leave" in tags
    assert "barracks" in tags


def test_candidate_rejects_job_posting_links_and_content():
    assert not orders_ingestion._is_candidate_link("https://www.indeed.com/viewjob?jk=123")
    assert not orders_ingestion._is_candidate_link("https://example.com/mco-5500-guidance")
    assert orders_ingestion._is_candidate_link("https://www.marines.mil/Portals/1/Publications/MCO%205500.6H.pdf")
    assert not orders_ingestion._is_candidate_text("Apply now for civilian police jobs on base")
    assert not orders_ingestion._looks_like_real_order_content(
        "Apply now for a career opportunity with benefits and open positions.",
        "Civilian Police Job Posting",
        "https://example.com/jobs/civilian-police",
    )
