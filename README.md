# KabuSys

日本株自動売買システムの一部（ライブラリ & 起動スクリプト群）。

このリポジトリはシグナル生成・ポートフォリオ構築・発注エンジン・監視・研究ツール・AI ベースのニュースセンチメント評価などを含むモジュール群で構成されています。

## 主な特徴
- シグナル → ポートフォリオ構築 → 発注までのパイプライン（純粋関数中心の portfolio モジュール）
- ExecutionEngine（発注エンジン）と Monitoring（稼働監視 / Kill Switch）
- Paper trading モード（本番 DB と完全に分離された paper_trading DB を使用）
- DuckDB を用いたファクター計算 / 研究用集計（prices_daily, raw_financials 等を参照）
- OpenAI（gpt-4o-mini）によるニュースセンチメント評価と市場レジーム判定（AI モジュール）
- 監視ログは SQLite（monitoring.db）へ保存、ログ回転は日次ローテーション
- ユーティリティ: .env 対話式生成ウィザード、設定検証 CLI、ペーパートレード検証レポート生成など

---

## 機能一覧（抜粋）
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading 時は MockBroker）
  - run_monitoring.py: SystemMonitor をポーリングして監視ログを記録
- 環境設定 / 検証
  - config_setup.py: 対話的に .env を作成 / 更新
  - validate_config.py: .env や config/*.yaml の事前検証
- モニタリング
  - system_monitor: CPU / メモリ / ディスク / プロセス生存 / データ鮮度の監視
  - trade_monitor, risk_monitor, monitoring_engine, kill_switch（異常時に kill.flag で Execution を停止）
  - monitoring_db: SQLite ベースの永続化層（テーブル作成・マイグレーション含む）
- ポートフォリオ構築
  - portfolio_builder: 候補選定・重み付け（等金額 / スコア加重）
  - position_sizing: 単元株丸め・リスクベース / 重みベースでの株数算出
  - risk_adjustment: セクター集中キャップ・レジーム乗数
- 研究（research）
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI（ai）
  - news_nlp: raw_news を OpenAI に投げて銘柄ごとのセンチメント評価を ai_scores に保存
  - regime_detector: MA200 とマクロニュースの LLM センチメントを合成して市場レジーム判定
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成

---

## セットアップ手順

前提: Python 3.9+ を想定（ソースは型ヒントにより 3.9+ 想定）。環境や使用する機能により追加パッケージが必要です。

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

3. 依存パッケージをインストール
   推奨（最低限）パッケージ:
   - duckdb
   - psutil
   - openai
   - PyYAML (config 検証用に任意)
   ```
   pip install duckdb psutil openai PyYAML
   ```
   必要に応じてその他パッケージを追加してください。

4. .env の作成
   対話式ウィザードで作るのがおすすめ:
   ```
   python -m kabusys.config_setup
   ```
   もしくはリポジトリルートに `.env` を用意（`.env.example` を参照）。自動ロードはデフォルトで有効（.env / .env.local がプロジェクトルートに存在すれば読み込まれます）。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. 設定の検証
   ```
   python -m kabusys.validate_config
   ```
   警告を厳しく扱う場合:
   ```
   python -m kabusys.validate_config --strict
   ```

注意: `.env` は機密情報（API キー等）を含むため絶対に Git にコミットしないでください。

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY（AI 機能を使用する場合）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
- LOG_LEVEL（例: INFO）
- LOG_DIR（ログ保存先; デフォルト: logs/）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒）

---

## 使い方

基本的な起動・コマンド例:

- ExecutionEngine を起動（本番 / paper_trading は KABUSYS_ENV で切替）
  ```
  # 事前に .env で KABUSYS_ENV を設定しておく
  python -m kabusys.run_execution
  ```
  実行時はプロセス優先度を高に設定し、PID ファイル（data/execution.pid）を生成します。`data/stop_requested.flag` があるとすぐに起動を中止します。paper_trading の場合は別 DB（PAPER_TRADING_SQLITE_PATH）を用いて本番 DB と分離します。

- Monitoring を起動（ポーリングで SystemMonitor を実行）
  ```
  # ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒、デフォルト 60）
  python -m kabusys.run_monitoring
  ```
  Monitoring は本番 sqlite_path を使用して監視ログを保存します（環境にかかわらず実 DB を参照）。

- .env の対話式作成
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading の検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  DB を明示する場合:
  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI ニューススコアリング（ライブラリ呼び出し例）
  ライブラリ API を直接呼ぶ場合:
  ```py
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 4, 20), api_key="sk-...")
  ```

停止・Kill Switch に関する操作
- ExecutionEngine を外部から止めたい場合、Monitoring の KillSwitch がトリガーすると `data/kill.flag` を作成します。手動で停止を指示する場合は同様に `data/kill.flag` にテキストを書いてください（KillSwitch は既存フラグがある場合は再書き込みしません）。Monitoring / Execution は `data/stop_requested.flag` を存在チェックしてループを抜けます（管理スクリプト等で停止要求を行う場合に使用）。

ログ
- ログは console (stdout) と日次ローテートファイル（デフォルト logs/<app_name>.log）に出力されます。ログディレクトリは `LOG_DIR` 環境変数またはデフォルト `logs/`。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数自動読み込み、Settings クラス
  - config_setup.py
    - .env の対話式ウィザード
  - validate_config.py
    - 起動前の設定チェック CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - Monitoring 起動スクリプト
  - monitoring/
    - monitoring_db.py
      - SQLite テーブル作成 & MonitoringDB クラス（読み書き）
    - system_monitor.py
      - システム状態・データ鮮度監視
    - trade_monitor.py
      - （トレード監視ロジック）
    - risk_monitor.py
      - ドローダウン・ポジション数監視
    - kill_switch.py
      - kill.flag 書き込みロジック
    - monitoring_engine.py
      - 監視器の束ねとポーリングループ
    - alert_manager.py
      - （アラート送信ロジック：LINE 等）
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py
      - 発注ロジック、ブローカー接続（Mock 対応）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
      - setup_logging(app_name, log_dir, level)
    - process_priority.py
      - set_process_priority / set_cpu_affinity
  - data/ (ランタイムで作成される想定)
    - monitoring.db, paper_trading.db, kill.flag, stop_requested.flag, execution.pid など
  - config/
    - system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml
      - 設定テンプレート（generate スクリプトで生成する想定）

---

## 実装上の注意点 / 運用メモ
- .env は OS 環境変数より低優先度で自動読み込みされます（`.env.local` は上書き）。自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- run_execution は paper_trading モード時に paper_trading 用 DB を使用し、本番 sqlite を汚しません。KABUSYS_ENV は必ず確認してください（`live` は本番実行）。
- Monitoring のポーリング間隔は `MONITOR_POLL_INTERVAL` で上書き可（秒、デフォルト 60）。0 以下や不正値の場合はデフォルトにフォールバックします。
- OpenAI を使用する機能（news_nlp, regime_detector）は API キーが必須です（環境変数 OPENAI_API_KEY または関数引数で渡す）。
- monitoring_db.init_monitoring_db() は冪等でテーブル作成および簡単なマイグレーション（カラム追加）を行います。初回起動時の手動マイグレーション不要。
- ログディレクトリ作成に失敗した場合、ファイル出力は無効化されコンソールのみにフォールバックします。
- process priority / CPU affinity 設定は OS に依存します。権限不足などで設定に失敗した場合は警告ログを出してスキップします。

---

必要があれば、README にサンプル .env、実際の起動シナリオ（systemd / cron / supervisor 用のユニット例）やより詳細な API ドキュメント（各モジュールの公開関数・引数仕様）を追記します。どの部分を詳しく書くか教えてください。