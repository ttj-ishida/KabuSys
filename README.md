KabuSys
=======

日本株向けのデータプラットフォーム / 自動売買補助ライブラリ。  
DuckDB をデータ層に用い、J-Quants からのデータ取得・ETL、ニュースの収集・NLP スコアリング、研究用のファクター計算、監査ログ（オーダー→約定のトレース）などを提供します。

概要
----
KabuSys は次の役割を持つ Python パッケージ群です。

- J-Quants API を用いた株価／財務／カレンダー等の差分 ETL（ページネーション・リトライ・レート制御対応）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini 等）を利用したニュースセンチメント解析（銘柄単位／マクロ判定）
- ファクター計算（モメンタム／バリュー／ボラティリティ等）・研究用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution）スキーマと初期化ユーティリティ
- 設定管理（.env 自動読み込み・環境変数保護）

主な機能
--------
- data.jquants_client: J-Quants からのデータ取得/保存（raw_prices / raw_financials / market_calendar など）
- data.pipeline: 日次 ETL の実行（run_daily_etl）と個別 ETL ヘルパー
- data.news_collector: RSS 収集・前処理・raw_news への保存
- ai.news_nlp.score_news: OpenAI を用いた銘柄別ニュースセンチメント算出 → ai_scores へ保存
- ai.regime_detector.score_regime: ETF（1321）MA とマクロニュースの LLM 結果を合成して市場レジーム判定
- research: ファクター計算（calc_momentum / calc_value / calc_volatility）、特徴量探索（IC、forward returns 等）
- data.quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
- data.audit: 監査ログテーブル定義・初期化（init_audit_schema / init_audit_db）
- config: .env 自動ロード、環境変数ラッパー（settings）

要求環境（目安）
----------------
- Python 3.10 以上（型ヒントで 3.10 の union 型を利用）
- pip によりインストールする依存例:
  - duckdb
  - openai
  - defusedxml
  - その他（標準ライブラリ以外が必要な箇所がある場合は個別に追加）

セットアップ手順
---------------
1. リポジトリをクローン／チェックアウトし、仮想環境を作成:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール（例）:
   - pip install duckdb openai defusedxml

   （プロジェクトで requirements.txt / pyproject.toml がある場合はそちらを利用してください。）

3. 環境変数設定:
   - プロジェクトルートに .env（または .env.local）を置くと、自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須の主なキー:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - KABU_API_PASSWORD: kabu ステーション API パスワード（発注連携を行う場合）
     - SLACK_BOT_TOKEN: Slack 通知に使う場合
     - SLACK_CHANNEL_ID: Slack 通知チャンネル ID
     - OPENAI_API_KEY: OpenAI を使う AI 機能（score_news 等）で必要
   - 任意／デフォルト:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化

   例 (.env.example):
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-xxxx
     KABU_API_PASSWORD=passwd
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

使い方（代表的な例）
-------------------

- DuckDB 接続の作成と日次 ETL 実行（pipeline.run_daily_etl）:
  ```
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=None)  # target_date=None で今日
  print(result.to_dict())
  ```

- ニュースのスコアリング（銘柄別、ai.news_nlp.score_news）:
  ```
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect(str(settings.duckdb_path))
  n = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n} codes")
  ```
  - OPENAI_API_KEY は settings（環境変数）または api_key 引数で渡せます。
  - score_news は失敗時に個別チャンクをスキップする設計です（フェイルセーフ）。

- 市場レジーム判定（ai.regime_detector.score_regime）:
  ```
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB の初期化:
  ```
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # :memory: も可能
  ```

- 研究用ユーティリティの利用例:
  ```
  from kabusys.research import calc_momentum, calc_forward_returns, zscore_normalize
  records = calc_momentum(conn, target_date=date(2026,3,20))
  returns = calc_forward_returns(conn, target_date=date(2026,3,20))
  normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
  ```

- カレンダー／営業日ユーティリティ:
  ```
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  is_trading_day(conn, date(2026,3,20))
  next_trading_day(conn, date(2026,3,20))
  ```

注意点 / 設計上の要点
-------------------
- ルックアヘッドバイアス防止:
  - 多くのモジュール（news_nlp, regime_detector, pipeline 等）は datetime.today()/date.today() を直接使わず、明示的な target_date を引数で受けるか、ETL の呼び出し側が日付を管理する設計になっています。
- フェイルセーフ:
  - LLM/API 失敗時は部分スキップまたはデフォルト値（例: macro_sentiment=0.0）で継続する実装が多く、全体停止を避けます。
- 冪等性:
  - DB への保存は ON CONFLICT（アップサート）やユニークキーによる冪等化を行います。ETL は同じデータを何度実行しても安全な設計です。
- .env 自動ロード:
  - プロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を自動で読み込みます。OS 環境変数が優先され、.env.local は .env を上書きします。自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
- テスト性:
  - OpenAI 呼び出しなどは内部的に差し替え可能（モックしやすい）設計になっています（例: _call_openai_api を patch）。

ディレクトリ構成（主なファイル）
-------------------------------
以下はパッケージ内部の主要モジュール構成（src/kabusys）です。実際のリポジトリではさらにトップレベルファイルや設定が存在することがあります。

- src/kabusys/
  - __init__.py
  - config.py                     -- 環境変数・設定管理（settings）
  - ai/
    - __init__.py
    - news_nlp.py                  -- ニュースセンチメント（銘柄単位）
    - regime_detector.py          -- 市場レジーム判定（1321 MA + マクロセンチメント合成）
  - data/
    - __init__.py
    - jquants_client.py           -- J-Quants API クライアント + 保存ユーティリティ
    - pipeline.py                 -- ETL パイプライン（run_daily_etl 等）
    - etl.py                      -- ETL 型の再エクスポート（ETLResult）
    - news_collector.py           -- RSS ニュース収集
    - calendar_management.py      -- 市場カレンダー管理（is_trading_day 等）
    - stats.py                    -- zscore_normalize 等
    - quality.py                  -- データ品質チェック
    - audit.py                    -- 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py          -- calc_momentum / calc_value / calc_volatility
    - feature_exploration.py      -- forward returns, IC, factor_summary, rank

ライセンス / コントリビューション
--------------------------------
- 本 README にライセンス情報は含まれていません。プロジェクトのトップレベルに LICENSE ファイルがあればそちらを参照してください。
- コントリビュートする場合は、まず issue を立て、テスト＋型チェックを行った PR を送ってください。

問い合わせ
----------
使い方、バグ、拡張提案などはリポジトリの issue をご利用ください。README に書かれている環境変数や依存関係の設定で不明点があれば具体的な状況（ログ・エラーメッセージ）を添えて報告してください。

以上。必要があれば「導入手順の詳細（examples スクリプト、requirements.txt の例、.env.example の生成）」や各モジュールの API リファレンスを別途作成します。希望があれば教えてください。