# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
データ収集（J-Quants）、ニュース収集・NLP（OpenAI）、ファクター計算、ETL、監査ログ、マーケットカレンダー管理、研究用ユーティリティなどを含みます。

本 README はコードベース（src/kabusys 以下）に基づく概要・機能・セットアップ・使い方・ディレクトリ構成を記載します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム／データプラットフォームを構築するためのライブラリ群です。主な目的は次の通りです。

- J-Quants API からのデータ取得（株価、財務、マーケットカレンダー）
- RSS ベースのニュース収集と前処理（SSRF防止・トラッキング除去）
- OpenAI を用いたニュースセンチメント/マクロセンチメント評価（gpt-4o-mini を想定）
- ETL パイプライン（差分取得・品質チェック・保存）
- 研究向けファクター計算、前方リターン、IC などの統計ユーティリティ
- 発注/約定に関する監査ログスキーマ（DuckDB）
- マーケットカレンダーと営業日ロジック

設計方針として「ルックアヘッドバイアスを排除する」「DB での冪等保存」「外部 API 呼び出しはリトライ/フェイルセーフで扱う」を重視しています。

---

## 主な機能一覧

- 環境設定読み込み（.env/.env.local、自動ロード、保護キー） — kabusys.config
- J-Quants API クライアント（取得・保存・トークン自動リフレッシュ・レート制御） — kabusys.data.jquants_client
- ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl） — kabusys.data.pipeline
- データ品質チェック（欠損・スパイク・重複・日付不整合） — kabusys.data.quality
- マーケットカレンダー管理（営業日判定、next/prev/get） — kabusys.data.calendar_management
- RSS ニュース収集と前処理（SSRF対策、トラッキング除去、記事ID生成） — kabusys.data.news_collector
- ニュース NLP（銘柄ごとのセンチメントスコア蓄積） — kabusys.ai.news_nlp.score_news
- 市場レジーム判定（ETF 1321 の MA とマクロニュースを LLM で合成） — kabusys.ai.regime_detector.score_regime
- 研究用ファクター計算（momentum/value/volatility 等） — kabusys.research
- 統計ユーティリティ（Zスコア正規化、rank, IC, summary） — kabusys.data.stats / kabusys.research.feature_exploration
- 監査ログスキーマ初期化・専用 DB 作成 — kabusys.data.audit

---

## 必要環境 / 依存パッケージ

- Python 3.10+
- 依存（代表例）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外の HTTP 周りは urllib を使用）
- その他、プロジェクト独自の import などに合わせて必要なパッケージを追加してください。

インストール例（仮に requirements.txt が用意されていない場合の参考）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 開発インストール（パッケージ化されていれば）
pip install -e .
```

---

## 環境変数（重要）

以下の環境変数が利用されます。必須のものは明示します（未設定時に ValueError が発生します）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — 環境: development / paper_trading / live （デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite パス（monitoring 用、デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると .env 自動ロードを無効化

OpenAI:
- OPENAI_API_KEY — OpenAI API を利用する機能（news_nlp / regime_detector）が必要とします。
  - score_news / score_regime の引数 api_key を渡すことでオーバーライド可能

.env の自動読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）から .env と .env.local を読み込みます（OS 環境変数が優先）。
- テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. Python 仮想環境を作成・有効化
3. 必要パッケージをインストール（上記参照）
4. プロジェクトルートに .env を作成（.env.example を参照することを想定）
   - 必須環境変数を設定する（JQUANTS_REFRESH_TOKEN など）
5. DuckDB 用ディレクトリを作成（例: mkdir -p data）
6. （必要なら）監査用 DB 初期化やスキーマ作成を行う

例 .env（参考）:

```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（例）

以下は Python スクリプトや REPL での利用例です。いずれも duckdb の接続を渡して使用します。

- 日次 ETL 実行（株価/財務/カレンダーの差分取得＋品質チェック）:

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコア付け（ai_scores テーブルへの書き込み）:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を使用
print(f"書き込み件数: {written}")
```

- 市場レジーム判定（market_regime への書き込み）:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化（専用 DB）:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

- マーケットカレンダー操作例:

```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

---

## ディレクトリ構成（主要ファイルと説明）

プロジェクトは src/kabusys 配下に実装されています。主要ファイル／モジュールは以下の通りです。

- src/kabusys/__init__.py
  - パッケージ定義。バージョン情報と主要サブパッケージのエクスポート。

- src/kabusys/config.py
  - .env 自動読み込み、環境変数の取得・検証（Settings クラス）。

- src/kabusys/ai/
  - __init__.py
  - news_nlp.py
    - ニュース記事を統合して OpenAI に投げ、銘柄ごとの ai_scores を作成。
    - calc_news_window / score_news / _score_chunk 等を提供。
  - regime_detector.py
    - ETF (1321) の MA 乖離とマクロニュースの LLM センチメントを合成して market_regime を判定。

- src/kabusys/data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（取得・保存関数、トークン管理、レート制御）。
  - pipeline.py
    - ETL のメイン処理（run_daily_etl など）と ETLResult。
  - etl.py
    - ETLResult の再エクスポート。
  - news_collector.py
    - RSS 収集・前処理・SSRF 対策・記事ID生成。
  - calendar_management.py
    - market_calendar 管理、営業日判定、calendar_update_job。
  - stats.py
    - 汎用統計ユーティリティ（zscore_normalize）。
  - quality.py
    - データ品質チェック（欠損・スパイク・重複・日付不整合）。
  - audit.py
    - 監査ログスキーマの DDL 定義と初期化ユーティリティ（init_audit_schema/init_audit_db）。

- src/kabusys/research/
  - __init__.py
  - factor_research.py
    - momentum / value / volatility ファクター計算（DuckDB SQL ベースで計算）。
  - feature_exploration.py
    - 将来リターン計算、IC（Spearman）計算、rank / factor_summary。

- その他
  - パッケージでは openai, duckdb, defusedxml など外部パッケージを利用。

---

## 開発上の注意点 / 設計上のポイント

- ルックアヘッドバイアス回避:
  - 多くの処理（ニュース窓、MA 計算、ETL）は datetime.today() の直接参照を避け、明示的な target_date を用います。バックテスト等での再現性を保つためです。
- 冪等性:
  - DB への保存は ON CONFLICT DO UPDATE などで基本的に冪等に行います。
- フェイルセーフ:
  - 外部 API（OpenAI, J-Quants）呼び出しはリトライやフォールバックを実装し、完全停止を避ける設計です（ただし不可欠なキー未設定は ValueError を送出します）。
- セキュリティ:
  - news_collector は SSRF 対策（リダイレクト検査、プライベートIP検出）、XML パースに defusedxml を使用、レスポンスサイズ制限等を実装しています。

---

## 参考: よくある運用コマンド

- ETL を Cron / バッチで実行する場合は、仮想環境を有効化して Python スクリプトから run_daily_etl を呼ぶのが基本です。
- OpenAI 呼び出しを多用する部分（news_nlp, regime_detector）は API コストに注意してバッチ処理を設計してください。

---

## 最後に

この README はコード中のドキュメント文字列（docstring）を元に作成しています。実行環境や API キーなど機密情報の管理には十分ご注意ください。必要であれば .env.example のテンプレートや追加の運用手順（systemd / cron / Dockerfile / CI）を別途作成します。