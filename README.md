# KabuSys

日本株向け自動売買システムのコードベース（README）。以下はリポジトリ内の主要スクリプト・モジュールをもとに作成した日本語ドキュメントです。

> 注意: .env は機密情報を含むので絶対にリポジトリにコミットしないでください。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能を提供するモジュール群から構成されるシステムです。

- 発注エンジン（ExecutionEngine）
- 監視（Monitoring）・アラート・Kill Switch
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- 研究用ファクター計算・特徴量解析（DuckDB を利用）
- ニュース NLP / レジーム判定（OpenAI を利用したセンチメント評価）
- 各種ユーティリティ（ログ設定、プロセス優先度設定など）
- CLI ツール（.env ウィザード、設定検証、Paper Trading レポート作成）

設計方針の一部：
- DuckDB を分析用 DB として使用、SQLite は監視/発注履歴用。
- Paper Trading（ペーパートレード）は本番 DB と分離して専用 SQLite を使用。
- 外部 API 呼び出し（OpenAI 等）は明示的に API キーが必要。
- 起動スクリプトはモジュールとして起動でき、ログ・PID・フラグファイルで外部制御が可能。

---

## 機能一覧（主な機能）

- Execution（発注）
  - Broker クライアント生成（実口座 or Mock）
  - OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動
  - ペーパートレード時は専用 SQLite（デフォルト: `data/paper_trading.db`）

- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、Execution プロセス生死を監視
  - TradeMonitor: 発注ログ監視（滞留注文・約定異常等）
  - RiskMonitor: ドローダウン・ポジション上限の監視、ダッシュボード更新
  - KillSwitch: 条件トリガーで `data/kill.flag` を書き込み、ExecutionEngine を停止
  - MonitoringEngine: 上記をまとめてポーリングしアラートや Kill Switch を評価

- Portfolio（銘柄選定・配分）
  - 候補選定（スコア順、上位 N）
  - 等金額・スコア加重の重み計算
  - セクター上限適用（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
  - ポジションサイズ計算（lot 単位丸め、aggregate cap 適用）

- Research（研究）
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
  - DuckDB 接続を受けて SQL + Python で完結

- AI（ニュース NLP / レジーム判定）
  - raw_news を集約して OpenAI に投げ、銘柄ごとにセンチメント（-1.0〜1.0）を算出し ai_scores に保存
  - ETF（1321）やマクロニュースを使って日次の市場レジーム（bull/neutral/bear）を判定して永続化
  - OpenAI 呼び出しはリトライ・バリデーション・スコアクリップなどの安全策あり

- ツール類
  - 環境設定ウィザード: `python -m kabusys.config_setup`（対話式で .env を生成）
  - 設定検証: `python -m kabusys.validate_config`（.env と config/*.yaml のチェック）
  - Paper Trading 検証レポート: `python -m kabusys.tools.paper_verification_report`（期間指定可）

---

## 必要な環境変数（主要）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- OpenAI 関連（AI 機能を使う場合）
  - OPENAI_API_KEY

- 使用可能／デフォルト
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: デフォルト `data/kabusys.duckdb`
  - SQLITE_PATH: デフォルト `data/monitoring.db`
  - PAPER_TRADING_SQLITE_PATH: デフォルト `data/paper_trading.db`（KABUSYS_ENV=paper_trading 時に使用）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - LOG_DIR: ログディレクトリ（デフォルト: logs/）
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など（Settings 参照）

注意点:
- `.env` は config_setup で生成可能（`python -m kabusys.config_setup`）。
- 自動で .env を読み込むロジックはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（ローカル開発）

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（代表例）
   - pip install duckdb psutil openai PyYAML
   - その他、発注先ブローカー用のライブラリなどがある場合は個別にインストールしてください。

3. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは `.env` を手動作成して必要な環境変数を設定してください。

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする: python -m kabusys.validate_config --strict

5. データディレクトリの作成（必要なら）
   - デフォルトでは `data/`、`logs/` ディレクトリが使用されます。多くは起動時に自動作成されますが、パーミッション等を事前に確認しておくと安全です。

---

## 使い方（起動コマンド例）

- ExecutionEngine を起動（通常）
  - python -m kabusys.run_execution
  - 実行中は `data/execution.pid`（デフォルト）などの PID ファイルを作成します。
  - ExecutionEngine は停止フラグ `data/stop_requested.flag` の存在を監視しており、ファイルが存在すると起動しない／実行中に停止します。

- Monitoring を起動（ポーリング監視）
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  - run_monitoring は監視ログ用の SQLite（Settings.sqlite_path）を本番パスで常に使用します（KABUSYS_ENV に関係なく本番監視DBを参照）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を直接指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 `PAPER_TRADING_SQLITE_PATH` でも指定可。

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

停止方法（運用上の注意）:
- 実行中の Engine を安全に停止するには、monitoring 側や管理者が `data/kill.flag` を書き込むか `data/stop_requested.flag` を作成します。KillSwitch による自動書き込みは risk 条件（ドローダウンやポジション上限）により行われます。
- `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動で kill.flag をクリアしますが、本番では危険な設定なので注意してください（デフォルトは 0）。

ログ:
- ロギングは統一された設定関数を使っており、ログファイルは `<LOG_DIR>/<app_name>.log`（デフォルト `logs/<app_name>.log`）に日次ローテーションで保存されます。

---

## 重要な動作・実装メモ

- run_monitoring は監視用 DB を開き、MonitoringEngine 相当の処理をポーリング実行します。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で制御可能（デフォルト 60 秒）。不正な値（0以下や非整数）が設定されるとデフォルトにフォールバックします。
- run_execution は KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使って発注を擬似化し、ペーパートレード用 SQLite（`PAPER_TRADING_SQLITE_PATH`）を使用して本番 DB と完全に分離します。
- Monitoring の DB 初期化処理（init_monitoring_db）は冪等であり、欠落カラムへのマイグレーション処理も含みます（例: `latency_ms` カラムの追加など）。
- AI モジュールは OpenAI API を利用します。API 呼び出しはリトライやレスポンスの厳格なバリデーションを行い、スコアは安全にクリップ（±1.0）して保存します。OpenAI SDK の種類やバージョン差分に配慮した実装になっています。
- process priority / CPU affinity の設定ユーティリティ（psutil 利用）を提供。権限不足や未対応 OS の場合は警告を出して安全にスキップします。

---

## ディレクトリ構成（主なファイル）

リポジトリの `src/kabusys` 下の主要ファイル/パッケージ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings 管理
  - config_setup.py            — .env 対話ウィザード
  - validate_config.py         — 起動前チェック CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - execution/                 — 発注関連コンポーネント（Engine, OrderManager, RiskManager, BrokerFactory 等）
  - monitoring/
    - monitoring_db.py
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
  - utils/
    - logging_setup.py
    - process_priority.py

（上記以外に data/, logs/ 等の運用ディレクトリを使用します。）

---

## 依存関係（代表的なライブラリ）

- duckdb
- psutil
- openai
- PyYAML（config 検証で使用、存在しない場合は YAML 検証をスキップ）
- 標準ライブラリ（sqlite3, logging, threading, datetime, pathlib 等）

インストール例:
- pip install duckdb psutil openai PyYAML

---

## 開発上の注意事項

- 本番（KABUSYS_ENV=live）では LINE 通知や kill flag の設定に注意してください。validate_config は本番向けのガード（設定漏れや危険設定の警告）を出します。
- Paper Trading は本番 DB と物理的に分離されますが、コード上の想定（API の振る舞い等）に差がある場合は検証が必要です。
- DuckDB のバインドや executemany の挙動はバージョン差で制約があります（コード内に互換性対策あり）。

---

## 補足（よく使うコマンドまとめ）

- .env ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

この README はソース内の docstring / コメントを元に要点をまとめたものです。実運用前に必ず `python -m kabusys.validate_config` で設定チェックを行い、テスト環境で各機能（特に発注・AI 呼び出し部分）を慎重に検証してください。