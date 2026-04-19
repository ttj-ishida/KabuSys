# KabuSys

日本株自動売買システム（ライブラリ兼軽量実行フレームワーク）

このリポジトリは、戦略（ファクター計算・ポートフォリオ構築）、Execution（発注エンジン／ペーパートレード対応）、Monitoring（稼働監視・Kill Switch）、AI 補助（ニュース NLP / レジーム判定）などを備えた自動売買システムのコア実装を含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（代表的なコマンド）
- 環境変数（主要項目）
- 実行時の挙動（ペーパートレード／本番分離、Kill Switch 等）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコアコンポーネント群です。特徴は以下の通りです。

- DuckDB / SQLite を使ったデータ管理（分析用 DB と監視/発注ログは分離）
- 戦略研究モジュール（ファクター計算、将来リターン、IC 計算、統計サマリー）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ決定、セクター上限等）
- ExecutionEngine（本番／ペーパートレード分離、リスク管理、注文管理）
- Monitoring（システム・注文・リスク監視、Kill Switch、通知）
- AI 補助（ニュースの NLP によるセンチメント、レジーム判定。OpenAI を使用）
- コマンドラインユーティリティ（環境設定ウィザード、設定検証、レポート生成など）

---

## 主な機能

- 設定管理（.env 自動読み込み、Settings クラス）
- 実行スクリプト
  - run_execution.py — ExecutionEngine 起動（KABUSYS_ENV に応じて本番または Mock）
  - run_monitoring.py — SystemMonitor のポーリングループ起動（停止フラグ対応）
- 監視
  - system_monitor, trade_monitor, risk_monitor による異常検出
  - Kill Switch（data/kill.flag）を書き込むことで ExecutionEngine の停止を要求
- ポートフォリオ
  - 候補選定、等重／スコア重み、リスクベースの株数決定、セクター制限、レジーム乗数
- 研究（research）
  - ファクター計算（モメンタム、バリュー、ボラティリティ）
  - 特徴量と将来リターンの解析（IC、統計サマリー）
- AI
  - ニュースセンチメント（OpenAI を利用。batch 処理・リトライ実装）
  - マクロニュースと MA を組合せた市場レジーム判定
- ユーティリティ
  - ロギング設定（console + 日次ローテートファイル）
  - プロセス優先度・CPU affinity 設定
- ツール
  - paper_verification_report — ペーパートレードの検証レポート生成

---

## セットアップ手順

1. リポジトリをクローンし、Python 仮想環境を用意します（Python 3.9+ を推奨）。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate

2. 必要なパッケージをインストールします（最低限の依存）:
   - duckdb
   - psutil
   - openai (AI 機能を使う場合)
   - PyYAML（config 検証で YAML の検査を行う場合に必要）

   例:
   - pip install duckdb psutil openai PyYAML

   （本プロジェクトには requirements.txt は含まれていないため、必要なパッケージを上記から選んでください）

3. .env を用意する
   - 対話式ウィザードで生成:
     - python -m kabusys.config_setup
   - または .env.example を参考に .env を作成してください（.env は Git に追加しないでください）。
   - 自動読み込み:
     - プロジェクトルートに .env / .env.local があれば起動時に自動読み込みされます（OS 環境変数優先）。
     - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

4. データディレクトリ作成
   - デフォルトでは data/ 以下に DB や PID/flag を格納します。必要に応じて事前に作成してください。起動時に自動作成される箇所もあります。

---

## 使い方（代表的なコマンド）

- 設定ウィザード（.env を対話式生成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱い（exit 1）
  - 例: python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番 / ペーパートレードは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution

  挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、DB は data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）に記録して本番 DB と分離します。
  - 起動前に data/stop_requested.flag が存在する場合は起動をスキップします。
  - ExecutionEngine の PID は data/execution.pid に書き込まれます。
  - 停止は data/stop_requested.flag（管理用）や data/kill.flag（Kill Switch）で制御されます。

- Monitoring を起動（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring

  オプション的な環境変数:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルトは 60。1 以上の整数を指定。
  - 監視は Settings で指定された sqlite_path（デフォルト data/monitoring.db）を使用します（monitoring は環境にかかわらず本番 sqlite_path を使用）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10
  - --db で PAPER_TRADING_SQLITE_PATH をオーバーライド可能。

---

## 主要な環境変数（デフォルト含む）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN (任意)
- LINE_USER_ID (任意)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB、デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB、デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (paper_trading の仮約定モード、デフォルト: "instant"。有効値: "instant" | "partial" | "never" | "reject")
- KABUSYS_ENV (実行環境: "development" | "paper_trading" | "live"。デフォルト: "development")
- LOG_LEVEL (デフォルト: INFO)
- LOG_DIR (ログ保存先、デフォルト: logs)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか。0/1。デフォルト: 0)
- MONITOR_POLL_INTERVAL (run_monitoring 用ポーリング秒数、デフォルト: 60)
- OPENAI_API_KEY (AI 機能を使用する場合に必要)

注意:
- .env 自動読み込みの優先順は OS 環境変数 > .env.local > .env です。
- OS 環境変数を保護したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化してください。

---

## 実行時の挙動・運用上の注意

- ロギング:
  - 共通 utility setup_logging により stdout と logs/<app_name>.log（日次ローテーション、30日分保存）へ出力されます。
  - ログディレクトリ作成が失敗した場合はコンソール出力のみで継続します。

- プロセス優先度:
  - run_execution/run_monitoring は起動時に set_process_priority("high") を呼びます（権限により失敗する場合あり）。

- DB 分離:
  - ExecutionEngine は paper_trading 環境では paper_sqlite_path（default: data/paper_trading.db）を使用して本番 DB と完全分離します。
  - Monitoring は環境にかかわらず本番 sqlite_path（Settings.sqlite_path）を利用します（監視ログを一元化）。

- Kill Switch / 停止制御:
  - KillSwitch はリスク条件（ドローダウンやポジション上限など）を満たすと data/kill.flag を書き込みます。ExecutionEngine はこのフラグを検知して安全停止します。
  - 手動停止要求やメンテナンス停止は data/stop_requested.flag を作成することで行います（run_execution/run_monitoring はこのフラグで起動/ループ停止を制御）。

- OpenAI（AI 機能）:
  - news_nlp, regime_detector 等は OPENAI_API_KEY を利用します。キー未設定時は API 呼び出しを行わないか、ValueError を投げます（関数による）。
  - API 呼び出しはリトライ・バックオフ実装がありますが、API 利用状況やエラーに注意してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主なファイルとサブパッケージの一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI + MA）
  - research/
    - __init__.py
    - factor_research.py     — モメンタム・ボラティリティ・バリュー計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - portfolio/
    - __init__.py
    - portfolio_builder.py   — 候補選定、重み計算
    - position_sizing.py     — 株数決定・資金配分
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ／永続化操作
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - trade_monitor.py       — （存在するはずの）注文監視ロジック
    - monitoring_engine.py   — 各 Monitor を束ねるループ
    - kill_switch.py         — Kill Switch 実装（flag ファイル書き込み）
    - alert_manager.py       — アラート送信（LINE 等）（参照される想定）
  - execution/
    - execution_engine.py    — ExecutionEngine（発注セッション管理）
    - order_manager.py
    - order_repository.py
    - risk_manager.py
    - reconciler.py
    - broker_factory.py
  - utils/
    - __init__.py
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/monitoring_db.py

（上記は本 README に含まれる主要ソースの抜粋です。実際のリポジトリでは他にも補助モジュールやマスタデータ読み込み等が存在する可能性があります。）

---

## よくある操作例

- 開発用ローカル起動（開発用 env を .env に設定）
  1. .venv を用意して依存をインストール
  2. python -m kabusys.config_setup
  3. python -m kabusys.validate_config
  4. python -m kabusys.run_execution （或いは python -m kabusys.run_monitoring）

- ペーパートレードの検証
  - KABUSYS_ENV=paper_trading を .env に設定し、python -m kabusys.run_execution を実行
  - トレードログはデフォルトで data/paper_trading.db に記録される
  - 検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Kill Switch の確認／解除
  - Kill Switch により data/kill.flag が書かれると本番 Execution は停止されます。
  - 起動時に自動でクリアしたい場合は KILL_FLAG_CLEAR_ON_START=1 を設定できます（本番では推奨しません）。
  - 手動で解除するにはファイルを削除（rm data/kill.flag）するか、KillSwitch.clear() を呼び出す運用スクリプトを用意してください。

---

## 開発者向けメモ

- DB スキーマやマイグレーションは monitoring_db.init_monitoring_db に定義されています。初期化は冪等（存在チェックあり）。
- AI 部分（news_nlp / regime_detector）は外部 API に依存するため、ユニットテストでは API 呼び出しラッパー関数をモックしてください（モジュール内に注記あり）。
- logging_setup は全体で統一されたログ出力を提供します。ログディレクトリが作成できない環境でも stdout 出力は保証されます。
- config.py は .env の自動ロード機能を持ちますが、テスト時やコンテナ環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って制御可能です。

---

## ライセンス / 注意事項

- 本 README に示したコードは学習 / 開発目的の実装例です。実際に本番資金での運用を行う場合は十分なテスト、監査、コンプライアンス手続きが必要です。
- .env に API キーやパスワードを平文で格納します。Git に含めないでください。

---

README はここまでです。必要なら以下の点を追加で作成します:
- 具体的な requirements.txt の提案
- systemd / supervisor 用の起動ユニット例
- デバッグ・ロギングの手順
- 各モジュール API の詳細ドキュメント（関数シグネチャ一覧）