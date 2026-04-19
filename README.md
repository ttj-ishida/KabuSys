# KabuSys

日本株向けの自動売買システム（ライブラリ / 実行スクリプト群）。

このリポジトリには、注文実行エンジン、監視（Monitoring）、ポートフォリオ構築ロジック、リサーチ用ファクター計算、OpenAI を使ったニュース NLP / レジーム判定、運用補助ツールなどが含まれます。

---

## 概要

主なコンポーネント

- Execution: 注文発行・注文管理・リスク管理を行う ExecutionEngine（run_execution.py）
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使い、本番 DB とは分離された `data/paper_trading.db` を使用
- Monitoring: システム稼働状況・注文状態・リスク指標を定期ポーリングして DB に記録・アラート/キルスイッチ評価を行う（run_monitoring.py）
  - Monitoring は KABUSYS_ENV に関係なく本番の SQLite (`SQLITE_PATH`) を使用
- Portfolio: 候補選定、重み計算、ポジションサイジング、セクター制約などの純粋関数群
- Research: DuckDB を使ったファクター計算・将来リターン・IC 計算など
- AI: OpenAI を用いたニュースセンチメント（news_nlp）・市場レジーム判定（regime_detector）
- Tools: ペーパートレード検証レポート等の CLI スクリプト（tools/paper_verification_report.py）
- Config: .env ウィザード（config_setup.py）／設定検証（validate_config.py）を用意
- Utils: ログ設定、プロセス優先度設定等の共通ユーティリティ

設計上のポイント
- .env 自動読み込み：プロジェクトルート（.git または pyproject.toml がある場所）から .env/.env.local を自動読み込み（無効化可）
- Paper trading は本番 DB と完全分離（デフォルト: data/paper_trading.db）
- AI 機能は OpenAI API キーが必要（環境変数 OPENAI_API_KEY）
- 監視サイクルや各種閾値は環境変数で調整可能

---

## 機能一覧

- 実行エンジン起動スクリプト（run_execution.py）
  - broker クライアントの生成（実口座 or Mock）
  - リスク管理（RiskManager）
  - Order 管理（OrderManager / OrderRepository）
  - 実行スレッド + PID 管理、stop フラグ対応
- 監視起動スクリプト（run_monitoring.py）
  - System / Trade / Risk モニタの定期実行
  - kill.flag を書く KillSwitch 実装（所定条件で ExecutionEngine を停止）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）
- monitoring DB 層（SQLite）: system_status, trade_logs, positions, risk_logs, dashboard テーブルの作成・マイグレーション
- RiskMonitor: ドローダウン・ポジション上限の検出と risk_logs 登録
- KillSwitch: フラグファイルによる停止通知（data/kill.flag）
- AI:
  - news_nlp.score_news: ニュース記事をまとめて LLM に投げ、銘柄ごとにセンチメントを ai_scores に書き込む
  - regime_detector.score_regime: ETF MA とマクロ記事の LLM 評価を合成して market_regime に保存
- Research:
  - ファクター計算（momentum, volatility, value）
  - 将来リターン、IC 計算、統計サマリ
- Tools:
  - paper_verification_report: ペーパートレード DB から性能指標（稼働率・約定率・レイテンシ等）を集計・判定

---

## 要件（想定）

- Python 3.10+
- 必要なパッケージ（主なもの）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証を行う場合は任意だが推奨）
- そのほか依存はプロジェクト配布の requirements.txt に従ってください（なければ上記をインストール）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. レポジトリをクローン／チェックアウト
2. Python 仮想環境を作成して依存をインストール（上記参照）
3. 環境変数を設定（.env ファイル作成を推奨）
   - 対話式ウィザードで .env を作る:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは手動で .env を作成（重要なキー）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development|paper_trading|live） — デフォルト: development
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（default: data/kabusys.duckdb）
     - SQLITE_PATH（default: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB。default: data/paper_trading.db）
     - LOG_LEVEL（例: INFO）
     - KILL_FLAG_CLEAR_ON_START（0/1。production では 0 推奨）
4. 設定検証:
   ```bash
   python -m kabusys.validate_config
   # --strict を付けると警告も失敗扱い
   python -m kabusys.validate_config --strict
   ```
5. データディレクトリを作成（必要に応じて）
   ```bash
   mkdir -p data logs
   ```

---

## 実行方法（使い方）

- 実行エンジン（ExecutionEngine）を起動
  - 本番 / Paper に依存してブローカーが切り替わります
  ```bash
  python -m kabusys.run_execution
  ```
  - run_execution は起動時にプロセス優先度を "high" にセットします
  - 起動を阻止したい場合は先に data/stop_requested.flag を作成すると起動せず終了します

- 監視ループ（Monitoring）を起動
  ```bash
  # デフォルトポーリング間隔 60 秒
  python -m kabusys.run_monitoring

  # 環境変数で間隔を変更
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - 監視は常に本番用の sqlite_path を参照します（KABUSYS_ENV に依らず）
  - 停止は data/stop_requested.flag を作成してください（監視プロセスはこれを検知して終了します）

- Kill Switch（リスクトリガ）による Execution の停止
  - KillSwitch は `data/kill.flag` を書き込み、ExecutionEngine 側が検知して停止します
  - 実行エンジン起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると自動でクリアされます（本番では 0 推奨）

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 関連（プログラムから直接呼ぶ）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OPENAI_API_KEY を環境変数で指定するか、api_key 引数に渡してください

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: execution の動作モード（development|paper_trading|live） — default: development
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合に必須）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）ファイルパス（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: PaperTrading 用 SQLite（paper_trading 時に使用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）
- PAPER_FILL_MODE: paper_trading の MockBroker の約定モード（instant|partial|never|reject）
- KILL_FLAG_PATH: kill.flag のパス（default: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" or "0"）

---

## ログ

- ログ出力は標準出力（stdout）と日次ローテートファイル（logs/<app_name>.log）に出力されます
- デフォルトのログディレクトリ: logs/
- ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging

---

## 停止・制御フラグ

- data/stop_requested.flag
  - run_execution.py / run_monitoring.py が監視している停止フラグ（外部からの強制停止要求）
- data/kill.flag
  - KillSwitch が書き込む停止フラグ（リスクにより Execution を停止させるためのもの）
- data/execution.pid
  - Execution の PID ファイル（run_execution による管理）

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主なファイル/ディレクトリと役割の一覧です。

- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- config.py — 環境変数 / 設定読み込みロジック（自動 .env ロード含む）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前の設定検証 CLI
- __init__.py — パッケージ初期化（バージョン等）
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成
- ai/
  - news_nlp.py — ニュース NLP（OpenAI 連携）
  - regime_detector.py — 市場レジーム判定（OpenAI を一部使用）
- monitoring/
  - monitoring_db.py — SQLite に対する読み書きレイヤ
  - system_monitor.py — システム・データ鮮度チェック
  - trade_monitor.py — （注文関連の監視ロジック）※実装ファイルあり
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書き込みロジック
  - monitoring_engine.py — モニタをまとめるエンジン
  - alert_manager.py — 通知管理（LINE 等）※実装ファイルあり
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数計算・丸め処理
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — ファクター計算（momentum/volatility/value）
  - feature_exploration.py — 将来リターン・IC 等
- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity 設定
- monitoring_db schema: system_status, trade_logs, positions, risk_logs, dashboard

（実際のリポジトリにはさらに execution, data, strategy 等のサブパッケージが存在する想定）

---

## 運用上の注意

- 本番環境（KABUSYS_ENV=live）では kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。0 を推奨します。
- OpenAI 呼び出しには API コストとレート制限があります。AI 関連処理はリトライ・バックオフを実装していますが、運用時は API キーとレートを監視してください。
- Paper trading は本番 DB と分離されていますが、設定ミスで本番 DB にアクセスすることがないよう .env の確認を徹底してください（validate_config でチェック可能）。
- ログディレクトリ/DB 配下は Git にコミットしないでください（.env に注意喚起あり）。

---

## よく使うコマンドまとめ

- .env ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
- 実行エンジン起動:
  ```bash
  python -m kabusys.run_execution
  ```
- 監視起動:
  ```bash
  export MONITOR_POLL_INTERVAL=60
  python -m kabusys.run_monitoring
  ```
- ペーパートレード検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README の内容はソースコードのコメント・Docstring を元に作成しています。追加で README に含めたい手順（デプロイ手順や systemd ユニット、Docker を使った運用例など）があれば教えてください。必要に応じてサンプル .env.example も作成できます。