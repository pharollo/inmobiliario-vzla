# Explorador inmobiliario Venezuela

2.372 avisos de locales, galpones y oficinas cosechados en septiembre de 2026 de
portales inmobiliarios venezolanos (ZonaVen, bienesonline, mercadopiso) y de
Facebook Marketplace.

Abrir: https://pharollo.github.io/inmobiliario-vzla/

## Notas

- Precios **pedidos**, no cerrados.
- El «desvío» compara cada aviso con la mediana de su estado y banda de tamaño.
- El «repago» supone que el local se alquila a la mediana de su banda: es
  **modelado**, nunca observado.
- Las fuentes **no se pueden promediar entre sí**: cubren zonas distintas y sus
  precios difieren hasta 2,5× dentro de la misma banda. Filtra por una sola
  fuente si vas a comparar $/m².
- Los teléfonos escritos dentro de los títulos van enmascarados.
- Página marcada `noindex`; no se pretende que aparezca en buscadores.

## Mantenimiento

`cosechar.py` corre solo cada lunes en GitHub Actions y recosecha **ZonaVen**.

Las otras tres fuentes están congeladas porque no responden a IPs de datacenter:
mercadopiso y bienesonline devuelven 403 o vacío desde el runner, y Facebook
Marketplace exige sesión en un navegador.

Para refrescar bienesonline hay que hacerlo **desde una máquina con IP doméstica**:

    python3 recosechar_bien.py     # actualiza datos/congelado.json
    git commit -am "..." && git push
    gh workflow run semanal.yml    # reconstruye la página

Marketplace y mercadopiso no tienen equivalente automático.
