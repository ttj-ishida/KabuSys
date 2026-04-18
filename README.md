# KabuSys

日本株向けの自動売買・リサーチ基盤（KabuSys）のリポジトリ。  
このREADMEはコードベースから抽出した使い方・セットアップ手順・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能群を提供します：

- 市場データ（DuckDB）を使ったファクター計算・リサーチ
- シグナルからのポートフォリオ構築・ポジションサイズ計算
- ExecutionEngine を通じた発注・注文管理（kabuステーション、またはペーパートレードの MockBroker）
- 監視（Monitoring）：システム状態、注文状況、リスク監視、Kill Switch
- AI モジュール（OpenAI）を使ったニュースセンチメント評価・レジーム判定
- Paper Trading 検証レポート生成スクリプト

本リポジトリは「本番用」「ペーパートレード用」「開発用」を環境変数で切り替えて利用できます。

---

## 主な機能一覧

- execution
  - ExecutionEngine による注文の作成・送信・リスク管理
  - Paper trading と Live（kabuステーション）を切替可能
- monitoring
  - SystemMonitor：CPU/メモリ/Disk・データ鮮度・Execution プロセス検査
  - TradeMonitor：注文滞留・約定異常などの検出
  - RiskMonitor：ドローダウンや保有銘柄数上限の監視
  - KillSwitch：条件成立時にフラグファイルを書き ExecutionEngine を停止
  - MonitoringEngine：定期ポーリングで上記を統合しアラート管理
- portfolio
  - 候補選定、等金額/スコア加重、リスク調整、ポジションサイズ計算（単元丸め含む）
- research
  - ファクター計算（Momentum, Volatility, Value 等）
  - 特徴量探索（Forward returns, IC, 統計サマリ）
- ai
  - news_nlp: OpenAI を用いたニュースセンチメント（ai_scores）生成
  - regime_detector: ETF とマクロニュースを合わせた市場レジーム判定
- utils
  - logging_setup: 標準化されたログ設定（コンソール + 日次ローテーション）
  - process_priority: プロセス優先度・CPU affinity 設定
- tools
  - paper_verification_report: ペーパートレード実績の検証レポート出力
- CLI 補助
  - config_setup: .env を対話的に生成
  - validate_config: 環境変数 / config/*.yaml の検証

---

## 要件（概略）

- Python 3.10+
- 主要依存ライブラリ（用途に応じてインストール）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config YAML 検証を行う場合）
- SQLite（標準で Python に同梱）
- kabuステーション API（Live 実行時）

実際の requirements.txt はプロジェクト配布時に合わせて用意してください。

---

## セットアップ手順（Quickstart）

1. リポジトリをクローン／配置
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) または .venv\Scripts\activate (Windows)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
     - AI 機能や YAML 検証を使わない場合は openai / PyYAML は任意
4. .env を用意する（推奨: 対話ウィザードで作成）
   - python -m kabusys.config_setup
   - ウィザード終了後、設定を検証:
     - python -m kabusys.validate_config
     - 必要な環境変数が未設定ならエラー/警告が出ます
5. ディレクトリとデフォルトファイル
   - デフォルトでは以下のパスを利用します（いずれも .env で変更可能）
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - PID / kill flag: data/execution.pid / data/kill.flag
     - ログ: logs/<app_name>.log

init_monitoring_db() により監視用の SQLite スキーマは起動時に自動作成（冪等）されます。

---

## 使い方（主要コマンド）

環境変数は .env に設定するか、シェルで export（Windows は set）してから実行してください。

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります

- ExecutionEngine を起動（本番または paper_trading）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBroker を使用し、ペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH）へ書き込みます
  - 起動時に data/stop_requested.flag が存在すると起動をスキップ
  - 実行中は data/execution.pid に PID を書きます

- Monitoring（常駐監視）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト: 60）
  - Monitoring は環境に関わらず本番用 sqlite_path を使用して監視ログを書きます

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数が優先されます）

- AI 関連（OpenAI API 必須）
  - ニュースセンチメント: kabusys.ai.score_news（プログラムから呼び出し）
  - レジーム判定: kabusys.ai.regime_detector.score_regime（プログラムから呼び出し）
  - OpenAI の API キーは OPENAI_API_KEY 環境変数または関数引数で渡します

---

## 停止 / Kill Switch の運用

- ExecutionEngine の停止を指示する方法
  - kill.flag: KillSwitch が書き込むフラグファイル（Settings.kill_flag_path、デフォルト data/kill.flag）
    - KillSwitch.evaluate() が条件を満たすと kill.flag に理由を書き込みます（存在すれば上書きしない）
    - ExecutionEngine 側は起動時やループ中に kill.flag の存在を検知すると停止します
  - stop_requested.flag: run_execution / run_monitoring が見る停止フラグ（data/stop_requested.flag）
    - 運用側で停止をリクエストする際にこのファイルを作成できます

- 起動時の注意
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします。Production（KABUSYS_ENV=live）では 0 を推奨します。

---

## ログ

- ログはデフォルトで `logs/` ディレクトリに日次ローテーションで出力されます（TimedRotatingFileHandler, 30日保持）。
- setup_logging() でログ出力先やレベルをカスタマイズできます。
- コンソール出力は stdout に行われます（cron 等でリダイレクトすると扱いやすい）。

---

## 環境変数（主要）

- 必須（validate_config でチェック）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

- DB パス
  - DUCKDB_PATH（例: data/kabusys.duckdb）
  - SQLITE_PATH（監視DB。例: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、例: data/paper_trading.db）

- AI / OpenAI
  - OPENAI_API_KEY（news_nlp / regime_detector を使う場合）

- Monitoring
  - MONITOR_POLL_INTERVAL（秒、デフォルト 60）

- その他
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / PAPER_FILL_MODE など多数（.env ウィザードで設定可能）

---

## 開発メモ / 注意点

- Monitoring は常に本番用 sqlite_path を参照して監視ログを記録します（run_monitoring の実装による）。
- run_execution は KABUSYS_ENV により paper_trading 用 DB を使用するため、本番 DB とデータは分離されます。
- OpenAI を利用する機能は API キーが必須で、コストが発生する可能性があります。運用前に十分にテストしてください。
- 一部の機能（YAML 検証など）は任意の依存（PyYAML）に依存します。validate_config は PyYAML がない場合は YAML 中身検証をスキップします。
- process_priority で High を設定しますが、環境によって権限不足で失敗する可能性があります（警告でスキップされます）。
- DuckDB を用いたリサーチ処理は SQL を主体に行われ、大規模データ分析に適しています。

---

## ディレクトリ構成

以下は src/kabusys 配下の主なファイル/ディレクトリと簡単な説明です（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数／Settings 管理、自動 .env ロード（.env / .env.local）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト（PID / stop flag 制御）
  - run_monitoring.py        — SystemMonitor 単独ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成ツール
  - ai/
    - news_nlp.py            — ニュース -> センチメント（OpenAI）
    - regime_detector.py     — レジーム判定（MA + マクロセンチメント）
  - research/
    - factor_research.py     — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py — forward returns, IC, 統計サマリ等
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み付け
    - position_sizing.py     — 株数決定・単元丸め・集約 cap
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ / 永続化 API
    - system_monitor.py      — CPU/メモリ/Disk・データ鮮度・プロセス監視
    - trade_monitor.py       — （注文関連監視。詳細は実装参照）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書き込み・判定
    - monitoring_engine.py   — 各 Monitor を束ねるループ実装
    - alert_manager.py       — （通知管理。実装参照）
  - execution/
    - execution_engine.py    — ExecutionEngine 実装（注文実行フロー）
    - broker_factory.py      — Broker クライアントの生成（実ブローカ / Mock）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ（コンソール + 日次ファイル）
    - process_priority.py    — 優先度・CPU affinity 設定ユーティリティ

（注）上記は抜粋です。実プロジェクトではさらに補助スクリプトやデータ定義、ドキュメント（Markdown）等が存在することが想定されます。

---

## よくある運用フロー（例）

1. .env を作成（python -m kabusys.config_setup）
2. 設定を検証（python -m kabusys.validate_config）
3. データ投入／DuckDB 準備（外部 ETL）
4. ExecutionEngine を起動（python -m kabusys.run_execution）
5. 別プロセスで Monitoring を起動（python -m kabusys.run_monitoring）
6. 定期的に paper_verification_report を使って検証する

---

もし README に追加してほしい情報（詳細な起動オプション、実行ログのサンプル、CI 設定、単体テストの書き方など）があれば教えてください。必要に応じて具体例・コマンドサンプルを追記します。