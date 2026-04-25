KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買に関する実運用向けコンポーネント群（ExecutionEngine、Monitoring、Portfolio Construction、Research、AI 補助など）を含む Python パッケージです。本リポジトリは発注・監視・リスク管理・バックテスト/リサーチ用のユーティリティ群を提供します。設計方針は「本番とテストを明確に分離」「フェイルセーフ」「ルックアヘッドバイアス回避」です。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV に応じて本番 / ペーパートレーディングを切り替え
  - RiskManager、OrderManager、Reconciler 等の組立てと実行スレッド管理
  - 停止フラグ（data/stop_requested.flag）で安全に停止可能
- Monitoring（run_monitoring.py）
  - SystemMonitor、TradeMonitor、RiskMonitor を定期ポーリング
  - kill.flag による外部からの強制停止（Kill Switch）
  - 監視情報を SQLite に永続化（monitoring_db）
- Portfolio Construction
  - 候補選定・重み付け（等金額・スコア加重）
  - ポジションサイズ算出（リスクベース、単元株丸め、合計キャップ調整）
  - セクターキャップ、レジーム乗数
- Research（DuckDB を用いたファクター計算・特徴量解析）
  - モメンタム / ボラティリティ / バリューのファクター計算
  - 将来リターン計算、IC（Information Coefficient）等
- AI 支援モジュール
  - news_nlp: OpenAI を用いたニュースセンチメント計算と ai_scores への書き込み
  - regime_detector: ma200 とマクロニュースの LLM センチメントを合成して市場レジーム判定
- ツール
  - config_setup: 対話式 .env 生成ウィザード
  - validate_config: .env と config/*.yaml の事前チェック CLI
  - paper_verification_report: ペーパートレード結果の検証レポート生成

セットアップ
-----------
1. Python（推奨: 3.10+）を用意します。

2. 必要なパッケージをインストールします（最低限の一覧）:
   - duckdb
   - psutil
   - openai
   - PyYAML（config.yaml の検証を行う場合）
   - （必要に応じて他の実装依存ライブラリ）

   例:
   pip install duckdb psutil openai PyYAML

   ※ 実環境では requirements.txt/poetry/poetry.lock を用意してください（本リポジトリには含まれていません）。

3. .env を作成します
   - 対話式ウィザードを使う:
     python -m kabusys.config_setup
   - もしくは手動で .env を作成（プロジェクトルートに配置）。主な環境変数:

     必須:
       - JQUANTS_REFRESH_TOKEN
       - KABU_API_PASSWORD

     選択 / デフォルト値:
       - KABUSYS_ENV (development | paper_trading | live) — default: development
       - DUCKDB_PATH — default: data/kabusys.duckdb
       - SQLITE_PATH — default: data/monitoring.db
       - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
       - LOG_LEVEL — default: INFO
       - KILL_FLAG_CLEAR_ON_START — default: 0
       - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 任意（本番アラート用）

   - 自動ロード:
     Settings モジュールはプロジェクトルートに .env/.env.local がある場合、自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

4. ディレクトリとファイルの準備
   - data/ ディレクトリや logs/ を作成するか、実行時に自動作成されます。
   - SQLite / DuckDB は指定パスにファイルを生成します（既存でも問題ありません）。

使い方
------
基本的な CLI（モジュール実行）:

- 設定ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  # 警告を FAIL 扱い

- ExecutionEngine を起動
  python -m kabusys.run_execution

  動作モード:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録し、本番 DB と分離されます。
  停止:
    - data/stop_requested.flag を作成すると起動中のループが終了します。
    - Kill Switch（monitoring により生成される data/kill.flag）で安全停止を指示できます。
  PID / フラグ:
    - 実行時に data/execution.pid（デフォルト）を使用します（Settings.pid_file_path から変更可）。

- Monitoring を起動
  python -m kabusys.run_monitoring

  ポーリング間隔:
    - 環境変数 MONITOR_POLL_INTERVAL で秒数を設定（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバックします。
  DB:
    - Monitoring は KABUSYS_ENV に関わらず settings.sqlite_path（デフォルト data/monitoring.db）を使用します。

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

プログラムからの利用（ライブラリ API）
- portfolio:
  from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
- research:
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
- ai:
  from kabusys.ai import score_news
  （regime_detector は kabusys.ai.regime_detector.score_regime を直接 import して使用）
- monitoring:
  MonitoringDB / MonitoringEngine / KillSwitch 等を組み合わせてカスタム監視を構築可能

運用上の注意
------------
- ロギング:
  - setup_logging() が各起動スクリプトから呼ばれ、logs/<app_name>.log に日次ローテーションで出力します。ログディレクトリの作成に失敗した場合はコンソールのみ出力されます。
  - 環境変数 LOG_LEVEL でログレベルを調整できます。

- プロセス優先度:
  - run_* スクリプトは起動時に set_process_priority("high") を試みます（psutil を使用）。権限によっては設定に失敗し警告になります。

- データベース:
  - monitoring_db.init_monitoring_db() は冪等にテーブルとマイグレーションを適用します。
  - duckdb は分析用途（prices_daily / raw_financials / raw_news 等）で使用されます。DuckDB のテーブルは別途準備してください。

- AI（OpenAI）:
  - news_nlp.score_news / regime_detector.score_regime は OPENAI_API_KEY を要求します（引数で渡すことも可）。
  - LLM 呼び出しはリトライ・クリップ・バリデーションやフェイルセーフ（失敗時スコアを無視/0にフォールバック）を備えていますが、実運用では API レート・コスト・応答検証に注意してください。

- Kill Switch / フラグ:
  - monitoring が重大なリスク条件を検出すると data/kill.flag を書き込み、ExecutionEngine を停止する設計です。KILL_FLAG_CLEAR_ON_START 環境変数で起動時の自動クリア挙動を決められます（本番では 0 推奨）。

ディレクトリ構成（主要ファイル）
------------------------------
リポジトリの主要モジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                 # Settings / .env 自動ロード・検証ユーティリティ
  - config_setup.py           # .env 対話式ウィザード
  - validate_config.py        # 設定検証 CLI
  - run_execution.py          # ExecutionEngine 起動スクリプト
  - run_monitoring.py         # SystemMonitor ポーリングループ起動スクリプト

  - execution/                # Execution 系（発注・リスク・リポジトリ等） — 実装ファイル群（省略）
  - monitoring/
    - monitoring_db.py        # SQLite 永続層 + MonitoringDB クラス
    - system_monitor.py       # system 状態・データ鮮度チェック
    - trade_monitor.py        # (存在) 発注ログ監視等
    - risk_monitor.py         # ドローダウン・ポジション上限監視
    - kill_switch.py          # kill.flag の作成/評価
    - monitoring_engine.py    # 各 monitor を束ねる実行エンジン
    - alert_manager.py        # (存在) 通知管理（LINE など）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             # ニュースの LLM スコアリング
    - regime_detector.py      # 市場レジーム判定
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

- data/                      # 実行時生成される SQLite/DuckDB/flag/pid 等（デフォルト）
- logs/                      # ログ出力ディレクトリ（デフォルト）

よくある操作例
---------------
- .env を作って起動前チェック:
  python -m kabusys.config_setup
  python -m kabusys.validate_config

- 監視プロセス起動（デーモン化は外部ツールで管理）:
  python -m kabusys.run_monitoring

- 実行エンジン起動（ペーパートレード）:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- 停止（安全停止フラグ作成）:
  touch data/stop_requested.flag

開発・拡張のヒント
------------------
- DuckDB 上のテーブル（prices_daily, raw_financials, raw_news 等）は研究/AI/レジーム判定で参照されます。適切な ETL を用意してデータを投入してください（kabusys.data.pipeline 等がある想定）。
- AI モジュールのテストは _call_openai_api をモックすることで安定させられます（既にテスト向けに設計されています）。
- settings は Settings クラス経由で取得するため、ユニットテスト時は環境変数を一時的に差し替えるか KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動ロードを無効化できます。

免責と注意
-----------
- 本プロジェクトはサンプルの自動売買システムの構成要素を示すものであり、実際の運用や資金投入は各自の責任で行ってください。実際の注文発行は Kabuステーション API によるため、本番環境では十分な検証と安全対策（回復手順・モニタリング・人による確認）を行ってください。

---
この README はコードベース（src/kabusys）からの抜粋に基づいて生成しています。実際の追加ファイル（execution モジュール内部 等）に応じて必要な情報や依存関係を追記してください。必要であれば README の英語版や systemd / supervisor 用のサービス定義例、docker-compose 例なども作成できます。希望があればお知らせください。