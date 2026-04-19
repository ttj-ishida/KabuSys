# KabuSys

日本株向けの自動売買システム（ライブラリ & 実行スクリプト群）。  
このリポジトリは取引エンジン、監視、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などの主要コンポーネントを含みます。

主な対象:
- ローカル開発 / ペーパートレード環境
- 本番（live）環境に向けた監視・キルスイッチ機能
- DuckDB / SQLite を用いた時系列分析とログ永続化

バージョン: 0.1.0

---

## 機能一覧

- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレード（MockBroker）に対応
  - リスク管理（RiskManager）、オーダー管理、照合（Reconciler）等の統合
- Monitoring（監視）
  - SystemMonitor（CPU/メモリ/ディスク・データ鮮度・プロセス監視）
  - TradeMonitor / RiskMonitor（注文の滞留・成立異常・ドローダウン監視）
  - KillSwitch による停止シグナル発行（data/kill.flag）
  - 監視ログは SQLite（monitoring.db）へ永続化
- Portfolio モジュール（純粋関数群）
  - 候補選定、重み計算、ポジションサイズ決定、セクター制限、レジーム乗数
- Research（ファクター計算・特徴量解析）
  - Momentum/Volatility/Value ファクター、将来リターン、IC、統計サマリー等
  - DuckDB を用いた高速処理
- AI モジュール
  - news_nlp: ニュース記事を OpenAI（gpt-4o-mini 等）でスコア化し ai_scores へ保存
  - regime_detector: ETF の MA とマクロニュースを組み合わせて市場レジーム判定
- ツール
  - 環境設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）
- ログ管理ユーティリティ（logs/<app>.log、日次ローテーション）
- プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 事前準備 / セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate.bat  # Windows
   ```

3. 依存パッケージをインストール  
   （requirements.txt がある場合はそれを使ってください。ない場合は下記の主要依存をインストール）
   ```
   pip install duckdb psutil openai
   # 監視・設定検証で YAML を使う場合:
   pip install pyyaml
   ```

4. .env の作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは .env を生成します。手動で設定する場合は .env.example を参考にしてください。

   必須環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   主要な環境変数（デフォルトや説明）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - DUCKDB_PATH: data/kabusys.duckdb
   - SQLITE_PATH: data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
   - LOG_LEVEL: INFO / DEBUG / ...
   - OPENAI_API_KEY: OpenAI を使う場合に必要
   - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

5. 設定の検証（任意だが推奨）
   ```
   python -m kabusys.validate_config
   # 警告も FAIL として扱いたい場合:
   python -m kabusys.validate_config --strict
   ```

6. 必要に応じてディレクトリを作成（実行時に自動作成される場合がありますが、明示的に用意しておくと権限周りで安全です）
   ```
   mkdir -p data logs
   ```

---

## 使い方（主要コマンド）

- ExecutionEngine（取引エンジン）を起動
  - 本番 / 開発 / paper_trading は KABUSYS_ENV で切り替え
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH／data/paper_trading.db）に記録されます。
  - 実行中は data/execution.pid ファイル（デフォルト）に PID が書き込まれます。
  - 停止方法:
    - プロセス側を自然終了（Ctrl-C）、あるいは kill.flag による外部停止（KillSwitch）、または stop フラグ（data/stop_requested.flag）で監視ループを止める仕組みがあります。

- Monitoring を起動（監視ループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は常に本番 sqlite_path を使用して監視テーブルへ書き込みます（環境に依らず）。
  - 停止方法:
    - data/stop_requested.flag を作成するとループは検知して終了します。
    - kill.flag（data/kill.flag）は ExecutionEngine に対する停止シグナルとして KillSwitch が書き込みます。

- .env の自動生成／編集
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- ライブラリ的に AI / リサーチ機能を呼ぶ
  - ニューススコア付与:
    ```py
    from kabusys.ai import score_news
    # duckdb_conn: duckdb connection, target_date: datetime.date, api_key: str
    score_news(duckdb_conn, target_date, api_key="...")
    ```
  - レジーム判定:
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")
    ```

---

## 監視・停止関連ファイル

- data/kill.flag
  - KillSwitch が起動条件を満たしたときに書き込まれるファイル。存在すると ExecutionEngine に停止指示を与えます。
  - 手動で削除するか、起動時に KILL_FLAG_CLEAR_ON_START=1 を設定するとクリアされます（本番では推奨されません）。

- data/stop_requested.flag
  - run_monitoring / run_execution のループ側が存在をチェックして終了します。運用上の安全停止に使用。

- data/execution.pid
  - ExecutionEngine が PID を書き込むために使用します（プロセス監視などに利用）。

---

## ロギング

- 共通ロギング設定は kabusys.utils.logging_setup.setup_logging を経由して行われます。
- デフォルトログディレクトリ: logs/
- 各アプリケーション別ログファイル: logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）
- ローテーション: 日次、30 日保持
- 環境変数:
  - LOG_LEVEL（デフォルト: INFO）
  - LOG_DIR（デフォルト: logs/）

---

## 主な設定項目 / 環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能利用時に必要)
- KABUSYS_ENV: development | paper_trading | live
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PAPER_FILL_MODE: instant | partial | never | reject (paper_trading の挙動)
- LOG_LEVEL, LOG_DIR
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）

---

## ディレクトリ構成（主要ファイルのみ）

src/
  kabusys/
    __init__.py
    config.py                     # 環境変数・設定管理
    config_setup.py               # .env 対話式ウィザード
    validate_config.py            # 設定検証 CLI
    run_execution.py              # ExecutionEngine 起動スクリプト
    run_monitoring.py             # Monitoring 起動スクリプト

    ai/
      __init__.py
      news_nlp.py                 # ニュース NLP スコアリング
      regime_detector.py          # 市場レジーム判定

    monitoring/
      monitoring_db.py            # SQLite 永続化層（監視ログ）
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      monitoring_engine.py
      kill_switch.py
      alert_manager.py            # （アラート送信ロジック、LINE 等）

    execution/
      broker_factory.py
      execution_engine.py
      order_manager.py
      order_repository.py
      reconciler.py
      risk_manager.py

    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
      __init__.py

    research/
      factor_research.py
      feature_exploration.py
      __init__.py

    tools/
      __init__.py
      paper_verification_report.py

    data/                          # 実行時に生成されることが多い
      *.db, kill.flag, stop_requested.flag, execution.pid

    utils/
      logging_setup.py
      process_priority.py
      __init__.py

その他:
  pyproject.toml / setup.py / requirements.txt（プロジェクトによる）

---

## 運用上の注意

- 本番環境（KABUSYS_ENV=live）では特に以下に注意してください:
  - .env に機密情報を保存する際は Git にコミットしないこと
  - KILL_FLAG_CLEAR_ON_START を 1 にしない（自動クリアは危険）
  - LINE の通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を適切に設定してアラートを受け取れるようにする
- OpenAI API の呼び出しはレートリミットや一時的なエラーを考慮した再試行ロジックがありますが、API キー管理・コスト管理は運用で注意してください。
- DuckDB / SQLite のファイルは定期的にバックアップしてください。特に paper_trading 用 DB（分離して運用）と本番 DB を混同しないこと。

---

## 開発に関して

- モジュールは可能な限り純粋関数（副作用を持たない）を目指して設計されています（portfolio, research 等）。
- DB スキーマは monitoring_db.init_monitoring_db に定義・マイグレーション処理を含みます。
- テスト時は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動 .env ロードを無効化できます。

---

## 問い合わせ / コントリビュート

バグ報告や改善提案は Issue にお願いします。プルリク歓迎です。PR では変更の概要・影響範囲・簡単な動作確認手順を添えてください。

---

以上が README.md の概要です。必要であれば「運用手順書（起動/停止スクリプト例）」「.env.example のサンプル」「よくあるトラブルシュート」などを追加作成します。どの文書を優先で追加しますか？