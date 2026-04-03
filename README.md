KabuSys
=======

概要
----
KabuSys は日本株向けのデータパイプライン・リサーチ・AI 支援分析・監査ログ・ETL を含む自動売買プラットフォームのコアライブラリ群です。J-Quants や RSS、OpenAI（gpt-4o-mini）等と連携して以下の処理を行います:

- J-Quants からの株価・財務・マーケットカレンダーの差分取得と DuckDB への保存（ETL）
- ニュース（RSS）収集と前処理、安全性対策
- OpenAI を利用したニュースセンチメント（銘柄毎）とマクロセンチメント評価
- 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- ファクター計算や特徴量探索（リサーチ用ユーティリティ）
- データ品質チェック
- 監査（signal → order_request → execution）用のテーブル定義と初期化ユーティリティ

主要な設計方針は「ルックアヘッドバイアスの排除」「冪等性」「外部 API のレート管理」「フェイルセーフ（API失敗時は処理継続）」です。

機能一覧
--------
主な機能（モジュール）:

- kabusys.config
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 環境変数ラッパ（settings）: J-Quants トークン、Kabu API、LINE、DB パス、監視閾値など

- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存・認証・レート制御・リトライ）
  - pipeline / etl: 日次差分 ETL（prices / financials / market_calendar）と ETLResult
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector: RSS 取得・前処理・SSRF 対策・記事ID生成・保存支援
  - calendar_management: 営業日判定、next/prev_trading_day、calendar 更新ジョブ
  - audit: 監査ログテーブル定義・初期化（冪等）と DB 初期化ユーティリティ
  - stats: z-score 正規化などの統計ユーティリティ

- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価して ai_scores に書き込む
  - regime_detector.score_regime: ETF(1321) の MA 乖離 + マクロニュースの LLM センチメントから市場レジームを判定して market_regime に保存

- kabusys.research
  - factor_research: モメンタム/バリュー/ボラティリティ等のファクター計算
  - feature_exploration: 将来リターン計算、IC（スピアマン）、統計サマリーなど

要件（推奨）
-------------
- Python 3.10 以上（代数的型ヒント、Union 表記を利用）
- 必要な Python パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS / OpenAI）

セットアップ手順
----------------

1. リポジトリをクローン（またはパッケージを取得）:
   - git clone ... （プロジェクトルートに .git または pyproject.toml があると .env 自動読み込みが有効になります）

2. 仮想環境を作成して有効化（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（最低限）:
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそれを使用してください:
    pip install -e . や pip install -r requirements.txt）

4. 環境変数の設定:
   - プロジェクトルートに .env または .env.local を置くと自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 代表的な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
     - OPENAI_API_KEY (for AI calls) または関数に api_key を渡す
     - KABU_API_PASSWORD: kabu API のパスワード
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用（任意）
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV: development | paper_trading | live
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

   - .env のパースは quotes、export プレフィックス、コメントを考慮して行われます。

5. ディレクトリの作成:
   - デフォルトの DB 保存先ディレクトリ (data/) やログ用ディレクトリを作成してください。多くの初期化関数は親ディレクトリを自動作成しますが、念のため。

基本的な使い方（コード例）
------------------------

- DuckDB 接続を開いて日次 ETL を実行する例:

  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))  # settings.duckdb_path は Path を返す
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- ニューススコアリング（OpenAI API キーが環境変数にある場合）:

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 19))  # 対象日を明示的に指定
  print(f"書き込んだ銘柄数: {written}")

- 市場レジーム判定:

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 19))

  ※ OPENAI_API_KEY が不要なら api_key 引数で指定できます（推奨: 明示）。

- 監査 DB の初期化:

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可

- カレンダー / 営業日ユーティリティ:

  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  print(is_trading_day(conn, date(2026, 3, 20)))
  print(next_trading_day(conn, date(2026, 3, 20)))

設計上の注意点
--------------
- ルックアヘッドバイアス防止:
  - 各関数は内部で datetime.today() を直接参照しないように設計されています。必ず target_date を明示して処理してください。
- 冪等性:
  - J-Quants 保存関数や監査テーブル初期化は冪等性（ON CONFLICT / INSERT … DO UPDATE）を考慮しています。
- フェイルセーフ:
  - API エラーや LLM のパース失敗は基本的に例外で停止させずフォールバック（0.0）やスキップを行います。ログで検知してください。
- セキュリティ（news_collector）:
  - RSS 収集時に SSRF 対策、リダイレクト検証、最大レスポンスサイズ制限、XML パース安全対策（defusedxml）を実装しています。

環境変数の自動読み込みについて
------------------------------
- kabusys.config はプロジェクトルート（.git または pyproject.toml がある親ディレクトリ）を探索し、.env と .env.local を順に読み込みます。
- 読み込み優先順: OS 環境変数 > .env.local > .env
- 自動ロードを停止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成
----------------
（重要ファイルのみ抜粋）

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
    - news_collector.py
    - calendar_management.py
    - stats.py
    - audit.py
    - audit の初期化ユーティリティ等
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research モジュールは zscore_normalize 等を再利用

- その他:
  - setup / pyproject.toml（プロジェクト配布用、存在すれば .env 自動検出に利用）

よくある Q&A / トラブルシューティング
-----------------------------------
- OpenAI の呼び出しでエラーが出る: OPENAI_API_KEY を設定するか score_* 関数に api_key を渡してください。API の一時エラーは自動リトライされますが、認証エラーは明示的な対処が必要です。
- J-Quants の認証失敗: JQUANTS_REFRESH_TOKEN が正しいか確認してください。jquants_client はトークンの自動リフレッシュと 401 時のリトライをサポートしています。
- DuckDB のスキーマがない / テーブルが見つからない: ETL・audit 初期化関数（init_audit_db 等）を先に呼んでスキーマを作成してください。
- .env の自動読み込みを無効化したい: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。

貢献・拡張
----------
- 新しいデータソース・ニュースソースを追加する場合は data/news_collector.py の RSS ソース定義と保存ロジックを拡張してください。
- 新しい戦略やリサーチ機能は research 以下にモジュールを追加し、監査ログを利用する場合は audit テーブルのルールに従って event を追加してください。

ライセンス・連絡先
-----------------
（ここに実プロジェクトでのライセンス表記や連絡先を追加してください）

以上が KabuSys コードベースの概要と利用方法です。初期セットアップや関数の詳細な挙動は各モジュールの docstring を参照してください。