with origem as(
    select *
    from {{ source('bronze', 'bronze_financeiro_anonimizado') }}
),

tratado as(
    select
        nr_atendimento,
        nr_interno_conta,
        substr(mes_ano_producao, 1, 3) as mes_abreviado,
        ano_producao,
        valor,
        convenio,
        hash_paciente,
        valor_recebido,
        valor_glosa,
        data_ingestao
    from origem
),

final as(
    select
        nr_atendimento,
        nr_interno_conta,
        valor,
        convenio,
        hash_paciente,
        valor_recebido,
        valor_glosa,
        data_ingestao,
        parse_date('%Y-%m-%d', concat(cast(ano_producao as string),'-', LPAD(CAST(mes_numero AS STRING), 2, '0'), '-01')) as mes_ano_producao
    from tratado
    left join {{ ref('mapa_mes_abrev') }} as mapa
        on tratado.mes_abreviado = mapa.mes_abrev
)

select * from final