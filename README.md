# KabuSys

バージョン: 0.1.0

日本株自動売買システムのコアライブラリ群。  
バックテスト／リサーチ用のファクター計算、ポートフォリオ構築、注文実行エンジン（本番 / ペーパートレード切替）、およびシステム監視・アラート機能を含みます。

---

## 概要

KabuSys は以下を目的とするモジュール化された Python パッケージです。

- 日次・ポートフォリオ構築に必要なファクター計算（DuckDB 経由）
- 発注ロジック（ExecutionEngine） — 本番・ペーパートレード対応
- モニタリング（System / Trade / Risk）と Kill Switch（フラグファイルによる強制停止）
- ニュース NLP（OpenAI）を用いたセンチメント集計／レジーム判定
- 運用支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）
- ロギング・プロセス優先度設定など運用ユーティリティ

---

## 主な機能一覧

- 環境設定ウィザード（.env 自動生成）: `kabusys.config_setup`
- 起動前設定検証: `kabusys.validate_config`
- ExecutionEngine（発注エンジン）: 本番 / ペーパートレード切替、リスク管理、オーダー管理
  - ペーパートレード時は MockBrokerClient を使用して `data/paper_trading.db` に記録（本番 DB と分離）
- Monitoring（System / Trade / Risk）: 定期ポーリング、監視ログ永続化（SQLite）
  - 監視は本番の SQLite（`SQLITE_PATH`）を使用
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）
- Kill Switch（`data/kill.flag`）: ドローダウンやポジション上限到達時にフラグ書き込みで ExecutionEngine を停止
- AI モジュール:
  - ニュースセンチメント集計（OpenAI）: `kabusys.ai.news_nlp`
  - 市場レジーム判定（MA + マクロセンチメント）: `kabusys.ai.regime_detector`
- ポートフォリオ構築:
  - 候補選定、等重/スコア重み、リスクベースのポジションサイズ計算、セクター上限適用
- リサーチ:
  - ファクター計算（モメンタム、バリュー、ボラティリティ）
  - IC / 将来リターン計算 / 統計サマリー
- 運用ツール:
  - ペーパートレード検証レポート生成: `kabusys.tools.paper_verification_report`

---

## 前提条件

- Python 3.9+（ソースは型注釈で modern Python を想定）
- 必要（想定）パッケージ:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定ファイル検証を行う場合）
- SQLite（Python 標準ライブラリの sqlite3 を使用）
- ネットワーク接続（OpenAI を使う場合）

（実際の requirements.txt がある場合はそれを使用してください。）

---

## セットアップ手順（開発 / 運用）

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（例）
   - pip install duckdb psutil openai pyyaml

3. プロジェクトルートで .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 手動で作る場合は `./.env` に必要な環境変数を記載してください。
     - 例（主な項目）:
       - JQUANTS_REFRESH_TOKEN (必須)
       - KABU_API_PASSWORD (必須)
       - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
       - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
       - SQLITE_PATH (デフォルト: data/monitoring.db)
       - PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB, デフォルト: data/paper_trading.db)
       - OPENAI_API_KEY (AI 機能を使う場合)
       - LOG_LEVEL (DEBUG/INFO/...)
       - KILL_FLAG_CLEAR_ON_START (0/1)

4. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

5. データディレクトリの作成（必要に応じて）
   - data/ : DB / pid / flag を保存します
   - logs/ : ログファイル（デフォルト）

---

## 使い方（主要コマンド）

- 監視ループ起動（SystemMonitor のポーリング）
  - MONITOR_POLL_INTERVAL 環境変数で秒数を変更可能（デフォルト 60）
  - python -m kabusys.run_monitoring
  - 停止方法:
    - Ctrl+C（KeyboardInterrupt）
    - またはプロジェクトルートの `data/stop_requested.flag` を作成するとループは安全に終了します。

- ExecutionEngine 起動（発注エンジン）
  - ペーパートレード: KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使い `data/paper_trading.db` に記録します（本番 DB と分離）。
  - python -m kabusys.run_execution
  - 実行中に停止するには `data/stop_requested.flag` を作成してください。
  - 実行時は pid ファイル（デフォルト `data/execution.pid`）が作成されます。

- .env ウィザード（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告で exit(1)

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - DB パスは `--db PATH` または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定

- AI 機能（プログラムから呼び出す）
  - ニューススコアリング: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 主要な環境変数（要点）

- JQUANTS_REFRESH_TOKEN — 必須
- KABU_API_PASSWORD — 必須
- KABUSYS_ENV — 実行モード: development / paper_trading / live（デフォルト: development）
  - paper_trading のとき run_execution は専用 DB（PAPER_TRADING_SQLITE_PATH）を使用
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- LOG_LEVEL, LOG_DIR — ログレベル／ログディレクトリ
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒）
- PAPER_FILL_MODE — ペーパートレードの約定動作（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に `data/kill.flag` を自動クリアするか（0/1）

---

## 運用メモ

- 監視（run_monitoring）は KABUSYS_ENV にかかわらず本番の `sqlite_path` を使用します（監視ログは本番 DB に集約される設計）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用の DB を使って本番 DB から分離します。
- Kill Switch:
  - `data/kill.flag` が作成されると ExecutionEngine に停止シグナルが送られます（KillSwitch がフラグを作成する仕組み）。
  - `KILL_FLAG_CLEAR_ON_START=1` を本番で設定するのは推奨されません（誤って自動クリアされるため）。
- 停止用フラグ:
  - `data/stop_requested.flag` — run_monitoring / run_execution のループ中断用
  - `data/kill.flag` — ExecutionEngine を強制停止させるための運用フラグ

- ログ:
  - `kabusys.utils.logging_setup.setup_logging` を全スクリプトで使っています。デフォルトで stdout と日次ローテートのファイル出力（logs/<app_name>.log）を設定します。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は起動時に必要なテーブル・カラムを冪等的に作成／マイグレートします。

---

## ディレクトリ構成（要約）

※ プロジェクトルートが `src/` 配下にある形を想定しています。

- src/kabusys/
  - __init__.py — パッケージ定義（__version__）
  - config.py — 環境変数 / 設定の読み込み・検証（Settings クラス）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py — SQLite への読み書き（永続化層）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py — 発注ログ監視（滞留注文/約定異常など）
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — フラグファイルによる停止判定
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — （アラート送信管理: LINE 等、実装参照）
  - execution/
    - execution_engine.py — 発注エンジン本体
    - broker_factory.py — ブローカークライアント生成（Mock / 実装）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 実行フロー関連
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・単元丸め・aggregate cap
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — モメンタム／バリュー／ボラティリティ計算
    - feature_exploration.py — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py — ニュースから銘柄ごとのセンチメント算出（OpenAI）
    - regime_detector.py — MA + マクロセンチメントでレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

- data/ （実行時に DB / pid / flag が置かれる想定）
  - monitoring.db, paper_trading.db, kabusys.duckdb など
  - execution.pid, stop_requested.flag, kill.flag

- logs/ （デフォルトログ出力先）

---

## 開発者向け補足

- DuckDB 接続を受け取り SQL + Python で処理する実装が多く、リサーチ部分は外部 API に依存しない設計です。
- AI 系（news_nlp / regime_detector）は OpenAI API を使います。API 呼び出しはリトライや失敗時のフェイルセーフを備えています（失敗時はスキップまたは中立値で継続）。
- モジュールの多くは副作用を最小化する純粋関数群（portfolio / research）と、DB 読み書きに特化した永続化層（monitoring_db）に分かれています。

---

必要であれば README の英語版、docker-compose / systemd ユニットの例、あるいは requirements.txt のテンプレートを追加で作成します。どれが必要か教えてください。