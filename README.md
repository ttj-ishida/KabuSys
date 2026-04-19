# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README（日本語）

この README はリポジトリ内の主要スクリプト・モジュール構成と、セットアップ・実行方法をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。  
主要な責務は次のとおりです。

- 市場データ（DuckDB に格納）を用いたファクター計算・研究機能
- ポートフォリオ構築・ポジションサイジング（等配分 / スコア加重 / リスクベース）
- 発注エンジン（ExecutionEngine）：kabuステーション等のブローカークライアントを通じた発注（本番 / ペーパートレード対応）
- 監視（Monitoring）：システム状態・注文状態・リスク監視、Kill Switch による強制停止
- AI 支援（OpenAI を用いたニュースセンチメント評価、レジーム判定）
- ペーパートレード検証レポート生成などのツール群

設計方針として「本番 DB とペーパートレード DB の分離」「ルックアヘッドバイアスを防ぐ設計」「外部 API 呼び出しは明示的に鍵を与えて行う（環境変数または引数）」等が採られています。

---

## 主な機能（モジュール一覧）

- kabusys.config
  - 環境変数読み込み・設定ラッパー（.env 自動ロード機能）
- kabusys.config_setup
  - .env を対話式に生成・更新するウィザード
- kabusys.validate_config
  - 起動前の設定検証（必須環境変数や config/*.yaml の存在チェック）
- kabusys.execution
  - ExecutionEngine、OrderManager、RiskManager、Reconciler など（発注ロジック）
  - ブローカークライアントのファクトリ（paper_trading 時は Mock を使用）
- kabusys.monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch 等
  - monitoring DB（SQLite）へのログ永続化（monitoring_db）
- kabusys.portfolio
  - 候補選定・重み付け・ポジション決定（portfolio_builder, position_sizing, risk_adjustment）
- kabusys.research
  - ファクター計算（momentum / volatility / value）や特徴量探索（IC 等）
- kabusys.ai
  - news_nlp: OpenAI を用いたニュースセンチメント -> ai_scores
  - regime_detector: ETF の MA とマクロニュースから市場レジーム判定
- kabusys.tools
  - paper_verification_report: ペーパートレード結果の検証レポートを生成
- kabusys.utils
  - logging_setup: 一貫したログ出力設定（stdout + 日次ローテーション）
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 前提（依存ライブラリ）

主に次を想定しています（プロジェクトルートで pip install を推奨）:

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config/*.yaml の中身検証に必要だが必須ではない）
- その他標準ライブラリ（sqlite3, logging, threading...）

インストール例:
```bash
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン / 取得
2. 依存パッケージをインストール（上記参照）
3. .env の作成（対話式ウィザード推奨）
   - コマンド例:
     ```bash
     python -m kabusys.config_setup
     ```
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う機能を使う場合:
     - OPENAI_API_KEY を設定（.env または環境変数）
4. 設定検証（任意）
   - 簡易チェック:
     ```bash
     python -m kabusys.validate_config
     ```
   - 警告も失敗として扱う厳格モード:
     ```bash
     python -m kabusys.validate_config --strict
     ```
5. DB 初期化はスクリプト実行時に自動で行われる（monitoring 用テーブル等は init_monitoring_db で作成）

デフォルトのファイルパス（変更可）:
- DuckDB: data/kabusys.duckdb (環境変数 DUCKDB_PATH)
- SQLite (monitoring): data/monitoring.db (環境変数 SQLITE_PATH)
- Paper trading SQLite: data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
- ログ: logs/<app_name>.log （環境変数 LOG_DIR で変更）
- PID / flag: data/execution.pid, data/stop_requested.flag, data/kill.flag

---

## .env（環境変数）例

以下は .env に設定する代表的なキー（config_setup で生成可能）:

- KABUSYS_ENV=development|paper_trading|live
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- LOG_LEVEL=INFO
- LOG_DIR=logs
- OPENAI_API_KEY=...  （AI 機能を使う場合）
- KILL_FLAG_CLEAR_ON_START=0

注意:
- KABUSYS_ENV によって挙動が変わります。`paper_trading` は発注を模擬し DB を別ファイルに分離します。`live` は本番動作です。

---

## 実行方法（主要スクリプト）

各コマンドはプロジェクトルートで実行してください。

- ExecutionEngine 起動（発注エンジン）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に保存されます。
  - 停止方法:
    - Monitoring 側や KillSwitch が data/kill.flag を作成すると ExecutionEngine 停止をトリガーします。
    - またプロジェクトルートの data/stop_requested.flag を作ると run_execution 起動済みループが検知して停止します。

- Monitoring 起動（ポーリングループ）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60 秒）
    - 例: `export MONITOR_POLL_INTERVAL=30`
  - Monitoring は settings.env に関わらず本番 sqlite_path を使用して監視ログを保存します（monitoring は本番 DB の監視を意図）。
  - 停止フラグ: data/stop_requested.flag を作成するとループが終了します。

- 設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` オプションで DB パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH が優先されます。

---

## よく使うフラグ / ファイル

- data/stop_requested.flag
  - run_monitoring.py / run_execution.py が存在を検知して安全に停止するためのフラグファイル
- data/kill.flag
  - KillSwitch（risk_monitor 等の判定で）が書き込むフラグ。ExecutionEngine の停止トリガーとして機能します
- data/execution.pid
  - ExecutionEngine の PID 管理用ファイル（run_execution が使用）

---

## ログ・診断

- ログ設定は kabusys.utils.logging_setup.setup_logging で統一的に行われます。
  - stdout（StreamHandler）とファイル（TimedRotatingFileHandler、日次ローテート、30日保持）に出力します。
  - デフォルトログディレクトリ: logs/
  - ログレベルは LOG_LEVEL 環境変数または引数で変更できます。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前チェック
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - execution/               — 発注エンジン関連（Engine, OrderManager, RiskManager, etc.）
  - monitoring/
    - monitoring_db.py       — monitoring 用 SQLite テーブル定義 + DB 操作ラッパ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
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
    - process_priority.py

---

## 注意事項 / 運用上のポイント

- 本番（KABUSYS_ENV=live）で動かす場合は必須環境変数や LINE 通知設定などを慎重に確認してください。validate_config の live 向けチェックが警告を出します。
- Paper Trading は本番 DB と完全に分離するように設計されています。PAPER_TRADING_SQLITE_PATH を必ず確認してください。
- OpenAI（news_nlp / regime_detector）を実行するには OPENAI_API_KEY が必要です。API 呼び出しは失敗耐性（リトライ・フォールバック）を備えていますが、API 利用量には注意してください。
- process_priority.set_process_priority はプラットフォームに依存するので、権限によっては設定に失敗する場合があります（警告ログのみ）。
- monitoring と execution は stop フラグ / kill フラグによって制御します。自動運用時はこれらの取り扱いルールを定めてください。

---

## 開発・拡張のヒント

- DuckDB 接続を渡す設計になっているため、テスト時にはインメモリ DB を使って関数単位で検証できます。
- AI 関連の外部呼び出しは _call_openai_api のラッパーをモックすることでテストしやすく設計されています。
- config/*.yaml のテンプレート生成スクリプト（scripts/generate_config.py）や追加ツールがある想定のチェックロジックがあります（リポジトリ内を確認してください）。

---

以上がこのコードベースの概要・セットアップ・運用ガイドです。必要があれば、起動シーケンス図・ER 図・代表的なログ例・よくあるトラブルシュートを別途まとめます。