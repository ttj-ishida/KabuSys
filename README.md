# KabuSys — 日本株自動売買システム

KabuSys は日本株向けのデータプラットフォーム・リサーチ・戦略実行を支援するライブラリ群です。  
主に以下の用途に対応します：データ ETL（J-Quants）、ニュース収集と NLP スコアリング、ファクター計算・特徴量解析、監査ログ（注文/約定トレーサビリティ）、市場レジーム判定など。

---

## 主要な機能（抜粋）

- データ取得 / ETL
  - J-Quants API から株価日足、財務、JPX カレンダー等を差分取得・DuckDB へ冪等保存
  - ETL パイプライン（run_daily_etl）と結果表現（ETLResult）

- データ品質管理
  - 欠損・重複・スパイク・日付不整合等の品質チェック（quality モジュール）

- ニュース収集・NLP
  - RSS ベースのニュース収集（news_collector）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント集約（news_nlp.score_news）
  - マクロニュースと MA200乖離を組み合わせた市場レジーム判定（ai.regime_detector.score_regime）

- リサーチ / ファクター
  - Momentum / Value / Volatility 等のファクター計算（research.factor_research）
  - 将来リターン計算、IC（Information Coefficient）等の特徴量解析（research.feature_exploration）
  - Zスコア正規化等の汎用統計ユーティリティ（data.stats）

- 監査ログ / トレーサビリティ
  - signal / order_request / executions を記録する監査スキーマ初期化・専用 DB (data.audit)

- 設定管理
  - .env / 環境変数の自動読み込み（config）、設定検証（必須変数チェック、環境／ログレベル等）

---

## 要件

- Python 3.10+（typing の union 表記や型ヒントに合わせて推奨）
- 主要依存（抜粋）:
  - duckdb
  - openai（OpenAI の新 SDK を使用する想定）
  - defusedxml
  - 標準ライブラリ（urllib, json, logging 等）

※ 実際のパッケージ名やバージョンはプロジェクトの pyproject.toml / requirements を参照してください。

---

## インストール（ローカル開発向け例）

1. 仮想環境を作成・アクティベート
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - pip install -e .   （ローカルパッケージとして開発インストールする場合）

---

## 環境変数 / .env

config モジュールはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して自動的に `.env` / `.env.local` を読み込みます（OS 環境変数が優先）。自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に必要な環境変数（必須）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知に使う Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI を利用する機能で使用（関数呼び出し時に引数で渡すことも可）

その他:
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- KABUSYS_ENV（development / paper_trading / live、デフォルト development）
- LOG_LEVEL（DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト INFO）

例 .env（参考、必ず .env.example を確認して生成してください）:
JQUANTS_REFRESH_TOKEN=...
OPENAI_API_KEY=...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...

---

## 使い方（代表的な例）

以下は Python スクリプトや REPL から呼び出す例です。各関数は DuckDB 接続を受け取ります。

1) DuckDB 接続を作る（デフォルトのパスを settings.duckdb_path から使う）
```python
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
```

2) ETL（日次パイプライン）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# target_date を指定しないと today が使われます
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

3) ニュースセンチメントスコア（OpenAI API キーは環境変数 OPENAI_API_KEY、もしくは api_key 引数）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

count = score_news(conn, target_date=date(2026,3,20))
print(f"scored {count} symbols")
```

4) 市場レジーム判定（MA200 と LLM による混合スコア）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))
```

5) 監査 DB を初期化（監査専用の DuckDB を作りたい場合）
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(settings.duckdb_path)  # 既存 DB に追加
# または init_audit_db(":memory:")
```

6) OpenAI キーを直接渡す場合
各 score_news / score_regime は api_key 引数を受けるので、テストやキー管理上の理由で環境変数を使いたくない場合は直接渡せます。

注意点:
- 各処理はルックアヘッドバイアス対策が組み込まれています（内部で date.today() を直接参照しない等）。
- OpenAI / J-Quants の API 呼び出しはリトライ・バックオフ・レート制御を備えていますが、API キーやレート制限に注意してください。

---

## よく使う関数一覧（参照用）

- data.pipeline
  - run_daily_etl(...) → ETLResult（株価・財務・カレンダー取得 + 品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl

- data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token

- data.news_collector
  - fetch_rss(url, source)  — RSS 取得＋前処理

- ai.news_nlp
  - score_news(conn, target_date, api_key=None)  — ニュースごとの ai_scores 書き込み

- ai.regime_detector
  - score_regime(conn, target_date, api_key=None)  — market_regime テーブル書き込み

- research.factor_research
  - calc_momentum / calc_volatility / calc_value

- research.feature_exploration
  - calc_forward_returns / calc_ic / factor_summary / rank

- data.audit
  - init_audit_schema / init_audit_db

- config
  - settings — 設定オブジェクト（settings.jquants_refresh_token 等）

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py — パッケージ初期化、バージョン情報
  - config.py — 環境変数 / .env の読み込みと Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの集約と OpenAI によるセンチメントスコア化、ai_scores への書き込み
    - regime_detector.py — MA200 とマクロニュースの LLM スコアを合成して market_regime を更新
  - data/
    - __init__.py
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポート
    - jquants_client.py — J-Quants API クライアント（取得・保存・トークン管理）
    - news_collector.py — RSS 取得・前処理・raw_news への保存（SSRF 対策等含む）
    - calendar_management.py — JPX カレンダー管理、営業日判定ユーティリティ
    - quality.py — データ品質チェック（欠損・重複・スパイク・日付不整合）
    - stats.py — Z スコア正規化など統計ユーティリティ
    - audit.py — 監査スキーマの DDL / 初期化（signal, order_requests, executions）
  - research/
    - __init__.py
    - factor_research.py — Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー
  - research/*, ai/*, data/* にある関数は DuckDB 接続を受け取り DB 内のテーブルを参照／更新します。

---

## 運用上の注意・設計方針（概要）

- Look-ahead バイアス回避: 各モジュールはデータの参照において将来データを参照しないよう設計されています（target_date を明示して差分を取る等）。
- 冪等性: DuckDB への保存は ON CONFLICT / DELETE→INSERT の方式で冪等性を確保。
- API 呼び出し: リトライや指数バックオフ、レートリミッティングを実装していますが、API のレート制限やエラーレスポンスに応じた運用が必要です。
- セキュリティ: news_collector は SSRF 対策や XML パースに対する防御を入れています。外部 URL を扱う際は注意してください。

---

必要であれば以下も提供できます：
- .env.example のサンプル
- 典型的な運用スケジュール（cron / Airflow 等）例
- テスト・CI 設定の雛形

ご要望があれば目的に合わせて README を拡張します（例: 部署向け運用手順やデプロイ手順など）。