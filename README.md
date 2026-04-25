KabuSys — 日本株自動売買システム
================================

このリポジトリは、シンプルかつ実用的な日本株向け自動売買フレームワークの一部実装です。
主要機能群には、注文実行エンジン、監視（Monitoring）、ポートフォリオ構築ロジック、研究用のファクター計算、
およびニュース NLP / レジーム判定のための AI 連携モジュールが含まれます。

要点
- Python >= 3.10 を想定（PEP 604 の型記法などを使用）
- DuckDB / SQLite をローカル DB に使用
- OpenAI（gpt-4o-mini 等）との連携機能あり（APIキー必須）
- ペーパートレード用に本番 DB と分離された専用 SQLite をサポート

機能一覧
---------
- 設定管理
  - .env の自動読み込み（.env / .env.local）、対話式ウィザード（kabusys.config_setup）
  - 起動前設定検証ツール（kabusys.validate_config）

- 実行（Execution）
  - ExecutionEngine を起動する run_execution スクリプト
  - 本番 / ペーパートレードを切り替え可能（KABUSYS_ENV）
  - RiskManager / OrderManager / Reconciler 等の基本コンポーネント組立

- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite に監視ログ（system_status / trade_logs / risk_logs / dashboard / positions）を永続化
  - Kill Switch（データに基づく停止フラグ書き込み）による安全停止

- ポートフォリオ構築（純粋関数）
  - 候補選定、等配分 / スコア加重、ポジションサイズ計算、セクターキャップ適用、レジーム補正

- 研究（Research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 接続で SQL 実行）
  - IC 計算、将来リターン計算、ファクター統計サマリ

- AI 連携
  - ニュース記事を LLM でスコアリングして ai_scores に格納（kabusys.ai.news_nlp）
  - マクロニュース + ETF MA200 を組合せた市場レジーム判定（kabusys.ai.regime_detector）
  - OpenAI API の呼び出しは堅牢化（リトライ・パース検証）

- ユーティリティ
  - ロギング初期化（コンソール + 日次ローテーションファイル）
  - プロセス優先度 / CPU affinity 設定
  - 各種 CLI ツール（設定ウィザード・検証・レポート生成）

セットアップ手順
---------------

1. Python と依存ライブラリのインストール
   - Python 3.10 以上を推奨
   - 必須ライブラリ（例）
     - duckdb
     - psutil
     - openai (AI 機能を利用する場合)
     - PyYAML（config の YAML 検証を行う場合、任意）
   - 例:
     pip install duckdb psutil openai PyYAML

   ※ requirements.txt がある場合はそれを使用してください（本リポジトリ断片には含まれていません）。

2. プロジェクトルートに移動
   - src 配下でパッケージが見つかる構成を想定しています。CWD に依存せず動作するよう設計されていますが、通常はプロジェクトルートで操作します。

3. 初期設定（.env）作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - ウィザードは .env を生成します（保存前に確認プロンプトがあります）。
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な設定:
     - KABUSYS_ENV: development | paper_trading | live
     - OPENAI_API_KEY: AI 機能使用時に必要

4. 設定検証
   - 作成後、設定検証ツールでチェック:
     python -m kabusys.validate_config
   - --strict オプションを付けると警告も失敗扱いになります:
     python -m kabusys.validate_config --strict

5. データディレクトリ
   - デフォルトの DB / ログパスは data/ および logs/ です。必要に応じて .env の DUCKDB_PATH / SQLITE_PATH 等で変更してください。
   - 起動時に自動作成されることもありますが、権限に注意してください。

使い方 (主なコマンド)
--------------------

- 実行エンジン（Execution）起動
  - 本番環境またはペーパー環境に応じて .env の KABUSYS_ENV を設定してから起動します。
  - 起動:
    python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録されます（本番 DB と分離）。
    - 実行中に data/stop_requested.flag が存在するとエンジンは停止します。
    - 実行中は data/execution.pid に PID が保存されます。

- 監視（Monitoring）起動
  - 起動:
    python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（デフォルト: 60）。
    例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は本番 sqlite_path を使用してログを記録します（KABUSYS_ENV に依存せず本番 DB を使う設計）。

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話的に作成 / 更新します。

- 設定検証
  - python -m kabusys.validate_config
  - YAML の中身チェックは PyYAML がインストールされている場合に行われます（未インストール時はスキップされ警告が出ます）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  - 出力: コンソールに各種指標（稼働率、注文成功率、レイテンシ等）と PASS/FAIL 判定を表示。

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY が必要です（.env に設定）。
  - プログラムAPI を直接呼び出して使用する想定:
    from kabusys.ai.news_nlp import score_news
    # DuckDB 接続を渡し target_date を指定して実行
  - API 呼び出しは料金・レート制限に注意してください。

停止方法（安全シャットダウン）
------------------------------
- run_monitoring / run_execution は stop flag ファイル（data/stop_requested.flag）を監視しています。フラグを作成するとループは停止します。
- Kill Switch（条件に応じて data/kill.flag を書き込む）により ExecutionEngine を停止させるガードが実装されています。
- ExecutionEngine 側でも data/execution.pid に PID が書き込まれます。

主な環境変数（抜粋）
--------------------
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパー用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（例: INFO）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。run_monitoring のみ。デフォルト: 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env の自動読み込みを無効化（テスト時に有用）

ディレクトリ構成（主要ファイル）
------------------------------
以下はパッケージ内部の主要モジュール一覧（抜粋）。実際のリポジトリにはさらにファイルやディレクトリがあります。

- src/kabusys/
  - __init__.py                — パッケージ定義、バージョン
  - config.py                  — Settings クラス（環境変数 / .env の自動ロード）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 起動前設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py              — ニュースの LLM スコアリング
    - regime_detector.py       — 市場レジーム判定
  - monitoring/
    - monitoring_db.py         — SQLite への監視ログ書き込み API
    - system_monitor.py        — システム状態 / データ鮮度チェック
    - trade_monitor.py         — （滞留注文等の監視用モジュール）
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - monitoring_engine.py     — 各 Monitor を束ねる実行ループ
    - kill_switch.py           — kill.flag 書き込みロジック
    - alert_manager.py         — （通知一括管理。LINE 等への通知を想定）
  - execution/
    - execution_engine.py      — 実行エンジン本体（EngineConfig 等）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py     — 候補選定 / 重み計算
    - position_sizing.py       — 発注株数計算
    - risk_adjustment.py       — セクター制限 / レジーム乗数
  - research/
    - factor_research.py       — Momentum/Value/Volatility 等の計算
    - feature_exploration.py   — 将来リターン / IC / 統計サマリ
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート出力
  - utils/
    - logging_setup.py         — 共通ロギング初期化
    - process_priority.py      — 優先度 / CPU affinity 設定

補足・運用上の注意
-----------------
- 本プロジェクトは設計上、KABUSYS_ENV に応じて発注動作を切り替えます。ライブ運用時は設定ミスが致命的な取引を招くため、validate_config を必ず実行して設定を確認してください。
- OpenAI 等の外部 API 呼び出しはコストとレート制限に注意して運用してください。AI 機能はフェイルセーフ（エラー時はスコア 0.0 にフォールバックする等）を備えていますが、運用ルールは厳格に設定してください。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリの作成に失敗した場合はコンソール出力のみになります。

ライセンス / 責務
-----------------
この README はコードベースの機能説明および運用手順の要約です。実際に資金を運用する場合は、追加の安全対策・監査・バックテストを十分に行ってください。

---

問題・追加で欲しい情報があれば（例: 実際の requirements.txt、設定例テンプレート、起動スクリプトの実行例ログ等）教えてください。README をそれに合わせて拡張します。