KabuSys — 日本株自動売買システム
================================

このリポジトリは、日本株の自動売買システム「KabuSys」のコアモジュール群です。
戦略（リサーチ / ファクター）・ポートフォリオ構築・発注実行・監視・AI（ニュースNLP/レジーム判定）などを含む設計になっています。

主な設計方針
- DuckDB を用いたオフラインリサーチ（prices_daily / raw_financials 等）と、
  SQLite を用いた軽量な監視 / 発注ログ永続化を併用する。
- 本番/ペーパートレードは環境変数 KABUSYS_ENV で切り替え可能（paper_trading 時は DB を分離）。
- 自動監視（MonitoringEngine）と ExecutionEngine の分離。監視は ExecutionEngine の停止/アラート・kill flag 出力などを行う。
- News NLP / Regime 判定は OpenAI（gpt-4o-mini）を利用する設計。API呼び出しはフェールセーフに実装。

機能一覧
- 実行（Execution）
  - ExecutionEngine（発注フロー、リスク管理、リコンサイル機能）
  - BrokerClientFactory による本番 / モック（paper_trading）クライアント切替
- 監視（Monitoring）
  - SystemMonitor：CPU/メモリ/ディスク/プロセス状態 / データ鮮度監視
  - TradeMonitor：滞留注文・約定異常検出
  - RiskMonitor：ドローダウン・ポジション上限監視
  - MonitoringEngine：上記モニタの定期実行、KillSwitch、AlertManager 統合
  - AlertManager：LINE Messaging API への通知（クールダウン制御）
  - Streamlit ベースの監視ダッシュボード
- ポートフォリオ構築（pure functions）
  - 銘柄候補選択、等金額／スコア加重配分、リスク調整（セクターキャップ・レジーム乗数）、ポジションサイズ算出（lot 単位丸め・集約上限）
- リサーチ
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（スピアマン）計算、特徴量統計
- AI（OpenAI）
  - news_nlp: raw_news を集約して LLM に投げ、銘柄ごとのセンチメントを ai_scores テーブルへ書き込み
  - regime_detector: ETF(1321) の MA とマクロニュースの LLM センチメントを合成して market_regime を算出・保存
- ツール
  - paper_verification_report: Paper Trading の検証レポート（稼働率・注文成功率・レイテンシ等）

セットアップ手順（開発用）
- Python 3.10+ を推奨
- 必要パッケージ（代表例）:
  pip install duckdb psutil requests streamlit openai
  （実プロジェクトでは requirements.txt を用意して pip install -r requirements.txt を実行してください）

環境変数（代表）
- 必須（実行によっては）
  - JQUANTS_REFRESH_TOKEN — J-Quants API トークン
  - KABU_API_PASSWORD — kabu ステーション API 用パスワード
- OpenAI
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector が必要）
- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
- 動作モード / DB パス等（デフォルト値は以下）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag
  - MONITOR_POLL_INTERVAL: 監視ポーリング秒数（run_monitoring 実行時に参照、デフォルト 60）
  - LOG_LEVEL, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

.env 自動読み込み
- プロジェクトルート（.git または pyproject.toml を基準）にある .env / .env.local が自動的に読み込まれます。
- OS 環境変数 > .env.local（override）> .env の順でマージされます。
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

使い方（主要コマンド・実行例）
- ExecutionEngine（発注エンジン）起動
  - デフォルト（本番/ペーパーは KABUSYS_ENV で制御）
    KABUSYS_ENV=live python -m kabusys.run_execution
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - ペーパートレードでは MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録されます。

- Monitoring（監視ループ）起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒指定（例: 30秒）
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 重要: run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視データは本番 DB を想定）。

- Streamlit ダッシュボード起動（読み取り専用 DB）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを明示:
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI / リサーチ機能（ライブラリ関数として利用）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - research.calc_momentum(conn, date), calc_volatility(...), calc_value(...)
  - これらは DuckDB 接続（duckdb.connect(...)）を受け取り、テストやバッチジョブから呼び出します。

注意点 / 実運用メモ
- run_monitoring は監視 DB の初期化（monitoring_db.init_monitoring_db）を行います。既存 DB に対するマイグレーション処理（列追加）も含まれます。
- run_execution は paper_trading 環境時に DB を分離します（settings.is_paper）。
- KillSwitch は data/kill.flag を書き込むことで ExecutionEngine 停止のシグナルを送ります。ExecutionEngine は起動時に kill flag を消去するオプション（Settings.kill_flag_clear_on_start）などを利用できます。
- OpenAI 呼び出しはリトライ・バックオフやレスポンスバリデーションが施されていますが、API キーの設定ミスや料金に注意してください。
- AlertManager は LINE トークンが未設定の時はログのみで終了します。大量通知を防ぐためクールダウン（デフォルト 30 分）を実装しています。
- PID ファイルや kill.flag の扱い、プロセス優先度の設定（psutil）が実行環境で動作するかを事前に確認してください（Linux / Windows の差分吸収あり）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                           — 環境変数 / .env ロード / Settings クラス
  - run_execution.py                    — ExecutionEngine 起動スクリプト
  - run_monitoring.py                   — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py      — Paper Trading 検証レポート CLI
  - ai/
    - __init__.py
    - news_nlp.py                       — ニュース NLP（OpenAI）で ai_scores を生成
    - regime_detector.py                — 市場レジーム判定（MA + マクロ NLP）
  - monitoring/
    - __init__.py
    - monitoring_db.py                  — SQLite テーブル定義・CRUD（MonitoringDB）
    - system_monitor.py                 — システム/データ鮮度監視
    - trade_monitor.py                  — 注文滞留 / 約定異常監視
    - risk_monitor.py                   — ドローダウン / ポジション上限監視
    - monitoring_engine.py              — 各 Monitor を束ねる
    - alert_manager.py                  — LINE 通知
    - kill_switch.py                    — kill.flag 管理
    - streamlit_dashboard.py            — Streamlit 監視ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - (... その他 Execution 系モジュールはここに配置 ...)
  - portfolio/
    - portfolio_builder.py              — 候補選択 / 等配分 / スコア加重
    - position_sizing.py                 — 株数計算（lot 丸め・集約 cap）
    - risk_adjustment.py                 — セクターキャップ / レジーム乗数
    - __init__.py
  - research/
    - factor_research.py                — Momentum / Volatility / Value
    - feature_exploration.py             — 将来リターン / IC / 統計サマリー
    - __init__.py
  - utils/
    - __init__.py
    - process_priority.py               — プロセス優先度 / CPU affinity ユーティリティ

開発・貢献
- コードはモジュール単位で設計されており、ユニットテストを書きやすい純粋関数（portfolio、research）の領域と、外部依存（DB・API）を扱う領域が分離されています。
- テスト時は環境変数自動ロードを無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）し、DuckDB の一時 DB を使うなどの方針が有効です。
- OpenAI 呼び出し等はテスト用に _call_openai_api を patch して差し替えられる設計になっています。

付記
- README に記載したコマンド例は開発向けの最小説明です。実運用ではプロセスマネージャ（systemd / Supervisor / Docker / k8s など）での管理、ログの集約、バックアップ、機密情報の安全管理（シークレット管理）を必ず実装してください。

---
この README はコードベースのコメント・ドキュメントを基に作成しています。追加で導入手順（requirements.txt / Dockerfile / systemd ユニット等）や API 契約書が必要であれば、用途に応じて追記できます。