KabuSys
======

日本株向けの自動売買／研究プラットフォーム（プロトタイプ）。  
ポートフォリオ構築、ポジションサイジング、リスク制御、発注エンジン、監視・アラート、研究用ファクター計算、ニュースNLP（OpenAI）などのコンポーネントを含みます。

バージョン: 0.1.0

プロジェクト概要
---------------
KabuSys は下記の責務を持つモジュール群で構成された日本株自動売買システムです。

- シグナル → ポートフォリオ構築 → 発注までの Execution エンジン
- 実行系を監視し、データ鮮度・プロセス状態・リスク指標でアラートや Kill Switch を発動する Monitoring
- DuckDB を使った研究向けファクター計算 / 特徴量解析モジュール
- OpenAI を使ったニュースのセンチメント評価・市場レジーム判定（AI モジュール）
- Paper Trading（ペーパートレード）モード（本番 DB と完全に分離）
- ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証、レポート生成）

主な機能一覧
-------------
- Execution
  - Broker クライアントの抽象化（実運用/モック切替）
  - OrderManager, RiskManager, Reconciler を組み合わせた ExecutionEngine
  - Paper trading モードでは data/paper_trading.db に記録し本番 DB と分離
- Monitoring
  - SystemMonitor: CPU/MEM/DISK、プロセス PID、データ鮮度監視
  - TradeMonitor / RiskMonitor: 滞留注文、約定異常、ドローダウン、ポジション上限監視
  - KillSwitch: 条件により data/kill.flag を書いて Execution を停止
  - MonitoringEngine: 各モニタを束ねてポーリング（ログ・アラート連携）
- Portfolio
  - 候補選定、等金額/スコア加重の重み計算
  - セクター上限適用、レジーム乗数計算
  - 発注株数算出（単元株丸め、リスクベース配分、aggregate cap）
- Research
  - DuckDB 接続で動くファクター計算（Momentum, Value, Volatility など）
  - 将来リターン、IC 計算、統計サマリー等
- AI
  - news_nlp: raw_news を OpenAI に送信して銘柄ごとのセンチメントを ai_scores に保存
  - regime_detector: ETF（1321）MA200 とマクロニュースセンチメントを合成し market_regime に書込
- Tools
  - config_setup: 対話式 .env ウィザード
  - validate_config: 起動前の設定検証 CLI
  - paper_verification_report: Paper Trading データから検証レポート生成

前提 / 必要パッケージ
-------------------
（プロジェクト内の import から推測される主要依存）
- Python 3.9+
- duckdb
- psutil
- openai
- （オプション）PyYAML（config の YAML 検証用）

インストール（例）
-----------------
1. リポジトリをクローン:
   - git clone <repo-url>
2. 仮想環境を作成して有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（requirements.txt がある場合はそれを利用）:
   - pip install duckdb psutil openai
   - （必要に応じて）pip install -r requirements.txt
4. 開発インストール（任意）:
   - pip install -e .

設定（.env）
-----------
KabuSys は環境変数 / .env による設定を前提とします。.env を対話式で作るには:

- 初期ウィザード:
  - python -m kabusys.config_setup

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API トークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
  - paper_trading: MockBroker を使用し data/paper_trading.db に記録
- OPENAI_API_KEY — OpenAI を使うモジュールで必要（AI 機能を使う場合）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒; デフォルト 60）
- PID/flag:
  - data/execution.pid（ExecutionEngine の PID ファイル）
  - data/stop_requested.flag（run_* スクリプトを停止するためのフラグ）
  - data/kill.flag（KillSwitch が Execution を止めるときに書き込む）

設定検証
-------
- .env と config/*.yaml の存在・基本チェック:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い

使い方（主要コマンド）
--------------------

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 戻り値: 0=OK, 1=FAIL

- ExecutionEngine 起動
  - デフォルト（環境に応じて本番/ペーパーが切替）
    - python -m kabusys.run_execution
  - Paper Trading にするには:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - これにより MockBroker を使い data/paper_trading.db に記録されます
  - 停止は data/stop_requested.flag を作成するか、Execution 側の kill.flag を利用

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定（デフォルト 60）
  - 監視は本番 sqlite_path を常に使用（環境に依存せず）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

- ログ
  - logs/<app_name>.log に日次ローテーションで出力（utils.logging_setup が管理）
  - コンソールは stdout に出力

運用ノート / 実行時注意
---------------------
- 本番環境 (KABUSYS_ENV=live) では特に以下に注意:
  - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等の必須設定を漏れなく設定すること
  - KILL_FLAG_CLEAR_ON_START は本番では 0 を推奨（自動クリアは危険）
  - LINE 通知の設定を行っておくとアラートが届きます（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）
- Paper Trading は本番 DB と明確に分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH）
- OpenAI を使う処理は API レート制限・エラーを考慮してバックオフ／フォールバック実装あり。API キーは必須

ディレクトリ構成
----------------
主要なファイル・ディレクトリ（src/kabusys 配下）:

- src/kabusys/
  - __init__.py                 — パッケージ定義（__version__）
  - config.py                   — 環境変数 / 設定管理
  - config_setup.py             — .env 対話ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py               — ニュースセンチメント（OpenAI）
    - regime_detector.py        — 市場レジーム判定（OpenAI + ETF MA）
  - monitoring/
    - monitoring_db.py          — SQLite 永続層（監視ログ）
    - system_monitor.py         — システム・データ鮮度監視
    - trade_monitor.py          — （trade モニタ、ファイル内に存在）
    - risk_monitor.py           — ドローダウン／ポジション上限監視
    - kill_switch.py            — Kill Switch 実装（data/kill.flag 書込）
    - monitoring_engine.py      — 各モニタを束ねるエンジン
    - alert_manager.py          — （アラート送信管理）
  - execution/
    - execution_engine.py       — ExecutionEngine 本体
    - broker_factory.py         — Broker クライアント生成
    - order_manager.py          — 注文管理
    - order_repository.py       — 注文永続化（SQLite など）
    - reconciler.py             — 注文整合性処理
    - risk_manager.py           — 注文発行前のリスクチェック
  - portfolio/
    - portfolio_builder.py      — 候補選定・重み計算
    - position_sizing.py        — 発注株数算出
    - risk_adjustment.py        — セクター上限・レジーム乗数
  - research/
    - factor_research.py        — Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py    — IC / ランク相関 / 統計サマリー
  - data/                       — 実行時に使用する DB / フラグ等を置くディレクトリ（例: data/monitoring.db, data/paper_trading.db）
  - utils/
    - logging_setup.py          — ログ設定ユーティリティ
    - process_priority.py       — プロセス優先度設定ユーティリティ
    - ...                       — 共通ユーティリティ群

（注）上記はコードベースの主要ファイルを抜粋したもので、実際の構成はリポジトリの内容に依存します。

開発時の補足
-------------
- DuckDB 接続を渡すことで研究コードは本番システムと分離して動かせます（read-only 想定）
- AI モジュールは OpenAI の API レスポンス依存のため、テスト時は _call_openai_api をモック化してテスト可能
- MonitoringDB（SQLite）はマイグレーションを組み込みで行う（列がなければ ADD COLUMN する）

問い合わせ・貢献
----------------
- バグ報告や機能提案は issue を立ててください。
- 開発に参加する場合はスタイルや設計方針（ログ/例外ハンドリング/DB 操作の冪等性）を尊重してください。

以上。必要であれば README の翻訳（英語版）・起動スクリプトの詳細な運用手順（systemd / cron / Docker など）・requirements.txt の生成補助を作成します。どれを優先しますか？