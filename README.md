KabuSys — 日本株自動売買システム
================================

このドキュメントはリポジトリ内のコードベース（src/kabusys/）に基づく README です。開発者・運用者向けにプロジェクト概要、機能、セットアップ方法、使い方、主要ファイル／ディレクトリ構成を日本語でまとめています。

プロジェクト概要
---------------
KabuSys は日本株向けの自動売買システムです。  
主な役割はシグナル生成 → 注文管理 → 発注（実口座 / ペーパートレード）→ 監視 / リスク管理 / アラートの一連のワークフローを提供することです。本リポジトリには以下の要素が含まれます。

- ExecutionEngine（発注エンジン）: ブローカークライアントを介して注文を管理・送信
- Monitoring（監視）: システム状態、注文の滞留や約定異常、ドローダウン監視と KillSwitch
- ポートフォリオ構築（選定・重み付け・数量計算）
- リサーチ・ファクター計算（DuckDB を用いたファクター群）
- AI モジュール（OpenAI を使ったニュース NLP、レジーム判定）
- ユーティリティ（ログセットアップ、プロセス優先度など）
- CLI ツール（.env ウィザード、設定検証、レポート生成）

主な機能一覧
---------------
- 起動スクリプト
  - run_execution: ExecutionEngine を起動（本番 / ペーパートレード切替）
  - run_monitoring: SystemMonitor をポーリングして監視ログを取得
- 環境設定
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: .env / config/*.yaml の検証 CLI
- Paper Trading
  - 実口座と分離された専用 SQLite（data/paper_trading.db）で動作
  - paper_verification_report: ペーパートレード結果の検証レポート生成
- 監視 / Kill Switch
  - SystemMonitor / TradeMonitor / RiskMonitor を統合する MonitoringEngine
  - KillSwitch が条件を満たすと data/kill.flag を書き込み発注エンジンへ停止シグナル
- AI 機能
  - news_nlp: OpenAI を用いたニュースセンチメント（ai_scores への書込み）
  - regime_detector: 市場レジーム判定（ma200 + マクロセンチメント）
- ポートフォリオ構築
  - 候補選定、等重・スコア加重、リスクベースの数量算出、セクター制限

セットアップ手順
----------------
以下はローカル開発 / 試験運用用の最低限の手順です。

1. リポジトリのクローン
   - git clone <repository-url>
   - (プロジェクトルートに src/ ディレクトリがあることを確認)

2. Python 仮想環境（推奨）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（代表的な必須パッケージ）
   - pip install duckdb psutil openai
   - 追加で YAML 検証や他機能を使う場合: pip install pyyaml

   ※ requirements.txt がある場合はそちらを使用してください（本ドキュメントでは仮定）。

4. 環境変数設定 (.env)
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに .env を作成する。主なキー（必須）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH （デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH （デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH （Paper Trading 用: data/paper_trading.db）
     - OPENAI_API_KEY （AI モジュールを使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID （任意、アラート用）
   - .env の自動読み込み:
     - .env はプロジェクトルート（.git または pyproject.toml を基準）から自動的に読み込まれます。
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化します。

5. 設定検証
   - python -m kabusys.validate_config
   - 必須環境変数不足や config/*.yaml の欠如を検出します。--strict をつけると警告もエラー扱いになります。

使い方
------
起動・停止、レポート生成、監視の実行方法を簡単に示します。

・ExecutionEngine（発注エンジン）の起動
- コマンド:
  - python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に取引ログを記録します（本番 DB と完全分離）。
  - 起動中は data/execution.pid に PID ファイルを書き、data/stop_requested.flag の存在でエンジンに停止指示を送る実装になっています。
- 停止:
  - data/stop_requested.flag を作成すると起動スレッドが検出して停止します（run_execution と run_monitoring の両方で同様のフラグを参照）。

・Monitoring（監視）の起動
- コマンド:
  - python -m kabusys.run_monitoring
- 挙動:
  - Settings に基づき SQLite（monitoring DB）と DuckDB に接続し、SystemMonitor を定期実行します。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト: 60）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを記録します（監視用 DB は共有の想定）。
  - 停止は data/stop_requested.flag の存在でループを抜けます。

・Kill Switch
- KillSwitch は条件（ドローダウンやポジション数上限）に合致すると data/kill.flag を書き込みます。
- ExecutionEngine は kill.flag の存在を検出して発注を止めるよう連携する設計です（設定で flag のパスは変更可能）。

・Paper Trading 検証レポート
- コマンド例:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB パスは引数 --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定可能（デフォルト: data/paper_trading.db）。
- 出力: 稼働率、注文成功率、送信率、レイテンシ指標、判定 PASS/FAIL

・AI 機能
- news_nlp.score_news / regime_detector.score_regime は OpenAI API（OPENAI_API_KEY）を必要とします。API 呼び出しはリトライや応答検証を含む堅牢な実装になっています。
- AI モジュールを使う場合は OPENAI_API_KEY を .env に設定してください。

主要な環境変数一覧（抜粋）
-------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- LOG_LEVEL — デフォルト: INFO
- LOG_DIR — デフォルト: logs/
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒（デフォルト 60）
- OPENAI_API_KEY — AI 機能で必須
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番でのアラート通知（任意）

運用メモ
--------
- ログ出力は kabusys.utils.logging_setup.setup_logging を通して統一されます。デフォルトで stdout と logs/<app_name>.log に日次ローテーションで出力します。
- プロセス優先度や CPU affinity を設定するユーティリティ（psutil 使用）があります。起動スクリプトは開始直後にプロセス優先度を "high" に設定しますが、権限がない場合は警告を出してスキップします。
- データベーススキーマのマイグレーションは monitoring_db.init_monitoring_db 内に小規模な ALTER が含まれています（冪等）。
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup 生成時も注意書きあり）。

ディレクトリ構成（代表的）
-------------------------
以下は主要なファイル／ディレクトリの概観（src/kabusys 配下）。実際のリポジトリではプロジェクトルートに config/、data/、logs/ などが存在します。

- src/
  - kabusys/
    - __init__.py
    - config.py                     — 環境変数 / Settings 管理（.env 自動ロード）
    - config_setup.py               — .env 対話式ウィザード
    - validate_config.py            — 設定検証 CLI
    - run_execution.py              — ExecutionEngine 起動スクリプト
    - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
    - execution/                     — 発注関連コンポーネント（order_manager 等）
    - monitoring/
      - monitoring_db.py            — 監視用 SQLite 永続化層
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - data/ (実行時に作成されることが多い)
      - monitoring.db (SQLITE_PATH)
      - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
      - kabusys.duckdb (DUCKDB_PATH)
      - execution.pid
      - stop_requested.flag
      - kill.flag
    - logs/
      - execution.log
      - monitoring.log
      - ... (日次ローテーション)

よくある運用ワークフローの例
---------------------------
1. 初期設定
   - python -m kabusys.config_setup
   - python -m kabusys.validate_config

2. 開発・テスト（ペーパートレード）
   - KABUSYS_ENV=paper_trading を .env に設定
   - python -m kabusys.run_execution
   - python -m kabusys.run_monitoring

3. 検証レポート作成（任意期間）
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

4. 停止
   - graceful stop: touch data/stop_requested.flag（両方のループが検知して終了します）
   - KillSwitch による停止: monitoring が条件を検出すると data/kill.flag を書き込み発注エンジンへ停止を指示します

補足 / 注意事項
---------------
- 本システムは実際の発注を行うため、KABUSYS_ENV=live の設定時には十分な注意が必要です。validate_config は live 時に注意喚起を出します。
- AI モジュールは外部 API を呼ぶためレイテンシ・レート制限・コストに注意してください。OPENAI_API_KEY を必ず管理してください。
- SQLite / DuckDB のファイルパスを適切に配置・バックアップすることを推奨します（データ破損対策）。
- 本 README はコードベースのソースに基づいて作成しています。実運用用の詳細な手順や systemd / container 化等は運用ガイドに別途まとめてください。

お問い合わせ
-----------
ソースの詳細な設計や運用ルール、追加のドキュメント化（API、DB スキーマ、運用 runbook）が必要な場合はリポジトリ管理者に相談してください。README の改善点や実運用上の注意点が見つかればプルリク等での反映を歓迎します。