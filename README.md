# KabuSys

KabuSys は日本株の自動売買・リサーチ・監視を目的とした軽量な Python パッケージです。  
このリポジトリには、戦略構築（ファクター計算・特徴量解析）、ポートフォリオ構築、発注エンジン、監視（モニタリング）、および AI 支援（ニュース NLP / レジーム判定）に関する主要ロジックが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

主な責務:

- データ分析用: DuckDB 経由のファクター計算・リサーチ機能（kabusys.research）
- ポートフォリオ構築: 候補抽出・重み付け・ポジションサイズ算出（kabusys.portfolio）
- 実行エンジン: 発注・注文管理・リスク制御（kabusys.execution ※実行エンジン本体は別モジュールに依存）
- 監視: システム稼働状況、注文・約定の監視、Kill Switch（kabusys.monitoring）
- AI: ニュースを LLM でスコア化してポートフォリオやレジーム判定に利用（kabusys.ai）
- ユーティリティ: ロギング設定、プロセス優先度制御、設定読み込みウィザードなど（kabusys.utils）
- CLI ツール: .env ウィザード、設定検証、ペーパートレード検証レポート 等

設計方針の一部:
- DuckDB を用いて分析データを高速に処理
- 本番（live）とペーパー（paper_trading）をロジック上で分離
- 外部 API 呼び出し（OpenAI など）は鍵が未設定時に安全にフォールバック
- .env の自動ロード・対話式生成・検証をサポート

---

## 機能一覧

- 環境設定
  - 対話式 .env ウィザード（kabusys.config_setup）
  - 設定ファイル / 環境変数の検証 CLI（kabusys.validate_config）
- 実行・監視
  - 実行エンジン起動スクリプト（run_execution.py）
    - KABUSYS_ENV=paper_trading で MockBroker を使いデータを分離
  - 監視（SystemMonitor）起動スクリプト（run_monitoring.py）
    - MONITOR_POLL_INTERVAL でポーリング間隔を変更可
    - kill.flag / stop_requested.flag による停止制御
- モニタリング
  - system_status / trade_logs / positions / risk_logs / dashboard の SQLite 永続化層
  - RiskMonitor によるドローダウン・ポジション上限検出
  - MonitoringEngine による複数モニタの定期実行とアラート連携
- ポートフォリオ構築
  - 候補選定、等比率 / スコア加重、リスクベースのポジションサイズ算出
  - セクターキャップ、レジーム乗数の適用
- リサーチ
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン計算、IC（情報係数）計算、統計サマリ
- AI（OpenAI）
  - ニュース記事のセンチメント評価（news_nlp）
  - 市場レジーム判定（regime_detector）
  - OpenAI API 呼び出しはリトライ・エラーハンドリング付き
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順

前提:
- Python 3.9+ を想定（コードは型注釈と最新ライブラリ構成に合わせているため）。
- SQLite は Python 標準ライブラリで提供されます。

依存パッケージ（最低限）:
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML (設定ファイル検証を行う場合に推奨)

例: 仮想環境作成とインストール
```
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install duckdb psutil openai pyyaml
```

プロジェクト初期化:
1. リポジトリルートに移動（プロジェクトルートは .git または pyproject.toml により自動検出されます）。
2. 対話式ウィザードで .env を作成:
   ```
   python -m kabusys.config_setup
   ```
   もしくは手動で .env を作成。必須環境変数:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

3. 設定検証:
   ```
   python -m kabusys.validate_config
   ```
   --strict を付けると警告も失敗扱いになります:
   ```
   python -m kabusys.validate_config --strict
   ```

ファイル・ディレクトリ（データ/ログ）の準備:
- デフォルトデータベース:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - ペーパートレード SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時）
- ログディレクトリ: logs/（setup_logging により自動作成を試みます）

注意:
- .env は絶対にリポジトリにコミットしないでください（config_setup.py でも注意書きあり）。

---

## 使い方

主要な起動・管理コマンド例を示します。

1. 実行エンジン（ExecutionEngine）起動
- 本番 / 開発 / ペーパー切替は環境変数 KABUSYS_ENV により制御します。
- 例: ペーパートレードで起動（MockBroker を利用し data/paper_trading.db に記録）
  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
- ストップはプロジェクトルートの `data/stop_requested.flag` を作成するか、監視側が `data/kill.flag` を書き込むことで実行エンジンに停止シグナルを送れます。

2. 監視プロセス起動
- SystemMonitor をポーリングで起動:
  ```
  python -m kabusys.run_monitoring
  ```
- ポーリング間隔を秒で変える（例: 30 秒間隔）
  ```
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
- monitoring は常に本番用 sqlite_path（.env の SQLITE_PATH）を使用します（監視用 DB を共有）。

3. .env ウィザード（再実行可）
```
python -m kabusys.config_setup
```

4. 設定検証（起動前チェック）
```
python -m kabusys.validate_config
```

5. Paper Trading 検証レポート生成
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# またはデフォルト DB を使用:
python -m kabusys.tools.paper_verification_report
```
- 環境変数 `PAPER_TRADING_SQLITE_PATH` で DB パスを指定できます。また CLI の `--db` オプションを使うことも可能です。

6. AI 機能（ニュース NLP / レジーム判定）
- OpenAI API キーを設定:
  ```
  export OPENAI_API_KEY=sk-...
  ```
- news_nlp や regime_detector の関数はパッケージ API として利用できます（例: kabusys.ai.score_news）。

ログ:
- ログは `logs/<app_name>.log`（例: logs/execution.log / logs/monitoring.log）に日次ローテーションで出力されます。コンソールは stdout に出力されます。

停止制御:
- `data/stop_requested.flag` を作成すると run_execution / run_monitoring のループはそれを検知して終了します。
- `data/kill.flag` は KillSwitch によって書き込まれ、ExecutionEngine 側で検知して停止するための安全装置です。KillSwitch はドローダウンやポジション上限等のトリガで作成されます。

---

## 設定項目（主要な環境変数）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DB/ログ:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパー用）
  - LOG_LEVEL: DEBUG|INFO|...（デフォルト: INFO）
  - LOG_DIR: ログ格納ディレクトリ（デフォルト: logs）
- AI:
  - OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- 監視関連:
  - MONITOR_POLL_INTERVAL: 監視ポーリング秒（run_monitoring が参照、デフォルト 60）
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START などは Settings クラスで管理

詳細は `src/kabusys/config.py` を参照してください（プロパティごとに説明があります）。

---

## ディレクトリ構成

以下は主要ソースの概要（パッケージルートは `src/kabusys`）:

- src/kabusys/
  - __init__.py                — パッケージ定義 (__version__)
  - config.py                  — 環境変数 / .env 自動ロード / Settings
  - config_setup.py            — 対話式 .env ウィザード（CLI）
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパー検証レポート生成スクリプト
  - ai/
    - __init__.py
    - news_nlp.py              — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py       — 市場レジーム判定（MA + LLM）
  - research/
    - __init__.py
    - factor_research.py       — Momentum / Volatility / Value ファクター
    - feature_exploration.py   — 将来リターン / IC / 統計サマリー
  - portfolio/
    - __init__.py
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 株数決定・投下スケール・単元丸め
    - risk_adjustment.py       — セクターキャップ・レジーム乗数
  - monitoring/
    - monitoring_db.py         — SQLite テーブル初期化・CRUD ユーティリティ
    - system_monitor.py        — システム状態 / データ鮮度チェック
    - trade_monitor.py         — （注文監視ロジックファイル）
    - risk_monitor.py          — ドローダウン / ポジション上限監視
    - kill_switch.py           — kill.flag 書き込みロジック
    - monitoring_engine.py     — 各 Monitor を束ねるエンジン
    - alert_manager.py         — （通知管理）
  - utils/
    - __init__.py
    - logging_setup.py         — 一貫したログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity 設定
  - portfolio, research, ai, monitoring の詳細実装は各ファイルを参照してください。

データ・ログ・フラグ:
- data/
  - monitoring.db (デフォルト SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - execution.pid, stop_requested.flag, kill.flag などの制御ファイル
- logs/
  - execution.log, monitoring.log, ...（日次ローテーション）

---

## 開発メモ / 注意点

- DuckDB へはパッケージ内で直接接続し、SQL で集計・ファクター計算を行っているため、分析用テーブル（prices_daily, raw_financials, raw_news など）の準備が必要です。
- AI 機能は OpenAI SDK を利用します。API キーが無い場合は例外が出る箇所もあるため、必要に応じて環境変数を設定してください（関数は明示的に api_key 引数を受け取れる設計）。
- run_execution はバックグラウンドスレッドで Engine を起動します。デバッグ時は thread.join の挙動などに注意してください。
- monitoring/monitoring_db.py はスキーマのマイグレーションを簡易に扱います（カラム追加処理など）。運用時の DB の取り扱いには注意してください。

---

上記はこのコードベースの概要と運用開始までの最低限の手順です。各モジュールの詳細な仕様や拡張（strategy/ execution の各コンポーネント実装、ブローカークライアント等）は対応するソースファイルと設計ドキュメント（PortfolioConstruction.md, StrategyModel.md など）を参照してください。必要であれば README を英語版にしたり、稼働手順をユースケース別に追記することも可能です。