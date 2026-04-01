KabuSys
=======

日本株向けの自動売買 / データ基盤ライブラリ。  
過去価格・財務データの ETL、ニュースの収集・LLM による NLP スコアリング、市場レジーム判定、研究用ファクター計算、監査（オーディット）テーブル管理などを提供します。

主な設計方針
- Look‑ahead バイアス排除を意識した日付ハンドリング（内部で date.today()／datetime.today() を不用意に参照しない）。
- J-Quants / OpenAI 等の外部 API に対してリトライやレート制御を実装。
- DuckDB をデータレイクに利用し、保存処理は冪等（ON CONFLICT）を基本とする。
- ニュース収集は SSRF 対策・サイズ制限・トラッキング除去などに配慮。

機能一覧
- ETL（data.pipeline）
  - 日次 ETL（株価・財務・カレンダー）の差分取得と保存（run_daily_etl 等）
  - J-Quants API クライアント（data.jquants_client）: 株価、財務、カレンダー、上場銘柄情報取得
- データ品質チェック（data.quality）
  - 欠損、重複、スパイク、日付不整合の検出
- マーケットカレンダー管理（data.calendar_management）
  - 営業日判定 / 前後営業日取得 / カレンダー更新ジョブ
- ニュース収集（data.news_collector）
  - RSS 取得、前処理、raw_news への冪等保存
- 監査ログ（data.audit）
  - signal → order_request → execution のトレース用テーブル定義と初期化ユーティリティ
- 研究用モジュール（research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化
- AI（ai）
  - ニュースセンチメントスコアリング（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
- 設定管理（config）
  - .env 自動読み込み（プロジェクトルート検出）と Settings オブジェクト

必要条件
- Python 3.10 以上（Union types / | 形式の型注釈を使用）
- 主要依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
その他、実行環境によって urllib 関連の標準ライブラリ、typing 等が必要です。

セットアップ手順（開発用）
1. リポジトリをクローン／ダウンロード
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - 実プロダクションではその他のユーティリティや linter 等を追加してください
4. 環境変数 / .env を用意
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env/.env.local を置くと自動読み込みされます。
   - 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

必須環境変数（settings 参照）
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（get_id_token で使用）
- KABU_API_PASSWORD — kabu ステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
推奨 / オプション（デフォルトあり）
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG/INFO/…（デフォルト INFO）
- OPENAI_API_KEY — OpenAI 呼び出し時に利用（関数呼び出し時に api_key を渡すことも可）

主な使い方（コード例）
- DuckDB 接続作成（ファイル DB を使用）
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")
- 日次 ETL 実行
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - res = run_daily_etl(conn, target_date=date(2026, 3, 20))
- ニューススコアリング（OpenAI API を利用）
  - from kabusys.ai.news_nlp import score_news
  - score_count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
- 市場レジーム判定（ETF 1321 の MA200 とマクロ記事の LLM スコア合成）
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
- 監査 DB 初期化（監査専用 DB）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")
- RSS フィード取得（単体）
  - from kabusys.data.news_collector import fetch_rss
  - articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")

注意点 / 運用向けメモ
- OpenAI への呼び出しは gpt-4o-mini（コード内で _MODEL 指定）と JSON mode を用いる想定。API レート制御・リトライロジックを組み込んでいますが、API キー管理とコスト管理は運用で注意してください。
- J-Quants API はレート制限（120 req/min）を遵守するために内部で RateLimiter を使用します。get_id_token は自動リフレッシュ機構を持ちます。
- news_collector は SSRF 対策（リダイレクト検査・プライベート IP ブロック）と受信サイズ制限を実装しています。
- ETL / 保存は基本的に冪等（INSERT ... ON CONFLICT DO UPDATE）で行うため、再実行に耐性があります。
- DuckDB の executemany に空リストを渡せないバージョンなどの互換性考慮がコード内にあります。
- バックテストや研究用途で外部データを利用する場合は、必ず「いつそのデータを知り得たか（fetched_at 等）」を考慮して Look‑ahead バイアスを防止してください（モジュールはその方針で設計されています）。

ディレクトリ構成（主なファイル・モジュール）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの LLM スコアリング（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント & 保存ユーティリティ
    - pipeline.py — ETL パイプライン（run_daily_etl 等）および ETLResult
    - etl.py — ETL インターフェース（ETLResult 再エクスポート）
    - calendar_management.py — マーケットカレンダー管理
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - quality.py — データ品質チェック（QualityIssue, run_all_checks）
    - news_collector.py — RSS 収集・前処理
    - audit.py — 監査ログテーブル定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー等
  - research/*, ai/*, data/* はさらに細かいユーティリティ／SQL 実装を含みます

ログレベルと環境の切り替え
- KABUSYS_ENV により環境モードを選択（development, paper_trading, live）。settings.is_live 等で判定可能。
- LOG_LEVEL 環境変数でログ出力レベルを制御。

トラブルシューティング（よくある問題）
- 環境変数未設定による ValueError:
  - settings の必須プロパティは設定がなければ ValueError を送出します。必要なキーを .env に設定してください。
- OpenAI / J-Quants API の認証失敗:
  - トークン期限切れやレート制限はログに記録され、リトライや自動トークンリフレッシュ（J-Quants）を行います。必要に応じてトークンを再発行してください。
- DuckDB 互換性:
  - 古い DuckDB バージョンでは executemany の扱いに注意が必要です。推奨は比較的新しい DuckDB を使用してください。

貢献
- バグ報告・機能提案は Issue を立ててください。PR には説明・再現手順を添えてください。

ライセンス
- （本リポジトリにライセンスファイルがある場合はそちらを参照してください。README に明記する場合は適切なライセンス名に差し替えてください。）

付録: よく使うワンライナー例
- ETL を今すぐ実行（Python REPL）
  - >>> import duckdb, datetime
  - >>> from kabusys.data.pipeline import run_daily_etl
  - >>> conn = duckdb.connect("data/kabusys.duckdb")
  - >>> run_daily_etl(conn, target_date=datetime.date(2026,3,20))

必要な情報や追加のサンプル（起動スクリプト、systemd ユニット、Dockerfile など）が必要でしたら教えてください。README に追記して提供します。