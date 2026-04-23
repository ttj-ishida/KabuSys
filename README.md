# KabuSys

日本株自動売買システムの軽量実装（ライブラリ / 起動スクリプト /運用ユーティリティ群）

このリポジトリは、戦略リサーチ、ポートフォリオ構築、注文実行、監視・アラート、そして AI を使ったニュースセンチメント/レジーム判定を含む一連のコンポーネントを含んでいます。設計方針は「本番 DB と分析環境の分離」「ルックアヘッドバイアス回避」「フェイルセーフ（API失敗時は安全側へフォールバック）」です。

---

## 主な特徴

- 環境設定管理（.env 自動読み込み / 対話式ウィザード）
- 実行エンジン（ExecutionEngine）：発注・注文管理・リスク管理を担う
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、本番 DB とは分離された paper_trading DB を利用
- 監視（MonitoringEngine）：システム状態、注文ログ、リスクを定期チェックし Kill Switch を起動可能
- ポートフォリオ構築モジュール（候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム係数）
- リサーチモジュール（DuckDB を利用したファクター計算、将来リターン・IC 計算など）
- AI モジュール（OpenAI を用いたニュースセンチメント / 市場レジーム判定）
- 運用ツール：対話式 .env 作成ウィザード、設定検証 CLI、Paper Trading 検証レポート生成

---

## 事前準備（セットアップ）

1. Python と依存ライブラリを用意
   - Python 3.9+ 想定
   - 主な依存（例）: duckdb, psutil, openai, PyYAML（設定検証時のみ）
   - インストール例:
     - pip install -r requirements.txt
     - requirements.txt がない場合は必要なパッケージを個別にインストールしてください。

2. プロジェクトルートに .env を配置
   - 対話式で生成するには:
     - python -m kabusys.config_setup
   - 生成後、設定を検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります。

3. 環境変数（主な項目）
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 任意 / 推奨:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
       - paper_trading: 実際の発注を行わず、別 DB（PAPER_TRADING_SQLITE_PATH）に記録
       - live: 本番運用
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — 監視用 SQLite（monitoring DB）デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
     - LOG_LEVEL — デフォルト: INFO
     - LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
     - OPENAI_API_KEY — OpenAI を利用する機能で必要
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート用（LINE）

   - 自動ロード:
     - プロジェクトルートにある `.env` と `.env.local` を自動で読み込みます（OS 環境変数が優先）。
     - 無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. データディレクトリ
   - デフォルトで使用するファイル・パス:
     - data/monitoring.db (監視 DB)
     - data/paper_trading.db (ペーパー取引用 DB)
     - data/kabusys.duckdb (分析用 DuckDB)
     - data/execution.pid (ExecutionEngine の PID 管理)
     - data/stop_requested.flag (監視・実行停止用フラグ)
     - data/kill.flag (Kill Switch 用フラグ)
   - これらの親ディレクトリは自動作成されます（ロギングや DB 作成時）。

---

## 簡単な使い方（コマンド）

- 対話的に .env を作成
  - python -m kabusys.config_setup

- 設定の事前検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループ（Monitoring）を起動
  - python -m kabusys.run_monitoring
  - 補足:
    - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト: 60）
    - monitoring は KABUSYS_ENV にかかわらず `Settings.sqlite_path`（本番監視 DB）を使用して初期化します
    - 停止: プロセスは data/stop_requested.flag の存在を検知して終了します

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録され本番 DB と分離されます
    - 起動時に data/stop_requested.flag が存在する場合は起動を行わず終了します
    - 実行中は data/execution.pid を使用して PID 管理を行います
    - 停止: data/stop_requested.flag を作成することでエンジンへ停止信号を送れます（または Kill Switch により data/kill.flag が書き込まれることもあります）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

---

## 運用上の重要点

- ログ
  - 共通ログ初期化: kabusys.utils.logging_setup.setup_logging(app_name="...") をスクリプトで使用
  - デフォルトログディレクトリ: logs/
  - 日次ローテーション、30日分保持

- プロセス優先度 / CPU affinity
  - 起動スクリプトは起動直後に set_process_priority("high") を呼び出して優先度を上げようとします（psutil を使用）。失敗した場合は警告を出して継続します。

- Kill Switch / 停止フラグ
  - KillSwitch（monitoring）から data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送る設計
  - ExecutionEngine/run_execution は data/stop_requested.flag の存在も監視します
  - Settings.kill_flag_clear_on_start が 1 の場合、起動時に kill.flag を自動クリアする挙動があります（本番では 0 推奨）

- AI 機能（OpenAI）
  - news_nlp や regime_detector は OPENAI_API_KEY を必要とします
  - API 呼び出しはリトライやフォールバックを実装しており、API 失敗時は安全側にフォールバックします（例: macro_sentiment=0.0）

- DB マイグレーション
  - monitoring_db.init_monitoring_db() は冪等でテーブルを作成し、軽微なカラム追加のマイグレーションを自動で行います（例: latency_ms, peak_value 追加）

---

## 簡単な開発フロー例

1. .env を対話式で作成
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config

3. 開発環境で Execution をペーパートレードで試す
   - export KABUSYS_ENV=paper_trading
   - python -m kabusys.run_execution

4. 監視を別プロセスで起動
   - python -m kabusys.run_monitoring

5. 検証（Paper Trading レポート）
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 主要なファイル / ディレクトリ構成

（src/kabusys 以下を想定）

- __init__.py
  - パッケージ情報（__version__ 等）

- config.py
  - Settings クラス（環境変数読み込み、.env 自動ロード、各種パス・閾値・フラグ）

- config_setup.py
  - .env 作成の対話式ウィザード

- validate_config.py
  - 起動前チェック CLI（必須環境変数・YAML ファイル・パス等の検証）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
  - MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能（デフォルト 60 秒）
  - data/stop_requested.flag を検出して終了

- run_execution.py
  - ExecutionEngine 起動スクリプト
  - paper_trading モードの切替、専用 DB 使用（PAPER_TRADING_SQLITE_PATH）
  - data/execution.pid 管理、data/stop_requested.flag で停止

- monitoring/
  - monitoring_db.py — SQLite を用いた永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — システム状態・データ鮮度のチェック
  - trade_monitor.py — （注文滞留・約定異常などのチェック）※実装ファイルを参照
  - risk_monitor.py — ドローダウン・ポジション上限の監視
  - kill_switch.py — kill.flag の書き込み / クリア
  - monitoring_engine.py — 各 Monitor を束ねるループ、AlertManager 連携

- execution/
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager など
  - 実際の注文ロジック・リスク制御の実装を含む（詳細は該当ファイル参照）

- portfolio/
  - portfolio_builder.py — 候補選定、重み計算
  - position_sizing.py — 株数決定、マージン・lot 丸め、aggregate cap
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- research/
  - factor_research.py — モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB を想定）
  - feature_exploration.py — 将来リターン、IC、統計サマリ

- ai/
  - news_nlp.py — raw_news を OpenAI に送りセンチメントを ai_scores に書き込む
  - regime_detector.py — ETF の MA200 とマクロニュースを統合して市場レジームを判定

- utils/
  - logging_setup.py — 標準化されたログ設定（コンソール + 日次ローテーションファイル）
  - process_priority.py — psutil を使ったプロセス優先度 / CPU affinity 設定

- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

---

## 注意事項 / ベストプラクティス

- .env は機密情報を含むため Git には絶対にコミットしないでください。
- 本番運用（KABUSYS_ENV=live）の場合は LINE 等の通知チャネルを必ず設定し、Kill Switch の自動クリア設定（KILL_FLAG_CLEAR_ON_START）はオフ（0）にしてください。
- OpenAI API キーを利用する機能はコスト・レイテンシが発生します。API 呼び出しはバッチ化・リトライ処理が施されていますが、運用時はレート制限に注意してください。
- DuckDB / SQLite のパスは必ず適切にバックアップ・管理してください。paper_trading は本番 DB と分離されていますが、誤操作を避けるためパス設定に注意してください。

---

この README はコードベースの主要点を抜粋したもので、実装の詳細や追加のユーティリティは各モジュールのドキュメント（ソース内 docstring）を参照してください。開発・運用に関する具体的な質問や手順の補足が必要であれば知らせてください。