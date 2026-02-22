from notion_client import Client
import os

def get_notion_client(api_key):
    return Client(auth=api_key)

def get_notion_pages(api_key):
    notion = get_notion_client(api_key)
    try:
        response = notion.search(
            filter={"property": "object", "value": "page"}
        )
        pages = []
        for page in response["results"]:
            title = "Untitled"
            # extract title from page properties
            props = page.get("properties", {})
            for prop in props.values():
                if prop.get("type") == "title":
                    title_list = prop.get("title", [])
                    if title_list:
                        title = title_list[0].get("plain_text", "Untitled")
                        break
            pages.append({
                "id": page["id"],
                "title": title
            })
        return pages
    except Exception as e:
        return []

def get_page_content(api_key, page_id):
    notion = get_notion_client(api_key)
    try:
        blocks = notion.blocks.children.list(block_id=page_id)
        text = ""
        for block in blocks["results"]:
            block_type = block["type"]
            block_data = block.get(block_type, {})
            rich_text = block_data.get("rich_text", [])
            for rt in rich_text:
                text += rt.get("plain_text", "") + " "
            text += "\n"
        return text.strip()
    except Exception as e:
        return ""