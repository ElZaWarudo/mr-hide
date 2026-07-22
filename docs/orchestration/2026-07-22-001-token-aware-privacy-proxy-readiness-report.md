---
title: Token-Aware Privacy Proxy Readiness Report
status: blocked
date: 2026-07-22
---

# Token-Aware Privacy Proxy Readiness Report

## Context Found

| Source | Contribution | Confidence |
|---|---|---|
| Decisiones explícitas de la conversación del 22 de julio de 2026 | Define un proxy de privacidad autónomo y componible; Presidio para detectar datos sensibles; alias reversibles y token-amigables; upstream configurable; y tres comportamientos para tools. | High |
| Decisiones explícitas sobre tools | El modo predeterminado no transforma definiciones, argumentos ni resultados de tools. `--safe-tool-calls` los transforma con alias compactos en modalidad best effort. `--tool-compatibility` utiliza sustitutos mock realistas, secuenciales, coherentes y reversibles. | High |
| Decisiones explícitas sobre correspondencias | La misma entidad reutiliza su sustituto dentro de la conversación; entidades distintas consumen el siguiente valor libre del banco; las correspondencias viven en memoria con TTL y se eliminan al reiniciar. | High |
| Decisiones explícitas sobre posicionamiento | El producto no depende de OCGO, Headroom ni de un proveedor concreto; debe preservar la composición con cualquier upstream y no convertirse en router o compresor general. | High |
| Inspección del workspace `C:/Users/User/Documents/personal/mr-hide` | El directorio está vacío: no es repositorio Git y no contiene instrucciones, código, documentación, build, tests, CI ni convenciones de entrega. | High |
| Documentación oficial de Microsoft Presidio revisada durante la conversación | Confirma el modelo analyzer/anonymizer, operadores personalizados y la necesidad de gestionar externamente el estado de correspondencias. | Medium |

## Missing Context

- **Product intent:** faltan usuarios/personas prioritarios, escenarios operativos iniciales, criterios medibles de éxito y una lista cerrada de no-objetivos para el MVP.
- **Current system shape:** no existe todavía una aplicación, estructura de módulos, límites de procesos ni flujo ejecutable que permita ordenar trabajo sobre una base real.
- **Technical execution context:** no están confirmados el lenguaje/runtime, gestor de paquetes, framework HTTP, estrategia de concurrencia, sistemas operativos soportados ni comandos de build/test/lint.
- **Data and interface context:** faltan contratos precisos para las rutas compatibles, campos transformables por protocolo, SSE/WebSocket, compresión de cuerpos, propagación de cabeceras, errores, alcance de sesión, normalización de entidades y formato/versionado de bancos mock.
- **Security and privacy contract:** falta concretar fail-open/fail-closed por tipo de fallo, tratamiento de secretos frente a PII, retención/TTL, límites de logging, amenazas de correlación y garantías explícitas de cada modo de tools.
- **Delivery context:** no hay repositorio Git, rama de integración, CI, estrategia de versionado/publicación, plataforma de distribución ni convenciones de PR/release.
- **Existing scope context:** falta una frontera priorizada entre MVP y capacidades posteriores para impedir que compatibilidad multiprotocolo, streaming, persistencia y bancos mock entren simultáneamente sin una secuencia validada.

## Why Roadmap Generation Is Unsafe

- Elegir los primeros roadmap items exigiría inventar si el MVP comienza por OpenAI Responses, Chat Completions, Anthropic Messages o un transporte genérico.
- La estrategia de sesiones y reversión determina el diseño de estado, streaming y recuperación de tool calls; todavía no existe un contrato técnico verificable.
- La selección de stack y sistemas operativos cambia la integración con Presidio, el modelo de procesos y los comandos de verificación.
- Sin una definición de MVP no es posible decidir si los bancos mock, WebSockets y compatibilidad de tools son trabajo inicial, paquetes posteriores o extensiones.
- Sin Git, CI ni estrategia de release no puede proponerse una secuencia de ramas/PRs respaldada por evidencia.

## Blocking Questions

- ¿Quién es el usuario prioritario del MVP y qué cliente/protocolo debe funcionar primero?
- ¿Qué capacidades exactas pertenecen al MVP y cuáles quedan explícitamente fuera?
- ¿Cuál es el stack confirmado y cuáles son los sistemas operativos soportados inicialmente?
- ¿Cuál es el contrato de privacidad ante fallos de Presidio, transporte o restauración?
- ¿Cómo se identifica una conversación y cuánto dura su bóveda reversible?
- ¿Qué endpoints, formatos de streaming y campos JSON deben soportarse en la primera entrega?
- ¿Cómo se inicializarán Git, CI, versionado, distribución y la rama de integración?

## Recommended Documents

- Crear `docs/initiative-brief.md` como fuente de verdad inicial. Debe consolidar las decisiones ya validadas, cerrar el alcance del MVP y resolver usuarios, protocolos, stack, seguridad, sesiones y entrega.
- Después del brief, crear únicamente los contratos especializados que el brainstorm determine necesarios, probablemente `docs/api-contracts.md` y `docs/security-privacy-contract.md`; no deben anticiparse antes de cerrar el brief.

## Exact Next Prompt

```text
Use compound-engineering:ce-brainstorm to draft docs/initiative-brief.md for the token-aware Presidio privacy proxy from docs/orchestration/2026-07-22-001-token-aware-privacy-proxy-readiness-report.md. Preserve every validated product decision, separate MVP from deferred scope, and resolve the blocking questions without inventing behavior.
```
