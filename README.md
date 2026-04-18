# KabuSys

日本株向けの自動売買システム（ライブラリ＋起動スクリプト群）。  
ポートフォリオ構築、シグナル生成・発注、監視、Paper Trading 検証、LLM を使ったニュース評価や市場レジーム判定などの機能を含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的を持つモジュール群と起動用スクリプトを含むプロジェクトです。

- 戦略（ファクター計算、特徴量探索）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- 発注エンジン（ExecutionEngine、注文管理、リスク管理、リコンサイル）
- 監視（System / Trade / Risk モニタ、Kill Switch、アラート）
- Paper Trading 用ログ & レポート生成
- ニュース NLP（OpenAI を用いた銘柄別センチメント評価）および市場レジーム判定

設計方針の例:
- DuckDB / SQLite を用いたデータ参照・永続化
- 環境変数 / .env による設定
- 起動スクリプトはプロセス優先度設定や PID / stop フラグ管理を含む
- LLM 呼び出しはフェイルセーフで、API 失敗時はフォールバック挙動を取る

---

## 主な機能一覧

- 環境設定ウィザード（対話式 .env 生成）: python -m kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml チェック）: python -m kabusys.validate_config
- Execution エンジン起動スクリプト（本番 / paper_trading 切替）: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
- Monitoring ポーリングループ起動: python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔上書き（デフォルト 60 秒）
- Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report
- ニュースセンチメント（OpenAI）: kabusys.ai.score_news（programmatic API）
- 市場レジーム判定（OpenAI + ETF MA 合成）: kabusys.ai.regime_detector.score_regime
- ポートフォリオ構築ユーティリティ（候補選定 / 等重・スコア重み / サイズ計算 / セクター制限）

---

## 必要要件（例）

- Python 3.10+ を想定
- 必須パッケージ（pip でインストール）:
  - duckdb
  - psutil
  - openai
- 任意 / 検証向け:
  - PyYAML（config/*.yaml の内容検証を行う場合）
- 標準ライブラリ: sqlite3 等

インストール例:
```bash
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをチェックアウトしてルートへ移動
2. Python 仮想環境を作成・有効化（推奨）
3. 依存パッケージをインストール（上記参照）
4. 環境変数設定（.env を作成）
   - 対話式ウィザードで作る:
     ```bash
     python -m kabusys.config_setup
     ```
   - 生成後、設定内容を検証:
     ```bash
     python -m kabusys.validate_config
     # 警告も厳密に扱いたい場合
     python -m kabusys.validate_config --strict
     ```
5. データディレクトリとログディレクトリの確認（必要に応じて手動作成）
   - デフォルト DB / ファイルパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - PID / flag: data/execution.pid, data/kill.flag, data/stop_requested.flag
   - ログディレクトリ: logs/（setup_logging が自動作成を試みます）

注意:
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- OpenAI を利用する機能を使う場合:
  - OPENAI_API_KEY を設定するか、関数呼び出しで渡す

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（default: development）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（ai 機能を使う場合）
- DUCKDB_PATH（default: data/kabusys.duckdb）
- SQLITE_PATH（monitoring 用、default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、default: data/paper_trading.db）
- LOG_LEVEL（default: INFO）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔、秒。default: 60）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）

---

## 使い方（コマンド例）

- .env 作成（対話式）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視ループ起動（monitoring）
  ```bash
  # デフォルトでは MONITOR_POLL_INTERVAL=60
  python -m kabusys.run_monitoring
  # 例: 30秒間隔にする
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  特徴:
  - 実行時にプロセス優先度を high に試行して設定します（権限が必要な場合あり）。
  - 停止は data/stop_requested.flag を作成することで行えます（既存フラグ検出でループを抜けます）。
  - 監視 DB は Settings.sqlite_path（環境にかかわらず本番 sqlite_path を使用）に接続して初期化します。

- Execution エンジン起動（発注）
  ```bash
  python -m kabusys.run_execution
  ```
  特徴:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB に記録（本番 DB と分離）。
  - 起動時に data/execution.pid を作成します（Settings.pid_file_path）。
  - 停止は data/stop_requested.flag を作成するか、エンジンが Kill Switch により停止されます。

- Paper Trading 検証レポート生成
  ```bash
  # デフォルト DB: data/paper_trading.db
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DBパスを直接指定
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI スコア / レジーム（プログラム API）
  - ニューススコア: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも api_key 引数を渡すか OPENAI_API_KEY 環境変数を設定する必要があります。

---

## 停止・Kill Switch

- 手動停止（実行スクリプト両方に適用）:
  - data/stop_requested.flag を作成すると、run_monitoring / run_execution はループ検知後に安全終了します。
- Kill Switch:
  - リスク条件（ドローダウン超過やポジション上限超過）などが検出されたときに data/kill.flag を書き込んで ExecutionEngine の停止を促します。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定している場合は自動クリアされる設定があります（本番では推奨されません）。

---

## ログ

- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一的に行われます。
- デフォルト: logs/<app_name>.log（日次ローテーション、30日分保持）
- コンソール出力は stdout に出力されます。

---

## トラブルシュートのヒント

- process priority の設定に失敗すると警告が出ます。権限が必要な場合があります。
- DuckDB / SQLite のファイルパスの親ディレクトリが存在しない場合、validate_config は警告しますが起動時に自動作成されることがあります。
- OpenAI 呼び出しは外部ネットワークに依存するため、API キー未設定やネットワークエラー時はフェイルセーフ（0.0 フォールバックやスキップ）となる箇所が多くあります。ログを参照してください。
- PyYAML がインストールされていないと config/*.yaml のパースチェックはスキップされます（validate_config が警告を出します）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_monitoring.py
    - run_execution.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
      - broker_factory.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/ (上記)
    - tools/
      - __init__.py
      - paper_verification_report.py
    - data/ (実行時に生成することがある。DB・PID・flag 等)
      - monitoring.db (default)
      - paper_trading.db (paper_trading 用)
      - execution.pid
      - stop_requested.flag
      - kill.flag
    - logs/ (ログ保存先、setup_logging が作成)

※ 上記はソース内の構成を抜粋・整理したものです。実際のリポジトリルートはプロジェクトルート（.git または pyproject.toml を基準）で認識されます。

---

## 開発者向けメモ

- 設定は .env / 環境変数を優先してロードするロジックがあります（kabusys.config）。
- モジュールは可能な限り純粋関数（DB参照を限定したり、外部副作用を最小化）で設計されています（ポートフォリオ計算や研究モジュールなど）。
- テスト時には OpenAI 呼び出し部分をモックすることを想定した設計（_call_openai_api の差し替え等）が行われています。
- monitoring_db.init_monitoring_db は既存 DB のマイグレーション（カラム追加）を試みるので、スキーマ変更時に互換性を保つためのロジックがあります。

---

もし README に追加してほしい詳細（例: .env.example の完全なサンプル、依存パッケージの exact requirements.txt、実稼働用の systemd unit ファイル例など）があれば指定してください。