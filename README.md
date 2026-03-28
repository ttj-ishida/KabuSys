# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL、ニュース収集・NLP、ファクター研究、監査ログ、取引監視などを含む一連のユーティリティ群を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの株価・財務・マーケットカレンダーの差分取得（ETL）
- RSS ベースのニュース収集と前処理（SSRF・サイズ制限・トラッキング除去等の安全設計）
- OpenAI を用いたニュースセンチメント（銘柄別 ai_score）およびマクロセンチメントによる市場レジーム判定
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ初期化・管理

設計方針として「ルックアヘッドバイアス防止」「冪等性」「フォールバック（DB未取得時の挙動）」「APIリトライ/レート制御/フェイルセーフ」を重視しています。

---

## 主な機能一覧

- data
  - ETL：run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント（取得 + DuckDB 保存 & リトライ・レート制御）
  - 市場カレンダー管理（is_trading_day, next_trading_day, prev_trading_day 等）
  - ニュース収集（RSS -> raw_news, news_symbols）
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計（zscore_normalize）
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント取得・ai_scores への保存
  - regime_detector.score_regime: ETF（1321）MA200 とマクロニュース（LLM）を合成して market_regime を書き込み
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数および .env 自動ロード / 必須項目チェック（settings オブジェクト）

---

## 要件（推奨）

- Python 3.10+（型アノテーションや一部の構文を使用）
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- （標準ライブラリ以外は pip で導入してください）

例（最低限）:
pip install duckdb openai defusedxml

※ 実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください。

---

## セットアップ手順

1. リポジトリをクローンしてパッケージをインストール
   - 開発時（editable）
     - pip install -e .
   - または必要パッケージをインストール
     - pip install duckdb openai defusedxml

2. 環境変数を設定
   - 必須（アプリ起動や一部機能で必要）
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - OPENAI_API_KEY : OpenAI API キー（score_news / score_regime で利用）
     - KABU_API_PASSWORD : kabuステーション API パスワード（発注等で利用）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID : Slack 通知に使用する場合
   - 任意（デフォルト値が設定されているもの）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
     - DUCKDB_PATH : デフォルト data/kabusys.duckdb
     - SQLITE_PATH : デフォルト data/monitoring.db

   推奨: プロジェクトルートに .env または .env.local を置くと自動で読み込まれます。
   読み込み順は OS 環境変数 > .env.local > .env。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

3. DuckDB ファイルの親ディレクトリ作成（必要に応じて）
   - 例: mkdir -p data

4. 監査ログ DB 初期化（任意）
   - from kabusys.data.audit import init_audit_db
   - conn = init_audit_db("data/audit.duckdb")

---

## 使い方（サンプル）

以下は簡単な利用例です。実行には環境変数（特に OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN）が必要です。

- DuckDB に接続して日次 ETL を実行する

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの NLP スコアリング（ai_scores に保存）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n}")
```

- 市場レジーム判定（market_regime に保存）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB を新規作成して初期化する

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は初期化済み DuckDB 接続
```

- 市場カレンダー / 営業日判定例

```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点:
- score_news / score_regime は OpenAI を呼び出します。api_key を引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- ETL や保存処理は DuckDB に対して冪等に行う設計です（ON CONFLICT DO UPDATE 等）。

---

## 環境変数一覧（主要なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- OPENAI_API_KEY (score_news/score_regime 必須) — OpenAI API キー
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注関連）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — Slack 通知設定
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視DB）パス（default: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development | paper_trading | live）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（値を設定すれば無効）

.env のパースはシェル風の export KEY=val 形式やクォートを考慮して堅牢に行われます。

---

## ディレクトリ構成（主なファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境設定の自動ロード / Settings
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py — ETL パイプラインと ETLResult
    - etl.py — ETL の公開インターフェース（ETLResult 再エクスポート）
    - jquants_client.py — J-Quants API クライアント（取得・保存）
    - news_collector.py — RSS 取得・前処理・raw_news 保存
    - calendar_management.py — market_calendar 管理・営業日判定
    - quality.py — データ品質チェック
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - audit.py — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - (その他) strategy, execution, monitoring などのパッケージが __all__ に想定されています

---

## 運用上の注意 / よくある質問

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を探索）基準で行われます。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しはリトライ・バックオフを備えていますが、API 料金やレート制限には注意してください。score_news はバッチ処理（最大 20 銘柄/コール）で送ります。
- J-Quants API はレート制限を守る実装（120 req/min）です。get_id_token はリフレッシュ対応します。
- DuckDB の executemany に関する互換性（空リスト不可）をコード中で考慮しています。
- 全てのタイムスタンプは UTC で保存する設計が一部のモジュールで前提になっています（audit.init で SET TimeZone='UTC'）。

---

必要であれば、README に実際の起動スクリプト例（cron / systemd / Dockerfile / GitHub Actions など）や、詳細なテーブルスキーマ、サンプル .env.example を追記できます。どの情報を優先して追加しますか？