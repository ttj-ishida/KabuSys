# KabuSys

日本株向け自動売買システムの参照実装です。  
本リポジトリはトレードのシグナル生成・ポートフォリオ構築・発注実行（本番/ペーパートレード）・監視・レポート・研究ユーティリティを含みます。

Version: 0.1.0

---

## 概要

- DuckDB を使ったリサーチ/ファクター計算
- SQLite を使った監視ログ / 発注履歴保存
- ExecutionEngine による発注実行（本番またはペーパートレード分離）
- MonitoringEngine によるシステム/取引監視、Kill Switch による安全停止
- LLM（OpenAI）を用いたニュース NLP（センチメント）および市場レジーム判定
- ペーパートレード検証レポートの生成ユーティリティ

設計方針の一部：
- 環境に依存する設定は .env で管理（自動ロード機能あり）
- ペーパートレードは本番 DB と分離（デフォルト: `data/paper_trading.db`）
- モジュールはテスト可能な純粋関数群と状態管理層に分離

---

## 主な機能一覧

- 実行系
  - ExecutionEngine（発注ロジック、リスク制御、オーダーマネージャ）
  - BrokerClientFactory（実ブローカー / Mock の切替）
- 監視系
  - SystemMonitor（CPU／メモリ／ディスク、データ鮮度、実行プロセス検出）
  - TradeMonitor（滞留注文や約定異常の検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件で `data/kill.flag` を書いて ExecutionEngine を停止）
  - MonitoringEngine（上記を束ねて定期実行）
- ポートフォリオ構築
  - 候補選定、重み付け、ポジションサイズ計算、セクターキャップ、レジーム乗数
- リサーチ・統計
  - ファクター計算（Momentum/Volatility/Value 等）
  - 将来リターン、IC 計算、統計サマリー
- AI 支援
  - ニュースセンチメント（OpenAI を利用）
  - 市場レジーム判定（MA + マクロセンチメントの合成）
- ツール
  - 環境設定ウィザード（`.env` 生成 / 更新）
  - 設定検証 CLI（`.env` と config/*.yaml の検証）
  - Paper Trading 検証レポート生成

---

## セットアップ手順

1. Python 環境を作る（推奨: 3.10+）
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate

2. 依存パッケージをインストール
   - 最低限推奨パッケージ:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML (config/*.yaml 検証を行う場合)
   - 例:
     - pip install duckdb psutil openai pyyaml

   > 実プロジェクトでは requirements.txt を用意して pip install -r で管理してください。

3. .env 作成（推奨）
   - ウィザードを使う:
     - python -m kabusys.config_setup
   - 手動で作成する場合は `config_setup.py` の項目を参照して `.env` を作成してください。
   - 自動ロード:
     - プロジェクトルートに `.env` / `.env.local` がある場合、起動時に自動で読み込まれます。
     - テスト等で自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. 設定の検証（任意）
   - python -m kabusys.validate_config
   - 警告を失敗にしたい場合は `--strict` を付ける

5. データディレクトリの確認
   - デフォルトの DB / ログファイルは `data/` と `logs/` に保存されます。起動スクリプトが自動作成しますが、権限等に注意してください。

---

## 主要な環境変数（主なもの）

- 認証 / API
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - OPENAI_API_KEY (AI 機能を使う場合)
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (通知用、任意)

- システム / パス
  - KABUSYS_ENV: execution の動作環境（development / paper_trading / live）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（default: data/paper_trading.db）
  - LOG_DIR: ログ保存ディレクトリ（default: logs/）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...）

- ペーパートレード挙動
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

- 監視
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等（Settings 経由で取得）

---

## 実行方法（代表例）

各スクリプトはパッケージモジュールとして実行できます（パッケージが PYTHONPATH にある前提）。

1. 環境セットアップ（例）
   - export KABUSYS_ENV=paper_trading
   - python -m kabusys.config_setup
   - python -m kabusys.validate_config

2. ExecutionEngine 起動
   - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード用 DB (`PAPER_TRADING_SQLITE_PATH`) に記録します。
     - 正常起動時は PID ファイル（デフォルト `data/execution.pid`）を設定します。
     - 停止は `data/stop_requested.flag`（スクリプトの存在チェック）または `data/kill.flag`（KillSwitch）で制御可能。

3. Monitoring 起動
   - python -m kabusys.run_monitoring
   - 挙動:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
     - Monitoring は KABUSYS_ENV に関わらず production の sqlite_path を使用します（監視は本番 DB を参照する設計）

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB: `data/paper_trading.db`。`--db` でパス指定可。

5. AI 関連（ニュース NLP / レジーム判定）
   - `kabusys.ai.news_nlp.score_news` / `kabusys.ai.regime_detector.score_regime` を呼び出す（スクリプトはライブラリ関数として利用）。
   - 実行には `OPENAI_API_KEY` の設定が必要。

---

## 停止・Kill Switch

- 手動停止（run_monitoring / run_execution のループを止める）
  - ファイル: `data/stop_requested.flag` を作成するとループは検知して終了します（run_* スクリプトで使用）。
- 自動停止（リスク条件による）
  - KillSwitch がトリガー条件を満たすと `data/kill.flag` を書き込み、ExecutionEngine 側が検出して停止します。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定していると起動時に kill.flag を自動クリアします（本番では `0` 推奨）。

---

## ログ・DB

- ログ:
  - デフォルト: logs/<app_name>.log（日次ローテーション、30日保持）
  - stdout にも出力されます（systemd / cron からの運用を想定して stdout を利用）
- SQLite（監視）:
  - デフォルト: data/monitoring.db（monitoring 用テーブルを init します）
- DuckDB（分析 / リサーチ）:
  - デフォルト: data/kabusys.duckdb

---

## 開発向けメモ

- .env の自動ロード
  - プロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を読み込みます。
  - テストで自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

- モジュール設計
  - 事前に DB スキーマ作成を行う関数（init_monitoring_db）があります。冪等性を考慮しているため何度呼んでも安全です。
  - AI 呼び出し部はリトライ・バックオフ・レスポンス検証などフェイルセーフ実装あり。

---

## ディレクトリ構成（主要ファイル）

以下はソースツリー（`src/kabusys` 以下）の主要モジュールと簡単な説明です。

- kabusys/
  - __init__.py — パッケージ初期化（バージョン等）
  - config.py — 環境変数 / Settings 管理、.env 自動ロード
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring のポーリングループ起動スクリプト

  - execution/
    - broker_factory.py — ブローカークライアント生成（実ブローカー / Mock 切替）
    - execution_engine.py — 実行エンジン本体
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注・管理・整合処理

  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化・CRUD ユーティリティ
    - system_monitor.py — システム／データ鮮度監視
    - trade_monitor.py — 取引ログ監視（滞留注文／約定異常）
    - risk_monitor.py — ドローダウン／ポジション上限監視
    - kill_switch.py — Kill Switch 実装
    - alert_manager.py — 通知送信（LINE 等、設定により利用）
    - monitoring_engine.py — 各 Monitor を束ねる

  - portfolio/
    - portfolio_builder.py — 候補選定・スコアソート
    - position_sizing.py — 株数計算・スケーリング（単元丸め・コスト考慮）
    - risk_adjustment.py — セクター上限・レジーム乗数

  - research/
    - factor_research.py — Momentum/Volatility/Value 等の計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計
  - data/ (想定: CSV / ETL / pipeline モジュールがある想定)
    - pipeline.py — prices_daily などの最終データ取得ユーティリティ（参照あり）
    - stats.py — 正規化ユーティリティ（zscore など）

  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI 利用）
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート

  - utils/
    - logging_setup.py — 共通ログ設定
    - process_priority.py — プロセス優先度 / CPU affinity 設定
    - （その他ユーティリティ）

---

## よくある運用フロー（例）

1. `.env` を作成（`python -m kabusys.config_setup`）
2. 設定検証（`python -m kabusys.validate_config`）
3. バッチ的に日次でリサーチ（DuckDB を更新）→ ファクター計算 → シグナル生成 → ExecutionEngine を稼働（本番またはペーパートレード）
4. 別プロセスで MonitoringEngine を常時稼働し、問題発生時は通知・Kill Switch 発動
5. 定期的に `python -m kabusys.tools.paper_verification_report` で検証

---

## 注意事項

- 本リポジトリは参照実装です。実運用前に必ず設定・ロジックをレビューし、サンドボックスで十分なテストを行ってください。
- 本番環境（KABUSYS_ENV=live）では Kill Switch・通知設定（LINE 等）や DB のバックアップ等、運用上の安全対策を徹底してください。
- OpenAI など外部 API キーは厳格に管理し、.env を絶対にリポジトリにコミットしないでください。

---

必要であれば、README にコマンド例（systemd ユニット、Dockerfile、CI 設定）や各モジュールの詳細ドキュメントを追加します。どの情報を優先して追加しましょうか？