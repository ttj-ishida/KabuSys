KabuSys — 日本株自動売買プラットフォーム（README）
=================================

概要
----
KabuSys は日本株のデータ収集（J-Quants）、品質チェック、特徴量生成、AI（ニュースセンチメント）評価、監査ログ管理、ならびに市場レジーム判定までを含む研究・実運用向けのモジュール群です。DuckDB を中心に ETL を行い、OpenAI（gpt-4o-mini）を用いたニュース NLP によるスコアリングや、ETF（1321）を用いたレジーム合成などが組み込まれています。

主な機能
--------
- データ取得 & ETL
  - J-Quants API から株価（日足）、財務データ、マーケットカレンダーを差分取得・保存
  - 差分/バックフィルロジック、ページネーション対応、レート制御、トークン自動リフレッシュ
- データ品質チェック
  - 欠損、スパイク、重複、将来日付／非営業日の検出（QualityIssue 型で集約）
- ニュース収集 & 前処理
  - RSS 取得、URL 正規化、SSRF 対策、記事 ID のハッシュ化、前処理
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースセンチメントを ai_scores に書き込む（バッチ・リトライ・検証）
  - マクロニュースから市場レジーム（bull/neutral/bear）を判定
- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC 計算、Z スコア正規化、統計サマリー
- 監査ログ（トレーサビリティ）
  - signal_events, order_requests, executions の監査スキーマを冪等的に初期化
- 設定管理
  - .env（.env.local）および環境変数の自動読み込み（プロジェクトルート検出）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能

セットアップ手順
----------------
1. リポジトリをクローン（例）
   - git clone <repo-url>
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - 推奨依存（最低限）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）
4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env を置くと自動読み込みされます。
   - 重要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=xxxxx        # 必須（J-Quants リフレッシュトークン）
     - KABU_API_PASSWORD=xxxxx            # kabu API パスワード（必要に応じて）
     - OPENAI_API_KEY=sk-...              # OpenAI 呼び出しに必要
     - LINE_CHANNEL_ACCESS_TOKEN=...      # （任意）通知用途
     - LINE_USER_ID=...                   # （任意）
     - DUCKDB_PATH=data/kabusys.duckdb    # デフォルトの DuckDB ファイルパス
     - SQLITE_PATH=data/monitoring.db     # 監視用 SQLite パス
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|... 
   - .env の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
   - 参考: settings オブジェクトは kabusys.config.settings でアクセスできます。
5. 初期 DB スキーマ（監査ログなど）の初期化
   - 監査ログ専用 DB を初期化する例（Python スクリプト）:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
   - 既存 DuckDB 接続に監査スキーマだけ追加する場合:
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)

使い方（主要な呼び出し例）
------------------------

- 日次 ETL の実行（株価・財務・カレンダーの差分取得 + 品質チェック）
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースのセンチメントスコア付与（ai_scores へ書き込み）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")

  ※ OpenAI API キーは OPENAI_API_KEY 環境変数か、score_news の api_key 引数で指定可能。

- 市場レジーム判定（market_regime テーブルへの書き込み）
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))

- 監査 DB 初期化（ファイル作成）
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")

- 研究・ファクター計算（例: モメンタム）
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026,3,20))
  # records は dict のリスト（date, code, mom_1m, mom_3m, mom_6m, ma200_dev）

設定（主な環境変数）
-------------------
- JQUANTS_REFRESH_TOKEN (必須) : J-Quants のリフレッシュトークン
- OPENAI_API_KEY (必要に応じて) : OpenAI API のキー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD : kabuステーション API パスワード（発注等を実装する場合）
- DUCKDB_PATH : データ用 DuckDB のパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視 DB のパス（デフォルト data/monitoring.db）
- KABUSYS_ENV : development / paper_trading / live（動作モード検証）
- LOG_LEVEL : ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると .env の自動ロードを無効化

注意点 / 設計上の注意
--------------------
- ルックアヘッドバイアス防止:
  - news_nlp, regime_detector などは内部で date.today() を参照しない設計。必ず target_date を渡して下さい。
  - prices_daily 等のクエリは target_date 未満を排他条件にする等の工夫が入っています。
- OpenAI 呼び出し:
  - JSON mode（response_format={"type": "json_object"}）を用い、レスポンスのバリデーションを行っています。API 失敗時はフェイルセーフ（スコア=0）で継続する設計です。
- J-Quants クライアント:
  - レート制御（120 req/min）、リトライ、401 トークン自動リフレッシュ、ページネーション対応を備えています。
- ニュース収集:
  - SSRF 対策、受信サイズ制限、XML パースの安全対策を実装しています（defusedxml 使用）。
- DuckDB バージョン差異:
  - 一部 executemany の制約（空リスト不可など）を考慮した実装が含まれています。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py               (パッケージ初期化、__version__)
- config.py                 (環境変数 / 設定管理: settings)
- ai/
  - __init__.py
  - news_nlp.py             (ニュースセンチメントスコアリング)
  - regime_detector.py      (市場レジーム判定)
- data/
  - __init__.py
  - jquants_client.py       (J-Quants API クライアント、保存関数)
  - pipeline.py             (ETL パイプライン / run_daily_etl / ETLResult)
  - etl.py                  (ETLResult 再エクスポート)
  - news_collector.py       (RSS ニュース収集・前処理)
  - calendar_management.py  (マーケットカレンダー管理)
  - quality.py              (データ品質チェック)
  - audit.py                (監査ログスキーマ初期化)
  - stats.py                (zscore_normalize 等)
- research/
  - __init__.py
  - factor_research.py      (mom/value/volatility ファクター計算)
  - feature_exploration.py  (forward returns, IC, summary, rank 等)
- ai、data、research の各モジュールはさらに内部で細かい関数・ロジックを提供します。

開発者向けヒント
-----------------
- テスト時は自動 .env 読み込みを無効化して isolation を保つ:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出しや外部ネットワーク呼び出しは単体テストでモックしやすいように内部関数を分離してあります（_call_openai_api 等）。
- DuckDB の接続は軽量でスレッドセーフではない点に注意。長時間稼働のサービスで共有接続を使う場合は設計検討が必要です。
- run_daily_etl は各ステップでエラーハンドリングを行い、品質チェック結果やエラーリストを ETLResult に格納します。監査・運用ログに記録して監視してください。

付録: 例 .env.example（参考）
---------------------------
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

サポート / 貢献
---------------
バグ報告や機能提案、プルリクエストはリポジトリの Issues / PR を通じてお願いします。ドキュメントの改善やテスト追加も歓迎します。

以上。質問や README に追記してほしい利用例やコマンドがあれば教えてください。