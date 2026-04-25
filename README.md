README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のサンプル実装です。本プロジェクトは次の主要機能を持ちます。

- 発注・実行エンジン（ExecutionEngine） — ブローカー抽象化、リスク制御、注文管理を含む
- 監視サブシステム（Monitoring） — システム状態・注文状況・リスク監視、Kill Switch
- ペーパートレード機能 — 本番 DB を触らない分離されたペーパートレードモード
- ポートフォリオ構築ユーティリティ — 候補選択、重み算出、ポジションサイジング、セクター制約等
- 研究用モジュール — ファクター計算、特徴量探索、IC 計算など（DuckDB ベース）
- AI モジュール — ニュースの LLM ベースセンチメント（OpenAI）・市場レジーム判定
- 運用用ユーティリティ — .env ウィザード、設定検証、ログ設定、プロセス優先度設定
- 運用レポートツール — ペーパートレード検証レポート生成

主な設計方針は「本番資産に触れない」「ルックアヘッドを避ける」「外部 API の失敗に対してフェイルセーフにする」ことです。

機能一覧
--------
- run_execution: ExecutionEngine を起動（KABUSYS_ENV による本番 / ペーパー切替）
- run_monitoring: SystemMonitor のポーリング監視を起動（MONITOR_POLL_INTERVAL で間隔指定可）
- config_setup: .env を対話的に作成・更新するウィザード
- validate_config: .env と config/*.yaml の事前検証 CLI
- tools.paper_verification_report: ペーパートレード検証レポート生成
- portfolio: 候補選定、重み付け、ポジションサイズ計算、セクター上限適用
- research: DuckDB を用いたファクター計算・forward return・IC・統計サマリー
- ai.news_nlp / ai.regime_detector: OpenAI を用いたニュースセンチメント／レジーム判定
- monitoring: MonitoringDB、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、MonitoringEngine
- utils: ロギング設定、プロセス優先度・CPU affinity 設定ユーティリティ

動作環境と依存
---------------
- Python 3.10 以上（型ヒントの union 表記などを使用）
- 必須ライブラリ（一部は運用機能で必須）:
  - duckdb
  - psutil
  - openai （AI 機能利用時）
- 任意（YAML 検証用）:
  - PyYAML
- SQLite は標準ライブラリで利用

例: 必要パッケージのインストール
  pip install duckdb psutil openai PyYAML

セットアップ手順
----------------
1. リポジトリをチェックアウト／展開
2. Python 環境を用意（venv 推奨）
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt  （requirements.txt がない場合は上記の個別インストール）
3. ディレクトリ作成
   mkdir -p data logs
4. 環境変数（.env）を作成
   python -m kabusys.config_setup
   ウィザードに従って J-Quants トークン、kabu API パスワード、KABUSYS_ENV 等を設定します。
5. 設定検証（任意・推奨）
   python -m kabusys.validate_config
   --strict をつけると警告も失敗扱いになります。

主要環境変数（抜粋）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードでの約定挙動（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）

使い方（コマンド例）
------------------
- .env の作成（ウィザード）
  python -m kabusys.config_setup

- 設定を検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番/ペーパーは KABUSYS_ENV に依存）
  python -m kabusys.run_execution

  ペーパートレード起動例:
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution

  実行中停止:
    - 監視側（KillSwitch）が生成する data/kill.flag により ExecutionEngine に停止シグナルを送れます。
    - またプロジェクトルートの data/stop_requested.flag を作成すると run_execution / run_monitoring の外側ループが終了します（運用用の停止フラグ）。

- Monitoring を起動
  python -m kabusys.run_monitoring
  環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（例: export MONITOR_POLL_INTERVAL=30）。

- ペーパートレード検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  DB パスは --db で指定するか、PAPER_TRADING_SQLITE_PATH 環境変数を利用します。

- AI 機能（サンプル）
  OpenAI API キーを設定（ENV: OPENAI_API_KEY）。ai.score_news / ai.score_regime の関数を Python から直接呼び出して利用できます（DuckDB 接続を渡す設計）。

運用上のファイル・フラグ
----------------------
- data/execution.pid: ExecutionEngine の PID（起動時に書き込まれる想定）
- data/stop_requested.flag: run_* スクリプトの外側ループ停止用フラグ（作成で停止）
- Settings.kill_flag_path (デフォルト data/kill.flag): KillSwitch による ExecutionEngine 停止シグナル
- logs/: ログ出力先（デフォルト）

ディレクトリ構成（主要ファイル）
------------------------------
以下はソースツリーの主要ファイルと概要（src/kabusys 配下を示します）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

  - execution/               — 発注・実行関連（Factory / Engine / OrderManager など）
    (実装ファイル群: broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager, ...)

  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py      — CPU/メモリ/ディスク・データ鮮度・プロセス監視
    - trade_monitor.py       — 注文ログ監視（滞留注文・約定異常検出 等）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag の書き込み / 管理
    - monitoring_engine.py   — 各 Monitor を束ねるポーリング実行
    - alert_manager.py       — （アラート送信ロジック、LINE等を想定）

  - portfolio/
    - portfolio_builder.py   — 候補選定、重み計算
    - position_sizing.py     — 株数計算、aggregate cap、lot rounding
    - risk_adjustment.py     — セクターキャップ、レジーム乗数

  - research/
    - factor_research.py     — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py — forward returns / IC / 統計サマリー

  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI 経由）
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント合成）

  - data/                    — 実行時生成の DB・フラグ等（通常は .gitignore）
  - logs/                    — ログファイル

ユーティリティ
-------------
- ロギング: kabusys.utils.logging_setup.setup_logging(app_name="...") を各起動スクリプトで呼ぶことで統一的に stdout と 日次ローテートログを書きます。
- プロセス優先度: kabusys.utils.process_priority.set_process_priority("high") を呼んで起動時に優先度を上げます（権限がない場合は警告で継続）。

注意事項・運用メモ
-----------------
- 本リポジトリには秘密情報（APIキー等）を含めないでください。.env を Git にコミットしないでください（config_setup でも注意喚起があります）。
- KABUSYS_ENV=live の場合は本番 DB / 実取引に接続される点に注意してください。validate_config の live ガードや LINE 通知設定等を事前に確認してください。
- OpenAI（AI 機能）を利用する場合は API コスト・レート制限に注意し、API キーの管理を厳重に行ってください。
- DuckDB / SQLite のファイルパスはデフォルトで data/ 以下です。永続化場所・バックアップ方針を事前に決めてください。
- run_execution/run_monitoring の停止や再起動は stop フラグ（data/stop_requested.flag）や kill.flag の挙動を理解した上で運用してください。

開発者向け情報
---------------
- 研究・集計関数は DuckDB 接続を受け取る純粋関数として実装されています。ユニットテストがしやすい設計です。
- AI 呼び出し (news_nlp / regime_detector) は API 呼び出し部分を関数でラップしており、テスト時には patch による差し替えで簡単にモック化できます。
- 設定の自動ロード: config.py はリポジトリルート（.git / pyproject.toml）を起点に .env/.env.local を自動でロードします。自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ライセンス / コントリビューション
---------------------------------
本 README に含まれる説明はプロジェクトの抜粋に基づくもので、実際の運用ではさらに安全性・冗長性・監視の強化が必要です。外部に公開する際は、対応するライセンスファイルを追加してください。

質問や補足の要望があれば、どの項目を詳しく書くか教えてください。