プロジェクト: KabuSys — 日本株自動売買 / データプラットフォーム
概要
- KabuSys は日本株のデータ取得（J-Quants）、ETL、品質チェック、ニュース収集/AIによるニュースセンチメント評価、ファクター計算、監査ログ（発注〜約定のトレーサビリティ）などを想定したライブラリ群です。
- 主に DuckDB をデータストアとして使用し、J-Quants API や OpenAI（gpt-4o-mini）を外部サービスとして利用します。
- バックテスト・リサーチ用のユーティリティ（ファクター計算、将来リターン、IC計算等）も含まれます。

主な機能一覧
- 環境設定管理
  - .env / .env.local の自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - settings オブジェクト経由でアプリ設定を参照可能（J-Quants トークン、OpenAI キー、DBパス 等）
- データ ETL（kabusys.data.pipeline）
  - 日次 ETL（市場カレンダー / 株価日足 / 財務データ）と品質チェックの統合実行
  - 差分取得・バックフィル・冪等保存（ON CONFLICT DO UPDATE）
- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足、財務、上場銘柄、マーケットカレンダーの取得
  - レートリミッティング、リトライ、401時のトークンリフレッシュ対応
- ニュース収集（kabusys.data.news_collector）
  - RSS から記事を収集し前処理して raw_news に保存（SSRF対策、XML安全パース、トラッキング除去）
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付整合性チェックを実行
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions などの監査テーブル定義と初期化ユーティリティ
- AI モジュール（kabusys.ai）
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価して ai_scores に保存
  - regime_detector.score_regime: ETF (1321) の MA200 乖離とマクロニュースの LLM センチメントを合成して市場レジーム判定
- リサーチ（kabusys.research）
  - calc_momentum / calc_value / calc_volatility 等のファクター計算
  - calc_forward_returns / calc_ic / factor_summary / rank などの探索的解析ツール
- 汎用統計ユーティリティ（kabusys.data.stats）
  - zscore_normalize（クロスセクション Z スコア正規化）

セットアップ手順（ローカル開発向け）
1. Python 環境
   - 推奨: Python 3.10 以上（PEP 604 型表記などを使用）
   - 仮想環境を作成して有効化する例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリのインストール（最低限）
   - pip install duckdb openai defusedxml
   - 実際のプロジェクトでは requirements.txt / pyproject.toml を用意して pip install -e . 等で管理してください。
   - 追加で Slack 等に通知する場合は slack-sdk 等のクライアントを導入してください。

3. 環境変数の設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（.git または pyproject.toml が存在するディレクトリがプロジェクトルートとして探索されます）。
   - 自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 主要な環境変数（必須 / 任意）:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabuステーション API パスワード（発注等で利用）
     - KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
     - SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot Token
     - SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
     - OPENAI_API_KEY (必須 for AI 機能) — OpenAI API キー（news_nlp / regime_detector 等で使用）
     - DUCKDB_PATH (任意) — デフォルト data/kabusys.duckdb
     - SQLITE_PATH (任意) — 監視用 SQLite のデフォルト data/monitoring.db
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
     - LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
   - .env の書式は shell の export やクォートに対応した柔軟なパーサが提供されます。

使い方（簡易サンプル）
- settings の参照
  - from kabusys.config import settings
  - settings.jquants_refresh_token などで値を取得（未設定時は ValueError）

- DuckDB 接続と ETL 実行（日次 ETL）
  - import duckdb
    from kabusys.config import settings
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect(str(settings.duckdb_path))
    from datetime import date
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- OpenAI を使ったニューススコアリング
  - from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect(str(settings.duckdb_path))
    from datetime import date
    n_written = score_news(conn, target_date=date(2026, 3, 20))
    print("written:", n_written)
  - OpenAI API キーは OPENAI_API_KEY 環境変数か、api_key 引数で渡します。

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect(str(settings.duckdb_path))
    from datetime import date
    score_regime(conn, target_date=date(2026,3,20))  # OpenAI key は環境変数か引数で

- 監査テーブル初期化
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")  # 必要に応じてパスを変更

- ファクター計算 / リサーチ
  - from kabusys.research.factor_research import calc_momentum
    conn = duckdb.connect(str(settings.duckdb_path))
    records = calc_momentum(conn, target_date=date(2026,3,20))
    # zscore 正規化
    from kabusys.data.stats import zscore_normalize
    normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])

注意点・設計上のポイント
- ルックアヘッドバイアス防止:
  - AI モジュール・ETL・リサーチ関数は内部で date.today() を不用意に参照しない設計が採られ、target_date を明示して使うことを想定しています。
- 冪等性:
  - DB への保存は ON CONFLICT DO UPDATE / INSERT … ON CONFLICT といった冪等処理を行います。
- フェイルセーフ:
  - 外部 API（OpenAI / J-Quants）呼び出しでエラーが発生しても、適切にフォールバックする設計（例: マクロセンチメント失敗時は 0.0 を使用）になっています。
- テストのために各モジュール内の外部呼び出し（OpenAI 呼び出しなど）をモック可能な実装になっています。

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py                        — 環境変数 / 設定管理
    - ai/
      - __init__.py
      - news_nlp.py                    — ニュースセンチメント評価（OpenAI）
      - regime_detector.py             — 市場レジーム判定
    - data/
      - __init__.py
      - calendar_management.py         — 市場カレンダー管理
      - etl.py                         — ETL エントリ（ETLResult 再エクスポート）
      - pipeline.py                    — ETL パイプライン実装
      - stats.py                       — 汎用統計ユーティリティ
      - quality.py                     — データ品質チェック
      - audit.py                       — 監査ログスキーマ/初期化
      - jquants_client.py              — J-Quants API クライアント + 保存ロジック
      - news_collector.py              — RSS ニュース収集
    - research/
      - __init__.py
      - factor_research.py             — Momentum/Value/Volatility 等
      - feature_exploration.py         — 将来リターン/IC/統計サマリー 等

追加の補足
- ロギングは settings.log_level で制御されます。デフォルトは INFO。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）から探索します。CI・テストで自動ロードを避けたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しや HTTP リクエストはネットワーク・レート制限・タイムアウトを考慮した実装になっていますが、運用時は API 利用量・コストに留意してください。

ライセンス / 貢献
- 現状 README はコードベースから作成したものです。実運用・公開リポジトリ化する場合は LICENSE、貢献ガイド、CI 設定等を追加してください。

必要があれば以下を作成します
- .env.example のテンプレート
- 実行例スクリプト（etl_run.py / score_news.py 等）
- requirements.txt / pyproject.toml の雛形

必要に応じて追加のドキュメント（API リファレンス、設計ドキュメント抜粋、運用手順）を作成します。どれを優先しますか？