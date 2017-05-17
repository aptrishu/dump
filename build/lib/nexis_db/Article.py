import re

attributes = [
    'ADVANCED-DATE', 'DATE', 'PUBLICATION', 'COMMITTEE', 'DISTRIBUTION',
    'EDITION', 'TITLE', 'COPYRIGHT', 'CORRECTION', 'HEADLINE', 'PUB',
    'CORRECTION-DATE', 'AFFILIATION',  'ART', 'AUTEUR', 'AUTOR', 'AUTORE',
    'AZIENDA', 'BILD', 'BILL-NO', 'BODY', 'BRANCHE-SIC', 'BUNDESLAND', 'BYLINE',
    'CHAPEAU', 'CITTA', 'CITY', 'COMPANY', 'CONTACT', 'CORREZIONE', 'COUNTRY',
    'D-DATE', 'DATA', 'DATA-CARICO', 'DATA-CORREZIONE', 'DATA-CHARGEMENT',
    'DATA-ERRATUM', 'DATELINE', 'DATUM', 'EDITOR-NOTE', 'EINLEITUNG',
    'ENHANCEMENT', 'ENTETE', 'ETAT', 'EXTRACTED-TERMS', 'FIRMA', 'GEOGRAFICO',
    'GEOGRAPHIC', 'GEOGRAPHIQUE', 'GRAFIK', 'GRAFIQUE', 'GRAFIC', 'HIGHLIGHT',
    'HLEAD', 'INDEXATION', 'INDUSTRIA', 'INDUSTRIE', 'INDUSTRY', 'INLEIDING',
    'KEYWORD', 'KOP', 'KORREKTUR', 'KORREKTUR-DATUM', 'LAENGE', 'LAND',
    'LANGUAGE', 'LANGUE', 'LEAD', 'LENGTE', 'LENGTH', 'LEVERANCIER', 'LINGUA',
    'LN-SUBJ', 'LOAD-DATE', 'LONGUEUR', 'LUNGHEZZA', 'NOTES', 'ORGANIZATION',
    'ORGANIZZAZIONE', 'PAESE', 'PAGE', 'PAGINA', 'PAYS', 'PERSON', 'PERSONA',
    'PLAATS', 'PRODUCT', 'PUB-TYPE', 'PUBBLICAZIONE', 'PUBLIKATION', 'QUELLE',
    'REGION', 'RUBRICA', 'RUBRIK', 'RUBRIQUE', 'SCHLAGWORT', 'SECTEUR',
    'SECTIE', 'SECTION', 'SEITE', 'SERIES', 'SIC', 'SOCIETE', 'SOGGETTO',
    'SOURCE', 'SPRACHE', 'STADT', 'STATE', 'STATO', 'SUBCOMMITTEE', 'SUBJECT',
    'SUJET', 'TAAL', 'TEKST', 'TERMINI', 'TERMS', 'TESTATA', 'TESTIMONY-BT',
    'TESTO', 'TEXT', 'TEXTE', 'THEMA', 'TICKER', 'TIME', 'TITEL',
    'TITEL-EINLEITUNG', 'TITOLO', 'TITRE', 'TTESTATA', 'TYPE', 'UEBERSCHRIFT',
    'UPDATGE', 'VILLE', 'VORSPANN']


def make_attribute_name(attr: str):
    return attr.lower().replace('-', '_')


class Article:

    def __init__(self, content: str, **kwargs):
        self.content = content
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self):
        result = "<Article text=" + repr(self.content)
        for attr in attributes:
            value = getattr(self, make_attribute_name(attr), None)
            if value is not None:
                result += " " + make_attribute_name(attr) + "=" + repr(value)

        return result + ">"

    @classmethod
    def _single_article_from_text(cls, text):
        kwargs = {}

        for attribute in attributes:
            start = text.find('\n'+attribute+': ')
            if start != -1:
                realstart = start+len(attribute)+2
                end = text.find('\n\n', realstart)
                end = end if end != -1 else len(text)
                content = text[realstart:end].split(';')
                kwargs[make_attribute_name(attribute)] = [
                    elem.strip() for elem in content]
                text = text[:start] + text[end:]

        return cls(text.strip(), **kwargs)

    @classmethod
    def from_nexis_text(cls, content):
        """
        Yields all articles from the given text file.

        :param content: The whole file as one string.
        """
        if content.startswith('\ufeff'):
            content = content[1:]
        articles = re.split(r'Dokument [0-9]+ von [0-9]+', content)
        for article in articles:
            article = article.strip()
            if not article:
                continue
            yield cls._single_article_from_text(article)
