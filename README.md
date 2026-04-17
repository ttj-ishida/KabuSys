KabuSys — 日本株自動売買システム（README）
================================

概要
----
KabuSys は日本株の自動売買 / 研究 / 監視を行うための軽量なコードベースです。
主な目的は次のとおりです。

- 日次・リアルタイムでの発注エンジン（ExecutionEngine）
- システム・注文・リスク監視（MonitoringEngine）
- ポートフォリオ構築・サイズ決定ロジック（Portfolio モジュール）
- ファクター計算・リサーチユーティリティ（Research モジュール）
- ニュース NLP を用いた AI ベースのスコアリング（AI モジュール）
- ペーパートレード用検証ツール（tools）

本 README はリポジトリ内の主要モジュールをもとに、セットアップ・実行手順やディレクトリ構成を日本語でまとめたものです。

機能一覧
--------
主な機能（抜粋）:

- Execution
  - ExecutionEngine を使った発注セッション起動（run_execution.py）。
  - 環境変数 KABUSYS_ENV により paper_trading / live / development を切替。
  - paper_trading では MockBrokerClient を使い paper_trading.db に記録して本番 DB と分離。

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク／データ鮮度／プロセス生存確認。
  - TradeMonitor: 滞留注文（stale orders）や約定異常価格の検知。
  - RiskMonitor: ドローダウン / ポジション上限の監視、ダッシュボード更新。
  - KillSwitch: しきい値超過時に data/kill.flag を書き込み ExecutionEngine を停止。
  - MonitoringEngine: 上記モニタをまとめてポーリング（run_monitoring.py）。

- Portfolio
  - 銘柄候補選定、等配分／スコア加重配分、ポジションサイズ計算、セクター上限・レジーム乗数。

- Research
  - momentum / volatility / value 等のファクター計算（DuckDB を使用）。
  - 将来リターン、IC（Information Coefficient）、統計サマリー等。

- AI
  - news_nlp: raw_news を LLM に送り銘柄別センチメントを ai_scores テーブルへ書込み。
  - regime_detector: ETF MA とマクロニュースの LLM 評価を合わせて市場レジーム判定。

- ツール
  - paper_verification_report: ペーパートレード DB を集計し PASS/FAIL 判定レポートを生成。

セットアップ手順
----------------

1. 前提
   - Python 3.9+（ソースは型アノテーションを利用）。
   - DuckDB（python duckdb パッケージ）
   - psutil（プロセス優先度 / CPU affinity 用）
   - OpenAI SDK（AI 機能を使う場合）
   - （任意）PyYAML（validate_config で config/*.yaml の検証を行う場合）

   例:
   pip install duckdb psutil openai PyYAML

   ※ requirements.txt がなければ上記を参考に必要パッケージをインストールしてください。

2. プロジェクトルートの検出と .env 自動読み込み
   - config モジュールは .git または pyproject.toml を基準にプロジェクトルートを探します。
   - 自動で .env / .env.local を読み込みます（無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

3. .env の準備（推奨）
   - 対話式ウィザードで作成:
     python -m kabusys.config_setup
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB。デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject、デフォルト: instant）
     - OPENAI_API_KEY（AI を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE 通知）

4. 設定検証
   - 起動前に設定を検証:
     python -m kabusys.validate_config
   - 警告をエラー扱いにする（CI 等で）:
     python -m kabusys.validate_config --strict

5. データディレクトリ
   - 既定で data/ 以下に DB や pid/flag ファイルを置きます。必要に応じて .env でパスを変更してください。

使い方（主要コマンド）
--------------------

- 設定ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン起動（Execution）
  python -m kabusys.run_execution
  動作:
  - Settings.env に応じて paper_trading モードでは専用 DB に記録。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了。
  - 実行中の停止は data/stop_requested.flag の作成で行えます（または kill.flag を監視して停止）。

- 監視ループ起動（Monitoring）
  python -m kabusys.run_monitoring
  オプション / 環境変数:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）。1 未満や無効値は 60 にフォールバック。
  動作:
  - 監視は常に production の sqlite_path を参照（KABUSYS_ENV に依存しない）。
  - data/stop_requested.flag を検出するとループを終了。

- ペーパートレード検証レポート
  python -m kabusys.tools.paper_verification_report
  オプション:
  --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能（デフォルト data/paper_trading.db）。

- AI 機能
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数か関数引数）。
  - news_nlp.score_news(conn, target_date, api_key=None) などの関数をプログラムから呼ぶ形で利用。

重要な運用・設計メモ
------------------
- paper_trading モードは本番 DB と完全分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を別に）。
- Kill Switch: RiskMonitor がしきい値を超えると KillSwitch が data/kill.flag を書き、ExecutionEngine に停止を促します。Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアされますが、本番では 0 を推奨します。
- プロセス優先度: run_* スクリプトは起動時に set_process_priority("high") を試みます（psutil を使用）。権限不足や未対応 OS では警告メッセージが出ますが処理は続行します。
- DB マイグレーション: monitoring_db.init_monitoring_db は簡単なマイグレーション処理（カラム追加など）を含み、冪等に実行できます。
- ロギング: 基本的に logging.INFO で起動しますが .env の LOG_LEVEL で制御できます。

ディレクトリ構成（主なファイル）
-----------------------------
以下は src/kabusys 配下の主要ファイルとディレクトリ（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境・設定管理
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py         — 市場レジーム判定（MA + LLM）

  - monitoring/
    - monitoring_db.py           — SQLite 監視 DB レイヤ
    - monitoring_engine.py       — モニタ統括
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py           — （未表示部分）アラート通知管理

  - execution/                   — 発注・注文管理関連（OrderRepository 等）
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - order_record.py

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py

  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py

  - tools/
    - __init__.py
    - paper_verification_report.py

  - utils/
    - __init__.py
    - process_priority.py        — プロセス優先度 / CPU affinity ユーティリティ

補足: よく使う環境変数（まとめ）
----------------------------
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 必須
- DUCKDB_PATH: data/kabusys.duckdb（分析用 DB）
- SQLITE_PATH: data/monitoring.db（監視ログ DB）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 時の DB）
- PAPER_FILL_MODE: instant | partial | never | reject
- OPENAI_API_KEY: AI 機能利用時に必要
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒）

ライセンス・貢献
----------------
（リポジトリに LICENSE があればその旨を記載してください。ここでは省略しています。）

最後に
-------
この README はソース上の docstring と設計コメントを基に作成しています。実際の運用前に
- .env を正しく設定し、
- python -m kabusys.validate_config での検証、
- 必要なパッケージ（duckdb / psutil / openai など）のインストール
を行ってください。問題があればソース内の各モジュールの docstring を参照してください。