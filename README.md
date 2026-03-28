# KabuSys — 日本株自動売買基盤（README）

概要
----
KabuSys は日本株向けのデータプラットフォーム / 研究 / 自動売買基盤のコアライブラリ群です。本リポジトリにはデータ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（約定トレーサビリティ）などの主要コンポーネントが含まれます。

特徴
----
- J-Quants API 経由の差分取得（株価・財務・カレンダー）、RateLimit とリトライ管理付き
- DuckDB を用いたローカルデータ保存と ETL パイプライン（日次 ETL）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント（ai_scores）および市場レジーム判定（market_regime）
- 研究用モジュール：モメンタム・ボラティリティ・バリュー等のファクター計算、前方リターン、IC 計算、統計サマリー
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal_events / order_requests / executions）スキーマ定義と初期化ユーティリティ
- 環境変数 / .env による設定管理（自動読み込み機能あり）

前提
----
- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / ニュース RSS）

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成・有効化します。
   - 例:
     python -m venv .venv
     source .venv/bin/activate

2. 必要パッケージをインストールします（プロジェクトに requirements.txt / pyproject があればそちらを使用してください）。
   - 例:
     pip install duckdb openai defusedxml

3. 環境変数を設定します（.env または .env.local をプロジェクトルートに配置）。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
     - OPENAI_API_KEY        : OpenAI API キー（score_news / regime 判定で使用）
     - KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL     : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN       : Slack 通知用ボットトークン（必須）
     - SLACK_CHANNEL_ID      : Slack チャネル ID（必須）
     - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH           : 監視用 SQLite のパス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV           : environment (development | paper_trading | live)（デフォルト development）
     - LOG_LEVEL             : ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

   - 自動ロード:
     パッケージはプロジェクトルート（.git または pyproject.toml を基準）にある .env / .env.local を自動で読み込みます。自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. DuckDB 等の初期スキーマは利用シーンごとに初期化してください（audit スキーマ等はライブラリ関数提供）。

基本的な使い方
-------------

※ 下記は Python REPL / スクリプトからの呼び出し例です。ファイルパスや日付は適宜置き換えてください。

- 設定の参照
  - from kabusys.config import settings
  - settings.duckdb_path, settings.jquants_refresh_token などで取得可能

- DuckDB 接続を開く
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - result は ETLResult オブジェクト（フェッチ数・保存数・品質問題などを含む）

- ニュースセンチメント（ai_scores）を生成する
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n = score_news(conn, target_date=date(2026,3,20))
  - 返り値は書き込んだ銘柄数

- 市場レジーム判定を実行する
  - from kabusys.ai.regime_detector import score_regime
  - r = score_regime(conn, target_date=date(2026,3,20))
  - market_regime テーブルへ書き込み（戻り値 1 が成功）

- 監査ログ（audit）スキーマを初期化する
  - from kabusys.data.audit import init_audit_db, init_audit_schema
  - audit_conn = init_audit_db("data/audit.duckdb")  # ファイル作成＋テーブル初期化
  - または既存 conn に対して init_audit_schema(conn, transactional=True)

- 研究用ファクター計算例
  - from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  - records = calc_momentum(conn, date(2026,3,20))

- データ品質チェックを実行
  - from kabusys.data.quality import run_all_checks
  - issues = run_all_checks(conn, target_date=date(2026,3,20))
  - issues は QualityIssue のリスト（check_name, table, severity, detail, rows）

注意事項 / 設計方針（要点）
-------------------------
- ルックアヘッドバイアス防止:
  - 各モジュールは内部で date.today() を無分別に参照せず、呼び出し元が target_date を指定して使用する設計になっています。バックテスト用途では特に注意してください。
- OpenAI 呼び出し:
  - OpenAI API 呼び出しにはリトライ／フェイルセーフが組み込まれており、API 失敗時にはスコアを 0 にフォールバックする等の安全策が取られています。
- ETL は部分失敗を許容し、品質チェックで問題を収集して呼び出し元が判断できるようにしています。
- RSS ニュース収集では SSRF 対策、受信サイズ制限、XML パーサーの安全版（defusedxml）を利用しています。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要モジュールと役割です（抜粋）。

- kabusys/
  - __init__.py                — パッケージメタ情報
  - config.py                  — 環境変数 / .env 管理と Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py              — ニュースの NLP スコアリング（score_news）
    - regime_detector.py       — マーケットレジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得＋DuckDB 保存）
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - etl.py                   — ETLResult の再エクスポート
    - news_collector.py        — RSS ニュース収集（fetch_rss 等）
    - calendar_management.py   — 市場カレンダー管理（is_trading_day 等）
    - quality.py               — データ品質チェックモジュール
    - stats.py                 — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                 — 監査ログ（signal / order / execution）定義・初期化
  - research/
    - __init__.py
    - factor_research.py       — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py   — forward returns / IC / rank / summary 等
  - ai/、data/、research/ 以下にある各モジュールは、DuckDB 接続を受けて SQL と Python を組み合わせて処理します。

開発・テスト時のヒント
---------------------
- 環境変数の自動読み込みはプロジェクトルート検出に .git または pyproject.toml を使用します。配布後やテスト環境で CWD に依存しない挙動を保つため、この挙動に注意してください。
- OpenAI 呼び出しはモック可能（テスト用に _call_openai_api をパッチ）になっています。
- news_collector._urlopen など、外部ネットワークを直接叩く箇所はテストで差し替えられるよう設計されています。

ライセンス / 貢献
-----------------
（このリポジトリのライセンス情報はここに追記してください）

最後に
------
この README はコードベース内の Docstring と実装を元に要点をまとめたものです。各モジュールには詳細な Docstring と設計コメントが含まれているため、利用時は該当モジュールのドキュメントも参照してください。必要であれば、サンプルスクリプトやユースケース別のハンドブックを別途作成できます。