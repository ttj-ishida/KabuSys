KabuSys — 日本株自動売買システム
==============================

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的とした Python パッケージ群です。本リポジトリは以下の主要機能を持ちます。

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク管理を行う（本番 / ペーパートレード対応）
- 監視（Monitoring）: プロセス健全性・データ鮮度・注文異常・リスク指標のポーリング監視とログ保存
- ポートフォリオ構築モジュール: 候補選定、重み付け、株数決定、セクター制約等の純粋関数群
- リサーチ/ファクター計算: DuckDB を用いたファクター・将来リターン・IC 等の計算
- AI モジュール: ニュースの LLM（OpenAI）を用いたセンチメント集約や市場レジーム判定
- ユーティリティ: ロギング設定、プロセス優先度設定、設定ウィザード/検証等

主な特徴 / 機能一覧
------------------
- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）
  - 設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- Execution
  - 本番 / ペーパー（KABUSYS_ENV に依存）
  - Paper Trading 時は MockBrokerClient を使い専用 SQLite（data/paper_trading.db）に分離
  - 停止制御: data/stop_requested.flag / data/kill.flag を用いた安全停止
- Monitoring
  - system_status / trade_logs / positions / risk_logs / dashboard を SQLite に永続化
  - リスク監視（ドローダウン・ポジション上限）と Kill Switch（条件達成で Execution 停止）
  - MONITOR_POLL_INTERVAL でポーリング間隔を調整可能（デフォルト 60 秒）
- Research
  - DuckDB ベースのファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン計算、IC（Spearman）や統計サマリ機能
- AI
  - OpenAI（gpt-4o-mini 等）を用いたニュースセンチメントスコアリング（ai_scores テーブルへ保存）
  - 市場レジーム判定（MA200 とマクロニュースの LLM 評価の合成）
- ツール
  - Paper Trading 検証レポート生成スクリプト（python -m kabusys.tools.paper_verification_report）

前提 / 必要環境
---------------
- Python 3.10+
- 必要パッケージ（主要なもの）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config YAML のパース検証は任意 — インストールが無い場合は警告となる）
- SQLite・ファイルシステムアクセス（data/, logs/ ディレクトリ）

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール:
   - pip install duckdb psutil openai PyYAML
   - 必要に応じて追加パッケージをインストールしてください。

3. 必要ディレクトリの作成（通常はスクリプトが自動作成するが手動で作ることも可）:
   - mkdir -p data logs

4. 環境変数の設定（.env の作成推奨）:
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
     - これによりプロジェクトルートに .env を作成・更新できます。
   - 最低限設定が必要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - AI 機能を使う場合:
     - OPENAI_API_KEY を環境変数に設定するか、score_regime 等の関数に直接渡す。

5. 設定検証:
   - python -m kabusys.validate_config
   - 警告も FAIL にしたい場合は --strict を付ける

使い方（実行方法）
-----------------
- 実行エンジン（ExecutionEngine）起動:
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用し、MockBroker を利用します（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中は data/stop_requested.flag を作成することで安全に停止できます（スクリプトが検出して stop を呼び出します）。
    - 実行プロセスの PID は data/execution.pid に書き込まれます（設定により変更可）。

- 監視プロセス（Monitoring）起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可（デフォルト 60 秒）。
  - 監視は Monitoring 用の sqlite DB（Settings.sqlite_path）を用います。Monitoring は KABUSYS_ENV に依らず本番 sqlite_path を参照します。
  - 停止: data/stop_requested.flag を作成すると監視ループを終了します。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別 DB を指定可能（優先順位: --db > 環境変数 PAPER_TRADING_SQLITE_PATH > data/paper_trading.db）

停止・Kill フラグ等
-------------------
- stop（即時ループ終了）:
  - data/stop_requested.flag を作成すると run_execution / run_monitoring のループは検知して終了します。
- Kill Switch（条件達成時に Execution を停止）:
  - monitoring の KillSwitch は data/kill.flag を書き込むことで ExecutionEngine 停止を要求します（Execution 側は起動時 / 監視時に kill.flag の存在を参照して動作）。
  - kill.flag を手動で削除する場合は rm data/kill.flag。動作により起動時に自動クリアする設定 KILL_FLAG_CLEAR_ON_START=1 が有効な場合もあります（設定により動作が変わります）。

ログ
----
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます（30 日分保持）。
- コンソールは stdout に出力されます。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一的に行われます。

よく使う環境変数（主なもの）
---------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 関連処理で必要）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で使用）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動でクリアするか（"1" で有効）

サンプル .env（抜粋）
--------------------
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
OPENAI_API_KEY=sk-...
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュールと役割の概略です。

- kabusys/
  - __init__.py                 — パッケージ初期化（バージョン等）
  - config.py                   — Settings クラス: 環境変数・.env 自動読み込み・検証
  - config_setup.py             — .env 対話式ウィザード（CLI）
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - run_monitoring.py           — SystemMonitor 起動スクリプト（python -m kabusys.run_monitoring）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - ai/
    - news_nlp.py               — ニュース NLP（OpenAI で銘柄ごとにセンチメント集計）
    - regime_detector.py        — 市場レジーム判定（MA + マクロニュース）
  - monitoring/
    - monitoring_db.py          — SQLite のテーブル定義 / 操作ラッパー
    - system_monitor.py         — システム状態・データ鮮度監視
    - trade_monitor.py          — （注文関連の監視、ファイル内で参照あり）
    - risk_monitor.py           — ドローダウン・ポジション上限監視
    - kill_switch.py            — kill.flag 管理
    - monitoring_engine.py      — Monitor を束ねるエンジン
    - alert_manager.py          — （通知管理、ファイル内で参照あり）
  - portfolio/
    - portfolio_builder.py      — 候補選定・等重/スコア重み計算
    - position_sizing.py        — 株数決定・資金配分ロジック
    - risk_adjustment.py        — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py        — ファクター計算（momentum/volatility/value）
    - feature_exploration.py    — 将来リターン・IC・統計サマリ
  - utils/
    - logging_setup.py          — ログ設定ユーティリティ
    - process_priority.py       — プロセス優先度 / CPU affinity ユーティリティ
  - その他（execution/*.py 等、発注・Order 管理に関するモジュール群が含まれる想定）

開発・貢献
----------
- コードスタイルは PEP8/型ヒントを基準に整備されています。テスト・CI の追加を歓迎します。
- 重大な変更を加える場合はまず issue を立て、設計方針を相談してください。

補足メモ
--------
- Monitoring は環境にかかわらず監視用 sqlite_path（デフォルト data/monitoring.db）を使います。Execution の DB は KABUSYS_ENV によって切り替わります（paper_trading 時は paper_sqlite_path）。
- AI 機能は OpenAI API に依存します。API 呼び出しはリトライ・バックオフや結果バリデーションを行う実装になっていますが、API キーとコスト管理には注意してください。
- ログディレクトリ作成に失敗した場合はコンソールログのみで動作継続します。

ライセンス
---------
- 本リポジトリに含まれるコードは（ここにライセンス情報を記載してください）。README にライセンスを明記していない場合はリポジトリの LICENSE ファイルを参照してください。

---

まずは:
- 仮想環境作成 → 依存インストール
- python -m kabusys.config_setup で .env を作成
- python -m kabusys.validate_config で検証
- python -m kabusys.run_monitoring / python -m kabusys.run_execution を実行して動作確認

必要があれば README の例やコマンド例を追加します。ほかに載せたい情報（例: systemd ユニット例、Dockerfile、サンプル .env.example）を教えてください。