# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリです。  
ETL（J-Quants 経由）、ニュース収集・NLP スコアリング（OpenAI）、リサーチ用ファクター計算、監査ログ（DuckDB）などを提供します。

概要
- 名前: KabuSys
- 目的: 日本株のデータ取得・品質管理・特徴量算出・ニュースセンチメント評価・監査ログを一貫して扱うためのライブラリ群。
- 設計方針:
  - ルックアヘッドバイアスを防ぐ設計（datetime.today()/date.today() を内部で直接参照しない等）
  - DuckDB を中心としたオンプレ・ローカル分析向け実装
  - OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価（JSON Mode）を組み込み
  - J-Quants API からの差分 ETL（rate limit / retry / token refresh 対応）
  - 冪等性を重視した DB 書き込み（ON CONFLICT 等）

主な機能
- データ取得 / ETL
  - J-Quants からの株価（日次 OHLCV）、財務情報、JPX マーケットカレンダー取得（jquants_client）
  - 差分 ETL / バックフィル / 品質チェック（data.pipeline）
- ニュース収集・NLP
  - RSS 取得・前処理・DB 保存（data.news_collector）
  - ニュースの銘柄別センチメントスコア化（ai.news_nlp.score_news）
  - マクロセンチメントと ETF MA を組み合わせた市場レジーム判定（ai.regime_detector.score_regime）
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（research.factor_research）
  - 将来リターン計算、IC 計算、ファクター統計サマリー（research.feature_exploration）
  - Z スコア正規化ユーティリティ（data.stats）
- データ品質とカレンダー
  - 品質チェック（欠損・重複・スパイク・日付不整合）（data.quality）
  - 市場カレンダー管理（data.calendar_management）
- 監査ログ（トレーサビリティ）
  - signal → order_request → execution の監査テーブル定義と初期化（data.audit）
- 設定管理
  - .env（自動読み込み） / 環境変数管理（config.Settings）

セットアップ手順（開発用）
1. 必要な Python バージョン
   - Python 3.10 以上を推奨

2. リポジトリをチェックアウトしてインストール
   - 任意: 仮想環境を作成・有効化
   - パッケージ依存はプロジェクト外ファイルにまとめられていないため最低限は以下をインストールしてください:
     - duckdb
     - openai
     - defusedxml
   例:
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があればそれを使ってください）

3. 環境変数 / .env
   - プロジェクトルートに .env または .env.local を置くと自動的に読み込まれます（config モジュールの自動ロード）。
   - 自動ロードを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数に設定

   主要な環境変数（.env に設定する例）
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - OPENAI_API_KEY=your_openai_api_key
   - KABU_API_PASSWORD=your_kabu_api_password
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi
   - SLACK_BOT_TOKEN=xoxb-...
   - SLACK_CHANNEL_ID=CXXXXXXX
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PID_FILE_PATH=data/execution.pid
   - KABUSYS_ENV=development  # development | paper_trading | live
   - LOG_LEVEL=INFO

   注意: config.Settings は必須項目を呼び出すと ValueError を出します。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動ロードを避けるか、必要な環境変数を設定してください。

使い方（Python API 例）
- 共通: DuckDB 接続を作成して関数へ渡す実装が多いです。
  from datetime import date
  import duckdb

  db_path = "data/kabusys.duckdb"
  conn = duckdb.connect(db_path)

- 日次 ETL を実行する
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントをスコア付けする（OpenAI API キーが必要）
  from kabusys.ai.news_nlp import score_news
  count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")  # api_key を省略すると環境変数 OPENAI_API_KEY を使用

- 市場レジーム（マクロ + MA200）を判定して DB に書き込む
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う

- 監査 DB の初期化（監査専用 DB を作る例）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")  # ディレクトリを自動作成して接続を返す

- ファクター計算の例
  from kabusys.research.factor_research import calc_momentum
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # records は dict のリスト（date, code, mom_1m, mom_3m, mom_6m, ma200_dev）

テスト / 開発のヒント
- OpenAI 呼び出しは各モジュール内で _call_openai_api のような関数に集約されています。単体テストでは unittest.mock.patch を使ってこれらをモックしてください（例: kabusys.ai.news_nlp._call_openai_api）。
- ETL の外部 API 呼び出しは jquants_client._request を経由します。ネットワーク依存部分はモックしてローカル検証を行ってください。
- 自動 .env 読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

ディレクトリ構成（主要ファイル・モジュールの説明）
- src/kabusys/
  - __init__.py
  - config.py
    - .env 自動読み込み、Settings（環境変数管理）
  - ai/
    - __init__.py
    - news_nlp.py        : ニュースの銘柄別センチメントスコア化（OpenAI）
    - regime_detector.py : ETF MA + マクロニュースで市場レジーム判定（OpenAI）
  - data/
    - __init__.py
    - jquants_client.py  : J-Quants API クライアント（取得・保存用ユーティリティ）
    - pipeline.py        : ETL パイプライン（run_daily_etl 等）
    - etl.py             : ETLResult の再エクスポート
    - news_collector.py  : RSS 収集と前処理（SSRF 対策・サイズ制限）
    - calendar_management.py : マーケットカレンダー管理（営業日判定等）
    - quality.py         : データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py           : zscore_normalize 等の統計ユーティリティ
    - audit.py           : 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py : Momentum / Volatility / Value の算出
    - feature_exploration.py : 将来リターン計算、IC、統計サマリー、ランク変換
  - ai、data、research 以下に多くの helper / 実装が含まれます。モジュール間は明確な境界（DB 接続を渡す、モック可能な内部呼び出し）で設計されています。

注意事項 / 実運用での留意点
- OpenAI API 呼び出しはコストがかかります。バッチ設計（news_nlp の chunking）に注意してください。
- J-Quants API のレート制限を守るため RateLimiter を実装していますが、実行環境の並列化等で追加の制御が必要になることがあります。
- settings.is_live / is_paper 等の環境フラグを使って発注等を切り替えてください（発注モジュールはこのコードベースに含まれていませんが、実運用では必須）。
- DuckDB の executemany に関するバージョン依存の挙動を考慮した実装がされているため、DuckDB のバージョン互換性に注意してください（README に requirements を追加することを推奨します）。

最後に
- 本 README はコードベースの現状に基づき要点をまとめたものです。実際に運用・開発をする際は各モジュールの docstring とログ出力を参照してください。必要であればサンプルスクリプトや CI 用のテスト・requirements.txt を追加することを推奨します。

もし README に追加したいサンプルスクリプトや、requirements.txt の候補（推奨パッケージ・バージョン）を作成してほしければ教えてください。