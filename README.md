# KabuSys

バージョン: 0.1.0

日本株向け自動売買システムのコアライブラリ群です。戦略（リサーチ・ファクター計算）、ポートフォリオ構築、発注エンジン、監視・アラート、AI を使ったニュース解析などのコンポーネントを含みます。

---

## プロジェクト概要

KabuSys は、銘柄選定 → ウェイト算出 → ポジションサイズ決定 → 発注管理 を行う自動売買フレームワークです。DuckDB を用いた時系列データ処理、SQLite による監視ログ永続化、OpenAI を利用したニュースセンチメント評価などを備え、実運用（live）・ペーパートレード（paper_trading）・開発（development）を切り替えて動作します。

主な設計方針:
- データ処理は基本的に DuckDB / 純関数で実装（再現性重視）
- 発注ロジックと監視は SQLite による永続化を行い安全性を担保
- AI 部分は外部 API 呼び出し時にフェイルセーフを備える（失敗時フォールバック）
- .env による環境設定、対話式ウィザードと検証ツールを提供

---

## 主な機能一覧

- ExecutionEngine 起動スクリプト（run_execution）
  - 本番 / ペーパートレードの分離（paper_trading では MockBrokerClient）
  - リスク管理（RiskManager）、発注管理（OrderManager / OrderRepository）、照合（Reconciler）
- Monitoring（run_monitoring）
  - システム / 発注 / リスク監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor）
  - Kill Switch（条件に応じた停止フラグ書き込み）
  - ログ（SQLite: monitoring.db）への永続化
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等金額／スコア加重、リスク調整（セクター制限、レジーム乗数）、ポジションサイズ算出
- リサーチ（kabusys.research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を使用）
  - 将来リターン、IC（Information Coefficient）、統計サマリ等
- AI モジュール（kabusys.ai）
  - ニュースのセンチメントスコアリング（OpenAI を利用）
  - 市場レジーム判定（MA + マクロセンチメント合成）
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
- 設定管理 / ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 起動前設定検証 CLI（validate_config）
  - 統一ログ設定、プロセス優先度設定ユーティリティ

---

## 前提条件

- Python 3.10 以上（typing の機能 / future annotations を使用）
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config 検証で YAML をチェックする場合）
- ネットワーク接続（OpenAI を使う場合）
- SQLite / DuckDB ファイルへの書込権限

※ 実行環境に合わせて適宜 requirements.txt を用意してインストールしてください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - （任意）pip install pyyaml

4. .env の作成（対話式推奨）
   - python -m kabusys.config_setup
     - ウィザードで J-Quants トークン、kabuAPI パスワードなどを入力して `.env` を生成します。
   - 生成後、設定を検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります。

5. データ / ログディレクトリの確認
   - デフォルトのデータ / ログ配置:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper trading DB: data/paper_trading.db
     - ログ: logs/
   - 必要に応じて .env の DU CKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を設定

---

## 使い方

### 実行系

- ExecutionEngine を起動（通常実行）
  - python -m kabusys.run_execution
  - KABUSYS_ENV を切り替える:
    - 本番: export KABUSYS_ENV=live
    - ペーパー: export KABUSYS_ENV=paper_trading
    - 開発: export KABUSYS_ENV=development
  - paper_trading の場合、MockBrokerClient が使われ、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
  - 起動時に data/stop_requested.flag が既に存在すると起動をスキップします。
  - 実行中は data/execution.pid に PID を書きます（設定で変更可能）。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で調整:
    - export MONITOR_POLL_INTERVAL=120  # 秒
  - 監視は常に本番の sqlite_path（SQLITE_PATH）を参照して記録します（KABUSYS_ENV に依存しない点に注意）。

- 停止
  - 監視/実行スクリプトは data/stop_requested.flag の存在をチェックし終了します。
  - Kill Switch（自動停止判定）が条件を満たした場合、data/kill.flag が書き込まれます。
  - kill.flag は Settings.kill_flag_clear_on_start の設定次第で起動時に自動クリアされる可能性があります（本番では 0 推奨）。

### ツール

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

### AI モジュール（プログラムから利用）

- ニューススコアリング（ai.news_nlp.score_news）
  - 例:
    - from openai import OpenAI  # openai SDK
    - import duckdb
    - from kabusys.ai import score_news
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, target_date, api_key="sk-...")

- レジーム判定（ai.regime_detector.score_regime）
  - 同様に duckdb 接続と API キーを渡して呼び出します。

注意: OpenAI API キーは環境変数 OPENAI_API_KEY でも指定可能。未指定時は ValueError が発生します。

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- LOG_LEVEL — デフォルト: INFO
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — AI 機能利用時に必要
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

詳細は kabusys.config.Settings のプロパティ実装を参照してください。

---

## ログ / データ / 管理ファイル

- logs/<app_name>.log — 日次ローテーションでログを出力（デフォルト 30 日保持）
- data/monitoring.db — 監視ログ（SQLite）
- data/paper_trading.db — ペーパートレード用 SQLite（paper_trading 時に使用）
- data/kabusys.duckdb — DuckDB（時系列データ、ファクター計算等）
- data/execution.pid — 実行エンジンの PID（デフォルトパス、設定可能）
- data/stop_requested.flag — 存在すると run_* スクリプトが停止・起動しない
- data/kill.flag — Kill Switch が発動した際に書き込まれる停止理由文字列

---

## ディレクトリ構成（主要ファイル）

src/ 以下の主な構成:

- kabusys/
  - __init__.py
  - config.py                — 環境変数・.env 読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
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
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py         (監視の詳細は実装ファイル参照)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py        (アラート送信ロジック)
  - execution/
    - execution_engine.py     (ExecutionCore)
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - research, data, portfolio 等の補助モジュール

（上は抜粋。詳細はリポジトリの src/kabusys/ 以下を参照してください）

---

## 開発・運用上の注意

- KABUSYS_ENV=live の設定時は設定ミスが致命的な影響を与える可能性があります。validate_config で十分に検査してください。
- .env は機密情報（API キー等）を含むため絶対にリポジトリにコミットしないでください。
- OpenAI など外部 API 呼び出しは失敗耐性を持ちますが、API キーやレート制限は運用者で管理してください。
- monitoring は監視のため必ずしも KABUSYS_ENV を切り替えずに本番の監視 DB (SQLITE_PATH) を使用します。意図しない DB を参照しないよう .env を確認してください。
- process priority や CPU affinity の設定はプラットフォーム依存で失敗する場合があります（権限不足等）。ログに警告が出ますが処理自体は継続します。

---

## 参考コマンドまとめ

- .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動
  - python -m kabusys.run_execution
- 監視エンジン起動
  - MONITOR_POLL_INTERVAL=120 python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README は開発・運用のための概要をまとめたものです。詳細や API 仕様、内部設計については各モジュールの docstring とコードコメントを参照してください。必要であれば README を拡張して、より具体的なデプロイ手順や監視運用手順を追加できます。