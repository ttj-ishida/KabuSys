# KabuSys

KabuSys は日本株向けのデータパイプライン・リサーチ・ニュースNLP・市場レジーム判定・監査ログなどを備えた自動売買システムのライブラリ群です。DuckDB をデータストアとして利用し、J-Quants API や OpenAI（LLM）を組み合わせて市場情報の収集・品質チェック・AIスコアリング・研究用ファクター計算を提供します。

バージョン: 0.1.0

---

## 主な機能

- データ取得 / ETL
  - J-Quants API からの株価（日足）、財務データ、JPX カレンダー取得（ページネーション対応、レート制御、トークン自動リフレッシュ、冪等保存）
  - 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- データ品質チェック
  - 欠損値、重複、スパイク、日付不整合などの検出（QualityIssue オブジェクト）
- ニュース収集・NLP
  - RSS 取得・前処理（SSRF 対策、トラッキングパラメータ除去、サイズ制限）
  - OpenAI を用いた銘柄別ニュースセンチメント（news_nlp.score_news）
- 市場レジーム判定
  - ETF(1321) の 200 日移動平均乖離とマクロニュースセンチメントを合成して日次レジーム（bull / neutral / bear）算出（ai.regime_detector.score_regime）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research.*）
  - 将来リターン計算・IC（Information Coefficient）・Z スコア正規化等
- 監査ログ（トレーサビリティ）
  - signal_events, order_requests, executions などの監査テーブルと初期化ユーティリティ（data.audit）
- 設定管理
  - .env 自動ロード（プロジェクトルート検出）と Settings API（kabusys.config.settings）

---

## 必要条件・依存ライブラリ

最低限必要な Python パッケージ（例）:
- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml

実行環境により追加ライブラリが必要になる場合があります（例: requests 等）。requirements.txt が無い場合は上記を個別にインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   - もし requirements.txt があれば:
     ```
     pip install -r requirements.txt
     ```
   - 手動で:
     ```
     pip install duckdb openai defusedxml
     ```

4. 環境変数（.env）を作成
   - プロジェクトルート（.git / pyproject.toml があるディレクトリ）に `.env` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（Settings 参照）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
     - OPENAI_API_KEY（score_news / regime_detector を使う場合）
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

---

## 使い方（クイックスタート）

以下は主要ユースケースの簡単な例です。

- DuckDB 接続を用意して日次 ETL を実行する:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントをスコアリングする:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  num_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数 OPENAI_API_KEY を利用
  print("written codes:", num_written)
  ```

- 市場レジームを判定して書き込む:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログ DB を初期化する:
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算:
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026,3,20))
  volatility = calc_volatility(conn, date(2026,3,20))
  value = calc_value(conn, date(2026,3,20))
  ```

- 設定の参照:
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

注意:
- LLM 呼び出し（OpenAI）は API キーが必要です。api_key 引数で明示するか環境変数 OPENAI_API_KEY を設定してください。
- 各関数は DuckDB の所定テーブル（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, market_regime, market_calendar 等）を前提としています。スキーマの初期化は別途用意するか、ETL 実行時に想定テーブルを作成してください。

---

## 設定（.env と自動ロード）

- パッケージ起動時にプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動ロードします。
- 自動ロードを無効化するには:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- Settings（kabusys.config.Settings）で取得可能な主要項目:
  - jquants_refresh_token: J-Quants リフレッシュトークン（必須）
  - kabu_api_password, kabu_api_base_url
  - slack_bot_token, slack_channel_id
  - duckdb_path, sqlite_path
  - KABUSYS_ENV (development / paper_trading / live)
  - LOG_LEVEL

---

## 主要 API / モジュール一覧（抜粋）

- kabusys.config
  - settings: 環境変数ラッパー
- kabusys.data
  - jquants_client: API 呼び出し・保存関数（fetch_* / save_*）
  - pipeline: run_daily_etl, run_prices_etl, run_financials_etl, ETLResult
  - news_collector: RSS 取得・前処理
  - calendar_management: 市場カレンダー管理・営業日判定
  - quality: データ品質チェック（check_missing_data, check_spike, ...）
  - audit: 監査テーブル初期化（init_audit_schema, init_audit_db）
  - stats: zscore_normalize
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメント取得・ai_scores へ保存
  - regime_detector.score_regime: 市場レジーム算出・market_regime へ保存
- kabusys.research
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank
- その他
  - kabusys.data.pipeline.ETLResult: ETL 実行結果の構造

---

## ディレクトリ構成（主要ファイル）

（リポジトリ内の src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py                 - パッケージ定義（バージョン: 0.1.0）
  - config.py                   - 環境変数 / 設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py               - ニュース NLP（score_news）
    - regime_detector.py        - 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py         - J-Quants API クライアント（fetch / save）
    - pipeline.py               - ETL パイプライン（run_daily_etl 他）
    - etl.py                    - ETL インターフェース（ETLResult 再エクスポート）
    - news_collector.py         - RSS ニュース収集
    - calendar_management.py    - マーケットカレンダー管理（営業日判定等）
    - quality.py                - データ品質チェック
    - stats.py                  - 統計ユーティリティ（zscore_normalize）
    - audit.py                  - 監査テーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py        - Momentum/Value/Volatility などのファクター計算
    - feature_exploration.py    - 将来リターン・IC・統計サマリー等

---

## 開発・貢献

- 大きな変更は Issue / PR を通してください。
- テスト時は .env 自動ロードを無効化することが推奨されます:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI や外部 API を呼ぶコードはモック可能な設計になっています（内部の _call_openai_api 等を patch して差し替えられます）。

---

必要であれば README に含める追加情報（例: データベーススキーマ、実運用時の運用手順、Slack 通知の使い方、詳細な関数引数一覧など）を追記できます。どの情報を優先して追記しましょうか？