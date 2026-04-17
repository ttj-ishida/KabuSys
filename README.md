# KabuSys

日本株自動売買システムのリポジトリ（部分実装）。  
この README はリポジトリ内の主要スクリプト・モジュールに基づき、セットアップおよび運用手順を整理したものです。

注意: 実際の運用では .env に機密情報（API トークン / パスワード等）を含めないようにし、特に本番（KABUSYS_ENV=live）での設定は慎重に行ってください。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコアコンポーネント群を含む Python パッケージです。主な役割は以下です。

- 市場データからファクター・特徴量を計算（research）
- ポートフォリオ構築・ウェイト算出・銘柄選定（portfolio）
- Execution エンジン・注文管理（execution）
- 監視（monitoring）: システム状態、注文状態、リスク指標の定期チェック・ログ記録
- AI 補助（ai）: ニュースの NLP によるセンチメント評価やレジーム判定（OpenAI）
- 運用支援ツール（tools）: Paper Trading の検証レポートなど
- 環境設定ウィザード・設定検証 CLI（config_setup / validate_config）

設計上、監視やレポジトリは SQLite / DuckDB を用いてログや分析データを永続化します。Paper Trading は本番 DB と分離して専用の SQLite を使用する仕組みになっています。

---

## 主な機能一覧

- SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセスの監視とログ化
- TradeMonitor: 滞留注文・約定価格異常の検出とリスクログ化
- RiskMonitor: ドローダウンやポジション上限の監視、Kill Switch トリガ生成
- KillSwitch / AlertManager: 条件に応じた停止フラグ書き込みと LINE 通知（設定時）
- MonitoringEngine: 各モニタを束ねたポーリング実行ループ
- ExecutionEngine 起動スクリプト: ブローカークライアントの切り替え（paper_trading 用 Mock）
- Portfolio モジュール: 候補選定、重み計算、ポジションサイズ算出、セクター制御等の純粋関数群
- Research モジュール: モメンタム／ボラティリティ／バリュー等のファクター計算、IC 計測
- AI モジュール: ニュースのセンチメントスコアリング（OpenAI）・市場レジーム検出
- CLI ツール: .env ウィザード（config_setup）、設定検証（validate_config）、Paper レポート生成

---

## 必要環境・依存ライブラリ（概要）

- Python 3.9+
- duckdb
- psutil
- openai（AI 機能利用時）
- requests（LINE 通知）
- PyYAML（設定ファイル検証を厳密に行う場合は推奨）

実プロジェクトでは requirements.txt を用意して pip install -r で管理する想定です。最低限、監視や Execution を動かす場合は duckdb と psutil が必要です。AI 機能は OpenAI API キーが必要です。

---

## セットアップ手順

1. リポジトリをクローンして Python 仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）

2. 依存ライブラリをインストールします（プロジェクトに requirements.txt がある場合）。
   - pip install -r requirements.txt
   - または最低限:
     - pip install duckdb psutil requests

3. .env の作成
   - 対話形式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に手動作成。
   - 重要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - デフォルトのファイルパス（省略時）:
     - DUCKDB_PATH = data/kabusys.duckdb
     - SQLITE_PATH = data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH = data/paper_trading.db

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにしたい場合は --strict を付けます。

5. 必要なディレクトリやデータの初期化
   - data ディレクトリがなければ作成（多くのスクリプトが自動作成する場合あり）。
   - DuckDB / SQLite の初期スキーマは各モジュール起動時に必要に応じて作成されます（例: monitoring_db.init_monitoring_db）。

---

## 主要な環境変数（代表）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時に使用）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: Kill Switch フラグファイル（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（0/1、デフォルト 0）
- LOG_LEVEL: ログレベル（INFO 等）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant/partial/never/reject）

環境変数は .env/.env.local や OS 環境変数で設定できます（Settings モジュール参照）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

---

## 使い方（実行コマンド例）

- 環境設定ウィザード（.env の作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 警告を FAIL にする: python -m kabusys.validate_config --strict

- 監視プロセス起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 説明:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60）。
    - 監視は環境にかかわらず本番 sqlite_path を使用（monitoring 用 DB は共有しないよう注意）。
    - 終了方法:
      - data/stop_requested.flag を作成するとループは終了します（スクリプトが検知）。
      - また KeyboardInterrupt（Ctrl+C）でも終了。

- Execution エンジン起動（注文実行）
  - python -m kabusys.run_execution
  - 説明:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録して本番 DB と分離します。
    - 起動直後に data/stop_requested.flag が既に存在する場合は起動を行わず終了します。
    - 停止方法:
      - data/stop_requested.flag の作成により実行中のエンジンを停止します。
      - Kill Switch（監視側が条件を満たすと data/kill.flag を書き込み）で停止を指示できます。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH を上書き）

- AI スコアリング / レジーム判定（プログラム的に呼ぶ）
  - kabusys.ai.score_news などの関数をインポートして使用します（OpenAI API キー必須）。

---

## 停止 / Kill フラグについて

- data/stop_requested.flag: run_monitoring / run_execution が監視する停止フラグ。存在したらループを安全に終了します（手動停止用）。
- data/kill.flag: KillSwitch が書き込むフラグで、ExecutionEngine を停止させるために監視側から作成されます。KILL_FLAG_CLEAR_ON_START=1 を付けると起動時に自動クリアできますが、本番では推奨されません。

---

## 注意事項（運用上のポイント）

- Paper Trading は本番 DB と完全分離するよう設計されています。KABUSYS_ENV=paper_trading に設定した場合は paper_trading 用 SQLite が使用されます。
- OpenAI API を利用する機能は API 障害に対してフェイルセーフに設計されており、API エラー時はデフォルト値（例: macro_sentiment=0.0）で継続するようになっています。API キーは安全に管理してください。
- process priority / CPU affinity の設定は psutil を使っておこないます。権限不足で設定に失敗することがあるため、その場合は警告に留まります。
- monitoring_db.init_monitoring_db は既存 DB に対するマイグレーション（列追加など）をある程度サポートしますが、本番環境では事前にバックアップを取ってください。
- LINE 通知を利用する場合は LINE_CHANNEL_ACCESS_TOKEN と LINE_USER_ID を設定する必要があります。AlertManager は同一カテゴリの通知にクールダウンを設けます。

---

## 主要ディレクトリ構成（抜粋）

リポジトリの主要な Python モジュール構成は以下の通りです（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py              — 環境変数 / .env 読込・ラッパ
  - config_setup.py        — .env 対話式ウィザード
  - validate_config.py     — 起動前の設定検証 CLI
  - run_monitoring.py      — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - ai/
    - news_nlp.py          — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py   — 市場レジーム判定（OpenAI）
  - monitoring/
    - monitoring_db.py     — SQLite 永続化層（スキーマ / CRUD）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/             — (注文実行関連モジュール群、リポジトリに依存)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py

（注）data / config ディレクトリや scripts はリポジトリルートに存在する想定です。config/*.yaml（system_config.yaml 等）は validate_config でチェック対象となります。

---

## 開発・拡張のヒント

- 新しい監視チェックを追加する場合は MonitoringDB に必要な列を追加し、init_monitoring_db にマイグレーションコードを追記してください。
- AI モジュールは OpenAI の SDK をラップしており、テスト用に _call_openai_api をモックする設計になっています。ユニットテストではモックを活用してください。
- Portfolio / Position Sizing 関数群は純粋関数（副作用なし）で設計されているためユニットテストが容易です。

---

## ライセンス・貢献

（この README ではライセンス情報は含まれていません。実際のプロジェクトでは LICENSE ファイルを追加してください。）  
貢献する場合はプルリクエストを送付してください。大きな変更は事前に Issue で相談してください。

---

以上がこのコードベースに関する README の概要です。必要ならば、特定のモジュール（例: ExecutionEngine の使い方、AI 呼び出し例、DB スキーマの詳解）について詳しいドキュメントを追加します。どの部分の詳細を優先して欲しいか指示してください。