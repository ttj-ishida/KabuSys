# KabuSys

日本株自動売買システムの軽量なコンポーネント群。戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）やペーパートレード検証用ユーティリティなどを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

このリポジトリは以下の責務を持つモジュール群で構成されています。

- データ処理・研究（DuckDB を利用したファクター計算、将来リターン、特徴量解析）
- ポートフォリオ構築（候補選定・重み算出・ポジションサイズ計算・セクター制限）
- 発注処理（ExecutionEngine）：実際のブローカー通知 / MockBroker（ペーパートレード）対応
- 監視（Monitoring）：システムの稼働状況、注文ログ、リスク指標の定期記録と Kill Switch
- AI 補助（OpenAI を用いたニュース NLP / レジーム判定）
- ユーティリティ（.env ウィザード、設定検証、検証レポート生成 等）

設計方針として、ルックアヘッドバイアス防止（日時の直接参照を避ける）、フェイルセーフ（API障害時のフォールバック）、DuckDB/SQLite によるローカル永続化、モジュール分離によるテスト容易性が挙げられます。

---

## 主な機能一覧

- 環境設定ウィザード（.env 生成・更新）: python -m kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml の事前チェック）: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト（本番 / paper_trading を切替）: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録
- Monitoring 起動スクリプト（SystemMonitor のポーリング）: python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
- MonitoringEngine：System / Trade / Risk モニタをまとめて運用（run / run_once）
- Kill Switch：risk のしきい値超過時に data/kill.flag を書き込み ExecutionEngine を停止
- Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report
- 研究用モジュール: ファクター計算（momentum/value/volatility）、forward return、IC など
- AI モジュール: ニュースセンチメント（news_nlp）、レジーム判定（regime_detector）
- ロギングセットアップ（コンソール + 日次ローテーションファイル）

---

## 前提条件（環境）

- Python 3.9+
- 推奨パッケージ（pip install でインストール）
  - duckdb
  - psutil
  - openai
  - PyYAML（設定検証時に config/*.yaml パースを行う場合）
- OS 標準ライブラリ以外の利用は一部モジュールで必要になります（上記参照）。

例:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 必要パッケージのインストール
   - pip install -r requirements.txt
   - requirements.txt がない場合は上記の必須パッケージを個別にインストール

4. 環境変数設定 (.env) の作成（ウィザード推奨）
   - python -m kabusys.config_setup
     - 対話式で .env を生成できます（デフォルト: プロジェクトルート/.env）
   - 手動で作成する場合は .env.example を参考にしてください（リポジトリにある場合）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告を厳格に扱う場合は --strict を付与して exit(1) を確認できます

6. データディレクトリの作成
   - デフォルトでは data/ に SQLite / PID / フラグファイル等を配置します。必要なパーミッションを確認してください。

---

## 主要な環境変数（抜粋）

必須（実行に必要）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要なオプション:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時に使用）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR
- LOG_DIR: ログファイル出力先（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI を使用するモジュールで参照
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 本番での自動 kill.flag クリア（0/1。0 推奨）

注意:
- Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を監視 DB に使用する設計の箇所があります（意図的）。
- paper_trading モードでは発注処理が本番 DB と分離され、data/paper_trading.db に記録される設計です。

---

## 使い方（起動例）

- 環境変数を読み込んだ状態で ExecutionEngine を起動（通常はサービス化して実行）
  - python -m kabusys.run_execution
  - 動作中は data/execution.pid に PID を書き込む
  - 起動前に data/stop_requested.flag が存在すると起動を中止します

- Monitoring（SystemMonitor のポーリング）を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring で 30 秒間隔に変更可能
  - 停止は KeyboardInterrupt、またはプロジェクトルート/data/stop_requested.flag を作成して監視ループに停止指示できます

- Kill Switch（監視が書き込む）により ExecutionEngine を停止するには
  - data/kill.flag が書き込まれると Execution 側で検出して停止処理を行う設計
  - KillSwitch.clear() は起動時に kill.flag を自動クリアするオプションがあり得ますが、本番ではクリアを無効（0）推奨

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - --db オプションで別 DB を指定可能
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD

- .env の作成・更新（対話式）
  - python -m kabusys.config_setup

- 設定チェック
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで終了コード 1 を返す

---

## 運用上の注意

- ログ: デフォルトで logs/<app_name>.log に日次ローテーションで出力されます。LOG_DIR 環境変数で変更可能。
- PID / フラグファイル: data/ ディレクトリに PID や stop/kill フラグを置く設計です。サービス化する際はこれらのファイル操作に注意してください。
- データ鮮度: SystemMonitor は DuckDB の prices_daily テーブル等を参照してデータ鮮度を検査します。DuckDB ファイルの準備を忘れずに。
- OpenAI API: news_nlp / regime_detector は OPENAI_API_KEY を要求します。API 利用にはコストとレートリミットを考慮してください。失敗時は安全側のフォールバック（スコア 0.0 等）を行う実装です。
- テスト / 開発モード: KABUSYS_ENV=development や paper_trading を利用して本番 API への誤発注を防いでください。

---

## ディレクトリ構成（主要ファイル）

プロジェクトルート/src/kabusys を想定した抜粋:

- kabusys/
  - __init__.py
  - config.py                — 環境変数・.env 自動ロード・Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — ペーパートレード検証レポート
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI）
  - research/
    - __init__.py
    - factor_research.py     — momentum/value/volatility 等
    - feature_exploration.py — forward returns / IC / summary
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化 / 永続化層
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （注文監視、ファイル内にあり）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag の作成・管理
    - monitoring_engine.py   — 各 Monitor の統合
    - alert_manager.py       — （通知ロジック）
  - execution/
    - execution_engine.py    — ExecutionEngine（起動・セッション管理）
    - broker_factory.py      — Broker クライアント生成（Mock と実ブローカー）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - monitoring/
    - monitoring_db.py       — （上記）
  - utils/
    - logging_setup.py       — 共通ログ設定
    - process_priority.py    — プロセス優先度・CPU affinity 設定
    - __init__.py

（実際のファイル数・配置はリポジトリ内を参照してください。上は主要モジュールの抜粋です）

---

## 開発者向け補足

- DuckDB を用いた研究モジュールは SQL と Python を組み合わせて実装されています。prices_daily / raw_financials / raw_news 等のテーブルが前提です。
- monitoring_db.init_monitoring_db() は冪等でテーブルとインデックスを作成し、必要ならマイグレーション（カラム追加）も行います。
- ローカルでの検証は paper_trading モードとペーパーデータベースを利用することで実際の発注 API に影響を与えずに行えます。
- OpenAI 呼び出し箇所は再試行（指数バックオフ）や厳格なレスポンス検証を行うよう実装されています。テスト時は各 _call_openai_api 関数をモックすることを想定しています。

---

必要であれば、README に含める「サンプル .env」「サービス化 (systemd) の例」「追加のコマンド一覧」なども作成します。どの情報を優先して追加しますか？