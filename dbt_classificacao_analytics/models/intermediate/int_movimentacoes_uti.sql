with movimentacoes as(
    select *
    from {{ ref('stg_bronze__movimentacoes') }}
),

unidades_ocupadas as(
    select *
    from movimentacoes
    where tipo in ('INTERNACAO', 'TRANSFER. PARA')
),

com_movimentacao_anterior as(
    select
        *,
        lag(data_hora_movimentacao) over(
            partition by atendimento
            order by data_hora_movimentacao
        ) as data_hora_movimentacao_anterior
    from unidades_ocupadas
),

unidades_de_saida as(
    select
        atendimento,
        hash_nm_paciente,
        tipo,
        unidade,
        data_hora_movimentacao_anterior as data_hora_entrada,
        data_hora_movimentacao as data_hora_saida,
        timestamp_diff(
            data_hora_movimentacao,
            data_hora_movimentacao_anterior,
            minute
        ) as minutos_na_unidade,
        round(timestamp_diff(
            data_hora_movimentacao,
            data_hora_movimentacao_anterior,
            minute
        ) / 60.0, 1) as horas_na_unidade,
        round(timestamp_diff(
            data_hora_movimentacao,
            data_hora_movimentacao_anterior,
            minute
        ) / 1440.0, 1) as dias_na_unidade,
        upper(unidade) like '%UTI%' as eh_uti,
        safra_mes
    from com_movimentacao_anterior
)

select * from unidades_de_saida