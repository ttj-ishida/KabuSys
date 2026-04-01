KabuSys
=======

日本株自動売買プラットフォーム（ライブラリ）です。  
データ取得（J-Quants）、ETL、ニュースNLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログなどを含むモジュール群を提供します。

主な目的
- J-Quants API から株価／財務／カレンダーを差分取得して DuckDB に保持
- RSS ニュースを収集し OpenAI で銘柄別センチメントを算出
- ETF とマクロニュースを組み合わせた市場レジーム判定
- 研究用途のファクター計算・特徴量解析ユーティリティ
- 発注・約定に至る監査テーブル（監査ログ）初期化・管理

機能一覧
- 環境設定管理
  - .env/.env.local を自動読み込み（プロジェクトルート検出：.git または pyproject.toml）
  - 必須設定に対する明示的なエラー
- データ取得・ETL
  - J-Quants クライアント（レートリミット・リトライ・トークン自動リフレッシュ）
  - 差分取得（バックフィル対応）と DuckDB への冪等保存
  - 市場カレンダー（JPX）更新ジョブ
  - ETL の品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース処理（news_collector）
  - RSS 収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - raw_news / news_symbols 連携
- ニュース NLP（OpenAI）
  - 銘柄別センチメント算出（gpt-4o-mini, JSON Mode、バッチ処理・リトライ）
  - 市場マクロセンチメント + ETF MA 乖離での日次レジーム判定（bull/neutral/bear）
- 研究（research）
  - Momentum / Volatility / Value ファクター計算
  - 将来リターン計算、IC（Spearman）、ファクター統計サマリー、Zスコア正規化
- 監査ログ（audit）
  - signal_events / order_requests / executions のスキーマと初期化ユーティリティ
  - 監査DB 初期化（DuckDB）

セットアップ手順（開発・利用）
1. Python 環境
   - Python 3.9+ を推奨（コードは型ヒントに Python 3.10 系を想定している箇所がありますが、3.9 以上で動作します）
2. 依存パッケージ（例）
   - duckdb
   - openai
   - defusedxml
   - （必要に応じて）slack-sdk など
   例:
   - pip install duckdb openai defusedxml
   - またはプロジェクトルートで pip install -e .（セットアップ用の setup/pyproject がある場合）
3. 環境変数 / .env
   - プロジェクトルートに .env（および任意で .env.local）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な変数（必須は明記）:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
     - OPENAI_API_KEY (必須 for NLP) — OpenAI API キー
     - KABU_API_PASSWORD (必須 for 実行モジュール) — kabuステーション API パスワード
     - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN (必須 if Slack 通知を使う)
     - SLACK_CHANNEL_ID (必須 if Slack 通知を使う)
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — 監視用 sqlite のパス（data/monitoring.db）
     - PID_FILE_PATH — 実行プロセスの PID ファイル（data/execution.pid）
     - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
     - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
   - 簡単な .env テンプレート例:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
4. データディレクトリ作成
   - .env に指定した path（例 data/）のディレクトリを作成しておきます。
     mkdir -p data

基本的な使い方（コード例）
- DuckDB 接続を作って日次 ETL を実行
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントのスコアリング（OpenAI API キーが必要）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {n_written}")

- 市場レジーム判定
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査DB（監査ログ）初期化
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を使って audit テーブルが作成済みか確認できます

注意点 / 運用上のヒント
- Look-ahead bias 防止
  - ライブラリの多くは datetime.today()/date.today() を直接参照せず、target_date を明示的に渡すよう設計されています。バックテストでの日付管理に注意してください。
- 環境変数の自動読み込み
  - パッケージインポート時にプロジェクトルート（.git または pyproject.toml を基準）を探索して .env/.env.local を読み込みます。テストなどで自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し
  - news_nlp と regime_detector は gpt-4o-mini を前提に JSON Mode を使うように設計されています。API 応答の構造に依存するため、SDK のバージョン差異に注意してください。
- J-Quants API
  - rate limit（120 req/min）を守る実装です。get_id_token はリフレッシュトークンから id token を発行します。ID トークンはキャッシュされ、必要時に自動リフレッシュされます。
- DuckDB executemany の注意
  - 一部コード（ai/news_nlp など）は DuckDB の executemany の制約に配慮して空リストを渡さないようにしています。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理（.env 自動ロード、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py — 銘柄ニュースの NLP スコアリング（OpenAI バッチ処理）
    - regime_detector.py — 市場レジーム判定（ETF MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存・リトライ）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETL インターフェース再エクスポート（ETLResult）
    - news_collector.py — RSS 収集（SSRF 対策、前処理、保存）
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - quality.py — 品質チェック
    - audit.py — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー等

ライセンス / 貢献
- 本リポジトリに付随するライセンスファイル（LICENSE）があればそれに従ってください。貢献方法やコントリビュートガイドがあればプロジェクトルートに記載してください。

トラブルシューティング
- 環境変数が足りない場合は Settings のプロパティが ValueError を出します。エラーメッセージに従って .env を確認してください。
- OpenAI / J-Quants の API エラーはログに詳細が出力されます。エラー種別に応じて自動リトライやフォールバック（0.0 スコア等）が組み込まれています。
- DuckDB 関連の SQL エラーは接続やスキーマの不整合が原因になりやすいです。スキーマ初期化（audit.init_audit_schema 等）を適切に行ってください。

以上。必要であれば README にサンプル .env.example、requirements.txt、さらに具体的な実行スクリプト例（cron / systemd 用）を追記します。どの追加情報が欲しいか教えてください。