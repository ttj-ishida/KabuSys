KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株の自動売買・研究用フレームワークです。  
本リポジトリには、実行エンジン（ExecutionEngine）、監視モジュール（Monitoring）、ポートフォリオ構築／容量計算、リサーチ用ファクター計算、LLM を使ったニュース NLP / レジーム判定などのコンポーネントが含まれます。設計方針として、本番（live）・ペーパートレード（paper_trading）環境の分離、環境変数による設定管理、SQLite / DuckDB を使ったローカル永続化を採用しています。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading DB に記録して本番 DB と分離
- Monitoring（run_monitoring.py / MonitoringEngine）
  - システム状態・データ鮮度・注文状況・リスクをポーリングしてログ保存、kill.flag を用いた停止シグナル
- 設定ウィザード（config_setup.py）
  - .env の対話的生成・更新をサポート
- 設定検証（validate_config.py）
  - .env と config/*.yaml の事前検証（--strict オプションで警告も失敗扱い）
- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - ペーパートレード DB から稼働率・成功率・レイテンシを集計して PASS/FAIL 判定
- ポートフォリオ構築モジュール（portfolio）
  - 候補選定、重み計算、ポジションサイズ計算、セクター上限・レジーム乗数などの純粋関数群
- リサーチ（research）
  - ファクター計算（モメンタム／ボラティリティ／バリュー）、IC 計算、統計サマリー
- AI モジュール（ai）
  - ニュースの LLM センチメント評価（OpenAI）と市場レジーム判定。API 呼び出しはリトライ・フォールバック実装あり
- ログ設定ユーティリティ、プロセス優先度設定ユーティリティ等

セットアップ手順
---------------
1. Python と依存ライブラリ
   - 推奨 Python バージョン: 3.9+
   - 必要パッケージ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML 検証を行う場合）
   - インストール例:
     - pip install duckdb psutil openai PyYAML

2. リポジトリルートに移動して .env を作成
   - 対話形式で作成:
     - python -m kabusys.config_setup
   - 手動で作る場合は .env.example（存在する場合）を参考に .env を作成してください。

3. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告も含めて厳格にチェックしたい場合:
     - python -m kabusys.validate_config --strict

4. データディレクトリ作成（必要に応じて）
   - デフォルトでは以下パスを使用します（.env で変更可）:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading 時)
     - PID / flag / logs: data/, logs/
   - 実行時に自動作成されることがありますが、権限やマウント先による失敗に注意してください。

主な環境変数（代表）
-------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- OPENAI_API_KEY（AI モジュールを使う場合）
- PAPER_FILL_MODE（paper_trading 用: instant | partial | never | reject）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）、デフォルト 60）

使い方
------

1. 実行エンジン起動（Execution）
   - デフォルト（環境に応じた DB を使用）:
     - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使い MockBrokerClient により発注を模擬します。
     - 実行中に data/stop_requested.flag を作成すると安全に停止します（停止フラグを検知して Engine.stop() を呼びます）。
     - 実行時に data/execution.pid を生成します（PID ファイルのパスは Settings で変更可）。

2. 監視プロセス起動（Monitoring）
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL を設定することでポーリング間隔を変更できます（例: MONITOR_POLL_INTERVAL=30）。
   - 監視は常に本番用の sqlite_path（monitoring DB）を使用します（環境にかかわらず）。

3. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - --db オプション、または環境変数 PAPER_TRADING_SQLITE_PATH を使用

4. その他ユーティリティ
   - 設定ウィザード: python -m kabusys.config_setup
   - 設定検証: python -m kabusys.validate_config [--strict]

設定と挙動の注意点
-----------------
- .env の自動ロード:
  - デフォルトでプロジェクトルートの .env / .env.local を自動ロードします。
  - テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB 分離:
  - paper_trading 環境は paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 sqlite_path と分離します。
- Kill Switch:
  - risk モニタ等が条件を満たすと data/kill.flag を作成して ExecutionEngine に停止を促します（Settings.kill_flag_clear_on_start により起動時に自動クリア可）。
- プロセス優先度:
  - 起動スクリプトは最初に set_process_priority("high") を試みます。OS 権限不足や未対応 OS の場合は警告が出て続行します。
- ログ:
  - logs/<app_name>.log に日次ローテートで出力（デフォルト 30 日分保持）。コンソールは stdout に出力します。

ディレクトリ構成（主要ファイル）
------------------------------
src/
  kabusys/
    __init__.py                -- パッケージ定義、バージョン
    config.py                  -- Settings クラス（環境変数管理・デフォルト）
    config_setup.py            -- .env 対話ウィザード
    validate_config.py         -- 設定検証 CLI
    run_execution.py           -- ExecutionEngine 起動スクリプト
    run_monitoring.py          -- Monitoring 起動スクリプト
    utils/
      logging_setup.py         -- ログ初期化ユーティリティ
      process_priority.py      -- プロセス優先度 / CPU affinity 設定ユーティリティ
    execution/                  -- 実行エンジン関連（Engine/OrderManager/RiskManager 等）
      ...
    monitoring/
      monitoring_db.py         -- SQLite 用永続化層（schema マイグレーション含む）
      system_monitor.py        -- システム状態 / データ鮮度監視
      risk_monitor.py          -- ドローダウン / ポジション上限監視
      trade_monitor.py         -- 発注・約定監視（参照実装あり）
      monitoring_engine.py     -- 複数モニタを束ねるループ
      kill_switch.py           -- kill.flag 書き込みユーティリティ
      alert_manager.py         -- （アラート管理。実装参照）
    portfolio/
      portfolio_builder.py     -- 候補選定・重み
      position_sizing.py       -- 株数算出・スケーリング
      risk_adjustment.py       -- セクターキャップ・レジーム乗数
    research/
      factor_research.py       -- ファクター計算（momentum/volatility/value）
      feature_exploration.py   -- IC / 統計サマリー
    ai/
      news_nlp.py              -- ニュース NLP / OpenAI 呼び出し・スコア保存
      regime_detector.py       -- LLM + MA200 によるレジーム判定
    tools/
      paper_verification_report.py  -- ペーパートレード検証レポート
    data/                      -- 実行時に使用する SQLite / DuckDB / flag / pid / logs など（外部に置くこと推奨）

トラブルシューティング
---------------------
- .env が未設定で起動が失敗する:
  - python -m kabusys.config_setup を実行して .env を作成してください。
  - validate_config で不足を事前確認してください。
- DuckDB / SQLite ファイルの親ディレクトリが存在しない:
  - 起動時にログディレクトリや data ディレクトリの作成に失敗することがあります。手動でディレクトリを作成してください（例: mkdir -p data logs）。
- OpenAI 呼び出しが失敗する:
  - OPENAI_API_KEY を環境変数に設定してください。
  - レート制限や一時的なネットワーク障害はリトライロジックで吸収しますが、API キーの権限や使用量に注意してください。
- process priority / CPU affinity の設定に失敗して警告が出る:
  - OS とユーザー権限に依存します。機能は推奨設定であり、失敗しても起動自体は継続します。

開発・拡張のヒント
-------------------
- DuckDB 接続を渡すことで research / ai モジュールは SQL を組み合わせた高速処理が可能です。
- モジュールは基本的に副作用を最小化する設計（純粋関数群 / DB 書き込みは監視 DB 層など）を意識しています。ユニットテストを書きやすい構造です。
- ai モジュールは OpenAI SDK の差し替えを想定しており、テストでは _call_openai_api をモックしてください。

最後に
------
この README はリポジトリ内のスクリプト・モジュールの実装コメントを元にまとめた利用ガイドです。実行前に必ず .env の設定・validate_config による検証を行い、特に KABUSYS_ENV=live の場合は本番用の設定（LINE 通知・Kill Switch 設定等）を慎重に確認してください。必要があれば各モジュールのソース内コメント（docstring）を参照して詳細実装を確認してください。