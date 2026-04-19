# KabuSys

日本株向け自動売買システム（軽量プロトタイプ）

このリポジトリは、日次〜リアルタイムでのシグナル生成・ポートフォリオ構築・発注（本番／ペーパートレード）およびシステム監視・アラート／Kill Switch を備えた自動売買基盤の実装例です。モジュールは可能な限り純粋関数や副作用の少ない設計を心がけており、DuckDB／SQLite をデータ層に使用します。

---

## 主要機能

- 環境設定ウィザード（.env 生成 / 更新）: kabusys.config_setup
- 起動前設定検証 CLI（env / config yaml のチェック）: kabusys.validate_config
- ExecutionEngine 起動スクリプト（発注ループ）: kabusys.run_execution
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し paper_trading DB に記録
- Monitoring ポーリング（各種モニタ）起動スクリプト: kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL で間隔変更可（デフォルト 60 秒）
  - 監視は monitoring DB（SQLite）へ永続化
- Monitoring コンポーネント
  - SystemMonitor: CPU/メモリ/Disk/プロセス生存・データ鮮度監視
  - TradeMonitor / RiskMonitor: 注文滞留・約定異常・ドローダウン・ポジション数監視
  - KillSwitch / AlertManager 経由で自動停止や通知を行う
- Portfolio construction ユーティリティ（候補選定・重み・ポジションサイズ）
- Research モジュール（ファクター計算・IC 評価・将来リターン計算）
- AI モジュール（OpenAI を用いたニュースセンチメント / レジーム判定）
- ツール: Paper Trading 検証レポート生成スクリプト

---

## 必要条件 / 依存ライブラリ（主要）

- Python 3.10+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（設定ファイルの検査を行う場合）
- （必要に応じて）sqlite3 は標準モジュール

pip インストール例（仮）:
pip install duckdb psutil openai pyyaml

---

## セットアップ手順（開発 / 初回導入）

1. リポジトリをクローンし仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存をインストール
   - pip install -r requirements.txt
   （requirements.txt がない場合は上の主要パッケージを個別にインストール）

3. .env の作成（ウィザード推奨）
   - python -m kabusys.config_setup
     - 対話式で .env を生成します（デフォルトはプロジェクトルートの .env）。
   - 自動ロード: config モジュールはプロジェクトルートに .env / .env.local がある場合、自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

4. 設定検証
   - python -m kabusys.validate_config
     - 必須環境変数やファイルパス整合性、（PyYAML がある場合）config/*.yaml の構文確認を行います。
     - --strict を付けると警告も失敗として扱います。

5. ディレクトリの準備
   - data/ と logs/ は自動生成されることが多いですが、手動で作成して権限を確認しておくと安心です。
     - mkdir -p data logs

6. DB 初期化
   - 監視テーブルなどは起動時に自動作成されます（init_monitoring_db を使用）。
   - Paper Trading 用 DB は KABUSYS_ENV=paper_trading のときに別ファイルを使用（デフォルト: data/paper_trading.db）。

---

## 主要な環境変数（よく使うもの）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: 実行環境（development | paper_trading | live） — デフォルト development
  - paper_trading: Mock ブローカー + data/paper_trading.db を使用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite ファイルパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動でクリアするか（0/1）

注意:
- config モジュールは .env と .env.local を自動でロードします（OS 環境変数が優先）。自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 実行方法（コマンド例）

- 環境ウィザード（.env の作成／更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗）: python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番/ペーパーいずれも）
  - python -m kabusys.run_execution
    - KABUSYS_ENV によって実挙動が変わります（paper_trading なら MockBroker）
    - 起動時に data/execution.pid に PID が書かれます（Settings.pid_file_path）

- Monitoring を起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書きできます。
    - Monitoring は Settings に従い監視用 SQLite（settings.sqlite_path）を常に使用します（KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可。

- AI 系（ニューススコア・レジーム判定）はそれぞれ関数経由で呼び出します（OpenAI API キーが必要）。

---

## 停止・Kill スイッチ

- run_execution.py / run_monitoring.py はプロジェクトルートの data/stop_requested.flag を検知すると終了します（自動停止用のフラグ）。
  - 停止させたい場合は stop_requested.flag を作成してください:
    - touch data/stop_requested.flag
- KillSwitch（自動停止）:
  - 監視が条件を満たすと Settings.kill_flag_path（デフォルト data/kill.flag）に理由を書き込みます。ExecutionEngine 側はこの kill.flag を検知して安全に停止します。
  - 注意: KILL_FLAG_CLEAR_ON_START=1 を本番環境で使うのは危険です（デフォルト 0 推奨）。

---

## ログ

- 共通のロギング初期化 util を使っています（kabusys.utils.logging_setup.setup_logging）。
- 出力:
  - コンソール（stdout）
  - 日次ローテーションのファイル（logs/<app_name>.log、デフォルト 30 日分保持）
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御します。

---

## ディレクトリ構成（主要ファイル抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数読み込み・設定管理
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリング起動スクリプト
  - utils/
    - logging_setup.py — ログ設定
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py — SQLite 永続化レイヤ（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - trade_monitor.py — （注文周りの監視。コードベースに依存）
    - kill_switch.py — フラグファイルによる停止シグナル作成
    - monitoring_engine.py — 各 Monitor を束ねる実行ループ
    - alert_manager.py — 通知（LINE 等）送信（実装参照）
  - execution/ — 発注エンジン、OrderManager, RiskManager, BrokerFactory 等（実際の実装を参照）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI 使用）
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート

（上記は本リポジトリに含まれる主要モジュールとその役割を抜粋したものです。詳細はソースコードの docstring を参照してください。）

---

## 開発・運用上の注意

- 本番実行時は KABUSYS_ENV=live を指定します。live では通知設定や kill flag の取り扱い等を慎重に確認してください。
- .env は秘匿情報を含むため絶対にバージョン管理（Git 等）にコミットしないでください。
- AI 機能（OpenAI）を利用する場合、API キーの取り扱いとコスト管理に注意してください。API 呼び出しはリトライやフェイルセーフ（失敗時はスコア0やスキップ）を組み込んでいますが、運用設計は必要です。
- データ鮮度やレジーム判定などはルックアヘッドバイアスを避ける実装方針を採っています（target_date 未満のデータのみ使用する等）。

---

必要であれば、README に含める具体的な systemd / Supervisor 用のサービスユニット例や、より詳しい運用手順（ログローテーション設定、定期バックアップ、DB マイグレーション方針など）も作成します。どの情報が欲しいか教えてください。