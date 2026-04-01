KabuSys — 日本株自動売買プラットフォーム（README）
概要
KabuSys は日本株向けのデータ基盤・リサーチ・AI 評価・監査ログ・ETL を含むライブラリ群です。本リポジトリは以下の機能群を提供し、自動化バッチや研究用途から運用（ペーパー / 本番）までを想定しています。

主な設計方針
- Look‑ahead bias を避ける設計（内部で datetime.today()/date.today() を直接参照しない）
- DuckDB を中心としたローカル DB ベースの ETL / 保存（冪等性を重視）
- J‑Quants API（株価・財務・カレンダー）の差分取得 + 保存（リトライ・レート制御あり）
- OpenAI（gpt-4o-mini）を用いたニュース NLP / マクロセンチメント評価（JSON Mode）
- 監査ログ（signal → order_request → execution）のスキーマと初期化ユーティリティ
- 安全性対策（RSS の SSRF 防止、XML を defusedxml でパース、API のリトライ/バッファ制御など）

機能一覧
- データ取得 / ETL
  - J-Quants クライアント（jquants_client）：株価日足、財務、上場銘柄、JPX カレンダーの取得と DuckDB への保存（save_*）
  - ETL パイプライン（data.pipeline）：日次 ETL（run_daily_etl）と個別 ETL ジョブ（run_prices_etl 等）
  - データ品質チェック（data.quality）：欠損、重複、スパイク、日付不整合検出
  - マーケットカレンダー管理（data.calendar_management）：営業日判定、next/prev_trading_day、calendar_update_job
  - ニュース収集（data.news_collector）：RSS 収集 / 前処理 / raw_news への保存（SSRF 対策あり）
  - 監査ログ（data.audit）：監査テーブル定義・初期化ユーティリティ（init_audit_schema / init_audit_db）
- 研究 / ファクター
  - research.factor_research：Momentum / Volatility / Value 等のファクター計算
  - research.feature_exploration：将来リターン計算 / IC / 統計サマリ / ランク変換
  - data.stats：クロスセクション Z スコア正規化ユーティリティ
- AI（OpenAI）
  - ai.news_nlp.score_news：ニュース記事を銘柄ごとにまとめ、LLM でセンチメントを算出して ai_scores テーブルへ保存
  - ai.regime_detector.score_regime：ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成して market_regime を判定・保存
- 設定管理
  - config.Settings：環境変数 / .env 自動ロード（.git または pyproject.toml をルートとして探索）、主要設定のプロパティを提供

セットアップ手順
前提
- Python 3.10 以上（コード中に 3.10 の型構文（|）を使用）
- DuckDB、OpenAI 用の公式パッケージ等が必要

1) 仮想環境作成（推奨）
  python -m venv .venv
  source .venv/bin/activate  # Unix/macOS
  .venv\Scripts\activate     # Windows

2) 必要パッケージのインストール（例）
  pip install duckdb openai defusedxml

  ※プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください。

3) 環境変数設定
- パスワードや API キーは環境変数で設定します。プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

主な環境変数
- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY         : OpenAI API キー（AI モジュールで使用）
- KABU_API_PASSWORD      : kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL      : kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN        : Slack ボットトークン（必須）
- SLACK_CHANNEL_ID       : Slack チャンネルID（必須）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH            : SQLite などのパス（デフォルト data/monitoring.db）
- PID_FILE_PATH          : 実行監視用 PID ファイルパス（デフォルト data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT : 監視閾値（%）
- KABUSYS_ENV            : development / paper_trading / live（デフォルト development）
- LOG_LEVEL              : DEBUG / INFO / WARNING / ERROR / CRITICAL

例（.env）
  JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  OPENAI_API_KEY=sk-...
  KABU_API_PASSWORD=your_password
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C01234567
  DUCKDB_PATH=data/kabusys.duckdb

4) DB 初期化（監査ログ）
  Python REPL やスクリプト内で：
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可

使い方（代表的な呼び出し例）
- DuckDB 接続を用意
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行（市場カレンダー → 株価 → 財務 → 品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースの AI スコアリング（score_news）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  cnt = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {cnt} symbols")

- 市場レジーム判定（score_regime）
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  res = score_regime(conn, target_date=date(2026, 3, 20))
  print("regime scored", res)

- 監査ログスキーマ初期化（既存接続に適用）
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

注意点 / 運用トピック
- OpenAI 呼び出しはコストとレイテンシが発生します。API キーの管理とレートに注意してください。
- J-Quants API はレート制限を厳守する設計（内部で固定間隔スロットリング）。大量バッチの運用時は監視が必要です。
- ETL は差分更新・バックフィル設計です。初回ロード時には大量のデータ取得が発生するので注意してください。
- DuckDB の executemany に関するバージョン差異（空リストを渡せない等）に留意している実装になっています。
- 新闻（news_collector）は SSRF 対策や受信サイズ制限を実装していますが、外部 RSS ソースを運用する際はソースの安全性を確認してください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理（Settings）
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメント算出（score_news）
    - regime_detector.py            — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（fetch / save）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETLResult 再エクスポート
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - news_collector.py             — RSS 収集・前処理
    - calendar_management.py        — 市場カレンダー管理
    - audit.py                      — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py            — Momentum/Value/Volatility 等
    - feature_exploration.py        — 将来リターン / IC / 統計サマリ
  - ai, research, data の各モジュールが公開する関数群を通じて、ETL → 研究 → 実行のワークフローを構成します。

貢献 / 開発メモ
- 単体テストでは OpenAI / ネットワーク呼び出しをモックすることを推奨します（コード中に mock を差し替える箇所に注意）。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml が基準）から行われます。テスト等で自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB スキーマ定義（raw_prices / raw_financials / market_calendar / ai_scores / market_regime 等）は外部ドキュメント（Schema）や別モジュールで管理される想定です。本 README は主要機能の概要と使い方にフォーカスしています。

ライセンス
- 本リポジトリに記載のライセンスに従ってください（リポジトリに LICENSE があればそちらを参照）。

お問い合わせ
- 開発者向けの設計ドキュメント（StrategyModel.md / DataPlatform.md 等）に依存する説明がコード内コメントにあります。詳細は該当ドキュメントを参照してください。

以上。README の追加補足やサンプルスクリプト（CLI 用や systemd / Cron 用のテンプレート）を作成することも可能です。必要であれば教えてください。