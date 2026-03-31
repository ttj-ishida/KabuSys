# KabuSys — 日本株自動売買プラットフォーム（README）

KabuSys は日本株向けのデータプラットフォーム／リサーチ／自動売買基盤を想定した Python パッケージです。本リポジトリはデータ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI を利用したセンチメント）、ファクター計算、監査ログ（発注→約定のトレース）などの主要コンポーネントを含みます。

---

## プロジェクト概要
- 目的：日本株データの ETL、品質管理、AI ベースのニュースセンチメント、ファクター研究、監査トレース機能を備えた自動売買基盤のコア機能群を提供する。
- 設計方針の要点：
  - ルックアヘッドバイアスを避ける（内部で `date.today()` を直接参照しない等の実装方針）。
  - DuckDB を主な永続 DB として利用（軽量で高速な分析用 DB）。
  - J-Quants API の利用（取得は rate limiter + リトライ付き）。
  - OpenAI（gpt-4o-mini）を用いたニュース NLP / マクロ判定（エラー時はフォールバックして継続する設計）。
  - 監査ログ（signal → order_request → executions の完全トレース）を DuckDB に保存。
  - 冪等性（ON CONFLICT / idempotent 保存）を重視。

---

## 主な機能一覧
- 環境設定管理（環境変数 / .env 自動ロード）
- J-Quants API クライアント（株価 / 財務 / カレンダー取得、保存用関数）
- ETL パイプライン（日次 ETL 実行、差分取得、品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- ニュース収集（RSS → raw_news、SSRF/サイズ制限/トラッキング除去 対策）
- ニュース NLP（OpenAI を使った銘柄別センチメント score_news）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメントで regime 判定）
- リサーチ機能（モメンタム / ボラティリティ / バリュー等のファクター計算）
- 監査ログ初期化・DB（signal_events, order_requests, executions）
- 汎用統計ユーティリティ（Zスコア正規化）

---

## 必要条件
- Python 3.10 以上（typing の `X | Y` 構文などを使用）
- 推奨ライブラリ（pip インストール）:
  - duckdb
  - openai
  - defusedxml
  - その他標準ライブラリの利用（urllib 等）

例：
pip install duckdb openai defusedxml

（実運用ではロギングやSlack連携等に追加パッケージが必要になる可能性があります）

---

## 環境変数（.env）
プロジェクトは .env / .env.local をプロジェクトルートから自動で読み込みます（OS 環境変数を優先）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（必須/任意）：
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意, default: development) — 有効値: development / paper_trading / live
- LOG_LEVEL (任意, デフォルト: INFO) — DEBUG/INFO/WARNING/ERROR/CRITICAL
- OPENAI_API_KEY (AI 機能利用時に必要)

例 (.env.example)
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順（開発用の簡易手順）
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml
   - （その他、運用で使うパッケージがあれば追加）
4. プロジェクトルートに .env を作成（上記の環境変数を設定）
   - 簡易例は .env.example を参照
5. DuckDB ファイルのディレクトリ作成（必要なら）
   - mkdir -p data

---

## 使い方（代表的なユースケース）

※以下は Python REPL / スクリプトでの利用例です。実行前に環境変数（J-Quants / OPENAI 等）を設定してください。

1) DuckDB に接続して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント（OpenAI 必須）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定しておくか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

3) 市場レジーム判定（1321 の MA200 とマクロセンチメントを合成）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログテーブルの初期化（監査用 DB 作成）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions が作成されます
```

5) リサーチ関数（例：モメンタム計算）
```python
import duckdb
from datetime import date
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は各銘柄ごとの dict のリスト
```

---

## 自動 .env 読み込みについて
- パッケージ初期化時にプロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` と `.env.local` を自動で読み込みます。
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- テストや特殊環境で自動読み込みを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 主要モジュール / API（概要）
- kabusys.config
  - settings: 環境変数読み込み・プロパティ（jquants_refresh_token, duckdb_path, env, is_live 等）
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token (J-Quants 認証)
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult 型
- kabusys.data.quality
  - run_all_checks / check_missing_data / check_spike / check_duplicates / check_date_consistency
- kabusys.data.news_collector
  - fetch_rss / preprocess_text / トラッキング除去・SSRF 対策付き RSS 収集
- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)
- kabusys.research.factor_research / feature_exploration / data.stats
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / zscore_normalize
- kabusys.data.audit
  - init_audit_schema / init_audit_db

---

## ディレクトリ構成（抜粋）
プロジェクト内の主要ファイル構成は次の通りです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - quality.py
    - calendar_management.py
    - news_collector.py
    - stats.py
    - audit.py
    - pipeline.py
    - etl.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/（その他ユーティリティ）
  - data/（各種データ処理モジュール）

（README では主要モジュールのみを列挙しています。詳細はソースコードを参照してください）

---

## 運用上の注意 / 補足
- OpenAI API を使う機能（news_nlp / regime_detector）は API 利用料金とレイテンシに注意してください。エラー時はフェイルセーフ（0.0 スコア）で継続する設計ですが、運用上のアラートは必須です。
- J-Quants API のレート制限（120 req/min）を尊重してください。jquants_client は内部でスロットリングを行いますが、複数プロセスで同一 API を叩く場合は追加の配慮が必要です。
- DuckDB の executemany の挙動（バージョン差）がコードに考慮されていますが、実際の環境での互換性確認を推奨します。
- 監査テーブルは削除を想定していません（トレース目的）。バックアップ戦略を検討してください。
- 本リポジトリのコードはベースライン実装です。実運用前に十分なテスト（特に API 認証、DB スキーマ、外部接続周り）を行ってください。

---

フィードバックや質問があれば教えてください。README のサンプル .env.example や具体的な実行スクリプトを追加で作成できます。