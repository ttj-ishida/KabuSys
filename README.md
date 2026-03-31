KabuSys — 日本株向けデータ基盤＋自動売買補助ライブラリ
=================================================

概要
----
KabuSys は日本株のデータ収集・ETL、品質チェック、特徴量算出、ニュースの NLP スコアリング、
および市場レジーム判定などをまとめた内部ライブラリ群です。J-Quants API や RSS を用いた
データ取得、DuckDB を利用した永続化、OpenAI（gpt-4o-mini）を用いたニュース解析や
レジーム判定ロジックを提供します。実際の発注モジュールは含まず、研究（Research）や
ETL／モニタリング／監査ログなどの基盤機能を中心に設計されています。

主な機能
--------
- ETL パイプライン（kabusys.data.pipeline）
  - 株価（日足）、財務データ、市場カレンダーの差分取得と保存
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - バックフィル／差分更新ロジック、結果を ETLResult で取得
- J-Quants API クライアント（kabusys.data.jquants_client）
  - レート制限管理、リトライ、トークン自動リフレッシュ、ページネーション対応
  - raw_prices / raw_financials / market_calendar への冪等保存ユーティリティ
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、SSRF 対策、前処理、raw_news への冪等保存設計
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI を用いた銘柄別ニュースセンチメント算出（JSON Mode、バッチ処理、リトライ）
  - calc_news_window（対象ウィンドウ計算）、score_news（ai_scores への保存）
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF(1321) の 200 日移動平均乖離とマクロニュースの LLM スコアを合成して
    'bull' / 'neutral' / 'bear' を算出し market_regime テーブルに保存
- データ品質チェック群（kabusys.data.quality）
  - 欠損 / スパイク / 重複 / 日付不整合の検出
- 監査ログ・トレーサビリティ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（momentum / value / volatility）や特徴量探索（forward returns / IC / summary）
- 汎用統計ユーティリティ（kabusys.data.stats）
  - Z スコア正規化など

動作要件（想定）
---------------
- Python 3.10+
- 必要な主なライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI API）

セットアップ手順
----------------
1. リポジトリを取得
   - git clone ... （内部リポジトリ想定）

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt や pyproject.toml がある場合はそちらを使用してください。）

4. 環境変数の設定
   - プロジェクトルートに .env / .env.local を置くと自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN : J-Quants 用リフレッシュトークン（必須）
     - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime 等で使用）
     - KABU_API_PASSWORD     : kabu ステーション API パスワード（必要時）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : Slack 通知に使用する場合
     - DUCKDB_PATH           : デフォルト data/kabusys.duckdb
     - SQLITE_PATH           : 監視用 SQLite のパス（オプション）
     - KABUSYS_ENV           : development / paper_trading / live
     - LOG_LEVEL             : DEBUG/INFO/WARNING/ERROR/CRITICAL
   - .env の例（簡易）
     - JQUANTS_REFRESH_TOKEN=xxxx
     - OPENAI_API_KEY=sk-xxxx
     - DUCKDB_PATH=data/kabusys.duckdb

5. データベース／監査スキーマ初期化（任意）
   - 監査ログ専用 DB を初期化する例:
     - python:
       from kabusys.config import settings
       from kabusys.data.audit import init_audit_db
       conn = init_audit_db(settings.duckdb_path)  # ":memory:" も可

使い方（簡易例）
----------------

- DuckDB 接続の作成
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行（run_daily_etl）
  - from kabusys.data.pipeline import run_daily_etl
  - from kabusys.config import settings
  - import duckdb, datetime
  - conn = duckdb.connect(str(settings.duckdb_path))
  - result = run_daily_etl(conn, target_date=datetime.date(2026,3,20))
  - print(result.to_dict())

- ニューススコアリング（OpenAI 必須）
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect(str(settings.duckdb_path))
  - n = score_news(conn, target_date=datetime.date(2026,3,20), api_key=None)  # env OPENAI_API_KEY を使用
  - print(f"scored {n} codes")

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - conn = duckdb.connect(str(settings.duckdb_path))
  - score_regime(conn, target_date=datetime.date(2026,3,20), api_key=None)

- 研究用ファクター計算
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - conn = duckdb.connect(str(settings.duckdb_path))
  - mom = calc_momentum(conn, datetime.date(2026,3,20))
  - vol = calc_volatility(conn, datetime.date(2026,3,20))

- 品質チェック（単体）
  - from kabusys.data.quality import run_all_checks
  - issues = run_all_checks(conn, target_date=datetime.date(2026,3,20))
  - for i in issues: print(i)

設定・挙動の注意点
-----------------
- .env 自動ロード
  - プロジェクトルート（.git または pyproject.toml を起点）に .env / .env.local がある場合、自動で読み込みます。
  - 読み込み順序: OS env > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト時など）。
- OpenAI 呼び出し
  - gpt-4o-mini を想定（response_format に JSON mode を使う想定）。
  - API の失敗時にはフェイルセーフによりスコア 0.0 を返す等の設計が各モジュールにあります（例: _score_macro, _score_chunk）。
- Look-ahead バイアス対策
  - バックテスト等での再現性確保のため、各モジュールは target_date を引数に取り、内部で date.today() を直接参照しない設計です。
- DuckDB executemany の制約（0 件のパラメータは送らないように注意）
  - ETL / ai_scores の挿入処理では空リストの executemany を避けるケアがあります。

ディレクトリ構成（主要ファイル）
------------------------------
以下はこの README に含まれているコードに基づく主要ファイル（省略あり）の概観です。

- src/kabusys/
  - __init__.py
  - config.py                       -- 環境変数／設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   -- ニュースNLP（score_news 等）
    - regime_detector.py            -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py        -- 市場カレンダー管理
    - etl.py                        -- ETL 公開インターフェース（ETLResult 再エクスポート）
    - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
    - stats.py                      -- 統計ユーティリティ（zscore_normalize）
    - quality.py                    -- データ品質チェック
    - audit.py                      -- 監査ログテーブル初期化
    - jquants_client.py             -- J-Quants API クライアント（fetch/save 等）
    - news_collector.py             -- RSS ニュース収集
  - research/
    - __init__.py
    - factor_research.py            -- ファクター計算（momentum/value/volatility）
    - feature_exploration.py        -- forward returns, IC, summary, rank
  - (他: strategy/ execution/ monitoring などのパッケージ名が __all__ に用意されている想定)

開発／拡張のヒント
-------------------
- テスト
  - OpenAI 呼び出しや HTTP 周りはモックしやすいように設計されています（_call_openai_api / _urlopen を patch）。
- ロギング
  - 設定は環境変数 LOG_LEVEL で制御（config.Settings.log_level）。
- DB スキーマ
  - audit.init_audit_schema を使って監査用テーブルを初期化できます。DuckDB のトランザクションの特徴に注意してください（ネストトランザクション非対応）。
- エラー処理
  - 多くの外部 API 呼び出しはリトライやフォールバックを備え、致命的な例外は上位に伝搬するよう設計されています。

ライセンス・貢献
----------------
（ここはプロジェクトの実際のライセンス／貢献ルールに従って記述してください）

付記
----
この README はコードベースの公開 API とコメントに基づき作成しています。運用環境での実行には
各種 API キー（J-Quants、OpenAI 等）の取得と安全な管理、適切な通知・監視設定を行ってください。
開発中の機能や実際の運用フロー（発注処理等）はこのライブラリの範囲外であり、別途実装が必要です。