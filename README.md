# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ＋起動スクリプト群）。  
このリポジトリは、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などの主要コンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたコンポーネント群です。

- 日次で銘柄のファクター計算・シグナル生成を行う研究モジュール（DuckDB を用いた過去価格・財務データ参照）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイジング、セクター制約・レジーム調整）
- 実際の発注を担う ExecutionEngine（paper_trading モードでのモックブローカー対応）
- システム / 注文 / リスク監視とアラート、Kill Switch による緊急停止
- ニュースを LLM に投げて銘柄別センチメントを算出する AI モジュール（OpenAI）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証等）
- ペーパートレード検証レポート出力ツール

設計方針の特徴:
- DuckDB + SQLite を併用（分析用 DuckDB、監視/注文ログ用 SQLite）
- 環境変数 / .env による設定（config_setup.py による対話式生成）
- 本番とペーパートレードを明確に分離（専用 DB）
- LLM 呼び出しはフェイルセーフ設計（API失敗はフォールバック）

---

## 主な機能一覧

- 実行（Execution）
  - ExecutionEngine の起動スクリプト（run_execution.py）
  - Paper trading（MockBroker）対応（KABUSYS_ENV=paper_trading）
  - 発注ログ / ポジション管理（SQLite）

- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - Kill Switch（条件により data/kill.flag を書き込み Execution を停止）
  - run_monitoring.py によるポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可能）

- ポートフォリオ構築（pure functions）
  - 候補選定、等金額・スコア加重の重み計算
  - ポジションサイズ計算（リスクベース、上限、単元株丸め、集約キャップ）
  - セクター上限適用、レジーム乗数

- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 接続で SQL 実行）
  - 将来リターン、IC（スピアマン）計算などの統計ユーティリティ

- AI（OpenAI を利用）
  - ニュース記事を LLM でスコアリングして ai_scores に保存（news_nlp）
  - マクロニュースと ETF MA を使った市場レジーム判定（regime_detector）

- ツール
  - 環境設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

- ユーティリティ
  - 統一ログ設定（kabusys.utils.logging_setup）
  - プロセス優先度 / CPU affinity（kabusys.utils.process_priority）
  - 環境変数自動ロード（.env / .env.local）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repo_url>
   - cd <repo_root>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 主要な依存（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（validate_config の YAML 検証時に利用）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt があればそれを利用してください:
    pip install -r requirements.txt）

4. 環境変数（.env）を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは手動で .env をルートに配置（.env には秘匿情報を含むため絶対に Git にコミットしない）

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit(1)）

6. データディレクトリ
   - デフォルトで使用されるパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログ: logs/
     - Kill/stop フラグ: data/kill.flag, data/stop_requested.flag
   - 必要なら事前にディレクトリを作成（多くのコードは自動作成を試みます）

注意: 本番環境で起動する前に .env の内容（特に KABUSYS_ENV=live / API キー / パスワード）を慎重に確認してください。

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

重要なオプション:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/…、デフォルト: INFO）
- OPENAI_API_KEY — OpenAI を利用する機能で必要
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

（config_setup.py で対話的に設定可能）

---

## 使い方（起動例）

- 環境確認（検証）
  - python -m kabusys.validate_config

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- ExecutionEngine（実行エンジン）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBroker を使用し、PAPER_TRADING_SQLITE_PATH に記録します
  - 起動時に data/stop_requested.flag が存在すれば起動せず終了します
  - 実行中に data/stop_requested.flag を作成すると安全に停止します
  - 実行時に data/execution.pid が作成されます

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 などでポーリング間隔を変更可能
  - 監視は常に本番用 sqlite_path を参照（環境にかかわらず監視 DB は同一）

- Paper Trading 検証レポートの生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI / レジーム判定（例）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=...)

ログ:
- setup_logging により logs/<app_name>.log に日次ローテーションで出力されます（logs/ ディレクトリ）

安全上の注意:
- KABUSYS_ENV=live での実行は実際に発注が行われます。各種保護（kill switch、リスクマネージャ等）が機能しますが、設定は十分に検証してください。
- data/kill.flag により ExecutionEngine に停止指令を出す仕組みがあります（KillSwitch）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定読み込みロジック
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py         — 統一ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity
  - execution/                 — 実行エンジン関連（Engine, BrokerFactory, OrderManager, RiskManager 等）
    - (多数の実装ファイル)
  - monitoring/
    - monitoring_db.py         — SQLite 永続層（監視ログ）
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - trade_monitor.py         — （TradeMonitor 実装が存在する前提）
    - alert_manager.py         — （アラート送信管理）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/                 — 監視関連（上記）
  - tools/
    - paper_verification_report.py
    - __init__.py

- data/                       — データファイル（DB・フラグ等、実行時に利用）
  - monitoring.db (デフォルト)
  - kabusys.duckdb (デフォルト)
  - paper_trading.db (ペーパートレード用)
  - kill.flag, stop_requested.flag, execution.pid など

- logs/                       — ログ出力先（デフォルト）

---

## 開発者向け補足

- DuckDB 接続を受け取り SQL を実行する実装が多く、テスト時はメモリ DB やテスト用ファイルを使用してください。
- AI モジュールは OpenAI SDK のエラー（429/5xx/Timeout 等）に対してリトライ実装が含まれますが、テスト時は API 呼び出しをモックすることを推奨します（関数単位で差し替え可能）。
- run_monitoring/run_execution は stop flag（data/stop_requested.flag）を監視して安全に停止します。CI や自動化ではこのファイルを用いて制御できます。
- validate_config は PyYAML が無い場合、YAML の内容検証をスキップします。YAML 検証を有効にするには PyYAML をインストールしてください。

---

もし README に追記したい具体的なコマンド例や systemd / Supervisor / Docker での運用例があれば教えてください。運用向けのサービス定義（systemd unit / コンテナ化）テンプレートも作成できます。