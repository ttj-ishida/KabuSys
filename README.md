# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ群

---

## プロジェクト概要

KabuSys は日本株のデータ取得・品質管理・ファクター計算・AI ニュースセンチメント解析・市場レジーム判定・監査ログ等を含む、研究〜本番までのワークフローをサポートする Python モジュール群です。  
主要な設計方針として以下を重視しています：

- Look-ahead バイアスの排除（datetime.today()/date.today() を内部ループで参照しない実装）
- DuckDB を用いたローカルデータ格納・高速集計
- J‑Quants API との差分 ETL / レート制御・リトライ
- OpenAI（gpt-4o-mini 等）を利用したニュース NLP（JSON モード）とフェイルセーフなリトライ設計
- 監査（audit）スキーマによるシグナル→発注→約定のトレーサビリティ

バージョン: 0.1.0

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数のラッパー（settings オブジェクト）
- Data (データ層)
  - J‑Quants API クライアント（取得・保存・ページネーション・トークン自動リフレッシュ・レート制御）
  - ETL パイプライン（差分取得 / バックフィル / 品質チェック）
  - 市場カレンダー管理（営業日判定 / next/prev トレード日）
  - ニュース収集（RSS → raw_news、SSRF対策、トラッキングパラメータ除去）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ（signal_events / order_requests / executions）スキーマ生成・初期化
  - 汎用統計ユーティリティ（Zスコア正規化）
- Research（研究用）
  - ファクター計算（Momentum / Value / Volatility / Liquidity）
  - 特徴量探索・将来リターン計算 / IC（Information Coefficient）計測 / 統計サマリー
- AI（OpenAI 連携）
  - ニュースタイトル/記事のセンチメント解析（JSON mode を利用）
  - マクロニュースと ETF（1321）MA200 乖離を合成した「市場レジーム判定」

---

## セットアップ手順

推奨 Python バージョン: 3.10 以上（PEP 604 の union 型表記等を利用）

必要パッケージ（代表例）:
- duckdb
- openai
- defusedxml

例（venv を使う場合）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# 開発中: pip install -e .
```

環境変数（最低限必要なもの）
- JQUANTS_REFRESH_TOKEN: J‑Quants の refresh token
- KABU_API_PASSWORD: kabu ステーション API パスワード（必要なら）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）

デフォルトの DB パス（settings 経由で変更可能）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（デフォルト）

.env 自動読み込み
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を起点に .env → .env.local を読み込みます。
- 読み込みの優先順位: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには環境変数をセット:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（代表的な例）

以下は Python REPL / スクリプト内でライブラリを利用する例です。DuckDB 接続は `duckdb.connect()` を使います。

1) ETL（日次 ETL 実行）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース NLP（OpenAI を用いた銘柄ごとのニューススコア）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# api_key を直接渡すか、環境変数 OPENAI_API_KEY を設定する
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込み銘柄数: {n_written}")
```

3) 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

4) 監査 DB の初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions テーブルが作成されます
```

5) 設定値参照（settings）
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)  # KABUSYS_ENV により判定
```

注意点
- OpenAI 呼び出しは外部 API であるため、APIキーの管理やレート制御を行ってください。
- ETL や AI スコアリングは DB に書き込みを行います。実行前にバックアップやテスト DB を利用することを推奨します。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J‑Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャネル
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視設定
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — .env 自動読み込みを無効化

.env には必須変数を入れておくと便利です（.env.example を参考に作成してください）。

---

## ディレクトリ構成

主要なファイルを抜粋した構成（src/ 配下）

- src/kabusys/
  - __init__.py
  - config.py                       # 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py                    # ニュース NLP（記事→ai_scores）
    - regime_detector.py             # ETF MA200 + マクロニュースで市場レジーム算出
  - data/
    - __init__.py
    - jquants_client.py              # J‑Quants API クライアント（fetch/save）
    - pipeline.py                    # ETL パイプライン（run_daily_etl 等）
    - etl.py                         # ETL インターフェース再エクスポート
    - calendar_management.py         # 市場カレンダー（is_trading_day 等）
    - news_collector.py              # RSS 収集（SSRF 対策等）
    - stats.py                       # 統計ユーティリティ（zscore_normalize）
    - quality.py                     # 品質チェック（欠損/スパイク/重複/日付不整合）
    - audit.py                       # 監査ログスキーマ / 初期化
  - research/
    - __init__.py
    - factor_research.py             # Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py         # 将来リターン / IC / summary / rank
  - monitoring/ (将来的に監視周りのコード)
  - strategy/ (戦略実装用モジュール)
  - execution/ (約定 / 発注処理)
- pyproject.toml (プロジェクトルート検出対象)
- .env, .env.local (環境設定)

---

## 実装上の注意・設計ノート

- Look-ahead バイアス対策:
  - 内部処理は target_date に依存しており、datetime.today() を直接使用しない方針です。
  - ETL/研究で使用する場合は対象日の明示を推奨します。
- OpenAI 呼び出し:
  - JSON Mode を利用し、厳密な JSON レスポンスを期待しますが、パース失敗時はスコア 0.0 にフォールバックする等フェイルセーフ化しています。
  - API の一時的な失敗や 5xx はリトライ（指数バックオフ）します。
- J‑Quants クライアント:
  - レート制限を守るため固定間隔スロットリングを導入しています（120 req/min を想定）。
  - 401 受信時は refresh token による id_token 再取得を行い 1 回リトライします。
- DuckDB への保存は原則冪等（ON CONFLICT DO UPDATE / DO NOTHING）で行います。
- news_collector は SSRF 対策、レスポンスサイズ制限、XML 攻撃対策（defusedxml）など安全措置を施しています。

---

## テスト / 開発補助

- 自動 .env 読み込みを無効にしてテストしたい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しや外部 API 呼び出しはモックしやすいように内部でラップしてあり、ユニットテスト時に patch して差し替え可能です（例: kabusys.ai.news_nlp._call_openai_api, kabusys.ai.regime_detector._call_openai_api など）。
- DuckDB のインメモリ接続 ":memory:" を使うとテストが容易です（kabusys.data.audit.init_audit_db も対応）。

---

## 最後に

この README はコードベースの主要機能・設計方針と基本的な使い方をまとめたものです。実運用を行う際は必ず環境変数や API キーの管理、DB のバックアップ、テスト環境での十分な検証を行ってください。必要に応じて README をプロジェクト固有の運用手順に合わせて拡張してください。