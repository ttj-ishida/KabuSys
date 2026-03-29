kabusys
=======

日本株向けのデータ基盤・リサーチ・自動売買補助ツール群をまとめたパッケージです。  
DuckDB をデータレイヤに用い、J-Quants からのデータ取得 / ETL、ニュース収集と LLM によるニュースNLP、ファクター計算、監査ログ（発注→約定のトレース）などの機能を提供します。

主な特徴
-------
- J-Quants API からの差分取得（株価・財務・マーケットカレンダー）と DuckDB への冪等保存
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- ニュース収集（RSS）と前処理、ニュースと銘柄の紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント分析（news_nlp）
- ETF（1321）MA とマクロニュースを組み合わせた市場レジーム判定（regime_detector）
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ）と特徴量解析ユーティリティ
- 監査ログスキーマ（signal_events / order_requests / executions）の初期化ユーティリティ
- 環境変数 / .env 自動読み込み（プロジェクトルート検出）

動作環境（推奨）
--------------
- Python 3.10+
- 必要パッケージ（実行に応じて）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外の追加依存は pyproject.toml を参照してください）

セットアップ
----------
1. リポジトリをクローン／チェックアウトし、開発環境を作成します。

   - 仮想環境作成例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージをインストール（プロジェクトルートで）:

   - 開発中に編集しながら使う場合:
     - pip install -e ".[dev]"  （pyproject.toml に extras がある場合）
   - 必要最低限:
     - pip install duckdb openai defusedxml

3. 環境変数の準備:

   プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（.git または pyproject.toml を基準にプロジェクトルートを検出）。テストや特別な場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。

   主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 処理を行う場合）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
   - LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)

使い方（簡易サンプル）
--------------------

- DuckDB 接続を作り、日次 ETL を実行する例:

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースNLP（ai スコア）を実行する例:

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY が環境変数にあれば api_key 引数は不要
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {n_written}")

- 市場レジームを評価して保存する例:

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を参照

- 監査ログ用の DuckDB を初期化する例:

  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")  # テーブルとインデックスを作成

重要な挙動・注意点
-----------------
- .env 自動読み込み:
  - プロジェクトルートが .git または pyproject.toml の存在で検出されると、.env → .env.local の順に読み込みます。
  - .env.local は .env を上書きします（ただし OS の環境変数は protected されます）。
  - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- Look-ahead bias 対策:
  - AI スコアリングやレジーム判定、ETL などの関数は実行時に datetime.today()/date.today() を無闇に参照しない設計。API 呼び出しやクエリでは target_date 未満の排他条件などルックアヘッドを防ぐ工夫があります。

- OpenAI 呼び出し:
  - news_nlp / regime_detector では OpenAI の Chat Completions（gpt-4o-mini）を JSON mode で利用する想定です。API キーは引数で渡すか、環境変数 OPENAI_API_KEY を使用します。API エラーやパースエラーはフェイルセーフでスキップし、ゼロや空結果で継続する設計です。

- J-Quants クライアント:
  - レートリミット（120 req/min）を守る RateLimiter、401 時のトークンリフレッシュ、ページネーション対応、冪等保存（ON CONFLICT DO UPDATE）などを備えています。

- DuckDB の executemany 空リストの扱い:
  - 一部の関数では DuckDB のバージョン差異を吸収するため、executemany に空リストを渡さないようチェックしています。

ディレクトリ構成（主要ファイル）
-------------------------------

- src/kabusys/
  - __init__.py  (パッケージ定義)
  - config.py    (環境変数・設定管理)
  - ai/
    - __init__.py
    - news_nlp.py          (ニュース NLG/NLP による銘柄別スコアリング)
    - regime_detector.py   (市場レジーム判定: ETF MA + マクロニュース)
  - data/
    - __init__.py
    - jquants_client.py    (J-Quants API クライアント + DuckDB 保存)
    - pipeline.py          (ETL パイプライン: run_daily_etl 等)
    - etl.py               (ETLResult の再エクスポート)
    - news_collector.py    (RSS 取得・前処理・raw_news 保存)
    - calendar_management.py (市場カレンダー管理・営業日判定)
    - quality.py           (データ品質チェック)
    - audit.py             (監査ログスキーマ初期化)
    - stats.py             (zscore_normalize 等統計ユーティリティ)
  - research/
    - __init__.py
    - factor_research.py   (モメンタム / バリュー / ボラティリティの計算)
    - feature_exploration.py (forward returns / IC / summary / rank 等)
  - monitoring/
    - （モニタリング関連モジュールを想定、必要に応じて実装）

各モジュールの役割（短評）
-----------------------
- config.py: .env 自動読み込み、必須環境変数取得用ユーティリティ（Settings クラス）
- data/jquants_client.py: API 呼び出し、保存、認証トークン管理
- data/pipeline.py: ETL の上位制御（calendar → prices → financials → 品質チェック）
- data/news_collector.py: RSS 取得、安全対策（SSRF・サイズ制限）・記事前処理
- ai/news_nlp.py: 銘柄毎にニュースをまとめて LLM に投げ、スコアを ai_scores に保存
- ai/regime_detector.py: ETF MA とマクロニュースを合成して market_regime を更新
- data/audit.py: 発注→約定の追跡に必要なスキーマを初期化するユーティリティ
- research/*: ファクター計算や統計解析用ユーティリティ群

開発・テスト
------------
- 自動読み込みを無効にして環境変数を明示的に注入することで単体テストが書きやすくなっています（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
- OpenAI 呼び出しや外部 HTTP の箇所はモックしやすいように呼び出し関数を分離しています（ユニットテストではモック推奨）。

ライセンス／貢献
---------------
- この README 内ではライセンス情報は含めていません。実際のリポジトリの LICENSE ファイルを確認してください。
- バグ報告や機能提案は issue を作成してください。プルリク歓迎です。

その他
-----
- この README はコードベースのコメントと API を元にまとめた概要ドキュメントです。各モジュールの詳細な使い方・引数仕様は該当ソースの docstring を参照してください。