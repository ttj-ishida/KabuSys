# KabuSys

日本株自動売買システムの一部（監視・実行・リサーチ・AI連携・ポートフォリオ構築ユーティリティ群）です。本リポジトリは、ExecutionEngine（発注実行）やMonitoringEngine（稼働監視）、研究用ファクター計算、ニュースNLPによるセンチメント集計等を含みます。

主な設計方針
- 本番とテスト（Paper Trading）を明確に分離（Paper Trading では専用の SQLite を使用）。
- ルックアヘッドバイアスを避ける実装（API 呼び出し・日付参照に注意）。
- フェイルセーフ設計（外部 API エラーは基本的にスキップして継続）。
- DuckDB を用いた時系列データ処理と SQLite による監視/注文ログの永続化。

---

目次
- プロジェクト概要
- 機能一覧
- 前提・依存関係
- セットアップ手順
- 環境変数（主なもの）
- 使い方（起動方法・ツール）
- ディレクトリ構成（主要ファイル説明）
- 補足 / 注意事項

---

プロジェクト概要
- KabuSys は日本株自動売買のコアロジック群（発注、リスクリミット、リコンシリエーション）と、監視・アラート、研究用ファクター計算、AI を用いたニュースセンチメント評価などを包含するモジュール群です。
- DuckDB をメインの時系列分析 DB（prices_daily, raw_financials 等）に使用し、SQLite を監視ログ・注文ログの永続化に使用します。

機能一覧
- ExecutionEngine 起動／発注管理（kabusys.run_execution）
  - Broker クライアントの抽象化（実ブローカー or MockBroker）
  - OrderManager による注文件作成・送信・同期
  - Reconciler による再起動時の自動復旧（OrderSent の突合とポジション差分検出）
  - RiskManager による建玉上限・ドローダウン等の制約
- MonitoringEngine（kabusys.monitoring）
  - SystemMonitor：CPU/メモリ/ディスク、プロセス死活、データ鮮度監視
  - TradeMonitor：滞留注文・約定異常価格検出
  - RiskMonitor：ドローダウン・ポジション上限監視とリスクイベント記録
  - KillSwitch：条件で ExecutionEngine を停止させるフラグファイル管理
  - AlertManager：LINE Push による通知（クールダウン管理）
  - streamlit ベースの監視ダッシュボード
- 研究・因子計算（kabusys.research）
  - モメンタム、ボラティリティ、バリュー等のファクター計算（DuckDB を用いた SQL＋Python 実装）
  - 将来リターン計算、IC（Information Coefficient）評価、統計サマリ
- ポートフォリオ構成（kabusys.portfolio）
  - 候補選定、等重・スコア重み配分、セクターキャップ適用、ポジションサイズ計算（単元株丸め・集約キャップ）
- AI（kabusys.ai）
  - news_nlp: raw_news を OpenAI に投げ、銘柄ごとのセンチメントを取得して ai_scores へ保存
  - regime_detector: ETF の MA とマクロニュースの LLM センチメントを合成して日次レジーム判定
- ユーティリティ
  - 環境設定自動読み込み（.env / .env.local）
  - プロセス優先度・CPU affinity 設定ユーティリティ
  - Paper Trading の検証レポート生成ツール

前提・依存関係
- Python 3.10+（typing の | None 構文などを利用）
- 主な Python パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（監視ダッシュボード用）
- 標準ライブラリ: sqlite3 等

（注）実行環境に合わせて pip install を行ってください。

セットアップ手順（例）
1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) / .venv\Scripts\activate (Windows)

2. 依存パッケージをインストール（requirements.txt がある場合はそれを使用）
   - pip install duckdb psutil requests openai streamlit

3. プロジェクトルートに .env を作成（.env.example を参照して必要な環境変数を設定）
   - 自動で .env/.env.local を読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

主要な環境変数（Settings で読み込むもの）
- 必須（未設定だと起動でエラー）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意 / デフォルトあり
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/…
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 専用 SQLite（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE: paper_trading 時の MockBroker 挙動（instant|partial|never|reject、デフォルト: instant）
  - PID_FILE_PATH / KILL_FLAG_PATH
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
  - OPENAI_API_KEY: OpenAI API を利用する機能で必要
- その他
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）。1 未満の値は無効扱いされデフォルトへフォールバック。

使い方（起動・ツール）
- 監視ループを起動（監視プロセス）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可（例: export MONITOR_POLL_INTERVAL=30）

- 実行エンジンを起動（発注処理）
  - KABUSYS_ENV を指定して Paper Trading と本番を切替
    - 本番（例）: KABUSYS_ENV=live python -m kabusys.run_execution
    - Paper Trading（モックブローカー、専用 DB へ記録）:
      - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - Execution 起動時はプロセス優先度を High に設定します（実装で最初に呼び出し）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db
  - デフォルト DB: data/paper_trading.db

- 監視ダッシュボード（Streamlit）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

重要な挙動メモ
- Paper Trading は本番監視 DB と分離して data/paper_trading.db に記録されます（settings.is_paper により切替）。
- Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を用いる設計箇所が存在する（run_monitoring の実装参照）。
- KillSwitch は指定された flag_path（デフォルト data/kill.flag）を書き込むことで ExecutionEngine 停止シグナルを出します。既に flag が存在する場合は上書きしません。
- .env の読み込み順: OS 環境 > .env.local > .env（OS 環境は保護され上書きされない）
- OpenAI 呼び出しはリトライ・バックオフ等を実装していますが、APIキー未設定時は機能をスキップないしエラーとなる箇所があります（news_nlp.score_news / regime_detector.score_regime など）。

ディレクトリ構成（主要ファイルの説明）
- src/kabusys/
  - __init__.py              — パッケージ定義
  - config.py                — 環境変数 / Settings 管理（.env 自動読み込みロジック含む）
  - run_monitoring.py        — SystemMonitor のポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト（paper_trading を考慮）
- src/kabusys/monitoring/
  - monitoring_db.py         — SQLite による監視ログ永続化（テーブル初期化・CRUD）
  - system_monitor.py        — CPU/メモリ/ディスク・プロセス・データ鮮度監視
  - trade_monitor.py         — 注文滞留・約定価格異常チェック
  - risk_monitor.py          — ドローダウン・ポジション上限の監視
  - kill_switch.py           — kill.flag の読書き（Execution 停止トリガ）
  - alert_manager.py         — LINE Push による通知（クールダウン）
  - monitoring_engine.py     — 各 Monitor を束ねる実行ループ
  - streamlit_dashboard.py   — Streamlit ベースの監視ダッシュボード
- src/kabusys/execution/
  - order_manager.py         — 発注フロー（Order 作成・送信・同期）
  - reconciler.py            — 再起動時の注文/ポジション突合
  - ...（ブローカー抽象・OrderRepository など、実装群）
- src/kabusys/portfolio/
  - portfolio_builder.py     — 候補選定・重み算出
  - position_sizing.py       — 発注株数計算（リスクベース/等配分等）
  - risk_adjustment.py       — セクター上限・レジーム乗数
- src/kabusys/research/
  - factor_research.py       — モメンタム / ボラ / バリュー ファクター計算（DuckDB ベース）
  - feature_exploration.py   — 将来リターン、IC、統計サマリ等
- src/kabusys/ai/
  - news_nlp.py              — raw_news を LLM でスコアリングして ai_scores に書き込む
  - regime_detector.py       — マーケットレジーム判定（MA + マクロ LLM）
- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 結果の簡易レポート生成

補足 / 注意事項
- SQLite / DuckDB ファイルのパスは Settings で定義されており、環境変数で上書き可能です（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）。
- psutil によるプロセス優先度変更や CPU affinity は権限に依存します。権限不足の場合は警告ログを出してスキップします。
- OpenAI API を利用する機能は API キー管理に注意してください（環境変数 OPENAI_API_KEY を利用）。
- DB マイグレーション用の軽微な処理（カラム追加チェックなど）を monitoring_db.init_monitoring_db 内で行います。既存 DB を直接操作する場合は注意して下さい。

ライセンス / 貢献
- 本 README 内ではライセンス情報は示していません。実際の配布リポジトリに LICENSE を追加してください。
- バグ修正・機能追加の際は、ユニットテストとローカルでの Paper Trading を走らせて動作確認をお願いします。

---

必要であれば README にコマンドの具体例（systemd ユニット、Dockerfile、CI 設定等）や .env.example のテンプレート、requirements.txt の候補を追記します。どの情報が欲しいか教えてください。