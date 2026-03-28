KabuSys — 日本株自動売買プラットフォーム（README 日本語版）
======================================================

概要
----
KabuSys は日本株のデータ取得・品質管理・特徴量算出・AI ベースのニュースセンチメント評価・市場レジーム判定・監査ログなどを備えた自動売買基盤向けライブラリ群です。主に以下を目的とします。

- J-Quants API からの差分 ETL（株価・財務・カレンダー）
- ニュース収集と OpenAI を用いた銘柄センチメント算出
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- ファクター計算・特徴量解析（研究用モジュール）
- 監査ログ（signal → order → execution のトレーサビリティ）
- データ品質チェックと夜間バッチ処理のユーティリティ

主な機能
--------
- データ ETL（kabusys.data.pipeline.run_daily_etl）
  - 差分取得、バックフィル、品質チェック、calendar の先読み
- J-Quants API クライアント（kabusys.data.jquants_client）
  - レートリミット・リトライ・トークン自動リフレッシュ対応
- ニュース収集（RSS）と前処理（kabusys.data.news_collector）
  - SSRF 対策、トラッキングパラメータ除去、サイズ制限
- AI ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini 想定）を用いた銘柄ごとのセンチメント算出
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離とマクロニュースの LLM スコアを合成
- 研究用ファクター計算（kabusys.research）
  - Momentum / Value / Volatility 等、IC・forward return 計算
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合検出
- 監査ログ初期化・DB（kabusys.data.audit）
  - 監査テーブル DDL、インデックス、init helper

前提条件
--------
- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- J-Quants API アカウント（リフレッシュトークン）
- OpenAI API キー（LLM 呼び出し用）
- （実運用）kabuステーション API のパスワードや Slack トークン など

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate   (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （実プロジェクトでは requirements.txt / pyproject.toml に依存関係を記載してください）

4. 環境変数 / .env を用意
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須キー（例）
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN — Slack 通知に使用
     - SLACK_CHANNEL_ID — Slack チャネル ID
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - OPENAI_API_KEY — OpenAI API キー（news_nlp/regime_detector 呼び出し時に api_key 引数でも指定可）
   - 任意・デフォルト
     - KABUSYS_ENV — development / paper_trading / live （デフォルト development）
     - LOG_LEVEL — DEBUG / INFO / ...（デフォルト INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）

   例 .env（サンプル）
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0112345
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development

使い方（主要 API と利用例）
--------------------------

1) DuckDB 接続を作成して ETL 実行（日次 ETL）
- サンプルコード（Python）
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(<path/to/duckdb>))  # 例: settings.duckdb_path
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- run_daily_etl は calendar → prices → financials → 品質チェック の順で実行し ETLResult を返します。

2) ニュースセンチメントの算出（AI）
- サンプル（1日分）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY は環境変数か引数で指定可能
  print(f"書込み銘柄数: {count}")

- score_news は raw_news と news_symbols を参照し ai_scores テーブルへ書き込みます。OpenAI 呼出しはバッチ処理（最大 20 銘柄/リクエスト）で行います。API エラー時はフォールバックして継続します。

3) 市場レジーム判定
- サンプル
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))  # OpenAI キーは env か引数で渡す

- ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM スコア（重み 30%）を合成して market_regime テーブルに冪等で書き込みます。

4) 監査ログ DB 初期化
- 監査ログ用 DuckDB を作成してスキーマ初期化
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可

- init_audit_db は必要なテーブル / インデックスを作成し、UTC タイムゾーンをセットします。

5) 研究（factor / forward return / IC）
- 例: モメンタム算出
  from kabusys.research.factor_research import calc_momentum
  records = calc_momentum(conn, target_date=date(2026,3,20))

- 研究モジュールは DuckDB の prices_daily / raw_financials のみを参照し、本番発注等には影響しません。

設定と挙動の注意点
-----------------
- 環境読み込み: kabusys.config はプロジェクトルート（.git または pyproject.toml を基準）を自動で探索し .env / .env.local を読み込みます。テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し: 関数は api_key 引数でキーを渡すこともできます。未設定の場合は環境変数 OPENAI_API_KEY を参照します。API 失敗時はフォールバック値を用いる設計（例: macro_sentiment=0.0）で堅牢性を高めています。
- Look-ahead バイアス対策: モジュールの多くは date / target_date を明示的に受け取り、datetime.today() を直接参照しない設計です（バックテストでのルックアヘッドを防止）。
- DuckDB executemany の制約に対応した実装（空パラメータ回避など）を行っています。

ディレクトリ構成（要約）
----------------------
src/kabusys/
- __init__.py                — パッケージ定義（公開サブパッケージ一覧）
- config.py                  — 環境変数／設定管理
- ai/
  - __init__.py
  - news_nlp.py              — ニュースセンチメント算出
  - regime_detector.py       — 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py        — J-Quants API クライアント + DuckDB 保存
  - pipeline.py              — ETL パイプライン（run_daily_etl 等）
  - etl.py                   — ETLResult 再エクスポート
  - news_collector.py        — RSS 取得・前処理
  - calendar_management.py   — 市場カレンダー管理（is_trading_day 等）
  - quality.py               — データ品質チェック
  - stats.py                 — 汎用統計ユーティリティ（zscore 正規化等）
  - audit.py                 — 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py       — Momentum/Value/Volatility 等
  - feature_exploration.py   — forward returns / IC / summary 等
- （その他）strategy/, execution/, monitoring/ など（公開 API 参照）

補足
----
- この README はコードベースから抽出した設計意図・利用法の要約です。実際の運用では依存関係管理（requirements.txt / pyproject.toml）、ログハンドラ設定、シークレット管理（Vault 等）の導入を推奨します。
- セキュリティ面: news_collector は SSRF/XML Bomb 対策を実装していますが、実運用ではネットワーク制限・監査ログ・レート制御を併用してください。

ライセンス、貢献方法など
----------------------
（このリポジトリのライセンス・コントリビュートポリシーをここに記載してください）

以上。必要であれば README に入れるサンプル .env.example、requirements.txt、あるいは具体的な CLI 利用例（cron ジョブ例、Dockerfile）を追加で作成します。どの情報を優先して追記しますか？