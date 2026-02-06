import contextlib
import json
import os
import re
import time
from glob import glob
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup
from lxml_html_clean import Cleaner
from tqdm import tqdm


class AlMeezanCollection:
    def __init__(self, folder: Path):
        self.df = None
        self.input_folder = folder
        self._read_documents_from_input_folder()

    def get_all_json(self):
        docs = []
        for f in glob(os.path.join(self.input_folder, "*.json")):
            docs.append(f)
        return docs

    def get_all_almeezan_doc(self):
        docs = []
        for f in self.get_all_json():
            docs.append(AlMeezanDocument().from_json(f))
        return docs

    def _read_documents_from_input_folder(self):
        """
        Currently, we are reading JSONs from local disk. This needs to be updated to read from a Postgres database or S3 bucket.
        """

        df_tmp = []
        for f in self.get_all_json():
            df_tmp.append(pd.read_json(f))

        self.df = pd.concat(df_tmp)
        self.df["law_id"] = self.df["law_id"].astype(int)
        self.df["law_number"] = self.df["law_number"].astype(int)
        self.df["law_num_articles"] = self.df["law_num_articles"].astype(int)
        self.df["law_year"] = self.df["law_year"].astype(int)

        self.df = self.df.reset_index().rename(columns={"index": "article_id"})
        self.df = self.df.sort_values(by=["law_year", "law_number"])

        self.df["article_content"] = self.df["articles"].apply(lambda x: x["content"])
        self.df["article_content_len_chars"] = self.df["article_content"].str.len()

    def _get_law_by_id(self, id: int) -> pd.DataFrame:
        return self.df[self.df["law_id"] == id]

    def _get_law_by_year_number(self, year: int, number: int) -> pd.DataFrame:
        return self.df[(self.df["law_year"] == year) & (self.df["law_number"] == number)]

    def get_law_text(self, id: int = None, year: int = None, number: int = None) -> str:
        if id:
            df_law = self._get_law_by_id(id)
        elif year and number:
            df_law = self._get_law_by_year_number(year, number)
        else:
            raise ValueError(
                f"Either `id` or the pair `year` and `number` must be provided. Provided were: id ({id}), year ({year}), number ({number})"
            )

        if df_law is None or df_law.empty:
            print(f"Could not find any law with id {id}, year {year} and number {number}.")
            return None

        def print_article(x: pd.DataFrame) -> str:
            s = f"== {x['article_id']} ==\n"
            s += f"{x['article_content']}\n"
            return s

        row = df_law.iloc[0]
        law_name, law_year, law_number = (
            row["law_name"],
            str(row["law_year"]),
            str(row["law_number"]),
        )

        str_series = df_law[["article_id", "article_content"]].apply(
            lambda x: print_article(x), axis=1
        )
        text = f"=== {law_name} ===\n"
        text += f"- Law Year: {law_year}\n"
        text += f"- Law Number: {law_number}\n\n"
        for _, v in str_series.items():
            text += v

        return text

    def get_number_of_laws(self, remove_canceled: bool = True) -> int:
        if remove_canceled:
            df = self.df[~(self.df["law_status"].isin(["ملغى", "canceled"]))]
        else:
            df = self.df

        return df.drop_duplicates(subset=["law_id"]).shape[0]

    def get_collection_text(
        self,
        sample: int | float = None,
        remove_canceled: bool = True,
        num_page: int = 1,
        num_max_pages: int = 1,
        show_year: bool = True,
        show_number: bool = True,
        show_name: bool = True,
        show_url: bool = True,
    ) -> str:

        if remove_canceled:
            df = self.df[~(self.df["law_status"].isin(["ملغى", "canceled"]))]
        else:
            df = self.df

        df_tmp = df.drop_duplicates(subset=["law_id"])
        if sample:
            df_tmp = df_tmp.sample(sample)

        # Get only the documents of a given page
        n_per_page = int(df_tmp.shape[0] / num_max_pages) + 1
        end = n_per_page * num_page
        df_tmp = df_tmp.head(end).tail(n_per_page)

        def stringfy_row(
            law: str, show_year: bool, show_number: bool, show_name: bool, show_url: bool
        ) -> str:
            s = "== Law =="
            if show_name:
                s += f"\n\t- Name: {law['law_name']}"
            if show_year:
                s += f"\n\t- Year: {law['law_year']}"
            if show_number:
                s += f"\n\t- Number: {law['law_number']}"
            if show_url:
                s += f"\n\t- URL: https://www.almeezan.qa/LawPage.aspx?id={law['law_id']}&language={law['lang']}"
            s += "\n"
            return s

        str_series = df_tmp.apply(
            lambda x: stringfy_row(x, show_year, show_number, show_name, show_url), axis=1
        )
        text = "=== Qatari Laws ===\n"
        for _, v in str_series.items():
            text += v

        return text


def sanitize(dirty_html):
    cleaner = Cleaner(
        page_structure=True,
        meta=True,
        embedded=True,
        links=True,
        style=True,
        processing_instructions=True,
        inline_style=True,
        scripts=True,
        javascript=True,
        comments=True,
        frames=True,
        forms=True,
        annoying_tags=True,
        remove_unknown_tags=True,
        safe_attrs_only=True,
        safe_attrs=frozenset(["src", "color", "href", "title", "class", "name", "id"]),
    )

    return cleaner.clean_html(dirty_html)


class AlMeezanDocument:
    def __init__(self):
        self.law_name = None
        self.law_id = None
        self.lang = None
        self.law_type = None
        self.law_number = None
        self.law_year = None
        self.law_num_articles = None
        self.law_status = None
        self.articles = {}
        self.name_conversion = {
            "type": {"en": "Type: ", "ar": "النوع: "},
            "number": {"en": "Number: ", "ar": "رقم:"},
            "date": {"en": "Date: ", "ar": "التاريخ:"},
            "status": {"en": "Status: ", "ar": "الحالة:"},
            "articles": {"en": "Number of Articles: ", "ar": "عدد المواد:"},
            "corresponding": {"en": "Corres", "ar": "الموافق"},
        }

    def __str__(self):
        return f"Law ID: {self.law_id}, Language: {self.lang}, Type: {self.law_type}, Number: {self.law_number}, Year: {self.law_year}, Number of Articles: {self.law_num_articles}, Status: {self.law_status}, Articles: {self.articles}"

    def get_content(self):
        s = f"Law Name: {self.law_name}\n"
        s += f"Law Year/Number: {self.law_year}/{self.law_number}\n"
        for article in self.articles:
            s += f"Article {article}\n{self.articles[article]['content']}\n"
        return s

    def __repr__(self) -> str:
        return self.__str__()

    def _get_soup(self, url, tidy_doc=True):
        print(url)
        page = requests.get(url, verify=False)  # Bypassing SSL verification
        if tidy_doc:
            # Tidy the document: the html is not well formed at all. Needed to us this package to clean it up.
            document = sanitize(page.content.decode("utf-8"))
        else:
            document = page.content
        return BeautifulSoup(document, "html.parser")

    def _get_header(self, soup, lang):
        law_name = soup.find("h3", id="ContentPlaceHolder1_lblTitle")
        if law_name:
            law_name = law_name.text.strip()

        law_type = soup.find("span", id="ContentPlaceHolder1_lblcardtype")
        if law_type:
            law_type = law_type.text.split(self.name_conversion["type"][lang])[1]
            law_type = law_type.strip()

        law_number = soup.find("span", id="ContentPlaceHolder1_lblNumber")
        if law_number:
            law_number = law_number.text.split(self.name_conversion["number"][lang])[1]
            law_number = int(law_number.strip())

        law_year = soup.find("span", id="ContentPlaceHolder1_lbldate")
        if law_year:
            law_year = law_year.text.split(self.name_conversion["date"][lang])[1]
            law_year = law_year.split(self.name_conversion["corresponding"][lang])[0]
            law_year = law_year.strip()
            law_year = int(law_year.split("/")[-1])

        law_num_articles = soup.find("span", id="ContentPlaceHolder1_lblArticlesNumber")
        if law_num_articles:
            law_num_articles = law_num_articles.text.split(self.name_conversion["articles"][lang])[
                1
            ]
            law_num_articles = int(law_num_articles.strip())
        else:
            law_num_articles = 0

        law_status = soup.find("span", id="ContentPlaceHolder1_lblstatus")
        if law_status:
            law_status = law_status.text.split(self.name_conversion["status"][lang])[1]
            law_status = law_status.strip()

        return law_name, law_type, law_number, law_year, law_num_articles, law_status

    def _get_articles(self, soup):

        article_soup = soup.find("ul", class_="bulleted-list")
        if not article_soup:
            print("Could not find any articles on this page. Returning empty lists.")
            return [], [], []

        # Article Names (not always the articles are names 1, 2, 3, 4....)
        article_names = article_soup.find_all("li", recursive=False)
        article_names = [a.find("a").text.strip() for a in article_names]
        # Remove eventual new lines and extra spaces from the names
        article_names = [" ".join(a.replace("\r\n", " ").split()) for a in article_names]

        # List of article
        article_urls = article_soup.find_all("li", recursive=False)
        article_urls = ["https://www.almeezan.qa/" + a.find("a").get("href") for a in article_urls]

        # Article content
        article_content = article_soup.find_all("li", recursive=False)
        for a in article_content:
            a.find("h4").decompose()
        article_content = [a.text.strip().replace("\n\n", "\n") for a in article_content]

        print(
            f"Article URLS: {len(article_urls)}, Article Content: {len(article_content)}, Article names: {len(article_names)}"
        )
        return article_urls, article_content, article_names

    def _extract_links_from_law_page(self, url):
        soup = self._get_soup(url, tidy_doc=False)
        links = soup.find("div", id="ContentPlaceHolder1_tablesection").find_all("a")
        return ["https://www.almeezan.qa/" + link.get("href") for link in links]

    def _assert_number_of_articles(self):
        assert len(self.articles) == self.law_num_articles

    def _brute_force_collection(
        self, law_id: int, lang: str, start: int, expected_num_articles: int, sleep_secs: int = 0
    ) -> None:
        print("Going to brute force collection")
        for article_id in tqdm(range(start, start + expected_num_articles + 1)):
            url = f"https://www.almeezan.qa/LawArticles.aspx?LawArticleID={article_id}&LawId={law_id}&language={lang}"
            self.manually_add_from_url(url)
            time.sleep(sleep_secs)
        print(f"Number of articles after brute force: {len(self.articles)}")

    def __get_first_article_from_url(self, law_id, lang):
        def __get_article_id_from_url(url):
            import re

            match = re.search(r"LawArticleID=(\d+)", url)
            if match:
                return int(match.group(1))
            return None

        # first_article_idx =
        soup = self._get_soup(f"https://www.almeezan.qa/LawPage.aspx?id={law_id}&language={lang}")
        first_related_link = "https://www.almeezan.qa/" + soup.find(
            "div", id="ContentPlaceHolder1_tablesection"
        ).find("a").get("href")

        if "LawArticleID" in first_related_link:
            article_idx = __get_article_id_from_url(first_related_link)
        else:
            soup2 = self._get_soup(first_related_link)
            url = soup2.find("ul", class_="bulleted-list").find("li").find("a").get("href")
            article_idx = __get_article_id_from_url(url)
        return article_idx

    def extract_info(
        self,
        law_id: int,
        lang: str,
        check_number_of_articles: bool = True,
        tree_section: int = 1,
        brute_force_collection_start: Optional[int] = None,
        override_num_articles: Optional[int] = None,
        brute_force_sleep_secs: Optional[int] = 1,
    ) -> None:

        self.law_id = law_id
        self.lang = lang

        doc_html = f"https://www.almeezan.qa/LawArticles.aspx?LawTreeSectionID={tree_section}&lawId={self.law_id}&language={self.lang}"
        print(f"Processing: {doc_html}")

        soup = self._get_soup(doc_html)
        # return soup
        (
            self.law_name,
            self.law_type,
            self.law_number,
            self.law_year,
            self.law_num_articles,
            self.law_status,
        ) = self._get_header(soup, lang)

        if brute_force_collection_start:
            print(f"Expected to find {self.law_num_articles} articles....")
            self.articles = {}  # Reset it before running brute force
            override_num_articles = (
                override_num_articles if override_num_articles else self.law_num_articles
            )
            self._brute_force_collection(
                self.law_id,
                self.lang,
                brute_force_collection_start,
                override_num_articles,
                brute_force_sleep_secs,
            )
            return

        article_urls, article_content, article_name = self._get_articles(soup)

        # Combine the two
        if len(article_urls) != self.law_num_articles:
            # that is the case for some of the pages. Here we have to unfortunately go to the Law Page and craw one by one of the articles.
            sub_links = self._extract_links_from_law_page(
                f"https://www.almeezan.qa/LawPage.aspx?id={self.law_id}&language={self.lang}"
            )
            article_urls, article_content, article_name = [], [], []
            for link in sub_links:
                article_soup = self._get_soup(link, tidy_doc=True)
                tmp_article_urls, tmp_article_content, tmp_article_name = self._get_articles(
                    article_soup
                )
                article_urls.extend(tmp_article_urls)
                article_content.extend(tmp_article_content)
                article_name.extend(tmp_article_name)

            # There are a few cases in which the articles are listed directly. For these cases we want to use another parser
            if len(article_urls) == 1 and self.law_num_articles > 1:
                article_urls, article_content, article_name = [], [], []
                for link in sub_links[1:]:
                    (
                        tmp_article_name,
                        tmp_article_content,
                        tmp_article_urls,
                    ) = self._manually_extract_from_url(link)
                    article_urls.append(tmp_article_urls)
                    article_content.append(tmp_article_content)
                    article_name.append(tmp_article_name)

        self.articles = {}
        for i in range(len(article_name)):
            # We might want to have an article name for cases like this one https://www.almeezan.qa/LawPage.aspx?id=2563&language=en
            self.articles[article_name[i]] = {"url": article_urls[i], "content": article_content[i]}

        print(
            f"Extracted {len(self.articles)} articles urls/content/name, expected {self.law_num_articles}"
        )

        if check_number_of_articles:
            # The first exception is ignored and we try to solve. If it fails, we throw the exception back to the caller...
            with contextlib.suppress(Exception):
                try:
                    self._assert_number_of_articles()
                except:
                    print("ERROR ASSERTING NUMBER OF ARTICLES....GOING TO BRUTE FORCE COLLECTION")
                    first_article_idx = self.__get_first_article_from_url(self.law_id, self.lang)
                    print(f"FIRST INDEX IS {first_article_idx}")
                    self.extract_info(
                        law_id,
                        lang,
                        check_number_of_articles=True,
                        tree_section=tree_section,
                        brute_force_collection_start=first_article_idx,
                    )
            # now it should have been solved....otherwise we flag it as an error
            self._assert_number_of_articles()

    def manually_add_article(self, article_name, article_url, article_content):
        self.articles[article_name] = {"url": article_url, "content": article_content}

    def _manually_extract_from_url(self, article_url):
        soup = self._get_soup(article_url)

        # Check if we have a list of events. This should not be the case, most of the time, only when laws change
        law_events = soup.find("div", attrs={"class": "events-content"})
        if law_events:

            law_text = law_events.find("li").find(
                "div", attrs={"class": "default-text-block"}
            )  # .find_all("span")
            article_name = law_text.find("span").text
            article_name = " ".join(article_name.replace("\r\n", " ").replace(".", " ").split())

            for component in law_text.find_all("span"):
                component.decompose()

            article_content = law_text.text.strip().replace("\n\n", "\n")
            return article_name, article_content, article_url

        # Get the part that we want to extract from an article page
        law_table = soup.find("div", attrs={"id": "ContentPlaceHolder1_ContentDiv"})

        if not law_table:
            print(f"Could not extract content from {article_url}")
            return None, None, None

        try:
            # Get Text
            table = law_table.find("table")
            if table:
                article_content = table.text
                article_content = article_content.strip().replace("\n\n", "\n")

                # Get Article name
                law_table.find("span", attrs={"class": "law-date"}).decompose()
                law_table.find("table").decompose()
                article_name = law_table.text.strip()
                article_name = " ".join(article_name.replace("\r\n", " ").replace(".", " ").split())

            else:
                # when we don't have a table, we need to extract what we can...
                # Get rid of law date and use everything else as law_name and law_content
                for t in law_table.find_all("span"):
                    if t.has_attr("class"):
                        t.decompose()

                article_name = " ".join([t.text for t in law_table.find_all("span")])
                article_name = " ".join(article_name.replace("\r\n", " ").replace(".", " ").split())
                # Remove article name
                [s.decompose() for s in law_table.find_all("span")]
                article_content = law_table.text.strip().replace("\n\n", "\n")

                print("ARTICLE NAME: ", article_name)
                print("ARTICLE CONTENT: ", article_content)
                # law_table.find("span", attrs={"class":"law-date"}).decompose()
                # parts = law_table.text.split("\n")
                # print("Number of parts: ", len(parts))
                # print("Parts: ", parts)
                # article_name = parts[0]
                # article_name = ' '.join(article_name.replace("\r\n", " ").replace(".", " ").split())

                # article_content = "\n".join(parts[1:]).strip()
                # article_content = article_content.strip().replace("\n\n", "\n")
        except:
            print(f"Failed to extract content from {article_url}")
            return None, None, None

        return article_name, article_content, article_url

    def manually_add_from_url(self, url):

        article_name, article_content, article_url = self._manually_extract_from_url(url)
        if not article_name:
            print(f"Failed to retrieve information for {url}")
            return None

        # Save object if all is good
        if len(article_content) > 0 and len(article_name) > 0:
            self.articles[article_name] = {"url": article_url, "content": article_content}
        else:
            print(
                f"Error loading article from {url}. Chars in Article name: {len(article_name)}, Chars in Article content: {len(article_content)}"
            )

    def quick_fix_missing_articles(self, start, num_articles):
        def extract_law_article_id(url):
            match = re.search(r"LawArticleID=(\d+)", url)
            if match:
                return match.group(1)
            return None

        def find_missing_articles(start, num_articles):

            found = {}
            for num in range(start, start + num_articles + 1):
                found[num] = 1

            for art in self.articles.values():
                num = int(extract_law_article_id(art["url"]))
                if num in found:
                    del found[int(num)]

            return list(found.keys())

        for article in find_missing_articles(start, num_articles):
            print("Adding manually article: ", article)
            self.manually_add_from_url(
                f"https://www.almeezan.qa/LawArticles.aspx?LawArticleID={article}&LawID={self.law_id}&language={self.lang}"
            )

    def from_json(self, filename):
        with open(filename, "r") as f:
            data = json.load(f)
            self.law_id = data["law_id"]
            self.law_name = data["law_name"]
            self.lang = data["lang"]
            self.law_type = data["law_type"]
            self.law_number = data["law_number"]
            self.law_year = data["law_year"]
            self.law_num_articles = data["law_num_articles"]
            self.law_status = data["law_status"]
            # Convert keys from int to string.
            self.articles = {k: v for k, v in data["articles"].items()}
            return self

    def to_dict(self):
        return {
            "law_name": self.law_name,
            "law_id": self.law_id,
            "lang": self.lang,
            "law_type": self.law_type,
            "law_number": self.law_number,
            "law_year": self.law_year,
            "law_num_articles": self.law_num_articles,
            "law_status": self.law_status,
            "articles": self.articles,
        }

    def to_json(self, filename):
        if filename:
            with open(filename, "w", encoding="utf8") as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=4)
        return self.to_dict()

    def get_full_law(self):
        full_law = [
            f"Law Name: {self.law_name}",
            f"Law Number: {self.law_number}",
            f"Law Year: {self.law_year}",
            f"Law Type: {self.law_type}",
            f"Number of Articles: {self.law_num_articles}",
            f"Status: {self.law_status}\n",
        ]
        for i in range(1, self.law_num_articles + 1):
            full_law.append(f"Article {i}\n{self.articles[i]['content']}")
        return "\n".join(full_law)
