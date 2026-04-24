# KabuSys

日本株自動売買システムの軽量実装。戦略の研究・ファクター計算、ポートフォリオ構築、注文実行エンジン（本番／ペーパートレード）、監視（Monitoring）や AI（ニュース NLP / レジーム判定）などのコンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要コンポーネントで構成されます。

- ExecutionEngine（発注実行）  
  - 本番口座／ペーパートレード切替対応。ペーパートレードでは MockBrokerClient を利用し DB を分離（`data/paper_trading.db`）。
- Monitoring（監視）  
  - システム状態（CPU/メモリ/ディスク）、データ鮮度、注文状況、リスク（ドローダウン・ポジション上限）を定期チェックし、kill flag の書き込みやアラート通知を行う。
- Research / Factor 計算  
  - DuckDB を使った価格・財務データのファクター計算（モメンタム、ボラティリティ、バリュー等）。
- Portfolio（銘柄選定・配分・ポジションサイズ計算）  
  - 候補選定・等比率・スコア加重、リスク調整（セクター上限、レジーム乗数）、株数決定（ロット丸め・aggregate cap）。
- AI モジュール（ニュース NLP / レジーム判定）  
  - OpenAI を用いたニュースのセンチメント計測やマクロセンチメントと ETF MA を合成した市場レジーム判定。
- ユーティリティ  
  - 環境設定ウィザード、設定検証、Paper Trading 検証レポート生成など。

---

## 主な機能一覧

- ExecutionEngine 起動スクリプト（run_execution）
  - `KABUSYS_ENV=paper_trading` でペーパートレードに切替（DB 分離）
  - プロセス優先度の設定、PID ファイル管理、停止フラグ検知
- Monitoring 起動スクリプト（run_monitoring）
  - 定期ポーリング（環境変数で間隔変更可）
  - system / trade / risk モニタを統合して kill flag を評価
- 環境設定ウィザード（config_setup） & 設定検証 CLI（validate_config）
- Paper Trading 検証レポート生成（tools.paper_verification_report）
- DuckDB を用いたファクター計算（research）
- ニュース NLP とレジーム判定（OpenAI 利用）
- ログ管理ユーティリティ（stdout + 日次ローテートファイル）

---

## セットアップ手順（開発/ローカル向け）

1. Python バージョン
   - Python 3.10 以上を推奨（型ヒントに `|` を使用しているため）。

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリのインストール（例）
   - pip install duckdb psutil openai
   - 任意: PyYAML（`validate_config` の YAML 検証用）: pip install pyyaml

4. 環境変数の準備（.env）
   - 対話式ウィザードで初期 .env を生成:
     - python -m kabusys.config_setup
   - 生成後は設定を検証:
     - python -m kabusys.validate_config
   - 自動ロード:
     - プロジェクトルートの `.env` / `.env.local` は実行時に自動で読み込まれます（無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

5. データ・ログ用ディレクトリ
   - デフォルトで以下ファイルが参照/作成されます:
     - data/monitoring.db (SQLite, 監視用)
     - data/paper_trading.db (ペーパートレード用)
     - data/kabusys.duckdb (DuckDB)
     - logs/（ログファイルを出力）
   - 実行時にディレクトリが自動作成されますが、適切な権限を確認してください。

---

## 重要な環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API 用パスワード

- 実行環境
  - KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）

- DB / ログ
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
  - LOG_LEVEL（"DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"、デフォルト: INFO）
  - LOG_DIR（ログの出力先、デフォルト: logs/）

- 実行／監視制御
  - PID_FILE_PATH（実行エンジンの pid ファイル、デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（kill flag のパス、デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。0/1。デフォルト: 0）
  - MONITOR_POLL_INTERVAL（監視ポーリング間隔（秒）。run_monitoring で参照。デフォルト: 60）
  - PAPER_FILL_MODE（ペーパートレードの約定挙動: "instant" / "partial" / "never" / "reject"。デフォルト: "instant"）

- OpenAI
  - OPENAI_API_KEY — ニュース NLP / レジーム判定で使用（必要な処理のみ）

例（.env の抜粋）
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-xxxx
```

---

## 使い方（主要コマンド）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

- ExecutionEngine 起動（デフォルトは Settings に従う）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV により本番/ペーパーの挙動が変わる
  - 停止: プロセスに割り当てられた PID ファイル（デフォルト data/execution.pid）を参照した停止や、data/stop_requested.flag (run_execution 内で監視) を利用

- Monitoring 起動（ポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI / レジームスコア等はそれぞれモジュール関数を呼び出すか、将来的な CLI を利用してください。実行には `OPENAI_API_KEY` が必要です。

---

## ログ・停止フラグ・PID

- ログ
  - デフォルト: logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）
  - stdout とファイル（TimedRotatingFileHandler、日次ローテーション）に同時出力

- 停止制御
  - 実行エンジン（ExecutionEngine）は以下のフラグファイルをチェック:
    - data/stop_requested.flag — 外部から強制停止を指示するための一時ファイル（run_* スクリプトで使用）
    - data/kill.flag — KillSwitch による自動停止トリガー（監視コンポーネントが書き込む）
  - PID 管理: data/execution.pid（Engine が起動時に作成）

---

## Monitoring DB（SQLite） — 主要テーブル

起動時に `init_monitoring_db()` により自動作成されます（冪等）。

主なテーブル:

- system_status (recorded_at, cpu_percent, memory_percent, disk_percent, process_ok)
- trade_logs (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
- positions (code PRIMARY KEY, qty, avg_price, current_price, updated_at)
- risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
- dashboard (id=1 固定行で集計値を保持。portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value)

Monitoring 用ユーティリティクラス: `kabusys.monitoring.monitoring_db.MonitoringDB`

---

## ディレクトリ構成（抜粋）

src/ 配下の主要ファイル・ディレクトリ:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/                — Execution 関連（BrokerFactory, Engine, OrderManager 等）
  - utils/
    - logging_setup.py
    - process_priority.py

（リポジトリ全体の詳細は実際のソースツリーを参照してください）

---

## 開発・運用時の注意点

- KABUSYS_ENV が `live` の場合は設定ミスが重大な影響を及ぼします。`validate_config --strict` で事前チェックを推奨します。
- OpenAI を利用する処理は API キーが必要です。API 呼び出しの失敗はフェイルセーフとして多くの箇所でフォールバック（スコア 0.0 等）する設計ですが、API 使用によるコストやレート制限に注意してください。
- DuckDB / SQLite のパスは環境変数で上書き可能です。運用時はバックアップ・適切な配置を検討してください。
- ログディレクトリや data ディレクトリの書き込み権限に注意してください。ログファイルのローテーションは設定済み（30日保持）。

---

## 参考・次のステップ

- .env を作成したら必ず:
  - python -m kabusys.validate_config
- 開発中は KABUSYS_ENV=development で安全に動作確認
- ペーパートレード検証:
  - KABUSYS_ENV=paper_trading をセットして発注フロー・検証レポートを確認

---

README はプロジェクトの要点をまとめたものです。詳細は各モジュールの docstring（ソース内コメント）を参照してください。追加で API ドキュメントや運用手順（systemd / supervisor 用のユニット例等）が必要であれば、そのテンプレートを作成します。必要なら教えてください。