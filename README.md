# KabuSys

日本株自動売買システムの軽量コンポーネント群（ライブラリ + 実行スクリプト群）。

このリポジトリは以下の責務を持ちます。
- 戦略・ポートフォリオ構築ロジック（純関数）
- リサーチ／ファクター計算（DuckDB を利用）
- 実行エンジン起動ロジック（paper_trading と本番を分離）
- 監視（System / Trade / Risk）とアラート（LINE）
- AI を利用したニュース NLP / レジーム判定（OpenAI）
- 各種ユーティリティ（プロセス優先度設定、.env ウィザード、設定検証など）

バージョン: 0.1.0

---

## 主な機能一覧

- 設定管理
  - .env の自動読み込み / 対話式ウィザード（kabusys.config_setup）
  - 設定検証ツール（kabusys.validate_config）

- 実行系
  - ExecutionEngine 起動スクリプト（run_execution.py）
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading 用 DB に書き込む（data/paper_trading.db）
    - 停止はフラグファイル（data/stop_requested.flag / data/kill.flag）で制御
    - 実行時にプロセス優先度を上げる（psutil を利用）

- 監視系
  - System / Trade / Risk モニタ（監視結果は SQLite に永続化）
  - MonitoringEngine（ポーリングループ）
  - run_monitoring.py — 監視ポーリングプロセスのエントリ（MONITOR_POLL_INTERVAL で間隔指定可能）
  - KillSwitch による停止（条件を満たすと data/kill.flag を書き込み）

- リサーチ / ポートフォリオ構築
  - ファクター計算（momentum, volatility, value）
  - 特徴量探索（forward returns, IC, summary）
  - ポートフォリオ候補選定、重み計算、ポジションサイズ算出、セクター上限・レジーム乗数

- AI 機能（OpenAI）
  - ニュースセンチメント（news_nlp.score_news）
  - マーケットレジーム判定（regime_detector.score_regime）
  - API 呼び出しは堅牢化（バッチ処理、リトライ、レスポンス検証、フェイルセーフ）

- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順

前提:
- Python 3.9+（型ヒントと一部ライブラリ依存により）
- SQLite（Python 標準モジュールで利用）
- DuckDB（分析用 DB）

1. リポジトリをクローンし、仮想環境を作成・有効化します（例: venv）

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージをインストールします（簡易例）

   ```bash
   pip install duckdb psutil openai requests pyyaml
   ```

   注意: 実際の requirements ファイルはこのコードスニペットに含まれていません。運用環境では固定バージョンを指定してください。

3. 環境変数を準備します
   - 対話式ウィザードで .env を作成することを推奨します:

     ```bash
     python -m kabusys.config_setup
     ```

   - もしくは、ルートに `.env` を置く。主要な環境変数（よく使うもの）は以下の通り。

     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR)
     - OPENAI_API_KEY (AI 機能利用時に必要)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート用、任意）

   - 例 (.env の一部):

     ```
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=your_jquants_token
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     ```

4. 設定を検証します

   ```bash
   python -m kabusys.validate_config
   # 警告も失敗にしたい場合:
   python -m kabusys.validate_config --strict
   ```

5. 必要に応じてデータディレクトリを作成します

   ```bash
   mkdir -p data
   ```

---

## 使い方（主要コマンド）

- .env を対話式で作る / 更新

  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証

  ```bash
  python -m kabusys.validate_config
  ```

- ExecutionEngine を起動（トレード実行プロセス）
  - デフォルトは KABUSYS_ENV に従う。本番用 DB は常に sqlite_path、paper_trading の場合は paper_sqlite_path を使用します。

  ```bash
  python -m kabusys.run_execution
  ```

  - 注意:
    - 起動前に data/kill.flag や data/stop_requested.flag が存在する場合は起動を行わない・即停止します。
    - 実行中は data/execution.pid に PID を書き込みます。
    - プロセス優先度は起動時に "high" に設定しようとします（psutil を利用）。

- 監視プロセスを起動（System / Trade / Risk の定期チェック）

  ```bash
  python -m kabusys.run_monitoring
  ```

  - ポーリング間隔を環境変数で上書きできます（秒単位）。例: 30 秒

    ```bash
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```

  - 監視は Settings にかかわらず、本番（sqlite_path）を使用して監視ログを残します。

- Paper Trading 検証レポートの生成

  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

  - デフォルトの DB は data/paper_trading.db。別パスを指定する場合は `--db` または環境変数 PAPER_TRADING_SQLITE_PATH を利用。

- AI 機能（ニューススコア / レジーム判定）
  - OPENAI_API_KEY を設定した上で、コードから kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出します。
  - CLI ラッパーはありません（ライブラリ関数として利用想定）。API キーは引数で渡すことも可能。

---

## 停止・Kill Switch の取り扱い

- 停止リクエスト:
  - 管理的にプロセスを停止したい場合はプロジェクトの data ディレクトリにフラグファイルを置きます。
    - data/stop_requested.flag : run_monitoring / run_execution の外部停止監視に使用
    - data/kill.flag : KillSwitch が書き込む停止フラグ（ExecutionEngine に即時停止を要求）
  - KillSwitch は RiskMonitor の結果（ドローダウン / ポジション上限等）に応じて data/kill.flag を作成します。
- Kill flag のクリア:
  - Settings.kill_flag_clear_on_start が `1` に設定されていると起動時に自動クリアされます（本番では `0` 推奨）。

---

## 主要コンポーネントの説明（簡易）

- kabusys.config
  - .env の自動ロード（.env, .env.local の順。OS 環境変数は保護される）
  - Settings クラス: 各種パス・閾値・環境フラグをプロパティとして提供

- kabusys.execution
  - ExecutionEngine, OrderManager, RiskManager, Reconciler, OrderRepository 等（実行の中核。サンプル起動スクリプトあり）

- kabusys.monitoring
  - monitoring_db: SQLite のテーブル初期化・簡易 CRUD
  - SystemMonitor, TradeMonitor, RiskMonitor: チェックロジック
  - KillSwitch, AlertManager: 停止制御・通知（LINE）
  - MonitoringEngine: すべてをまとめて定期実行

- kabusys.portfolio
  - 銘柄選定（select_candidates）、重み計算（equal/score）、ポジションサイズ計算（risk_based 等）
  - セクター制限、レジーム乗数調整

- kabusys.research
  - DuckDB を用いたファクター計算（momentum / volatility / value）
  - forward returns、IC、統計サマリー等

- kabusys.ai
  - news_nlp: ニュース記事を集約して OpenAI API に投げ、銘柄別センチメントを ai_scores に書き込む
  - regime_detector: ETF（1321）の MA200 乖離とマクロニュースの LLM センチメントを合成して市場レジームを判定

- kabusys.utils
  - process_priority: プラットフォーム差を吸収してプロセス優先度 / CPU affinity を設定

---

## ディレクトリ構成

（主要ファイルを抽出した簡易ツリー）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
    - execution/
      - (ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等)
      - run scripts 呼び出し元が存在
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - monitoring/monitoring_db.py
    - utils/
      - process_priority.py

- data/
  - monitoring.db (デフォルトの SQLite、監視ログ)
  - paper_trading.db (paper_trading 用 SQLite)
  - kabusys.duckdb (DuckDB ファイル)
  - execution.pid, stop_requested.flag, kill.flag などのランタイムフラグ

---

## 注意事項 / 運用上のポイント

- 環境区分（KABUSYS_ENV）
  - development: ローカル開発。発注を行わないようなモード想定
  - paper_trading: 発注ロジックはモックブローカーを使い、paper 用 DB に記録（実口座と分離）
  - live: 本番。本番接続情報（API トークン等）は厳重に管理すること

- DB の分離
  - 監視は常に sqlite_path（デフォルト data/monitoring.db）を参照してログを残す設計
  - run_execution は KABUSYS_ENV=paper_trading の場合 paper_sqlite_path を使い、本番 DB と分離する

- OpenAI / 外部 API
  - AI 機能を利用するには OPENAI_API_KEY が必要。API 呼び出しはリトライ・検証を行うが、API のコスト・レート制限に注意
  - LINE 通知を使う場合は LINE_CHANNEL_ACCESS_TOKEN と LINE_USER_ID を設定

- 権限・プラットフォームの差
  - プロセス優先度設定や CPU affinity の設定はプラットフォーム依存・権限依存で失敗する可能性がある（警告を出してスキップ）

- テスト・開発
  - .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能（ユニットテスト等で有用）
  - 多くのモジュールは純粋関数ベースで設計されており、ユニットテストが比較的書きやすい

---

必要であれば、README にサンプル .env.example、より詳細なデプロイ手順（systemd / supervisor 用の unit 例）や docker-compose 例なども追加できます。どの情報を追加したいか教えてください。