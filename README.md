# KabuSys — 日本株自動売買システム (README)

以下はこのリポジトリ（src/kabusys）の概要と使い方ガイドです。  
コード内の設計方針や CLI ツールを反映した実用的な手引きになっています。

---

## プロジェクト概要

KabuSys は日本株自動売買システムの参照実装です。  
主な目的は次の通りです。

- 戦略（ファクター計算・シグナル生成）とポートフォリオ構築のための研究モジュール（DuckDB を利用）
- 実際の発注処理を行う ExecutionEngine（kabuステーション等のブローカークライアントを抽象化）
- システム稼働・リスク監視と Kill Switch（フラグファイルによる安全停止）
- Paper Trading 用の分離された DB を用いた検証機能
- ニュース NLP / レジーム判定のための OpenAI（LLM）連携

設計上の特徴：
- 環境変数・.env による設定管理（自動読み込み）*
- DuckDB（分析用）と SQLite（監視・発注ログ）を併用
- プロセス優先度 / CPU affinity 管理、ログの日次ローテーション、堅牢なエラーハンドリング
- 本番／ペーパーの DB 分離や、起動・停止フラグファイルによる運用管理

\* .env 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。

---

## 主な機能一覧

- 設定管理
  - 対話式ウィザードで `.env` を生成/更新（kabusys.config_setup）
  - 起動前の設定検証ツール（kabusys.validate_config）

- 実行・監視
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）
    - `KABUSYS_ENV=paper_trading` では MockBroker を用い、paper DB（デフォルト data/paper_trading.db）へ記録
  - Monitoring ポーリング（kabusys.run_monitoring）
    - システム状態・注文ログ・リスク監視を定期実行、Kill Switch を評価

- ポートフォリオ構築（純粋関数）
  - 候補選定、等配分/スコア加重、ポジションサイズ計算、セクターキャップ、レジーム乗数

- 研究・ファクター計算（DuckDB）
  - momentum / volatility / value 等のファクター計算（prices_daily, raw_financials 参照）
  - 将来リターン計算、IC 計算、統計サマリ

- AI（LLM）連携
  - ニュースのセンチメントスコアリング（kabusys.ai.news_nlp）
  - マクロニュースと ETF MA を用いた市場レジーム判定（kabusys.ai.regime_detector）
  - OpenAI API を利用（モデル: gpt-4o-mini を想定）

- 運用ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順

以下はローカル開発 / 試験的運用の最低限の手順です。

前提
- Python 3.10+ を推奨（typing の一部注釈に依存）
- システムに応じたネイティブパッケージ（psutil 等）をインストール可能であること

依存パッケージ（例）
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config/*.yaml の検証を行う場合に任意）

インストール例（venv 推奨）
- python -m venv .venv
- source .venv/bin/activate
- pip install -U pip
- pip install duckdb psutil openai pyyaml

環境変数（必須）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / 推奨の設定（デフォルトがあるものも含む）
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（又は DEBUG 等）
- OPENAI_API_KEY: OpenAI を使用する場合に必要

.env を対話式で作成する（推奨）
- python -m kabusys.config_setup
  - 画面の指示に従って .env を作成します（.env は絶対に Git 管理しないでください）

設定検証
- python -m kabusys.validate_config
  - `--strict` を付けると警告も失敗扱いになります

ログディレクトリ
- デフォルトで `logs/` に日次ローテーションでログが保存されます。`LOG_DIR` 環境変数で変更可。

---

## 使い方（主なコマンド・実行例）

基本的にモジュールは CLI 実行用に `python -m kabusys.<module>` で呼びます。

1. .env の作成（対話式）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - 厳密モード: python -m kabusys.validate_config --strict

3. ExecutionEngine 起動（実際の発注ロジックを実行）
   - python -m kabusys.run_execution
   - 備考:
     - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使い、paper_trading DB（PAPER_TRADING_SQLITE_PATH）へ記録します
     - 起動時に `data/stop_requested.flag` が存在する場合は起動しません
     - 実行中は `data/execution.pid` に PID が記録され、停止はフラグファイル `data/stop_requested.flag` や kill.flag によって行える仕組みがある

4. Monitoring 起動（ポーリング）
   - python -m kabusys.run_monitoring
   - 環境変数 `MONITOR_POLL_INTERVAL`（秒）で間隔を上書き可能（デフォルト 60 秒）
   - Monitoring は Settings の sqlite_path（監視 DB）を使用（環境によらず本番 sqlite_path を参照）

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
   - 簡易的な稼働率、注文成功率、レイテンシ指標などを出力します

6. AI 機能（ニュース NLP / レジーム判定）
   - OpenAI API キーが必要: `OPENAI_API_KEY` を環境変数に設定
   - ニューススコア付け（プログラムから呼ぶ API）:
     - from kabusys.ai.news_nlp import score_news
     - score_news(duckdb_conn, target_date, api_key=None)  # api_key を明示的に渡すことも可
   - レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(duckdb_conn, target_date, api_key=None)

運用上のファイル・フラグ
- data/kill.flag : KillSwitch が立てるフラグ（ExecutionEngine に停止シグナル）
- data/stop_requested.flag : 起動スクリプトからの外部停止要請（プロセスを安全に終了）
- data/execution.pid : ExecutionEngine の PID（存在/鮮度チェックに利用）

---

## 主要な設定項目（要点）

- KABUSYS_ENV: development / paper_trading / live
  - paper_trading は本番 DB と分離された paper DB を使用
- DUCKDB_PATH: DuckDB ファイル（分析データ）
- SQLITE_PATH: 監視用 SQLite（system_status / trade_logs / positions / risk_logs / dashboard）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（paper_trading 実行時に使用）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒）
- LOG_LEVEL / LOG_DIR: ログ出力の調整
- OPENAI_API_KEY: OpenAI を使う場合に必須
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（本番では 0 推奨）

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数/.env の読み込みと Settings
    - config_setup.py          — .env の対話式ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — Monitoring ポーリング起動スクリプト
    - tools/
      - paper_verification_report.py  — Paper Trading レポート生成
    - portfolio/
      - portfolio_builder.py   — 候補選定・重み計算
      - position_sizing.py     — 株数決定・スケーリング
      - risk_adjustment.py     — セクター制限・レジーム乗数
    - research/
      - factor_research.py     — momentum/value/volatility 等の計算（DuckDB）
      - feature_exploration.py — 将来リターン・IC・統計サマリ
    - ai/
      - news_nlp.py            — ニュース NLP（OpenAI 呼び出し・スコア集約）
      - regime_detector.py     — レジーム判定（ETF MA + マクロ NLP）
    - monitoring/
      - monitoring_db.py       — SQLite のスキーマと永続化ユーティリティ
      - system_monitor.py      — システム状態・データ鮮度監視
      - trade_monitor.py       — （注文周りの監視: 省略ファイル群に依存）
      - risk_monitor.py        — ドローダウン・保有数監視
      - kill_switch.py         — Kill Switch フラグの管理
      - monitoring_engine.py   — 各モニタを束ねる実行器
      - alert_manager.py       — （通知管理。省略されている実装に依存）
    - utils/
      - logging_setup.py       — 統一的なログ設定（stdout + 日次ファイルローテーション）
      - process_priority.py    — プロセス優先度・CPU affinity 管理
    - data/                    — 実行時に作成されるファイル（DB / pid / flags / logs 等）

---

## 運用上の注意点 / ベストプラクティス

- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- 本番（KABUSYS_ENV=live）では `KILL_FLAG_CLEAR_ON_START=0` を推奨します（自動クリアは危険）。
- Monitoring はデフォルトで SQLite の `SQLITE_PATH` を使用します（paper_trading でも監視 DB は本番の sqlite_path を参照します。run_execution は paper_trading 時に paper DB を使う点に注意）。
- OpenAI 等の外部 API を利用する部分は、API キー管理・レート制限・リトライで設計されていますが、本番ではキーやコスト管理に注意してください。
- ログディレクトリ作成が失敗した場合、ファイル出力は無効化されコンソール出力のみになります（setup_logging の挙動）。
- Execution 起動前に `python -m kabusys.validate_config` で設定をチェックすることを推奨します。

---

## 参考コマンドまとめ

- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

---

必要であれば、README に含めるサンプル .env テンプレートや、より詳細な運用手順（systemd ユニットや cron の例）、データベース初期化手順、テスト方法なども追記できます。どの情報を優先して拡充しますか？