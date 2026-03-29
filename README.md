# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォーム用ライブラリです。ETL による市場データ収集、ニュースの NLP スコアリング、ファクター計算、マーケットレジーム判定、監査ログ（トレーサビリティ）など、トレーディングプラットフォームで必要となる基本機能群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

本プロジェクトは以下の目的で設計されています。

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への冪等保存（ETL）
- RSS ベースのニュース収集と OpenAI を利用した銘柄別センチメント（ai_score）算出
- マーケットレジーム判定（ETF の MA 乖離 + マクロニュースの LLM スコア）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution）を残すスキーマと初期化ユーティリティ

設計上の特徴として、バックテストでのルックアヘッドバイアスを避けるために日付取得の取り扱いに注意を払っており、外部 API 呼び出しはリトライやレート制御、フェイルセーフが施されています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（認証・ページネーション・保存関数）
  - マーケットカレンダー管理（営業日判定、next/prev/get_trading_days）
  - ニュース収集（RSS -> raw_news）
  - データ品質チェック（missing / spike / duplicates / date consistency）
  - 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news：銘柄ごとの ai_score を生成）
  - 市場レジーム判定（score_regime：1321 の MA + マクロニュースで bull/neutral/bear を判定）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- 設定管理（kabusys.config）：.env 自動ロード、必須環境変数チェック
- 監視・通知（Slack トークン等：設定により連携可能）

---

## 必要な依存パッケージ（例）

- Python 3.9+
- duckdb
- openai
- defusedxml

実行環境によっては以下も必要になります（標準ライブラリで代替している部分もあります）：
- urllib（標準）
- datetime, json など（標準）

依存はプロジェクトに合わせて requirements.txt / pyproject.toml に追加してください。例:

pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン／取得します。

2. 仮想環境の作成（任意）:
   python -m venv .venv
   source .venv/bin/activate  # Linux / macOS
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール:
   pip install duckdb openai defusedxml

4. 環境変数 / .env を準備する:
   プロジェクトルート（.git や pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（kabusys.config が自動ロード）。

   自動ロードを無効にする場合:
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主要な環境変数（必須・任意）:
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
   - KABU_API_BASE_URL (任意) — kabuAPI ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN (必須) — Slack ボットトークン（通知連携用）
   - SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
   - DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH (任意) — SQLite パス（監視用など、デフォルト: data/monitoring.db）
   - KABUSYS_ENV (任意) — 環境: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL (任意) — DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
   - OPENAI_API_KEY (必須 for AI functions) — OpenAI API キー（score_news / score_regime で参照）

   .env の記述例:
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb

5. データベース初期化（監査ログ等）:
   監査ログ用 DB を作る例:
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可

---

## 使い方（代表的な API）

以下は主な操作の簡単な使用例です。実行前に必ず環境変数（特に API キー）を設定してください。

- DuckDB 接続の作成と ETL 実行（日次）

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# target_date を指定しなければ今日の日付を使います
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースに基づく銘柄別スコア算出

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数に設定されている前提
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジーム判定（ETF 1321 を利用）

```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算

```python
import duckdb
from datetime import date
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
factors = calc_momentum(conn, target_date=date(2026, 3, 20))
# factors は dict のリスト（date, code, mom_1m, mom_3m, mom_6m, ma200_dev）
```

- 監査ログスキーマの初期化（既存 DB に追加）

```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

注意:
- AI 関連関数（score_news, score_regime）は OpenAI API を呼び出します。API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- ETL / API 呼び出しにはレート制御・リトライやフェイルセーフが組まれていますが、実運用ではログ監視とエラーハンドリングが重要です。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要モジュールと簡単な説明です。パスは src/kabusys 以下を想定しています。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み、settings オブジェクトを提供
  - ai/
    - __init__.py
    - news_nlp.py       — ニュースから銘柄別センチメントを算出（OpenAI 使用）
    - regime_detector.py — マーケットレジーム判定（MA + LLM）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存）
    - pipeline.py       — ETL パイプライン（run_daily_etl 等）
    - etl.py            — ETLResult の再公開インターフェース
    - news_collector.py — RSS からニュース収集（SSRF 対策等）
    - calendar_management.py — マーケットカレンダー管理 / 営業日判定
    - quality.py        — データ品質チェック
    - stats.py          — 統計ユーティリティ（zscore_normalize）
    - audit.py          — 監査ログ（スキーマ定義と初期化）
  - research/
    - __init__.py
    - factor_research.py    — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー等

---

## 動作設計上の注意点・運用メモ

- 設定管理
  - .env / .env.local はプロジェクトルート（.git または pyproject.toml がある場所）から自動読み込みされます。既存の OS 環境変数は上書きされません。.env.local は .env より優先して上書きされます。
  - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テストで有用）。

- Look-ahead バイアス対策
  - モジュールの多くは datetime.today() / date.today() を直接参照せず、呼び出し元が target_date を明示的に渡すことを想定しています。バックテストでの利用時は target_date を適切に指定してください。

- フェイルセーフ
  - OpenAI / J-Quants API 呼び出しではリトライ・バックオフ・フォールバックが実装されています。AI の失敗時はスコアをゼロにフォールバックする等、継続可能な設計です。

- テスト
  - OpenAI 呼び出しやネットワーク I/O 部分はモックしやすいように内部呼び出しが分離されています（ユニットテストでの差し替えを推奨）。

---

## 参考・拡張ポイント

- Slack 連携や監視ツールへの通知は現状設定のみを提供しています。具体的な通知フローは運用スクリプト側で実装してください。
- DuckDB スキーマ（raw_prices / raw_financials / market_calendar / ai_scores / market_regime 等）は ETL を動かす際に期待される構造があるため、初期スキーマ定義を用意しておくことを推奨します（プロジェクト配布時に schema 初期化スクリプトを追加することが望ましい）。
- バックテスト環境で利用する際は、取得日時（fetched_at）や market_calendar の扱いに注意してください（look-ahead を避けるために過去時点の状態を再現する必要があります）。

---

もし README に「セットアップ用のスクリプト」「サンプル .env.example」「schema 初期化 SQL」などを追加したい場合は、必要なフォーマット（例: pyproject.toml / requirements.txt / Dockerfile）や具体的な運用シナリオ（開発環境 / 本番 / paper_trading）を教えてください。README をその内容に合わせて拡張します。