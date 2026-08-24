"""
Preprocessamento do relatório bruto de movimentações.

RESPONSABILIDADE:
    O relatório de movimentações nasce desconfigurado na exportação do
    sistema hospitalar, sem cabeçalho de coluna reconhecível, com linhas
    de metadado (unidade de internação, data) intercaladas entre as linhas
    de dado, e com deslocamento de coluna variável (a posição da HORA muda
    dependendo se a linha tem ou não uma coluna de paciente).

    Este módulo reconstrói o layout correto ANTES de qualquer validação
    Pandera, schemas_movimentacoes.py espera colunas nomeadas
    (ATEND, TIPO, ORIGEM, etc.), não o arquivo bruto.

ORIGEM:
    Lógica adaptada de um script já validado em outro projeto, que lida
    com o mesmo relatório bruto. Trazida para este projeto para evitar
    dependência cruzada entre repositórios e ambiguidade de qual versão
    do tratamento está em uso.
"""

import re
import logging

import pandas as pd

logger = logging.getLogger(__name__)

def _propagar_unidade_e_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Propaga UNIDADE e DATA das linhas de metadado para as linhas de dado.

    O relatório bruto intercala linhas de cabeçalho de seção
    ("Unidade de Internação: ...", "Data: ...") com as linhas de
    movimentação em si. Cada linha de movimentação pertence à
    unidade/data do cabeçalho de seção mais recente acima dela.

    Args:
        df: DataFrame bruto, lido com header=None.

    Returns:
        Mesmo DataFrame, com colunas UNIDADE e DATA preenchidas
        linha a linha.
    """
    df = df.copy()

    unidade_atual = None
    data_atual = None

    df["UNIDADE"] = None
    df["DATA"] = None

    for numero_linha, linha in df.iterrows():
        if str(linha[0]).startswith("Unidade de Internação"):
            unidade_atual = linha[6]
        elif str(linha[0]).strip() == "Data:":
            data_atual = linha[2]

        df.at[numero_linha, "UNIDADE"] = unidade_atual
        df.at[numero_linha, "DATA"] = data_atual

    return df

def _eh_horario(valor) -> bool:
    """
    Verifica se um valor está no formato de horário (HH:MM:SS).

    Usado para detectar em qual posição de coluna a HORA está —
    o deslocamento varia conforme o layout da linha (ver
    reconstruir_layout).

    Args:
        valor: valor a verificar (qualquer tipo).

    Returns:
        True se o valor casa com o padrão HH:MM:SS.
    """
    if pd.isna(valor):
        return False
    return bool(re.match(r"^\d{2}:\d{2}:\d{2}$", str(valor).strip()))


def _filtrar_linhas_de_dado(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove linhas de metadado, mantendo só linhas de movimentação real.

    Uma linha é de dado válido quando a coluna 1 (posição do Atend.)
    contém um número, linhas de cabeçalho de seção não têm isso.

    Args:
        df: DataFrame já com UNIDADE/DATA propagados.

    Returns:
        DataFrame filtrado, só com linhas de movimentação.
    """
    return df[pd.to_numeric(df[1], errors="coerce").notna()]

def _normalizar_linha(linha: pd.Series) -> dict | None:
    """
    Reconstrói uma linha de movimentação para o layout final nomeado.

    O relatório bruto desloca as colunas de dado dependendo de a linha
    ter ou não uma coluna extra de identificação de paciente, por isso
    HORA aparece em posições diferentes (10, 7 ou 8) dependendo do caso.
    Detecta qual layout se aplica testando essas três posições em ordem.

    Args:
        linha: uma linha do DataFrame já filtrado (só linhas de dado).

    Returns:
        Dicionário com as colunas no layout final (ATEND, NM_PACIENTE,
        HORA, TIPO, ORIGEM, DESTINO, TIP_ACOM, CID, CONVENIO,
        MOTIVO_ALTA, UNIDADE, DATA), ou None se nenhum layout casar.
    """
    if _eh_horario(linha[10]):
        return {
            "ATEND": linha[1],
            "NM_PACIENTE": linha[3],
            "HORA": linha[10],
            "TIPO": linha[11],
            "ORIGEM": linha[13],
            "DESTINO": linha[15],
            "TIP_ACOM": linha[16],
            "CID": linha[17],
            "CONVENIO": linha[18],
            "MOTIVO_ALTA": linha[19],
            "UNIDADE": linha["UNIDADE"],
            "DATA": linha["DATA"],
        }
    elif _eh_horario(linha[7]):
        return {
            "ATEND": linha[1],
            "NM_PACIENTE": linha[3],
            "HORA": linha[7],
            "TIPO": linha[8],
            "ORIGEM": linha[10],
            "DESTINO": linha[12],
            "TIP_ACOM": linha[13],
            "CID": linha[14],
            "CONVENIO": linha[15],
            "MOTIVO_ALTA": linha[16],
            "UNIDADE": linha["UNIDADE"],
            "DATA": linha["DATA"],
        }
    elif _eh_horario(linha[8]):
        return {
            "ATEND": linha[1],
            "NM_PACIENTE": linha[3],
            "HORA": linha[8],
            "TIPO": linha[9],
            "ORIGEM": linha[11],
            "DESTINO": linha[13],
            "TIP_ACOM": linha[14],
            "CID": linha[15],
            "CONVENIO": linha[16],
            "MOTIVO_ALTA": linha[17],
            "UNIDADE": linha["UNIDADE"],
            "DATA": linha["DATA"],
        }
    else:
        return None

def reconstruir_layout_movimentacoes(df_bruto: pd.DataFrame) -> pd.DataFrame:
    """
    Reconstrói o relatório bruto de movimentações para o layout final.

    Ponto de entrada único deste módulo, orquestra as etapas:
      1. Propaga UNIDADE e DATA das linhas de metadado
      2. Filtra só linhas de dado real (Atend. numérico)
      3. Normaliza cada linha para o layout final nomeado,
         detectando automaticamente o deslocamento de coluna (A/B/C)
      4. Loga (sem interromper) linhas que não casaram em nenhum layout

    Args:
        df_bruto: DataFrame lido com header=None, direto do upload
            (arquivo .xlsx desconfigurado, conforme exportado
            do sistema hospitalar).

    Returns:
        DataFrame no layout final, pronto para validação Pandera
        (schemas_movimentacoes.py).
    """
    df = _propagar_unidade_e_data(df_bruto)
    df = _filtrar_linhas_de_dado(df)

    linhas_normalizadas = []
    linhas_descartadas = 0

    for _, linha in df.iterrows():
        linha_normalizada = _normalizar_linha(linha)
        if linha_normalizada is not None:
            linhas_normalizadas.append(linha_normalizada)
        else:
            linhas_descartadas += 1

    if linhas_descartadas > 0:
        logger.warning(
            f"{linhas_descartadas} linha(s) do relatório de movimentações "
            f"não casaram com nenhum layout conhecido e foram descartadas. "
            f"Investigar se o sistema de origem mudou o formato de exportação."
        )

    df_final = pd.DataFrame(linhas_normalizadas)
    df_final = df_final.reset_index(drop=True)

    logger.info(
        f"Reconstrução de layout concluída: {len(df_final)} linhas normalizadas "
        f"de {len(df_bruto)} linhas brutas."
    )

    return df_final