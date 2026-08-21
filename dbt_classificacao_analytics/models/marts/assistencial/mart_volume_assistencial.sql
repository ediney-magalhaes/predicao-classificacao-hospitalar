select bronze.atendimento,
       bronze.safra_mes,
       bronze.grupo_sus,
       bronze.complexidade_sus,
       bronze.especialidade,
       bronze.convenio,
       bronze.uf,
       bronze.municipio,
       bronze.tipo_internacao,
       bronze.sexo,
       bronze.idade,
       bronze.nr_dias,
       bronze.cid_1_principal,
       bronze.capitulo_breve,
       bronze.grupo_cid,
       bronze.unidade_saida,
       faixa.faixa_etaria,
       convenio_fonte.fonte as fonte_convenio,
       coalesce(leito_unidade.unidade, 'Não mapeado') as unidade_agrupada

from {{ ref('stg_bronze__saidas') }} as bronze
left join {{ ref('faixa_etaria') }} as faixa
    on bronze.idade = faixa.idade
left join {{ ref('mapa_convenio_fonte') }} as convenio_fonte
    on bronze.registro_ans = convenio_fonte.registro_ans
left join {{ ref('mapa_leito_unidade') }} as leito_unidade
    on bronze.unidade_saida = leito_unidade.leito
