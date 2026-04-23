# KabuSys — 日本株自動売買フレームワーク

このリポジトリは日本株向けの自動売買／リサーチ基盤のプロトタイプ実装です。  
主要な機能として、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、LLM を使ったニュース NLP（OpenAI）などのユーティリティ群を含みます。

主な設計思想
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV に依存）
- DuckDB を分析用途に利用、SQLite を軽量な監視／履歴用 DB に利用
- 環境設定は .env を経由して行い、対話式ウィザード・検証ツールを提供
- LLM 呼び出しはフェイルセーフでリトライ・部分書き込みを行う（部分失敗による既存データ消失を回避）

---

## 機能一覧

- 起動スクリプト
  - run_execution.py: 発注エンジン ExecutionEngine を起動
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔上書き可）
- 環境設定
  - config_setup.py: 対話式 .env ウィザード
  - validate_config.py: .env および config/*.yaml の事前検証 CLI
- 監視
  - monitoring/*: SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine、SQLite の永続化層
  - MonitoringDB: system_status, trade_logs, positions, risk_logs, dashboard テーブル定義とマイグレーション
- 発注（Execution）
  - execution/*: BrokerClientFactory、ExecutionEngine、OrderManager、RiskManager、Reconciler、OrderRepository 等
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、data/paper_trading.db に記録
- ポートフォリオ構築
  - portfolio/*: 候補選定、重み付け、セクター制約、ポジションサイズ計算などの純粋関数群
- リサーチ
  - research/*: ファクター計算（モメンタム / バリュー / ボラティリティ）、将来リターン、IC 計算、統計サマリー
  - DuckDB を使った SQL + Python 実装
- AI（LLM 統合）
  - ai/news_nlp.py: ニュースを集約して OpenAI でセンチメント生成 → ai_scores に書込
  - ai/regime_detector.py: ETF の MA200 乖離とマクロニュースを組合せて市場レジーム判定・書込
- ツール
  - tools/paper_verification_report.py: ペーパートレード履歴の検証レポート生成（稼働率 / 成功率 / レイテンシ 等）
- ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定（コンソール + 日次ローテーション）
  - utils/process_priority.py: プラットフォーム非依存のプロセス優先度設定

---

## セットアップ手順

前提
- Python 3.10+（型注釈や union 型表記に対応したバージョンを推奨）
- Git リポジトリをクローンしてプロジェクトルートに移動

推奨パッケージ（最低限）
- duckdb
- psutil
- openai
- pyyaml（config 検証時に YAML 検査を行うため）

例（venv を使ったインストール）
```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install duckdb psutil openai pyyaml
```

.env の準備
1. 対話式ウィザードで初期 .env を作成（推奨）
```bash
python -m kabusys.config_setup
```
2. 作成済みの .env があればプロジェクトルートに配置してください（.env は絶対にコミットしないでください）。

必須環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）※デフォルト: development

主要なデフォルトパス（.env 未設定時）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading モード用）
- LOG_DIR: logs/
- PID/FLAG: data/execution.pid, data/kill.flag, data/stop_requested.flag

ログディレクトリ
- デフォルトは logs/ に日次ローテーションでログファイルを出力します（例: logs/execution.log）。

---

## 使い方

基本的な起動コマンド例（プロジェクトルートから実行）

- 設定検証（起動前に推奨）
```bash
python -m kabusys.validate_config
# 警告も失敗にしたい場合は --strict を付ける
python -m kabusys.validate_config --strict
```

- 発注エンジン起動（ExecutionEngine）
  - 開発（デフォルト: KABUSYS_ENV=development）では発注は行われません
  - ペーパートレード: KABUSYS_ENV=paper_trading と設定すると MockBrokerClient を用い、paper_trading DB に記録
```bash
# 例: paper_trading で起動
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution
```

- 監視ループ起動（SystemMonitor のポーリング）
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）
```bash
# ポーリング間隔を 30 秒に変更して起動
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```

- Paper Trading 検証レポート生成
```bash
# デフォルト DB を参照
python -m kabusys.tools.paper_verification_report

# 期間を指定
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# DB パスを指定
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

- AI スコアリング / レジーム判定（ライブラリ関数として呼び出し）
  - OpenAI API キーは env OPENAI_API_KEY、または関数引数で渡す
  - 例: news_nlp.score_news(conn, target_date, api_key="...")
  - これらは DuckDB 接続（duckdb.connect(...)）を渡して使用します

停止・運用に関するフラグ
- data/stop_requested.flag: run_execution / run_monitoring が存在を検知すると終了するための開発用停止フラグ
- data/kill.flag: KillSwitch により ExecutionEngine を強制停止するためのフラグ（監視コンポーネントが書き込む）
- data/execution.pid: ExecutionEngine の PID ファイル（起動時に設定）

監視 / アラート
- MonitoringEngine は SystemMonitor / TradeMonitor / RiskMonitor を結合し、条件に応じて KillSwitch を発動・AlertManager 経由で通知します（AlertManager 実装はプロジェクト内に応じて拡張します）。

---

## よく使う環境変数（一覧）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: 必須
- KABU_API_PASSWORD: 必須
- KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI 呼出しに使用
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。run_monitoring 用）

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要なファイル/ディレクトリ構成です。

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — SystemMonitor ポーリング起動スクリプト
  - config.py                       — Settings（.env 自動読み込み / accessors）
  - config_setup.py                 — 対話式 .env 作成ウィザード
  - validate_config.py              — 起動前設定検証 CLI
  - tools/
    - __init__.py
    - paper_verification_report.py   — ペーパートレード検証レポート
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュース NLP → ai_scores 書込（OpenAI 統合）
    - regime_detector.py             — 市場レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py               — SQLite テーブル定義 + MonitoringDB
    - monitoring_engine.py           — 各 Monitor を束ねる実行ループ
    - system_monitor.py              — システム・データ鮮度監視
    - risk_monitor.py                — ドローダウン・ポジション上限監視
    - trade_monitor.py               — （実装参照 / 注文監視）
    - kill_switch.py                 — Kill Switch 実装（flag ファイル操作）
    - alert_manager.py               — （アラート送信ロジック）
  - execution/
    - broker_factory.py              — BrokerClientFactory（本番 / mock 分岐）
    - execution_engine.py            — ExecutionEngine（発注セッション）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - ...（発注系コンポーネント）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/                            — 実行時に使用されるファイル（DB / flag / pid）※リポジトリに含めない

注: 上記は主要ファイルの抜粋です。テストや補助スクリプトは別途含まれることがあります。

---

## 運用上の注意点 / ヒント

- 本番運用前に必ず `python -m kabusys.validate_config` で設定検証を行ってください。
- KABUSYS_ENV=paper_trading を使うと本番 DB と完全分離されたペーパー用 DB に記録されます。運用ミスで本番発注しないよう本番設定は慎重に扱ってください。
- OpenAI を利用する機能（news_nlp, regime_detector）は API キーと課金が必要です。API 呼び出しの失敗時は安全にフォールバックする実装ですが、テスト時はモックしてください（各モジュールの _call_openai_api はパッチ可能）。
- ログはデフォルト logs/ に出力されます。cron / systemd で起動する場合は stdout/stderr の扱いに注意してください（logging_setup は stdout を使います）。
- stop / kill フラグはファイルベースで扱います（data/stop_requested.flag, data/kill.flag）。自動化や運用 UI を作る場合はこれらの存在確認・操作に留意してください。

---

必要があれば、README を拡張して下記を追加します。
- requirements.txt の例
- systemd ユニットファイル例
- より詳細な .env.example
- 各コンポーネントの API / 設計ドキュメント（関数シグネチャ一覧）