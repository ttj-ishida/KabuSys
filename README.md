KabuSys
=======

概要
----
KabuSys は日本株向けのデータプラットフォームと自動売買支援ライブラリです。  
J-Quants API からのデータ取得（株価・財務・マーケットカレンダー）、RSS ニュース収集、LLM を使ったニュースセンチメント評価、ファクター計算、ETL パイプライン、監査ログ（発注／約定トレース）などを包含します。  
モジュール設計は「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ」を重視しており、バックテスト・本番・研究用途で使えるよう分離されています。

主な機能
--------
- データ収集 / ETL
  - J-Quants からの株価日足 / 財務 / 上場情報 / カレンダー取得（ページネーション対応、トークン自動リフレッシュ、レート制限対応）
  - ETL パイプライン（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック
- ニュース収集
  - RSS フィードの取得・正規化・前処理・raw_news への冪等保存（SSRF 対策、トラッキング除去、サイズ制限）
- ニュース NLP（LLM）
  - 銘柄別ニュースを LLM（gpt-4o-mini）でスコアリングして ai_scores に保存（score_news）
  - マクロニュースを使った市場レジーム判定（score_regime）
  - OpenAI 呼び出しはリトライ / バックオフを備えフェイルセーフ（失敗時は 0.0 フォールバック）
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルの初期化・運用ユーティリティ（init_audit_schema / init_audit_db）
  - 発注→約定のトレーサビリティ設計
- 研究用ユーティリティ（research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン・IC・統計サマリー・Zスコア正規化
- データ品質チェック（quality）
  - 欠損、重複、スパイク、日付不整合の検出（QualityIssue を返す）
- 市場カレンダー管理（calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job

セットアップ手順
----------------

前提
- Python 3.10+ を想定（typing の Union 表記などを使用）
- DuckDB を利用するためネイティブバイナリをインストールできる環境

1) 仮想環境
- 推奨: venv を使う
  - python -m venv .venv
  - source .venv/bin/activate  または  .venv\Scripts\activate

2) 必要パッケージのインストール（例）
- pip install duckdb openai defusedxml
- その他プロジェクトで必要なパッケージがあれば追加してください。

3) 環境変数（.env）設定
- 以下の環境変数が利用されます（必須は README 内で明記）:
  - JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD (必須): kabuステーション API パスワード
  - KABU_API_BASE_URL (任意): kabu API のベース URL (デフォルト: http://localhost:18080/kabusapi)
  - SLACK_BOT_TOKEN (必須): Slack 通知を使う場合の Bot トークン
  - SLACK_CHANNEL_ID (必須): Slack チャネル ID
  - DUCKDB_PATH (任意): DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH (任意): SQLite path（デフォルト data/monitoring.db）
  - KABUSYS_ENV (任意): development / paper_trading / live（デフォルト development）
  - LOG_LEVEL (任意): DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- 自動読み込み:
  - パッケージ初期化時にプロジェクトルート（.git または pyproject.toml を探索）にある .env / .env.local を自動で読み込みます。
  - 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env の例:
  JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  KABU_API_PASSWORD=your_kabu_password
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C01234567
  DUCKDB_PATH=data/kabusys.duckdb
  KABUSYS_ENV=development

4) データベース初期化（監査ログ）
- 監査用 DB を初期化する例:
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")

使い方（代表例）
----------------

- ETL を日次で回す（Python スクリプト例）
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- ニュース NLP（銘柄別スコア生成）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  print("written:", n_written)

- 市場レジーム判定
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- 監査スキーマ初期化（既存接続に適用）
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

- ファクター計算 / 研究用ユーティリティ
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value, zscore_normalize

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))
  mom_norm = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])

注意点 / 設計上の挙動
-------------------
- ルックアヘッドバイアス防止:
  - 多くの処理（news window 計算、prices クエリ等）は target_date 未満あるいは特定のウィンドウでデータを取得し、未来データを参照しないよう設計されています。
- LLM 呼び出し:
  - OpenAI (gpt-4o-mini 等) を利用する関数は API キーを引数で受け取るか環境変数 OPENAI_API_KEY を使用します。
  - API エラー時はリトライやフォールバック（スコア = 0.0）する実装です。過度な信頼は避けてください。
- 冪等性:
  - ETL → save_* 関数は ON CONFLICT DO UPDATE 等で冪等になっています。複数回実行しても既存データを上書きします。
- 品質チェック:
  - quality.run_all_checks は問題を検出して QualityIssue のリストを返します。呼び出し側で停止/通知の判断をしてください。
- セキュリティ / ネットワーク:
  - news_collector は SSRF 対策・プライベートホスト検査・最大応答サイズ制限・gzip 解凍制限を備えています。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py (パッケージエクスポート)
- config.py (環境変数 / 設定ロード)
- ai/
  - __init__.py
  - news_nlp.py (ニューススコア・LLMラッパ)
  - regime_detector.py (市場レジーム判定)
- data/
  - __init__.py
  - jquants_client.py (J-Quants API クライアント、保存関数含む)
  - pipeline.py (ETL パイプライン・run_daily_etl 等)
  - etl.py (ETLResult 再エクスポート)
  - news_collector.py (RSS 収集・前処理)
  - quality.py (データ品質チェック)
  - stats.py (Zスコア等統計ユーティリティ)
  - calendar_management.py (market_calendar 管理)
  - audit.py (監査ログスキーマ / init_audit_db)
- research/
  - __init__.py
  - factor_research.py (モメンタム/バリュー/ボラティリティ)
  - feature_exploration.py (forward returns, IC, rank, summary)
- ai、data、research のテストや utilities はプロジェクト外に配置される想定

開発 / 貢献
------------
- コードはモジュール単位での差し替えやユニットテストを想定して設計されています（外部呼び出しのラッパ関数をモックしやすい）。
- LLM / ネットワーク呼び出しはテスト時にモックすることを推奨します（news_nlp._call_openai_api や regime_detector._call_openai_api 等をパッチ）。

ライセンス / 注意
-----------------
- 本 README はコードベースの概要・使用例を示すものであり、実運用にあたっては API キーの管理、レート制限、注文ロジックの安全性、リスク管理、法令順守等を各自で確認してください。

必要に応じて README に追記します。たとえば:
- requirements.txt の正確な依存一覧
- docker-compose / systemd などでのデプロイ手順
- 具体的な .env.example（完全版）
などが必要であれば教えてください。