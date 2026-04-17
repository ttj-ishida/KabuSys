# KabuSys — 日本株自動売買システム (README)

このリポジトリは日本株向けの自動売買システム「KabuSys」のコアライブラリです。  
本ドキュメントはコードベースから抽出した概観、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめた README です。

重要: この README はソースコード（src/kabusys 以下）を参照して作成しています。実運用前に必ず設定（.env、config/*.yaml 等）を確認してください。

---

## プロジェクト概要

KabuSys は次の主要コンポーネントを備えた日本株自動売買システムのライブラリ群です。

- ExecutionEngine（発注エンジン）
  - live（実口座） / paper_trading（ペーパートレード）をサポート
  - Broker クライアント抽象により本番とモックを切り替え可能
- Monitoring（監視）
  - システム状態、注文滞留、ドローダウン等の監視とアラート、Kill Switch
  - SQLite で監視ログを永続化
- Portfolio（銘柄選定・配分・ポジション決定）
  - 候補選出、等重/スコア加重、リスク調整、ポジションサイズ算出
- Research（ファクター計算・特徴量解析）
  - モメンタム、ボラティリティ、バリューなどのファクター計算
  - 将来リターンや IC（Information Coefficient）計算
- AI 支援（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価・市場レジーム判定
- ツール群
  - 設定ウィザード、設定検証、ペーパートレード検証レポート等

設計方針の一部:
- DuckDB を分析用 DB、SQLite を監視・発注ログ用に使用
- 実口座とペーパートレードの DB を分離
- ルックアヘッドバイアス防止（日時参照の扱いに注意）
- フェイルセーフ設計（API失敗時のフォールバック、部分失敗時の DB 保護）

---

## 機能一覧（抜粋）

- 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - config_setup: 対話式で .env を生成・更新
  - validate_config: 起動前に環境・YAML の検証（--strict で警告も失敗扱い）
- Execution
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV によるモード切替）
  - BrokerClientFactory により Mock と実ブローカを切り替え
  - Paper trading は data/paper_trading.db（デフォルト）に記録
- Monitoring
  - run_monitoring: SystemMonitor のポーリングループを実行（MONITOR_POLL_INTERVAL で間隔指定可）
  - MonitoringEngine: System / Trade / Risk の各モニタを統合しアラート・Kill Switch を評価
  - MonitoringDB: SQLite に system_status / trade_logs / positions / risk_logs / dashboard を作成・永続化
- Portfolio構築
  - 候補選出、各種重み付け、セクター上限適用、レジーム乗数、株数算出（丸めや利用可能現金に対するスケーリング含む）
- Research
  - DuckDB 接続からファクターを計算（モメンタム、ATR、PER/ROE 等）
  - IC、統計サマリー、将来リターン計算
- AI（外部 API 連携）
  - news_nlp.score_news: ニュースを LLM で評価し ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF MA と LLM マクロセンチメントを合成して日次レジーム判定
  - リトライ・バックオフやレスポンス検証を備える
- ツール
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL 判定レポートを生成

---

## 依存関係（主要）

最低限必要な外部パッケージ（プロジェクトに requirements.txt がない場合は下記をインストールしてください）:

- Python 3.9+（型注釈等の利用を前提）
- duckdb
- psutil
- openai
- PyYAML（config の YAML 検証時に必要、オプション）
- その他（標準ライブラリ）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を準備
   - 上記の通り venv を作成し依存パッケージをインストール

2. .env を作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは手動でプロジェクトルートに `.env` を作成する。主な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (ペーパートレード DB, デフォルト: data/paper_trading.db)
     - LOG_LEVEL (DEBUG|INFO|...)
     - OPENAI_API_KEY (AI 機能使用時に必要)
     - その他: LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用、任意）
   - 自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われる。自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

3. 設定検証
   - .env を作成したら検証を実行:
     ```
     python -m kabusys.validate_config
     ```
   - 警告も失敗扱いにする strict モード:
     ```
     python -m kabusys.validate_config --strict
     ```

4. データディレクトリの作成（必要に応じて）
   - デフォルトの DB パスは `data/` 以下を参照することが多いので、必要ならディレクトリを作成してください:
     ```
     mkdir -p data
     ```

---

## 使い方（コマンド & 環境変数）

- ExecutionEngine を起動
  - ローカル起動（KABUSYS_ENV に応じて paper/live が切替）
  ```
  python -m kabusys.run_execution
  ```
  - 注意: run_execution は起動時に PID ファイルを書き、data/stop_requested.flag があると起動をスキップします。KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使用され、ペーパーデータベース（PAPER_TRADING_SQLITE_PATH）に記録されます。

- Monitoring を起動
  - SystemMonitor をポーリングするスクリプト:
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）。
    - 例: 30秒間隔で実行:
      ```
      export MONITOR_POLL_INTERVAL=30
      python -m kabusys.run_monitoring
      ```
  - 停止フラグ: プロジェクトの data/stop_requested.flag が存在するとループは終了します。

- 設定ウィザード（.env の作成/更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report
  # 期間指定例:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を個別指定:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを指定可能（コマンドライン引数が優先）。

- AI 機能（プログラムとして呼び出す）
  - news_nlp.score_news(conn, target_date, api_key=None) — OpenAI API キーが必要（api_key 引数 または OPENAI_API_KEY 環境変数）
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、DB 内の raw_news / prices_daily 等のテーブルを参照します。

- Kill Switch / フラグファイル
  - KillSwitch は設定された flag_path（Settings.kill_flag_path、デフォルト: data/kill.flag）へ理由を記述して Execution エンジン停止を促します。
  - 手動で停止させたいときは kill.flag（書き込み）や stop_requested.flag（run_* スクリプトの停止トリガ）を利用します。

---

## 主な設定（Settings による環境変数一覧）

（コード src/kabusys/config.py に定義されている主要項目）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（任意）
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (instant | partial | never | reject) — ペーパートレードの約定挙動
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- CPU/MEM/DISK 閾値（CPU_THRESHOLD_PCT 等）
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL

.env の自動読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）を上位へ探索して `.env` と `.env.local` を読み込みます。
- OS 環境変数が優先されます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 開発・デバッグのヒント

- psutil を使うため、実行環境に依存する機能（プロセス優先度設定や CPU affinity）はパーミッションや OS により失敗する場合があります。エラーは警告として扱われ、起動は継続されます。
- DuckDB の SQL を用いた分析部分は多くの関数で SQL を直接記述しています。デバッグ時は DuckDB コンソールや簡易スクリプトでクエリを試すと良いです。
- AI 関連は外部APIに依存するため、テスト時は _call_openai_api をモックしてください（各モジュールにモック箇所のコメントがあります）。
- run_execution / run_monitoring は stop フラグや PID ファイルに注意して実行してください。

---

## ディレクトリ構成（主要ファイル・モジュール）

以下は src/kabusys 配下の主要モジュールです（抜粋）。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py            — .env 対話式ウィザード
    - validate_config.py         — 設定検証 CLI
    - run_execution.py           — ExecutionEngine 起動スクリプト
    - run_monitoring.py          — SystemMonitor ポーリングスクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py              — ニュース NLP スコアリング（OpenAI）
      - regime_detector.py       — 市場レジーム判定（OpenAI）
    - monitoring/
      - monitoring_db.py         — SQLite スキーマ + DB アクセス
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py         — （未表示の続きあり）
    - execution/                  — ExecutionEngine 周辺（order_manager 等）
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
      - execution_engine.py
      - broker_factory.py
      - order_record.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - utils/
      - process_priority.py
      - __init__.py
    - data/                       — 実行時生成される data/*.db やフラグファイルが入る想定（リポジトリ外）
- pyproject.toml / setup 等（プロジェクトルート; この README のルートに存在する想定）

（注）一部の実装ファイルは本 README のソース抜粋に含まれていませんが、上のツリーはコード内の import 構造から概観を再現しています。

---

## よく使うファイル / フラグ

- data/execution.pid — Execution の PID（Settings.pid_file_path）
- data/stop_requested.flag — run_* スクリプトの手動停止トリガ
- data/kill.flag — KillSwitch による ExecutionEngine 停止フラグ（Settings.kill_flag_path）
- data/monitoring.db — 監視ログ（Settings.sqlite_path）
- data/paper_trading.db — ペーパートレード DB（PAPER_TRADING_SQLITE_PATH）
- data/kabusys.duckdb — 分析用 DuckDB（DUCKDB_PATH）

---

## ライセンス・貢献

この README にはライセンス情報や貢献ガイドは含まれていません。実際のプロジェクトルートに LICENSE / CONTRIBUTING.md 等があればそちらを参照してください。

---

この README はコードの解説と利用ガイドを目的としています。運用や実運用パラメータ（特に本番口座での発注設定や Kill Switch の扱い）は慎重に確認・テストしてから使用してください。質問や追加で欲しい項目（例: より詳細な実行例、テスト手順、API ドキュメントなど）があれば教えてください。