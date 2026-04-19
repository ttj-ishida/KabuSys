# KabuSys

日本株自動売買システムの軽量実装（ライブラリ + 実行スクリプト群）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買（Execution）とそれを監視する Monitoring、研究 / リサーチ用のモジュール群、AI を用いたニューススコアリングやレジーム判定などを含む小規模なフレームワークです。DB には SQLite（監視・ペーパートレード用）と DuckDB（分析用）を使用し、実行環境は `.env` や環境変数で切り替え可能です。

設計方針の要点:
- 実行スクリプト（execution / monitoring）はプロセス優先度設定・ログ設定を共通化
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離（data/paper_trading.db）
- AI（OpenAI）連携はオプションでフェイルセーフ（API 不在時はエラー回避）
- 設定は .env で管理。ウィザード・検証 CLI を提供

---

## 主な機能一覧

- ExecutionEngine 起動スクリプト（run_execution）
  - 実際の発注ロジックを持つエンジンの起動
  - KABUSYS_ENV=paper_trading のとき MockBrokerClient を使用し DB を分離
  - 停止フラグ / PID 管理（data/execution.pid, data/stop_requested.flag）
- Monitoring（run_monitoring / monitoring_engine）
  - システム監視（CPU/メモリ/Disk、プロセス生存チェック、データ鮮度）
  - 取引監視（滞留注文・異常約定など）
  - リスク監視（ドローダウン、ポジション上限）
  - Kill Switch（条件で data/kill.flag を書き込む）
- ポートフォリオ構築
  - 候補選定、等金額 / スコア加重配分、セクター制約、ポジションサイズ計算
- リサーチ / ファクター計算
  - Momentum, Volatility, Value などを DuckDB 上で計算
  - 将来リターン計算、IC 計算、統計要約
- AI モジュール（オプション）
  - ニュース NLP（OpenAI を用いた銘柄ごとのセンチメントスコア化）
  - レジーム判定（ETF の MA と LLM のマクロセンチメントを合成）
- ツール
  - paper_verification_report: ペーパートレード DB を集計して検証レポートを出力
- ユーティリティ
  - ログ設定（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
  - .env ウィザード（config_setup）および設定検証 CLI（validate_config）

---

## セットアップ手順

1. リポジトリをクローン／展開し、作業ディレクトリをプロジェクトルートにする。

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 依存パッケージをインストール
   - 最低限の主要依存例:
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
     - (任意) PyYAML（config/*.yaml の検証に使用）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt` を使用してください）

4. .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - あるいは既存の .env を手動で作成（.env.example を参照）

5. 設定の検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合: python -m kabusys.validate_config --strict

6. データディレクトリ
   - デフォルトでは以下のパスを使用します。必要に応じて .env で上書きしてください。
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db

7. ログディレクトリ
   - デフォルト: logs/
   - 権限やディレクトリ作成に失敗するとコンソール出力のみになります。

---

## 必須 / 主要な環境変数

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

オプション・主要:
- KABUSYS_ENV — 実行環境: development / paper_trading / live (default: development)
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — SQLite (monitoring)（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（default: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI API を使う場合に必要
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL — monitoring ポーリング間隔（秒、run_monitoring で使用、default: 60）
- PAPER_FILL_MODE — ペーパートレードの fill 動作（instant | partial | never | reject）

注意:
- .env 自動読み込みはデフォルトで有効（プロジェクトルートの .env / .env.local）。無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（実行コマンド例）

- 実行エンジン（Execution）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録されます。
  - 停止: data/stop_requested.flag を作成すると実行スレッドは検知して停止します。
  - 実行中は data/execution.pid に PID を書きます。

- 監視ループ（Monitoring）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は本番 sqlite_path を環境に関わらず使用します（monitoring は常に本番監視 DB を対象）

- .env の対話式作成 / 更新
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告をFAIL扱い）: python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI モジュールの使用例（ライブラリ呼び出し）
  - from kabusys.ai.news_nlp import score_news
  - from kabusys.ai.regime_detector import score_regime
  - 両関数とも DuckDB 接続（duckdb.connect(...)）と target_date（datetime.date）および OPENAI_API_KEY（引数または環境変数）を必要とします。

---

## 停止 / Kill Switch

- run_execution と run_monitoring はプロジェクトの data/stop_requested.flag を監視しており、存在すると安全に終了します。
  - stop フラグの場所: `<project_root>/data/stop_requested.flag`
- Kill Switch は条件（ドローダウンやポジション上限）で `data/kill.flag` を書き込み、ExecutionEngine に停止を促します（Execution 側で kill.flag の存在をチェックしてください）。
- Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアされます（本番では 0 推奨）。

---

## ディレクトリ構成（概要）

（ルート: src/kabusys 以下を示す）

- kabusys/
  - __init__.py — パッケージ情報（バージョン等）
  - config.py — 環境変数・設定読み込み・Settings
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py — ログ設定ユーティリティ（stdout + 日次ローテート）
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py — SQLite ベースの永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 取引関連監視（ファイル内に実装）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - monitoring_engine.py — 各 Monitor を束ねる実行エンジン
    - alert_manager.py — アラート通知（LINE 等を想定、ファイル内に実装）
  - execution/
    - execution_engine.py — ExecutionEngine 本体（発注ループ等）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py / broker_factory.py — 実行に関する各コンポーネント
  - portfolio/
    - portfolio_builder.py — 銘柄候補選定 / 重み計算
    - position_sizing.py — 発注数計算・スケールダウンロジック
    - risk_adjustment.py — セクター制約・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum / volatility / value）
    - feature_exploration.py — 将来リターン・IC・統計解析
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA + LLM）
  - data/ — （実行時に使う SQLite / DuckDB / flag / pid 等を配置）
  - logs/ — ログファイル（logs/<app_name>.log）

---

## 補足 / 開発メモ

- DuckDB は分析用途（prices_daily / raw_financials / raw_news 等）に使われます。実行前に必要なテーブルを用意してください（ETL スクリプト等は別途用意する想定）。
- monitoring の DB 初期化は init_monitoring_db により冪等に実行されます（マイグレーション含む）。
- OpenAI を利用する機能は API 呼び出し失敗時にフォールバックする設計になっていますが、API キーが未設定の場合は明示的に例外を投げる関数もあります（呼び出し側で扱いを検討してください）。
- テスト時は config の自動ロードを無効化できます: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- ログ設定はアプリ名ごとに logs/<app_name>.log へ日次ローテーションで保存されます。ログディレクトリ作成に失敗した場合はコンソールのみ出力されます。

---

必要であれば README の英語版や、例となる .env.example、docker-compose / systemd ユニット例、さらなる CLI 使い方（ExecutionEngine の引数詳細など）も追加作成できます。どの部分を優先して充実させますか？