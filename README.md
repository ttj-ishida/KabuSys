# KabuSys

日本株自動売買システム（KabuSys）のコードベース README。  
このドキュメントはリポジトリ内のモジュール群（監視、実行エンジン、ポートフォリオ構築、リサーチ、AI 補助など）の概要、セットアップ、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を支援するシステム群です。主要コンポーネントは次のとおりです。

- ExecutionEngine：発注ロジック・注文管理・リスク管理を司る実行エンジン（本番 / ペーパートレード対応）。
- Monitoring：システム状態、注文ログ、リスク監視を行い、必要時にキルスイッチ（停止フラグ）を作動。
- Portfolio：銘柄選定、配分、ポジションサイズ算出等の純粋関数群（PortfolioConstruction.md に準拠）。
- Research：DuckDB を用いたファクター計算や特徴量探索（ファクター計算、IC 等）。
- AI 補助：ニュースを LLM（OpenAI）でスコアリングし、market_regime の判定などに活用。
- ユーティリティ類：ログ設定、プロセス優先度、設定読み込みウィザード、設定検証ツール等。

設計上の特徴：
- 本番（live）とペーパートレード（paper_trading）で DB を分離。
- DuckDB を分析用 DB、SQLite を監視 / 取引ログ用 DB として利用。
- OpenAI を用いた NLP 処理は API キー必須だが、失敗時はフェイルセーフにより継続する実装。

---

## 主な機能一覧

- 実行エンジンの起動スクリプト（run_execution.py）
  - KABUSYS_ENV による paper_trading / live 切替
  - BrokerClientFactory によるブローカークライアント抽象化
  - RiskManager、OrderManager、Reconciler 等による発注・リスク制御
- 監視ループ（run_monitoring.py / MonitoringEngine）
  - CPU / メモリ / ディスク / プロセスの健全性監視
  - 注文の滞留チェック・約定異常検出
  - リスク監視（ドローダウン、ポジション上限）
  - Kill Switch（data/kill.flag）による安全停止
- 設定管理 CLI
  - config_setup.py：.env の対話的作成/更新ウィザード
  - validate_config.py：.env と config/*.yaml の事前検証
- Paper Trading 検証ツール
  - tools/paper_verification_report.py：ペーパートレード DB から検証レポート生成
- AI モジュール
  - ai/news_nlp.py：ニュースを LLM でセンチメント評価して ai_scores に書き込み
  - ai/regime_detector.py：ETF の MA200 とマクロニュースで市場レジーム判定
- Research
  - research/factor_research.py：モメンタム、ボラティリティ、バリュー等のファクター計算
  - research/feature_exploration.py：将来リターン、IC、統計サマリー等
- Logging / Utilities
  - utils/logging_setup.py：一貫したログ出力（stdout + 日次ファイルローテーション）
  - utils/process_priority.py：プロセス優先度 / CPU affinity 設定

---

## 必要条件（推奨）

- Python 3.10 以上（PEP 604 の型記述を使用しているため）
- SQLite（標準ライブラリ）
- 必須 Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - （推奨）PyYAML（config YAML 検証に使用）
- その他：ネットワーク接続（kabuステーション API / OpenAI 利用時）

※ 実行環境により追加パッケージが必要な場合があります。requirements.txt を用意している場合はそちらを利用してください。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境の作成（任意だが推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージのインストール
   - 例（pip で個別インストール）:
     ```
     pip install duckdb psutil openai
     pip install pyyaml  # optional: validate_config の YAML 検証用
     ```
   - もし requirements.txt があれば:
     ```
     pip install -r requirements.txt
     ```

4. 環境変数の準備（.env）
   - 対話ウィザードを使うと簡単です：
     ```
     python -m kabusys.config_setup
     ```
   - 必須変数（最低限設定が必要）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な任意/デフォルト値
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード専用）
     - OPENAI_API_KEY: OpenAI API を利用する場合は設定

5. 設定検証（起動前確認）
   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```

---

## 実行・使い方

以下は主要スクリプトの起動方法とポイントです。

- ExecutionEngine を起動
  - 本番 / ペーパーは KABUSYS_ENV に依存（.env で設定）
  ```
  python -m kabusys.run_execution
  ```
  - 起動時に data/stop_requested.flag が存在すると起動を中止します。
  - 実行中は data/execution.pid に PID が書かれます。

- Monitoring を起動
  - 監視ループを起動します（デフォルト 60 秒間隔）
  - MONITOR_POLL_INTERVAL 環境変数で秒数を上書き可能（例: 30）
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - stop フラグ（data/stop_requested.flag）で監視ループの終了ができます。

- .env の対話的作成 / 更新
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report
  # 期間指定例
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定例
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI モジュール（プログラム内部経由で利用）
  - news_nlp.score_news(conn, target_date, api_key=None) を呼んでニューススコアを ai_scores に保存
  - regime_detector.score_regime(conn, target_date, api_key=None) で market_regime を更新
  - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定

- 停止・Kill Switch
  - 実行エンジンを強制停止させたい場合は監視側が data/kill.flag を書き込む仕組み
  - 管理者が手動で停止フラグを作る場合は kill.flag の作成（path は Settings.kill_flag_path で上書き可）
  - stop_requested.flag（run_execution/run_monitoring が監視）を作ると監視/実行スクリプトが安全に終了します。

---

## 環境変数（主要）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 重要 / よく使う
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
  - OPENAI_API_KEY — OpenAI を使う場合必須
  - LOG_LEVEL — DEBUG/INFO/…（デフォルト INFO）
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用）
  - PAPER_FILL_MODE — ペーパートレードの埋め方 ("instant" | "partial" | "never" | "reject")（デフォルト "instant"）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアするか（開発用）

validate_config.py により起動前に設定をチェックできます。

---

## ディレクトリ構成（主要ファイルの説明）

（リポジトリの src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込みと Settings クラス
  - config_setup.py
    - .env を対話式に生成するウィザード CLI
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（本番 / ペーパー分岐）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - execution/  (発注関連；主要クラス参照があるが詳細は各ファイルを参照)
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - monitoring/
    - monitoring_db.py
      - SQLite スキーマ初期化と永続化 API
    - system_monitor.py
      - CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py
      - 注文ログの異常検出（滞留・価格異常など）
    - risk_monitor.py
      - ドローダウン・ポジション上限監視
    - kill_switch.py
      - kill.flag の読み書き／評価
    - monitoring_engine.py
      - 各 Monitor を束ねるエンジン
    - alert_manager.py
      - （アラート送信管理）
  - portfolio/
    - portfolio_builder.py
      - 候補選定・重み計算
    - risk_adjustment.py
      - セクター上限・レジーム乗数
    - position_sizing.py
      - 発注株数算出（lot 単位丸め・aggregate cap 等）
  - research/
    - factor_research.py
      - Momentum / Volatility / Value 等のファクター計算（DuckDB ベース）
    - feature_exploration.py
      - 将来リターン、IC、統計サマリー等
  - ai/
    - news_nlp.py
      - OpenAI を用いたニュースセンチメント評価
    - regime_detector.py
      - ma200 とマクロニュースで市場レジーム判定
  - tools/
    - paper_verification_report.py
      - ペーパートレード DB から検証レポートを生成
  - utils/
    - logging_setup.py
      - 一貫したログ設定ユーティリティ
    - process_priority.py
      - プロセス優先度・CPU affinity 設定ユーティリティ

---

## 運用上の注意・設計メモ

- DB 分離
  - paper_trading は paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離されます。
- ログ
  - logging_setup.setup_logging を各スクリプトが呼び出して統一的にログを出力します（stdout と日次ローテートファイル）。
- Kill Switch / Stop フラグ
  - 実行制御はファイルベース（data/kill.flag, data/stop_requested.flag）。運用ではこれらファイルの作成・削除を慎重に扱ってください。
- OpenAI 利用
  - news_nlp / regime_detector は OpenAI API を使います。API キーを正しく管理し、モデル（デフォルト gpt-4o-mini）やレート制限に注意してください。
  - LLM 呼び出しはリトライ・バックオフ実装がありますが、外部依存なので失敗時のフォールバック（スコア 0.0 等）を設けています。
- 可搬性
  - process_priority 等では Windows / POSIX の差を吸収していますが、権限不足により設定できない場合は警告を出してスキップします。

---

## 開発・拡張ヒント

- Research 系関数は DuckDB 接続を受け取る純粋関数群です。ローカルで DuckDB にデータをインポートし、関数単体のユニットテストを作ると解析が楽です。
- Portfolio 系は純粋関数で副作用がないため、単体テストの作成が容易です。
- AI モジュールの外部 API 呼び出し部分は個別にモック化可能（各モジュールは API 呼び出し wrapper を分離しているため、テストで差し替えやすくなっています）。

---

README にはプロジェクトの全側面をカバーしましたが、個々のモジュールの詳細（クラス、引数、返り値など）は各ファイルのドキュメンテーション文字列を参照してください。追加で API ドキュメントや運用手順（デプロイ、サービス化、cron/systemd 例）が必要であれば作成します。