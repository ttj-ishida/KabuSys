KabuSys
=======

日本株向けのデータプラットフォームと自動売買補助ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP による銘柄スコアリング、ファクター計算、マーケットレジーム判定、監査ログ（発注／約定トレース）などを含むモジュール群を提供します。

主な目的
- J-Quants API を用いた株価/財務/カレンダーの差分 ETL
- RSS ベースのニュース収集と OpenAI を使ったニュースセンチメントスコアリング
- ファクター計算（モメンタム / ボラティリティ / バリュー等）と特徴量探索ユーティリティ
- 市場レジーム判定（ETF MA + マクロニュースの LLM 評価を合成）
- 監査ログ用の DuckDB スキーマ初期化とトレース機能
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）

主な機能一覧
- 環境変数/設定読み込み（kabusys.config）
  - .env/.env.local 自動読み込み（プロジェクトルート検出）
  - 必須設定チェック（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等）
- データ ETL（kabusys.data.pipeline / jquants_client）
  - 差分取得、ページネーション対応、トークン自動リフレッシュ、レート制御、リトライ
  - DuckDB へ冪等保存（ON CONFLICT）
  - カレンダー更新ジョブ、価格・財務データ更新、日次統合 ETL（run_daily_etl）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・正規化・SSRF 対策・前処理・raw_news への冪等保存
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI (gpt-4o-mini) を使ったバッチセンチメント解析
  - チャンク処理、リトライ、レスポンス検証、ai_scores への保存
- レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）の 200 日 MA 乖離 + マクロニュース LLM 評価の線形合成による日次レジーム判定
  - DB への冪等書込
- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（momentum, volatility, value）、将来リターン、IC 計算、統計サマリー
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合の検出
- 監査ログ初期化（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルと索引の作成、監査用 DB 初期化ユーティリティ

動作環境・依存
- Python >= 3.10（型注釈に | を使用）
- 必要なパッケージ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ（urllib, json, logging 等）を多用

セットアップ手順（ローカル開発向け）
1. リポジトリを取得
   - git clone ... （プロジェクトルートに .git または pyproject.toml があれば自動で .env 読込対象を検出します）

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存をインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements.txt があれば pip install -e . や pip install -r requirements.txt を使用）

4. 環境変数 / .env ファイルを準備
   - プロジェクトルートに .env（または .env.local）を配置すると、kabusys.config により自動読込されます。
   - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で利用）。

   推奨する .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   OPENAI_API_KEY=sk-...
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

5. DuckDB 用ディレクトリ作成
   - mkdir -p data

使い方（簡易サンプル）
- DuckDB 接続を作成して日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  # target_date を指定しない場合は今日が使われます
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースに対する NLP スコアを生成（ai_scores へ書き込み）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数か api_key 引数で指定
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written scores: {written}")
  ```

- 市場レジーム判定を行う
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DuckDB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # init_audit_db はスキーマ作成後の接続を返します
  ```

設定・運用上のポイント / 注意事項
- 自動環境変数読み込み
  - kabusys.config はプロジェクトルート（.git または pyproject.toml）を基に .env/.env.local を自動で読み込みます。
  - 読み込み順: OS 環境変数 > .env.local > .env（.env.local が .env を上書き）
  - テスト時に自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- Look-ahead bias（ルックアヘッドバイアス）対策
  - AI 評価・ETL・レジーム判定・研究用関数の多くは date 引数を明示的に受け取り、内部で datetime.today()/date.today() を参照しない設計です。これによりバックテストや検証で未来情報を使わないようにしています。

- 冪等性・トランザクション
  - jquants_client の保存関数や監査スキーマ初期化は冪等に設計されています（ON CONFLICT 等）。
  - ETL やスコア保存はトランザクションを用いて部分失敗時の安全性を高めていますが、運用でのバックアップと監視は必要です。

- 外部 API 呼び出しの堅牢性
  - J-Quants、OpenAI への呼び出しはリトライと指数バックオフ、レート制御（J-Quants: 120 req/min）を組み合わせています。
  - OpenAI 呼び出しは JSON Mode を尊重しつつも、パース失敗時はフェイルセーフ（0.0 で代替）する設計です。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースセンチメント解析（OpenAI）
    - regime_detector.py           — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得・保存）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETL インターフェース再エクスポート（ETLResult）
    - news_collector.py            — RSS 取得 / 前処理
    - calendar_management.py       — マーケットカレンダー管理
    - stats.py                     — 統計ユーティリティ（zscore_normalize 等）
    - quality.py                   — データ品質チェック
    - audit.py                     — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py           — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py       — 将来リターン/IC/統計サマリー 等
  - monitoring/ (コードベース内で参照あり: Slack 等へ通知する実装を想定)
  - execution/ (発注ロジック用モジュールを想定)
  - strategy/ (戦略生成・シグナル化のためのプレースホルダ)

開発・拡張に関するメモ
- テスト
  - 外部 API 呼び出し（OpenAI / J-Quants / ネットワーク）周りはモックして単体テストを行ってください。各モジュール内で置き換えやすいヘルパー関数（_call_openai_api など）を用意してあり、patch による差し替えが可能です。
- セキュリティ
  - RSS フェッチは SSRF 対策（ホスト/IP 検証、リダイレクト検査、受信サイズ制限）を実装していますが、運用時にはネットワーク制御やプロキシ経由の検査を推奨します。
- 運用
  - ETL は差分取得＋バックフィル（デフォルト 3 日）を行うため、API 側の後出し修正に対して寛容です。
  - 監査ログは削除しない前提で設計されています。order_request_id を冪等キーとして二重発注防止を担保してください。

貢献
- バグ報告・機能追加は issue / PR を通じてお願いします。コード設計の方針（ルックアヘッド禁止、冪等性、API リトライ）を踏襲して実装してください。

以上が KabuSys の概要と導入ガイドです。必要であれば、各モジュールの使い方（関数別の引数説明、返り値、例外挙動）を個別のドキュメントとして追加できます。どの部分の詳細を優先して作成しますか？