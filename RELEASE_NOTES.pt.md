# NaviXav 1.4.15

Publicado em 2026-08-08.

## Correções

- Os pedidos sobre licenciamento comercial e contribuições utilizam agora o endereço de contacto dedicado ao NaviXav.
- A atualização automática passa a instalar-se realmente: o assistente que aguarda o fecho do NaviXav era lançado sem qualquer consola e morria de imediato, pelo que a atualização era anunciada como agendada e a aplicação reabria na versão anterior. O assistente mantém ainda o seu próprio registo junto do instalador, para que uma falha futura possa ser analisada.
- Os instaladores transferidos deixam de se acumular: cada atualização apaga os anteriores e o instalador faz o mesmo no final. Meio gigabyte tinha-se acumulado numa máquina acompanhada desde as primeiras versões. Os registos são mantidos, para que uma falha continue a poder ser analisada.

## Alterações

- Nettoyage des installateurs telecharges.
- Correctif mise a jour automatique.
- Update NaviXav contact email.

O instalador é verificado através da sua soma de verificação SHA-256 antes de qualquer atualização automática.
