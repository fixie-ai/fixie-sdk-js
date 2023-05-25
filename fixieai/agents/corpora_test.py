import json

from fixieai.agents import corpora


def test_request_serialization():
    request = corpora.CorpusRequest(partition="partition", page_token="token")
    as_dict = request.to_dict()
    assert isinstance(as_dict, dict)

    # Assert query can be reconstructed from as_dict
    request_reconstructed = corpora.CorpusRequest.from_dict(as_dict)
    assert isinstance(request_reconstructed, corpora.CorpusRequest)
    assert request_reconstructed == request

    # Assert serialize_as_dict produces a json serializable string
    as_json = json.dumps(as_dict)
    as_dict_from_json = json.loads(as_json)
    request_reconstructed = corpora.CorpusRequest.from_dict(as_dict_from_json)
    assert isinstance(request_reconstructed, corpora.CorpusRequest)
    assert request_reconstructed == request


def test_response_serialization():
    response = corpora.CorpusResponse(
        partitions=[
            corpora.CorpusPartition("part1", "part1token"),
            corpora.CorpusPartition("part2"),
        ],
        page=corpora.CorpusPage(
            [
                corpora.CorpusDocument("doc1", "content".encode()),
                corpora.CorpusDocument("doc2", "moreContent".encode("cp037"), "cp037"),
            ],
            "continuationToken",
        ),
    )
    as_dict = response.to_dict()
    assert isinstance(as_dict, dict)

    # Assert response can be reconstructed from as_dict
    response_reconstructed = corpora.CorpusResponse.from_dict(as_dict)
    assert isinstance(response_reconstructed, corpora.CorpusResponse)
    assert response_reconstructed == response

    # Assert serialize_as_dict produces a json serializable string
    as_json = json.dumps(as_dict)
    as_dict_from_json = json.loads(as_json)
    response_reconstructed = corpora.CorpusResponse.from_dict(as_dict_from_json)
    assert isinstance(response_reconstructed, corpora.CorpusResponse)
    assert response_reconstructed == response
