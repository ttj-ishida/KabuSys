# KabuSys

日本株自動売買システムのコアライブラリと起動スクリプト群。シグナル生成・ポートフォリオ構築・ポジションサイズ計算・発注実行・監視・リスク管理・AI スコアリング（ニュース NLP）などのコンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。主な機能は次の通りです。

- 戦略（ファクター）計算と特徴量探索（research）
- 銘柄選定・配分・株数決定（portfolio）
- 発注エンジン / リスク管理 / 注文管理（execution）
- 監視（system / trade / risk）と Kill Switch（monitoring）
- ニュースの LLM ベースセンチメント評価（AI）
- ペーパートレード用の分離された DB と検証レポート生成ツール（tools）
- 環境設定ウィザードと設定検証ツール（config）

設計方針の一部:
- DuckDB を分析用 DB、SQLite をランタイム（監視 / ペーパートレード）に使用
- 本番環境・ペーパートレード環境を分離（KABUSYS_ENV）
- ルックアヘッドバイアス防止のため日時参照を明示的に渡す実装
- フェイルセーフ（外部 API 失敗時は安全側フォールバック）

---

## 機能一覧

- config
  - .env 管理（自動読み込み、対話式ウィザード: `config_setup`）
  - 設定検証 CLI（`validate_config`）
- execution
  - ExecutionEngine: ブローカークライアントを使った発注セッション実行
  - ペーパートレード時は MockBroker を使用し、専用 SQLite に記録
- monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態・データ鮮度監視
  - TradeMonitor: 注文の滞留/約定異常検出（trade_logs参照）
  - RiskMonitor: ドローダウン / ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件達成時に `data/kill.flag` を書き込んで停止シグナル発行
  - MonitoringEngine: 各 Monitor をまとめて定期実行、アラート発行
- portfolio
  - 候補選定（スコア降順）と等金額 / スコア加重の重み計算
  - セクターキャップの適用、レジーム乗数
  - ポジションサイズ算出（unit rounding, aggregate cap 等）
- research
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン計算、IC（情報係数）、統計サマリー
- ai
  - ニュース NLP（OpenAI）を用いた銘柄ごとのセンチメントスコア生成
  - 市場レジーム判定（ETF MA とマクロニュースの合成）
- tools
  - Paper Trading 検証レポート生成 CLI（稼働率、注文成功率、レイテンシ等）

---

## セットアップ手順（推奨）

1. Python 環境を準備
   - Python 3.9+ を推奨（実行環境で利用可能なバージョンに合わせてください）
   - 仮想環境を作成して有効化
     ```bash
     python -m venv .venv
     source .venv/bin/activate  # macOS / Linux
     .venv\Scripts\activate     # Windows
     ```

2. 必要パッケージをインストール
   - 代表的な依存:
     - duckdb
     - psutil
     - openai
     - PyYAML（validate_config の YAML 検証に任意で使用）
   - 例:
     ```bash
     pip install duckdb psutil openai PyYAML
     ```
   - （requirements.txt がある場合はそちらを利用してください）

3. 環境変数 (.env) の作成
   - 対話式ウィザードを使用:
     ```bash
     python -m kabusys.config_setup
     ```
   - 生成後、設定内容を検証:
     ```bash
     python -m kabusys.validate_config
     ```
     --strict を付けると警告もエラー扱いになります。

   - 主要な環境変数（抜粋）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（例: INFO）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番での通知用、任意）
   - 自動 .env 読み込みはデフォルトで有効。無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. データディレクトリとログディレクトリの準備
   - デフォルトで `data/` と `logs/` にファイルが作られます。パーミッションを確認してください。

---

## 使い方（起動方法・主要コマンド）

- ExecutionEngine（発注エンジン）起動
  - 簡単起動（スクリプト実行）
    ```bash
    python -m kabusys.run_execution
    ```
  - 動作ポイント
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、`PAPER_TRADING_SQLITE_PATH` に記録されます（本番 DB と完全分離）。
    - 起動時に `data/stop_requested.flag` が存在すると起動せず終了します。
    - 実行中に `data/stop_requested.flag` を作成するとエンジンに停止要求が送られます。
    - PID ファイル: data/execution.pid（Settings.pid_file_path で上書き可能）

- Monitoring（監視プロセス）起動
  - 起動:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
  - 動作ポイント:
    - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用して監視テーブルを初期化します（環境に依らず本番パス）。
    - `data/stop_requested.flag` を検知すると監視ループが終了します。
    - MonitoringEngine は SystemMonitor / TradeMonitor / RiskMonitor を呼び出し、KillSwitch がトリガーを満たせば `data/kill.flag` を書き込みます。

- Paper Trading 検証レポート生成
  - CLI:
    ```bash
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - DB パスは `--db` オプション、または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定できます。

- 環境設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ライブラリとしての利用（例）
  - AI のニューススコアリングをプログラムから呼ぶ:
    ```python
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,1), api_key="sk-...")
    ```

---

## 環境フラグ / ファイルの説明

- data/stop_requested.flag
  - 起動中プロセス（run_execution / run_monitoring）がこのファイルを検出すると優雅に終了します（即時停止要求）。
- data/kill.flag
  - KillSwitch によって書き込まれるファイル。ExecutionEngine 起動時に明示的に取り扱う設定がある場合は注意。Settings.kill_flag_clear_on_start により起動時に自動クリア可能（本番では 0 推奨）。
- data/execution.pid
  - ExecutionEngine の PID を出力するファイル（Settings.pid_file_path）。
- data/*.db
  - data/kabusys.duckdb: 分析用 DuckDB（デフォルト）
  - data/monitoring.db: 監視用 SQLite（デフォルト）
  - data/paper_trading.db: ペーパートレード専用 SQLite（KABUSYS_ENV=paper_trading）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込み、Settings クラス
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - SystemMonitor ポーリング起動スクリプト
- execution/
  - エンジン・注文管理・ブローカー抽象化（BrokerClientFactory 等）
- monitoring/
  - monitoring_db.py（SQLite schema + CRUD）
  - system_monitor.py / trade_monitor.py / risk_monitor.py
  - monitoring_engine.py / kill_switch.py / alert_manager.py
- portfolio/
  - portfolio_builder.py（候補選定・重み）
  - position_sizing.py（株数決定）
  - risk_adjustment.py（セクターキャップ・レジーム乗数）
- research/
  - factor_research.py（モメンタム等）
  - feature_exploration.py（IC・統計）
- ai/
  - news_nlp.py（ニュース NLP スコア）
  - regime_detector.py（市場レジーム判定）
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py（統一ログ設定）
  - process_priority.py（プロセス優先度 / CPU affinity）
- data/ (生成される)
  - *.db, *.pid, kill.flag, stop_requested.flag
- logs/ (生成される)
  - execution.log, monitoring.log 等

---

## 運用上の注意・トラブルシューティング

- データベース / ログディレクトリの権限に注意してください。`logs/` ディレクトリ作成に失敗した場合はコンソールのみのログになります（warning が出ます）。
- OpenAI を使う機能（news_nlp / regime_detector）は `OPENAI_API_KEY` が必要です。未設定だと ValueError を送出します（スクリプトによってはフォールバック動作をする箇所もあります）。
- validate_config は PyYAML がないと YAML ファイル内容チェックをスキップしますが、警告が出ます。必要に応じて PyYAML をインストールしてください。
- KABUSYS_ENV=paper_trading を使うことで本番 API への誤発注リスクを低減できます（MockBroker と別 DB を使用）。
- MONITOR_POLL_INTERVAL は run_monitoring でポーリング間隔を秒で上書きできます。1 未満や不正値を与えるとデフォルト 60 秒にフォールバックします。
- Production（KABUSYS_ENV=live）では `KILL_FLAG_CLEAR_ON_START` を 0 にしておくことを推奨します（自動クリアは危険）。

---

必要に応じて README を拡張して、具体的な起動例、systemd / supervisor 用のユニット定義、テスト方法、CI 設定などを追記できます。必要なら追加で作成します。