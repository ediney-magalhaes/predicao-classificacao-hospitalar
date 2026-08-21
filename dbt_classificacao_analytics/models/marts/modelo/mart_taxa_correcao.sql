select
    safra_mes,
    total_registros,
    correcoes_grupo,
    correcoes_complexidade,
    correcoes_ambos,
    taxa_correcao_grupo,
    taxa_correcao_complexidade,
    tempo_revisao_min,
    versao_modelo
from {{ ref('int_correcoes_hitl') }}