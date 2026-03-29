# KabuSys

日本株向けの自動売買 / データパイプライン基盤ライブラリです。  
DuckDB をデータレイヤに採用し、J-Quants API や RSS、OpenAI（LLM）を利用してデータ取得・品質チェック・AI スコアリング・市場レジーム判定・監査ログ管理などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的で設計されたモジュール群を含みます。

- 市場データ（株価／財務／マーケットカレンダー）の差分 ETL と保存（J-Quants API）
- ニュース収集（RSS）と NLP に基づく銘柄センチメント算出（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースセンチメントの合成）
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ等）と特徴量解析ユーティル
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → execution）のスキーマ初期化と管理
- 環境変数管理（.env の自動読込、Settings オブジェクト）

設計方針の例:
- ルックアヘッドバイアスを避ける（内部で date.today() を盲目的に参照しない）
- DuckDB を用いた効率的な SQL 処理
- 外部 API 呼び出しはリトライ・レート制御・フェイルセーフを実装

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save: daily quotes, financials, market calendar, listed info）
  - ニュース収集（RSS -> raw_news、SSRF 対策、ID 生成）
  - カレンダー管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）
  - 品質チェック（missing_data, duplicates, spike, date consistency, run_all_checks）
  - 監査ログ初期化（init_audit_schema, init_audit_db）
  - 汎用統計（zscore_normalize）
- ai
  - ニュース NLP スコアリング（score_news）
  - 市場レジーム判定（score_regime）
  - OpenAI を用いた JSON Mode 呼び出し（gpt-4o-mini）
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - Settings クラスによる環境変数アクセスと .env 自動読み込みロジック

---

## セットアップ手順（開発 / 実行環境）

1. Python 環境を作成（例: venv）
   - python3 -m venv .venv
   - source .venv/bin/activate

2. 依存パッケージをインストール
   - 必要なパッケージ（本コードベースから推定）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt/pyproject.toml があればそちらを使ってください）

3. パッケージを editable インストール（オプション）
   - pip install -e .

4. 環境変数の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと、自動で読み込まれます（config.py の自動読み込み）。
   - 自動 `.env` 読み込みを無効にするには:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 必須環境変数（.env に記載例）
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - OPENAI_API_KEY=...  （AI モジュールを使う場合）
   - KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
   - LOG_LEVEL=INFO|DEBUG|...  （デフォルト: INFO）
   - DUCKDB_PATH=data/kabusys.duckdb  （デフォルト）
   - SQLITE_PATH=data/monitoring.db  （モニタリング DB）
   - (任意) KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   注意: Settings クラスは必須キー未設定時に ValueError を投げます（例: settings.jquants_refresh_token）。

---

## 使い方（コード例）

以下は主要 API の簡単な利用例です。DuckDB 接続には `duckdb.connect()` を使用します。

- 日次 ETL を実行する
  - 目的: 市場カレンダー / raw_prices / raw_financials を差分取得して保存し品質チェックを実行
  - 例:
    ```python
    import duckdb
    from datetime import date
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())
    ```

- ニュース NLP スコアリング（OpenAI を利用）
  - 前提: OPENAI_API_KEY が環境変数に設定されているか、api_key 引数で渡す
  - 例:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    written = score_news(conn, target_date=date(2026, 3, 20))
    print(f"書き込んだ銘柄数: {written}")
    ```

- 市場レジーム判定
  - 例:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 3, 20))
    ```

- 監査ログ DB の初期化
  - 例:
    ```python
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # これで監査用テーブルが作成されます
    ```

- 研究用ファクター計算
  - 例:
    ```python
    from kabusys.research.factor_research import calc_momentum
    import duckdb
    from datetime import date

    conn = duckdb.connect("data/kabusys.duckdb")
    momentum = calc_momentum(conn, target_date=date(2026,3,20))
    # momentum は dict のリスト（date, code, mom_1m, ...）
    ```

---

## 主要モジュール / ディレクトリ構成

以下はパッケージ内の主要ファイル構成（src/kabusys 以下）です。重要モジュールを抜粋しています。

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py          # ニュースから銘柄別スコアを生成
    - regime_detector.py   # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py    # J-Quants API クライアント（fetch/save）
    - pipeline.py          # ETL パイプライン（run_daily_etl 等）
    - etl.py               # ETL 型（ETLResult 再エクスポート）
    - news_collector.py    # RSS 収集・前処理
    - calendar_management.py  # 市場カレンダー管理
    - quality.py           # データ品質チェック
    - stats.py             # 統計ユーティリティ（zscore_normalize）
    - audit.py             # 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py   # モメンタム / バリュー / ボラティリティ
    - feature_exploration.py  # forward returns / IC / summary / rank
  - research/*

上記に加え、ユーティリティやモジュール間の補助関数が含まれます。

---

## 環境変数と設定（まとめ）

主な環境変数:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- OPENAI_API_KEY (AI 機能使用時)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live、デフォルト: development)
- LOG_LEVEL (DEBUG|INFO|...、デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

config.Settings を通じてコード内からアクセスできます（例: from kabusys.config import settings; settings.jquants_refresh_token）。

---

## 注意点 / トラブルシューティング

- 必須環境変数が未設定だと settings プロパティで ValueError が投げられます。エラーメッセージに従って .env を用意してください。
- OpenAI を使う関数（score_news, score_regime）は API 呼び出しを伴います。API キーの設定と利用料金に注意してください。テスト時は関数内の _call_openai_api をモック可能です。
- J-Quants API はレート制限とリトライ処理が組み込まれています。get_id_token は refresh token を用いて id token を取得します。
- News Collector は SSRF 対策・gzip 大きさチェック・XML 脆弱性対策を行っています。RSS の取得で例外が上がる場合はログを確認してください。
- DuckDB バージョン差異により executemany の空リストがエラーになる制約に注意（pipeline/news_nlp 等で guard 処理あり）。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を起点）を探索します。テストで読み込みを抑制するには KABUSYS_DISABLE_AUTO_ENV_LOAD を使ってください。

---

必要であれば、README に実行コマンドや CI/デプロイ手順、.env.example のテンプレート、よくあるエラーと対処法などを追加します。どの情報を優先して追記しますか？