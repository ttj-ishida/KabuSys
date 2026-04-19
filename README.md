# KabuSys

日本株の自動売買システムのコアライブラリ群です。バックエンドの実行エンジン、監視・アラート、ポートフォリオ構築、リサーチ（ファクター計算）および AI（ニュース NLP / レジーム判定）などの機能を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

このリポジトリは以下の責務を持つモジュールで構成されています。

- ExecutionEngine: 発注・リスク管理・注文管理を統括する実行エンジン（run_execution.py）。
- Monitoring: システム状態、取引/注文の監視、Kill Switch による自動停止を行う（run_monitoring.py）。
- Portfolio: 銘柄選定・重み付け・株数決定・リスク調整の純粋関数群。
- Research: DuckDB を用いたファクター計算・特徴量探索（モメンタム・ボラティリティ・バリュー等）。
- AI: ニュースのセンチメントスコア付与（OpenAI）や市場レジーム判定。
- Tools: ペーパートレード検証レポートなどのユーティリティスクリプト。
- Utils: ロギング設定、プロセス優先度設定など運用ユーティリティ。
- 設定管理: .env の対話式ウィザード（config_setup.py）と設定検証 CLI（validate_config.py）。

設計上のポイント:
- .env を使った環境変数管理（自動ロード機能あり）。
- paper_trading 環境では発注はモック化され、DB は専用の paper_trading.db に保存して本番 DB と分離。
- DuckDB を分析用 DB、SQLite を監視・発注ログ用に使用。
- OpenAI を利用する機能は API キーで保護（環境変数 OPENAI_API_KEY）。

---

## 主な機能一覧

- 実行エンジン起動（run_execution.py）
  - 本番 / ペーパートレード切り替え（KABUSYS_ENV）
  - BrokerClientFactory によるブローカークライアント抽象化
  - リスク管理、注文管理、reconciliation（照合）

- 監視サービス（run_monitoring.py）
  - CPU / メモリ / ディスク / 実行プロセスの監視
  - 取引・注文の滞留・約定異常監視
  - Kill Switch による自動停止（data/kill.flag）
  - ポーリング間隔を環境変数で上書き可能（MONITOR_POLL_INTERVAL）

- ポートフォリオ構築
  - 候補選定、等重・スコア重み、リスクベースのポジションサイズ計算
  - セクターキャップ適用、レジーム乗数

- リサーチ（DuckDB ベース）
  - モメンタム / ボラティリティ / バリュー計算
  - 将来リターン計算、IC（Information Coefficient）などの統計解析ユーティリティ

- AI（OpenAI）
  - ニュース記事の銘柄別センチメントスコア化（ai_scores テーブルへ書込）
  - マクロニュース + ETF MA200 による市場レジーム判定（market_regime テーブル）

- 運用ツール
  - .env 対話式生成ウィザード（config_setup）
  - 起動前の設定検証（validate_config）
  - Paper Trading 検証レポート生成ツール（paper_verification_report）

---

## セットアップ手順（クイックスタート）

前提:
- Python 3.9+（環境に合わせて適切なバージョンを利用）
- システム依存ライブラリ: psutil, duckdb, openai（AI機能利用時）、PyYAML（設定 YAML 検証に必要）

1. リポジトリ取得・仮想環境作成
   - git clone ...
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール（例）
   - pip install -r requirements.txt
   - requirements.txt がない場合は最低限次を入れてください:
     - pip install psutil duckdb openai

   ※ PyYAML は設定ファイルのパース検証を行いたい場合に必要:
   - pip install pyyaml

3. 環境変数設定（.env 作成）
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI を使う機能を利用する場合（任意だが必要な機能あり）

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い

5. 初回起動前にログ・データディレクトリを確認
   - デフォルト DB / ログ:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログディレクトリ: logs/
   - ログは自動作成されますがパーミッションなどに注意

---

## 使い方（起動 / 実行例）

- 監視プロセス起動
  - MONITOR_POLL_INTERVAL でポーリング間隔を秒指定可能（デフォルト 60 秒）
  - python -m kabusys.run_monitoring
  - 監視は monitoring DB（Settings.sqlite_path）を使用（KABUSYS_ENV に依存せず本番 sqlite_path を使用）

- 実行エンジン起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合:
    - MockBrokerClient を使用して発注はモック化され、データは data/paper_trading.db に保存（本番 DB と分離）
  - 起動時に data/execution.pid を生成・PIDを管理します
  - 停止：data/stop_requested.flag を作成するとループが終了します（run_monitoring も同様に stop_requested.flag を監視）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを直接指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- .env 対話式生成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- AI スコア算出 / レジーム判定（コード API）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
  - これらは DuckDB 接続を受け取り DB を読み書きします（OPENAI_API_KEY が必要）

---

## 主要な環境変数

- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring 用）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする（1=クリア、0=クリアしない。production では 0 推奨）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）

---

## 停止・Kill Switch に関する運用メモ

- 強制停止シグナル（ExecutionEngine を停止するために監視側が書き込むフラグ）
  - data/kill.flag: KillSwitch により作成される（存在すればエンジンが停止するトリガー）
  - KillSwitch は条件（ドローダウン超過、ポジション上限超過等）を満たすと flag を書きます
- 手動で即時停止したい場合:
  - data/stop_requested.flag を作成すると run_execution / run_monitoring のループが終了します
- 起動時の自動クリア:
  - KILL_FLAG_CLEAR_ON_START=1 を設定するとエンジン起動時に kill.flag が自動で削除されます（本番では推奨されません）

---

## ロギング

- ログ設定は kabusys.utils.logging_setup.setup_logging を使用して統一されます。
- 出力先:
  - コンソール（stdout）
  - 日次ローテーションファイル: logs/<app_name>.log（デフォルト、30 日分保持）
- ログレベルやログディレクトリは環境変数で制御可能（LOG_LEVEL, LOG_DIR）

---

## ディレクトリ構成（主要ファイル）

以下はソースディレクトリ（src/kabusys）の要約ツリーです（主要ファイルのみ）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度設定
  - execution/                — 実行エンジン関連（Engine, OrderManager, BrokerFactory 等）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py              — ニュース NLP（OpenAI）
    - regime_detector.py      — 市場レジーム判定（OpenAI + ETF MA200）
  - data/                     — ランタイム生成: DB / PID / フラグファイル 等（既定）
  - tools/
    - paper_verification_report.py

（上記はリポジトリの一部抜粋です。詳細はソースを参照してください）

---

## 運用上の注意点 / よくある質問

- paper_trading は本番 DB を汚さない設計:
  - KABUSYS_ENV=paper_trading の場合、Execution は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。
  - Monitoring は環境に関係なく本番用 sqlite_path を使用する点に注意してください（監視は本番 DB を直接参照する想定）。

- OpenAI を使う機能:
  - OPENAI_API_KEY を指定してください。API 呼び出しは失敗時にリトライやフェイルセーフ（スコア 0 など）を行う実装ですが、APIキー未設定では例外になります。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等で必要な列がなければ ALTER TABLE で追加します（例: peak_value, latency_ms）。

- ログディレクトリ/ファイル作成に失敗した場合:
  - logging_setup は作成に失敗した際にファイルハンドラをスキップし、コンソール出力のみで継続します。

- プロセス優先度設定:
  - set_process_priority("high") を用いて起動直後に優先度を上げますが、権限がない環境では警告が出てスキップされます。

---

## 開発 / 貢献

- コードを読む際は各モジュールの docstring を参照してください（関数単位で設計意図・引数・戻り値が記載されています）。
- テストや CI の設定はこの README に含まれていません。まずはローカルで .env を用意して validate_config を実行し、run_monitoring / run_execution を試してください。

---

必要であれば、README に「環境変数の完全一覧」や「よく使う SQL サンプル」「開発時のデバッグ手順」等を追加できます。どの情報を追加したいか指示してください。