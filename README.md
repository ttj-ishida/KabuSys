# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買・研究・監視を目的としたモジュール群です。  
README はプロジェクトの概要、機能一覧、セットアップ手順、使い方および主要ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は以下を目的とした Python ベースのシステムです。

- 市場データを用いたファクター計算・研究（DuckDB を利用）
- ポートフォリオ構築（候補選定・重み算出・ポジションサイズ計算）
- 発注エンジン（本番・ペーパートレードを区別）
- 実行系の監視・アラートおよび自動停止（Kill Switch）
- ニュース NLP を利用した AI スコアリング（OpenAI）
- ペーパートレードの検証レポート生成

設計上の特徴：

- DB（DuckDB / SQLite）を分離して分析と監視・発注履歴を管理
- 本番とペーパートレードの DB は分離（KABUSYS_ENV=paper_trading の場合）
- .env 自動読み込み（プロジェクトルートに基づく）
- 実行スクリプトはプロセス優先度設定、PID/停止フラグ等を扱う

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config / config_setup / validate_config
  - 環境変数管理、.env 作成ウィザード、起動前検証ツール
- kabusys.execution
  - ExecutionEngine（発注処理）・OrderManager・RiskManager など
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
- kabusys.monitoring
  - SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine
  - SQLite に監視ログを永続化（monitoring_db）
- kabusys.portfolio
  - 候補選定（select_candidates）、重み計算（equal/score）、ポジションサイズ計算
  - セクターキャップ、レジーム乗数適用
- kabusys.research
  - ファクター計算（momentum/value/volatility）、将来リターン、IC 計算、統計サマリ
- kabusys.ai
  - news_nlp: OpenAI を用いたニュースのセンチメントスコアリング
  - regime_detector: ETF とマクロニュースを用いた市場レジーム判定
- kabusys.tools
  - paper_verification_report: ペーパートレード検証レポート生成

その他ユーティリティ：
- ログ設定（kabusys.utils.logging_setup）
- プロセス優先度設定（kabusys.utils.process_priority）
- DB 初期化・マイグレーション（monitoring_db）

---

## セットアップ手順

前提
- Python 3.10+（typing の union 表記や注釈に依存）
- システムにより追加ライブラリ（psutil, duckdb, openai 等）が必要

推奨的なセットアップ手順：

1. リポジトリをクローンして作業ディレクトリへ移動
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell/CMD)
   ```

3. 必要パッケージをインストール（例）
   ```bash
   pip install -r requirements.txt
   ```
   requirements.txt がない場合は最低限以下をインストールしてください：
   - duckdb
   - psutil
   - openai (AI 機能を使う場合)
   - PyYAML（validate_config で YAML 検証を行う場合に推奨）
   例：
   ```bash
   pip install duckdb psutil openai pyyaml
   ```

4. ディレクトリ作成（デフォルトの DB / ログ保存先）
   ```bash
   mkdir -p data logs
   ```

5. 初回設定：対話式ウィザードで .env を作成
   ```bash
   python -m kabusys.config_setup
   ```
   生成した .env の値を確認後、設定検証を行います。

6. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告も厳格にチェックする場合:
   python -m kabusys.validate_config --strict
   ```

注意：
- 自動ロードはデフォルトで有効（プロジェクトルートの .env / .env.local を読み込みます）。無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env は絶対に Git にコミットしないでください（config_setup 生成ヘッダにも記載あり）。

---

## 環境変数（主なもの）

- 必須:
  - JQUANTS_REFRESH_TOKEN - J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD - kabuステーション API パスワード

- 重要な設定とデフォルト:
  - KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト: development
    - paper_trading の場合、Execution は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使う
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag
  - KILL_FLAG_CLEAR_ON_START: 0（起動時に kill.flag を自動でクリアするか。1 は開発用）
  - PAPER_FILL_MODE: instant|partial|never|reject（paper_trading の注文模擬挙動）
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒）。run_monitoring で使用（デフォルト 60）

その他、OpenAI を使う機能では OPENAI_API_KEY が必要になります。

---

## 使い方（主な CLI / モジュール）

1. 実行エンジン（ExecutionEngine）の起動
   - 本番・ペーパー共通エントリ:
   ```bash
   python -m kabusys.run_execution
   ```
   - 特記事項:
     - 起動時にプロセス優先度を high に設定します。
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します。
     - 実行中は data/stop_requested.flag の存在をポーリングして停止を検知します。
     - Kill Switch による停止は data/kill.flag が書かれることで発動します（kill_switch モジュール）。

2. 監視ループの起動
   ```bash
   python -m kabusys.run_monitoring
   ```
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒、デフォルト 60）。
   - 監視は監視用 SQLite（Settings.sqlite_path）を使用。Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を参照します（監視ログを本番 DB に集約したい設計）。
   - 停止は data/stop_requested.flag を作成することでループが終了します。

3. .env ウィザード（対話式）
   ```bash
   python -m kabusys.config_setup
   ```

4. 設定検証
   ```bash
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict
   ```

5. ペーパートレード検証レポート（ツール）
   ```bash
   python -m kabusys.tools.paper_verification_report
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   # DB を明示する場合:
   python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
   ```

6. AI / 研究用関数（Python API）
   - DuckDB 接続を開いてモジュール関数を呼び出す例：
   ```python
   import duckdb
   from datetime import date
   from kabusys.research import calc_momentum

   conn = duckdb.connect("data/kabusys.duckdb")
   result = calc_momentum(conn, date(2026, 4, 1))
   ```
   - ニュース NLP（OpenAI）が必要な機能の呼び出し例：
   ```python
   from kabusys.ai import score_news
   # conn: DuckDB connection, target_date: datetime.date, api_key optional
   n = score_news(conn, target_date, api_key="sk-...")
   ```

7. 停止 / Kill フラグの使い分け
   - data/stop_requested.flag:
     - run_execution / run_monitoring がポーリングして検出すると優雅にシャットダウンします。
   - data/kill.flag:
     - KillSwitch が条件を満たした場合に書かれ、ExecutionEngine 側で停止を誘発します（本番保護用）。

---

## 起動時の挙動・注意点

- プロセス優先度は起動直後に set_process_priority("high") に設定されます（プラットフォーム依存。設定失敗時は警告）。
- logging は共通ユーティリティ setup_logging により stdout と日次ローテーションファイル（logs/<app_name>.log）へ出力します。
- monitoring の DB 初期化は init_monitoring_db により冪等で実行され、必要なら ALTER TABLE による簡易マイグレーションを行います。
- AI 関連機能は OpenAI API キー（OPENAI_API_KEY）を要求します。API 呼び出しはリトライロジックおよびフェイルセーフ（失敗時に 0 などでフォールバック）を実装しています。
- データの鮮度チェックやリスクアラートは monitoring 側で定期的に評価します。必要に応じて alert_manager による通知が送られます（LINE 等の設定は .env の設定に依存）。

---

## ディレクトリ構成

以下は主要ファイル／ディレクトリの抜粋です（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数読み込み・Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースセンチメント（OpenAI）
    - regime_detector.py      — 市場レジーム判定（ETF + マクロ）
  - monitoring/
    - monitoring_db.py        — SQLite schema & CRUD
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py        — （ファイル内に実装あり）
    - kill_switch.py
    - alert_manager.py        — （アラート送信ロジック）
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - data/                     — （デフォルトの保存先: data/*.db, flag ファイルなど）
  - logs/                     — ログ保存（setup_logging により作成される）

注：上記はソース内のコメント / 実装に基づく抜粋です。リポジトリ全体の詳細は実際のファイルを参照してください。

---

## よくある質問・トラブルシューティング

- Q: .env を読み込まない／別の .env を読み込みたい  
  A: 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してから必要な .env を手動で読み込むか、config_setup で指定したパスで作成してください。.env.local は .env を上書きする目的で使用できます。

- Q: run_monitoring が本番 DB を参照してしまう（テスト環境に影響しないか不安）  
  A: 設計上、Monitoring は Settings.sqlite_path（本番）を使用します。テスト目的でモニタリングを分離したい場合は Settings を差し替えるか、環境変数 SQLITE_PATH を一時的に別ファイルへ向けてください。

- Q: OpenAI 呼び出しでエラーが出る／API キーがない  
  A: OPENAI_API_KEY を .env に設定してください。AI 機能は API 通信に依存するため、API 欠如時は関連機能はエラーまたはフォールバック動作になります（score_news はキー未設定で ValueError を送出）。

---

## 開発メモ / 参考

- DB マイグレーションは簡易に SQL を追加している箇所があります（monitoring_db.init_monitoring_db）。本格的な移行が必要な場合は専用マイグレーション管理を導入することを推奨します。
- ログや PID / flag を監視するために systemd / supervisor 等でサービス化することを想定しています。run_* スクリプトはデーモン化せずフォアグラウンドで動作します。
- AI や外部 API 呼び出しは冪等性や部分失敗時の保護（既存スコアを不必要に消さない等）を意識して実装されていますが、運用時は十分に検証してください。

---

必要があれば README に含める詳細（systemd ユニットの例、より詳しい設定例、各モジュールの API 使用例など）を追加で作成します。どの情報を追加したいか教えてください。