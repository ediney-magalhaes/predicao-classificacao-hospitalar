with source as(
    select *
    from {{ source('bronze', 'bronze_movimentacoes_anonimizado') }}
),

renamed as(
    select
        atend as atendimento,
        hash_nm_paciente,
        safe.parse_datetime('%Y-%m-%d %H:%M:%S', data || ' ' || hora) as data_hora_movimentacao,
        tipo,
        origem,
        destino,
        unidade,
        tip_acom,
        cid,
        convenio,
        motivo_alta,
        safra_mes,
        data_ingestao
    from source
)

select * from renamed