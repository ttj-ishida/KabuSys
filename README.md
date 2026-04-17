# KabuSys — 日本株自動売買システム

このリポジトリは日本株のアルゴリズム売買およびそれを支える監視・リサーチ・AI アシスト機能を含むモジュール群です。コードは純粋関数群、DB 永続化層、Execution/Monitoring のランチャースクリプト、AI（OpenAI）連携、レポートツールなどで構成されています。

---

## プロジェクト概要

- ExecutionEngine: ブローカークライアントを使って注文を作成・管理・執行するコアエンジン（本番 / ペーパートレード対応）。
- Monitoring: System / Trade / Risk モニタを定期実行して状態を DB に記録し、Kill Switch やアラート発行を行う。
- Portfolio モジュール: 候補選定・重み算出・リスク調整・ポジションサイズ計算などの純粋関数群（DB 参照なし）。
- Research: DuckDB を用いたファクター計算・特徴量探索（prices_daily, raw_financials 参照）。
- AI: OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価／市場レジーム判定。
- ツール: 設定ウィザード、設定検証 CLI、Paper Trading 検証レポートなど。

---

## 主な機能一覧

- 実行（Execution）
  - 本番 / ペーパートレードを環境変数で切り替え
  - RiskManager による注文制約・サーキットブレーカー
  - Reconciler によるブローカーとの整合性維持

- 監視（Monitoring）
  - CPU/メモリ/Disk/プロセス状態の定期記録（SQLite）
  - 注文の滞留・約定異常検出
  - ドローダウン／ポジション数監視と Kill Switch（data/kill.flag）
  - アラート発行（LINE 連携用トークン設定可能）

- リサーチ
  - モメンタム／ボラティリティ／バリュー等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）算出、統計サマリー

- AI（OpenAI）
  - ニュースを LLM でスコアリングして ai_scores に保存
  - マクロニュース + ETF MA による日次レジーム判定（bull/neutral/bear）

- ユーティリティ
  - プロセス優先度・CPU affinity 設定（psutil）
  - .env 対話式作成ウィザード、設定検証 CLI
  - Paper Trading 用検証レポート出力

---

## セットアップ手順（開発 / ローカル）

1. リポジトリをクローン／配置

2. Python 環境を用意（推奨: venv）
   - 例:
     python -m venv .venv
     source .venv/bin/activate

3. 必要なパッケージをインストール
   - 本プロジェクトの実行に最低限必要な外部パッケージ例:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で任意）
   - 例:
     pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください）

4. .env の作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - あるいは .env.example を参考に手動作成
   - 自動ロード:
     - デフォルトで .env / .env.local はプロジェクトルートから自動読み込みされます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

5. 設定検証（起動前チェック）
   python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱い（exit(1)）になります。

---

## 主要環境変数（抜粋とデフォルト）

- 必須:
  - JQUANTS_REFRESH_TOKEN : J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD     : kabuステーション API パスワード

- 実行環境:
  - KABUSYS_ENV : development | paper_trading | live（デフォルト: development）
    - paper_trading の場合、MockBroker を使用・DB は data/paper_trading.db に分離

- DB 関連:
  - DUCKDB_PATH : 分析用 DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH : 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH : ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）

- AI:
  - OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector で使用）

- 監視 / 実行制御:
  - PID_FILE_PATH : ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH : Kill Switch フラグファイル（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START : 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）
  - MONITOR_POLL_INTERVAL : run_monitoring のポーリング間隔（秒、デフォルト: 60）
  - PAPER_FILL_MODE : ペーパートレードの約定モード（instant, partial, never, reject）

- ログ:
  - LOG_LEVEL : DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）

---

## 使い方（実行コマンド）

- 設定ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番またはペーパー）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient が利用され、データは data/paper_trading.db に記録されます。
  - 実行中に data/stop_requested.flag が存在するとエンジンは停止します。
  - 実行時に process priority を "high" に設定します（psutil を使用）。

- Monitoring 起動
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（例: MONITOR_POLL_INTERVAL=30）
  - 監視は Settings で指定した sqlite_path（監視 DB）を使用します（監視は常に本番 sqlite_path を参照）。

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite ファイルを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH を上書き）

- AI 機能（ニューススコア / レジーム判定）
  - OPENAI_API_KEY を設定してから呼び出す（内部関数呼び出し / スクリプト経由）
  - 例: Python スクリプト内から kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼ぶ

---

## 停止・キル機構

- data/stop_requested.flag
  - run_monitoring / run_execution が監視する停止フラグ（ファイルが存在するとループを抜ける）

- data/kill.flag
  - KillSwitch により書き込まれると ExecutionEngine に停止シグナルを送れる（Execution 起動側で KILL_FLAG_CLEAR_ON_START=1 の場合起動時に自動クリア）

- PID ファイル
  - ExecutionEngine は起動時に pid を data/execution.pid に書き込み、SystemMonitor が存在確認してプロセス生存チェックを行います。stale PID は検出されると削除され、リスクログに記録されます。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- config_setup.py            — .env 対話式ウィザード
- validate_config.py        — 起動前チェック CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — Monitoring 起動スクリプト

subpackages:
- ai/
  - news_nlp.py             — ニュースの LLM スコアリング
  - regime_detector.py      — 市場レジーム判定
- monitoring/
  - monitoring_db.py        — SQLite 永続化層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py        — （アラート発行の窓口、未完の可能性あり）
- execution/                 — 発注・リスク・オーダー管理周り（Engine 等）
  - (order_manager, order_repository, reconciler, risk_manager, execution_engine など)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- monitoring/                — 上記の監視関連（再掲）
- utils/
  - process_priority.py      — プロセス優先度・CPU affinity
- tools/
  - paper_verification_report.py
- data/                      — 実行時に使用するデータディレクトリ（DB / flag / pid 等）

（実際のツリーはリポジトリのルートをご確認ください）

---

## .env のサンプル（抜粋）

以下は最低限よく使うキーの例です（値は例示）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
PAPER_FILL_MODE=instant

注意: .env は絶対に公開リポジトリにコミットしないでください。

---

## 実行時の注意点 / 運用メモ

- KABUSYS_ENV に応じて挙動が大きく変わります（特に paper_trading / live）。
- Paper トレードではブローカー操作はモックされ、本番 DB と分離されます。
- OpenAI を使う機能は API コスト・レイテンシに注意。失敗時はフォールバック（スコア0.0等）する実装もありますが、キー未設定では例外が出ます。
- Monitoring は監視 DB にログを連続書き込みします。DB ファイルのバックアップ・ローテーションを検討してください。
- プロセス優先度設定や CPU affinity は psutil に依存します。権限不足で失敗することがあります（警告が出るのみで続行）。

---

## テスト / 開発時のヒント

- 自動 .env ロードを無効化する:
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- Monitoring のポーリング間隔を短くして動作確認:
  MONITOR_POLL_INTERVAL=5 python -m kabusys.run_monitoring
- validate_config で設定ミスを事前に検出:
  python -m kabusys.validate_config --strict

---

必要であればこの README に実行例やトラブルシュート（よくあるエラーと対処法）、CI 用のセットアップ手順、依存関係一覧（requirements.txt）追記も可能です。どの情報を追加しましょうか？