with movimentacoes as (
    select
        *,
        case
            when tipo in ('INTERNACAO', 'TRANSFER. DE') then 'entrada'
            when tipo in ('TRANSFER. PARA', 'ALTA') then 'saida'
        end as tipo_evento
    from {{ ref('stg_bronze__movimentacoes') }}
),

ordenado as (
    select
        *,
        lead(data_hora_movimentacao) over (
            partition by atendimento
            order by
                data_hora_movimentacao,
                case when tipo_evento = 'saida' then 0 else 1 end
        ) as data_hora_saida_unidade
    from movimentacoes
),

unidades_ocupadas as (
    select
        atendimento,
        hash_nm_paciente,
        tipo,
        unidade,
        data_hora_movimentacao as data_hora_entrada,
        data_hora_saida_unidade as data_hora_saida,
        timestamp_diff(data_hora_saida_unidade, data_hora_movimentacao, minute) as minutos_na_unidade,
        round(timestamp_diff(data_hora_saida_unidade, data_hora_movimentacao, minute) / 60.0, 1) as horas_na_unidade,
        round(timestamp_diff(data_hora_saida_unidade, data_hora_movimentacao, minute) / 1440.0, 1) as dias_na_unidade,
        upper(unidade) like '%UTI%' as eh_uti,
        safra_mes
    from ordenado
    where tipo_evento = 'entrada'
)

select * from unidades_ocupadas