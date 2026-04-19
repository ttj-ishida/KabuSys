# KabuSys — 日本株自動売買システム

簡潔なプロジェクト概要、主要機能、セットアップ手順、使い方、ディレクトリ構成をまとめた README です。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール式のシステムです。以下の主要責務を持ちます。

- 注文実行（ExecutionEngine）とリスク管理
- システムおよび取引の監視（Monitoring）
- ポートフォリオ構築・銘柄選定・ポジションサイズ計算（Portfolio）
- リサーチ（ファクター計算、特徴量解析）
- ニュース NLP を使ったセンチメント評価・レジーム検出（AI モジュール）
- ペーパートレード用の分離された DB と検証レポート機能
- 起動前設定ウィザード / 設定検証ツール

本リポジトリは純粋関数群・永続化層・起動スクリプト・ユーティリティ群に分かれており、テストやデプロイがしやすい設計になっています。

---

## 機能一覧（主なコンポーネント）

- run_execution.py
  - ExecutionEngine の起動スクリプト
  - KABUSYS_ENV=paper_trading のときは MockBroker を使い、paper_trading.db に書き込む（本番 DB と分離）
  - 起動時に `data/execution.pid` を扱い、停止フラグで安全停止
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
  - MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）
  - 監視ログは SQLite（monitoring.db）へ永続化
- monitoring/
  - SystemMonitor: CPU/メモリ/Disk・実行プロセス有無・データ鮮度を監視
  - TradeMonitor: 取引イベントの監視（滞留注文、約定異常など）※実装ファイル参照
  - RiskMonitor: ドローダウン・ポジション上限等の監視と risk_logs 記録
  - KillSwitch: 条件により `data/kill.flag` を作成して ExecutionEngine に停止シグナル
  - MonitoringDB: SQLite テーブル（system_status, trade_logs, positions, risk_logs, dashboard）の初期化と操作
  - MonitoringEngine: 各 Monitor を束ねるポーリング実行
- execution/
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等（発注・リスクロジック）
- portfolio/
  - 銘柄選定、重み付け、ポジションサイズ計算、セクターキャップ、レジーム乗数等の純粋関数
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ
- ai/
  - news_nlp: OpenAI を用いたニュースセンチメント集約・ai_scores への書込み
  - regime_detector: ETF の MA200 乖離と LLM によるマクロセンチメントを統合して market_regime を判定
- tools/
  - paper_verification_report.py: ペーパートレード DB を解析して PASS/FAIL レポートを生成
- utils/
  - logging_setup: stdout + 日次ローテートファイルで統一的なログ出力設定
  - process_priority: プラットフォーム非依存のプロセス優先度 / CPU affinity 設定
- config_setup.py
  - 対話式ウィザードで `.env` を生成・更新
- validate_config.py
  - `.env` や `config/*.yaml` の事前チェック CLI

---

## システム要件（推奨・依存）

最低限必要なもの（該当パッケージは環境に応じて pip でインストール）:

- Python 3.9+（コードは型注釈と一部較新 API を想定）
- 必須ライブラリ（例）
  - duckdb
  - psutil
  - openai
- 推奨 / オプショナル
  - PyYAML（validate_config の YAML 検証に使用）
- DB: SQLite（標準モジュール sqlite3）
- ネットワークアクセス（kabuステーション API、OpenAI 等を使う場合）

（requirements.txt は本リポジトリに同梱されていない想定のため、環境に合わせて上記を pip で入れてください）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo_url>
   cd <repo_root>
   ```

2. 仮想環境を作成して依存をインストール（上記参照）

3. .env を作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは手動で `.env` を作成（`.env` に機密情報を含むため絶対に Git にコミットしないでください）

   主な必須環境変数:
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   オプション:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
   - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
   - OPENAI_API_KEY（AI モジュールを使う場合）
   - LOG_LEVEL（例: INFO）

4. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. 必要なディレクトリ作成（logs, data などはログ設定や PID/flag 書き込み時に自動作成されますが、事前に作成しておくと安全です）
   ```
   mkdir -p data logs
   ```

---

## 使い方（代表的なコマンド・動かし方）

- ExecutionEngine の起動（本番／ペーパーは KABUSYS_ENV で切替）
  ```
  # ペーパートレードを使う場合は .env で KABUSYS_ENV=paper_trading にする
  python -m kabusys.run_execution
  ```
  実行時:
  - 起動時にプロセス優先度を high に設定し、指定された sqlite(本番または paper) と DuckDB に接続します。
  - `data/execution.pid` を使用（設定可能）。
  - `data/stop_requested.flag` を置くとループが検知して停止します。

- Monitoring の起動
  ```
  # ポーリングループを始める
  python -m kabusys.run_monitoring

  # ポーリング間隔を環境変数で変更（秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  備考:
  - Monitoring は環境に関わらず production の sqlite_path を使用して system_status 等を記録します（監視 DB は一元）。
  - 停止フラグはプロジェクトの data/stop_requested.flag（run_monitoring では上位親の data/stop_requested.flag を参照）です。

- ペーパートレード検証レポート
  ```
  # デフォルト DB (data/paper_trading.db) を参照
  python -m kabusys.tools.paper_verification_report

  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # 別 DB 指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- `.env` の (再)生成 / 更新
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

---

## 主要な動作・運用メモ

- DB
  - DuckDB: 分析用（prices_daily, raw_financials, ai_scores, market_regime 等）
  - SQLite: 監視ログ・発注ログ（monitoring.db）。ペーパートレード時は paper_trading.db を別途使用して本番 DB と分離

- Kill Switch / Stop
  - KillSwitch（monitoring.kill_switch）は条件を満たすと `data/kill.flag` を書き、ExecutionEngine 側で検出して安全停止させます。
  - `data/stop_requested.flag` を置くと run_* スクリプトがループを抜けて終了します（オペレーターからの即時停止用）。

- ログ
  - 共通ユーティリティ `kabusys.utils.logging_setup` を通じて stdout と daily rotating file に出力します（logs/<app_name>.log）。
  - デフォルトログレベルは LOG_LEVEL 環境変数または設定ファイルに依存（デフォルト "INFO"）。

- OpenAI（AI モジュール）
  - AI モジュールは環境変数 OPENAI_API_KEY を使います。未設定時は score_regime/score_news 呼び出しでエラーとなるので注意。
  - レスポンスの頑健性確保（JSON バリデーション、リトライ、部分書き込み）を実装しています。

- Paper Trading
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ書き込みます。本番 DB と完全分離されています。

---

## ディレクトリ構成（主要ファイル）

（リポジトリのルートに `src/kabusys` がある想定）

- src/kabusys/
  - __init__.py
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - config.py — Settings（環境変数 / .env のロードとアクセス）
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化 / 永続化操作（MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度をチェック
    - trade_monitor.py — 取引関連の監視（滞留注文など、実装ファイル参照）
    - risk_monitor.py — ドローダウン / ポジション上限の検出
    - kill_switch.py — kill.flag の作成 / 解除
    - monitoring_engine.py — 各 Monitor を束ねる
    - alert_manager.py — 通知（LINE 等）を行うモジュール（実装参照）
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - research/
    - factor_research.py, feature_exploration.py, __init__.py
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI 呼び出し、ai_scores 書込）
    - regime_detector.py — MA200 と マクロセンチメントの統合
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

---

## 開発 / テスト時のヒント

- 自動テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を "1" に設定して .env 自動ロードをオフにできます（テスト用に明示的な環境を設定したい場合）。
- DuckDB のクエリはテスト用に小さな価格データセットを用意すると高速に検証できます。
- OpenAI 呼び出しはユニットテストで外部 API をモックすることを推奨します（score_news/_call_openai_api を patch）。

---

## 既知の注意点 / 将来の改善候補

- position_sizing の lot_size は全銘柄共通で 100 固定。将来的に銘柄別 lot サイズをサポートする予定。
- price の欠損時のフォールバック（前日終値や取得原価）に関する TODO コメントあり。
- 一部の DuckDB executemany は空リストを受け付けないバージョンの互換性対応が入っています。DuckDB バージョンに依存する振る舞いに注意してください。

---

README は必要に応じてプロジェクト固有の README テンプレートや運用手順に合わせて調整してください。追加で各モジュールの API ドキュメント（関数引数・戻り値・例）や運用チェックリストが必要であれば、フォローします。