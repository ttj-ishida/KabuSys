# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README（日本語）。

この README は、リポジトリ内の主要スクリプト / モジュール構成と、セットアップ・起動の手順、主要な環境変数の説明、開発時に便利なコマンドなどをまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。  
主な責務は以下の通りです。

- 市場データ（DuckDB）を用いたリサーチ／ファクター計算
- ポートフォリオ構築、ポジションサイズ計算（純粋関数群）
- ExecutionEngine による発注処理（本番 / ペーパートレード対応）
- 監視（System / Trade / Risk）と Kill Switch（異常時の自動停止）
- ニュース NLP / レジーム判定（OpenAI を用いたセンチメント評価）
- 運用を支援するツール（ペーパートレード検証レポート生成など）

設計方針として、「ルックアヘッドバイアスを避ける」「本番とペーパートレードのデータ分離」「フェイルセーフ（API失敗はスキップして継続）」などが採用されています。

---

## 主な機能一覧

- 実行スクリプト
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV により本番／paper_trading を切替）
  - run_monitoring: SystemMonitor のポーリングループを実行
- 設定関連 CLI
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: .env と config/*.yaml の検証（--strict オプションあり）
- 監視
  - monitoring_engine: System/Trade/Risk の統合ポーリングとアラート / Kill Switch 評価
  - RiskMonitor / SystemMonitor / TradeMonitor（監視ロジック）
  - monitoring_db: SQLite を使った永続化（system_status, trade_logs, positions, risk_logs, dashboard）
- ポートフォリオ構築（純粋関数）
  - candidate 選定、等重 / スコア重み付け、リスク調整（sector cap、regime multiplier）
  - position sizing（risk_based / equal / score）
- 研究（research）
  - ファクター計算（momentum / value / volatility）
  - feature exploration（forward returns, IC, summary）
- AI（OpenAI 統合）
  - news_nlp: ニュースから銘柄別センチメントを算出して ai_scores に書き込み
  - regime_detector: ETF とマクロニュースを組合せて市場レジーム判定
- ツール
  - paper_verification_report: ペーパートレード DB を解析して検証レポート出力

---

## セットアップ手順（開発向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 環境の準備（例: 仮想環境）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .\.venv\Scripts\activate    # Windows
   ```

3. 必要パッケージをインストール
   - このリポジトリに requirements.txt がある場合:
     ```
     pip install -r requirements.txt
     ```
   - 最低限必要となるライブラリ（参考）:
     - duckdb, psutil, openai, pyyaml（validate_config の YAML 検証用）など

4. 環境変数（.env）を作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - または手動で `.env` を作成。自動ロードルール:
     - OS環境変数 > .env.local > .env の順で読み込まれます
     - 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

5. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリやログディレクトリの作成（多くは自動で作られますが手動で用意しておくと安心）
   - デフォルト:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログ: logs/
     - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag

注意: 実行には外部 API キー（J-Quants, kabuステーション パスワード, OpenAI など）が必要です。必須環境変数は次節で説明します。

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

よく使う（デフォルト付き）:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、default: INFO）
- LOG_DIR — ログディレクトリ（default: logs/）
- OPENAI_API_KEY — OpenAI API を使う機能（news_nlp / regime_detector）で必要
- PAPER_FILL_MODE — ペーパートレードの約定動作（instant / partial / never / reject）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト60）
- KILL_FLAG_PATH — kill.flag のパス（default: data/kill.flag）
- PID_FILE_PATH — 実行プロセスの PID ファイル（default: data/execution.pid）

設定は `.env` / `.env.local` に記載するか、実行環境の環境変数として与えてください。

---

## 使い方 / 実行例

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動
  - 本番（KABUSYS_ENV=live / development 等に応じて動作が変わる）
    ```
    python -m kabusys.run_execution
    ```
  - ペーパートレード
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
    ペーパートレード時は専用 MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。本番 DB と完全分離されます。

- Monitoring 起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を環境変数で変更:
    ```
    export MONITOR_POLL_INTERVAL=30   # 30 秒ごとに実行
    ```
  - run_monitoring は常に本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを記録します。

- Kill Switch / 停止管理
  - 異常時に ExecutionEngine を停止させたい場合は `data/kill.flag` を書き込む（KillSwitch）。
  - 外部から即時停止させたい場合は `data/stop_requested.flag` を作成すると run_execution/run_monitoring 側が検知して終了処理を行います。

- Paper Trading 検証レポート出力
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（news_nlp / regime_detector）
  - 使用するには `OPENAI_API_KEY` を設定してください。
  - 例（Python API を直接使う場合）:
    ```
    from kabusys.ai.news_nlp import score_news
    # duckdb_conn は duckdb.connect(...)
    score_news(duckdb_conn, target_date=date(2026,4,11), api_key="...")
    ```

---

## 運用上のポイント・注意事項

- ペーパートレードは本番 DB と分離されています（PAPER_TRADING_SQLITE_PATH を使用）。
- run_execution / run_monitoring はプロセス優先度を上げようとします（psutil を使用）。権限不足で警告が出ることがありますが、致命的ではありません。
- ログはデフォルトで logs/<app_name>.log に日次ローテートで出力されます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。
- validate_config は config/*.yaml の存在確認と YAML パース（PyYAML 必須）を行います。config ファイルはスクリプトで生成可能（repo内に generator がある場合）。
- AI を呼ぶ機能では、API エラーやレートリミットに対してエクスポネンシャルバックオフとフォールバックが実装されています。キー未設定時はエラーを投げるものと、フォールバック（0.0）するものがありますのでドキュメントの該当関数説明を確認してください。
- データ鮮度やプロセス停止、滞留注文等を監視し、必要に応じて kill.flag を書き込む自動応答機能が備わっています。特に本番運用時は LINE 通知等のアラート設定を確認してください（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）。

---

## ディレクトリ構成（抜粋）

以下はこのリポジトリに含まれる主なモジュールとファイルのツリー（コードベースから抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定読み込みと Settings クラス
  - config_setup.py            — .env 対話ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py              — ニュース NLP（OpenAI）
    - regime_detector.py       — 市場レジーム判定（OpenAI + ETF MA）
  - monitoring/
    - monitoring_db.py         — SQLite テーブル初期化 + DB ラッパー
    - system_monitor.py
    - trade_monitor.py         — （存在する場合、トレード監視）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py         — （アラート処理）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
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
  - monitoring/monitoring_db.py (上記)
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - data/ (runtime ディレクトリ、デフォルト)
    - monitoring.db (default)
    - paper_trading.db (paper_trading 用)
    - kabusys.duckdb
    - execution.pid
    - kill.flag
    - stop_requested.flag
- pyproject.toml / その他プロジェクトメタ（プロジェクトルートで検出）

（リポジトリによってはファイルが追加されている場合があります。上は主要ファイルの抜粋です。）

---

## よくある質問 / トラブルシューティング

- Q: run_execution が起動せずすぐ終了する  
  A: data/stop_requested.flag が存在すると起動をスキップします。不要な場合は削除してください。

- Q: .env が自動で読み込まれない  
  A: 自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）で行います。CI 等で無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- Q: OpenAI を使うとエラーが出る  
  A: `OPENAI_API_KEY` を環境変数にセットしてください。API のレート制限や一時的な接続障害はリトライ処理で緩和されますが、キー未指定では例外となる関数があります。

---

必要であれば README にサンプル .env テンプレートや systemd / cron での起動例（サービス unit ファイル例）、運用チェックリスト（監視項目としきい値）なども追加できます。どの内容を優先して追加しますか？