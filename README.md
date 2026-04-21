# KabuSys

日本株向けの自動売買システム（ライブラリ & 起動スクリプト群）

この README はリポジトリ内のコード（monitoring / execution / portfolio / research / AI 等）を基に作成した概要・セットアップ・使い方ドキュメントです。

---

## プロジェクト概要

KabuSys は日本株自動売買のためのモジュール群と起動スクリプトを提供するプロジェクトです。主な目的は以下です。

- 注文エンジン（ExecutionEngine）による発注管理（paper/live 切替対応）
- システム監視（SystemMonitor）やリスク監視（RiskMonitor）、アラート発行・Kill Switch
- ポートフォリオ構築（候補選定、重み付け、株数算出）
- リサーチ（ファクター計算、将来リターン、IC 計算）
- AI ベースのニュースセンチメント評価（OpenAI を利用）
- 運用/検証ツール（ペーパートレード検証レポート等）

設計上のポイント：
- Paper Trading と Live は DB を分離（ペーパートレードは `data/paper_trading.db` を使用）
- DuckDB を分析用 DB に使用（デフォルト `data/kabusys.duckdb`）
- 環境設定は .env（.env.local）経由で読み込まれる。CLI ウィザード・検証ツールあり
- logging、プロセス優先度、CPU affinity をユーティリティで統一

---

## 機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動（KABUSYS_ENV による paper/live 切替）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔制御）
- 設定管理
  - config.py: 環境変数・Settings クラス（必須・オプション項目の集約）
  - config_setup.py: .env を対話式に作成/更新するウィザード
  - validate_config.py: .env / config/*.yaml の事前検証 CLI
- 監視
  - monitoring/monitoring_db.py: 監視用 SQLite スキーマの初期化・操作
  - monitoring/system_monitor.py, trade_monitor.py, risk_monitor.py など：各種監視ロジック
  - monitoring/kill_switch.py: kill.flag を書き込むことで ExecutionEngine を停止させる仕組み
  - monitoring/monitoring_engine.py: 複数モニタの統合ポーリング
- 実行（Execution）
  - execution/*: ブローカークライアント、ExecutionEngine、注文管理、リコンシリア（詳細は実装を参照）
- ポートフォリオ構築
  - portfolio/*: 候補選定、重み付け（等重/スコア重み）、ポジションサイズ計算、セクター制限、レジーム乗数
- 研究・リサーチ
  - research/*: ファクター計算（Momentum/Value/Volatility）、特徴量探索、IC 計算
- AI
  - ai/news_nlp.py: OpenAI を使ったニュースセンチメント集約・ai_scores 書込
  - ai/regime_detector.py: ma200 とマクロニュースの LLM 評価を組合せて市場レジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレードの検証レポート出力

---

## 必要要件（概略）

- Python 3.9+（型ヒント等を使用しているため最新の 3 系推奨）
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - pyyaml（config YAML の検証に任意で使用）
- SQLite（Python 標準ライブラリに同梱）

依存関係はプロジェクトに requirements.txt があればそちらを利用してください。無ければ pip で上記パッケージをインストールしてください。

例:
pip install duckdb psutil openai pyyaml

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. 仮想環境作成（任意）
   python -m venv .venv
   source .venv/bin/activate
3. 依存パッケージをインストール
   pip install duckdb psutil openai pyyaml
4. 環境設定ファイルの作成（推奨: ウィザード利用）
   python -m kabusys.config_setup
   - 指示に従って .env を作成します（J-Quants トークンや kabu API パスワードなどを設定）
5. 設定検証（任意）
   python -m kabusys.validate_config
   - --strict を付与すると警告も失敗扱いになります
6. DB 初期化
   - 基本的に起動スクリプトが起動時に必要なテーブルを作成します（monitoring DB など）
   - DuckDB 用のテーブル等は別途データロードスクリプトがある想定（prices_daily 等）

---

## 主要な環境変数（デフォルト値）

- KABUSYS_ENV: execution 環境
  - 有効値: development / paper_trading / live
  - デフォルト: development
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API トークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
- OPENAI_API_KEY: OpenAI を利用する場合に設定
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（DEBUG 等指定可）
- LOG_DIR: logs/
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- KILL_FLAG_CLEAR_ON_START: 0（1 にすると起動時に kill.flag を自動クリア）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。run_monitoring で使用。デフォルト 60）

注意:
- Paper Trading 時は ExecutionEngine は MockBrokerClient を使い、paper 用 DB に記録されます（本番 DB と分離）。
- Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使う設計の箇所があります（特に run_monitoring のコメントを参照）。

---

## 初期設定 (.env)

対話式ウィザードで .env を作成:
python -m kabusys.config_setup

作成後は必ず設定検証を実行してください:
python -m kabusys.validate_config

---

## 実行方法

プロジェクトルートで Python モジュールとして実行します。

- ExecutionEngine を起動（本番/ペーパーは KABUSYS_ENV に依存）
  python -m kabusys.run_execution

  実行フロー概要:
  - Settings 読み込み
  - DB 接続（paper_trading の場合は paper_sqlite_path を使用）
  - BrokerClientFactory によるブローカークライアント生成（Mock を含む）
  - ExecutionEngine を別スレッドで run_session 実行
  - `data/stop_requested.flag` の存在を監視して停止（ファイル存在で停止）

- SystemMonitor（監視ループ）を起動
  python -m kabusys.run_monitoring

  挙動:
  - Settings 読み込み
  - monitoring DB を初期化
  - SystemMonitor を初期化
  - ポーリングループで monitor.check_once() を定期実行
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（秒。デフォルト 60）
  - ループは `data/stop_requested.flag` 存在で終了

- .env の検証
  python -m kabusys.validate_config
  オプション: --strict（警告も FAIL 扱い）

- .env ウィザード
  python -m kabusys.config_setup

- Paper Trading 検証レポート出力
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション: --db PATH でペーパートレードの SQLite を指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI モジュール（例）
  - ニューススコアリング: kabusys.ai.score_news を呼ぶ（プログラム内から利用）
  - OpenAI API を使用するためには OPENAI_API_KEY が必要

---

## 停止方法・Kill Switch

- 実行中の run_execution / run_monitoring は以下のフラグファイルを参照して停止を検出します
  - data/stop_requested.flag: run_execution/run_monitoring が直接監視している停止フラグ（存在すると起動を中止または停止動作）
  - data/kill.flag: KillSwitch が条件を満たしたときに書き込まれるフラグ。ExecutionEngine 側がこれを検出して停止する設計になっています

フラグの操作例:
- 停止要求の作成:
  touch data/stop_requested.flag
- 停止フラグの削除:
  rm data/stop_requested.flag
- KillSwitch のクリア（KillSwitch クラスの clear() を使うかファイルを削除）
  rm data/kill.flag

注意: 本番環境では KILL_FLAG_CLEAR_ON_START を 0 にしておくことを推奨します。

---

## ログ

- デフォルト出力先: 標準出力（コンソール）とファイル（logs/<app_name>.log、日次ローテーション）
- ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution")
- LOG_DIR 環境変数でログディレクトリを上書き、LOG_LEVEL でログレベルを指定できます

---

## 開発・テストに関する注意点

- .env の自動読み込みはデフォルトで有効。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時など）。
- DuckDB や SQLite のスキーマはコード内の SQL で定義されています。データを外部から準備する際は対応するテーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime など）を作成してください。
- OpenAI を使う機能は API 呼び出しを行うため API キーが必要です。テスト時はモック化（unittest.mock）を行うことを推奨します（コード中でもテスト向け差替えを想定した設計があります）。
- Paper Trading は production DB と分離されるように設計されています。環境変数 `KABUSYS_ENV=paper_trading` を指定すると paper DB が使われます。

---

## ディレクトリ構成

リポジトリ内で主なファイル・ディレクトリは以下の通りです（src/kabusys を想定）:

- src/kabusys/
  - __init__.py
  - config.py                    — Settings / .env 自動ロード
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパー検証レポート
  - ai/
    - news_nlp.py                — ニュースセンチメント（OpenAI）
    - regime_detector.py         — 市場レジーム判定（ma200 + LLM）
    - __init__.py
  - monitoring/
    - monitoring_db.py           — SQLite スキーマ & DB 操作ヘルパ
    - system_monitor.py          — システム状態・データ鮮度監視
    - trade_monitor.py           — 発注ログ監視（滞留注文等）
    - risk_monitor.py            — ドローダウン・ポジション上限監視
    - kill_switch.py             — kill.flag 書き込みロジック
    - monitoring_engine.py       — 複数モニタの統合ポーリング
    - alert_manager.py           — （存在想定）アラート送信管理
  - execution/
    - broker_factory.py          — ブローカクライアント生成
    - execution_engine.py        — ExecutionEngine コア
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py       — 候補選定・重み付け
    - position_sizing.py         — 株数算出・集約キャップ適用
    - risk_adjustment.py         — セクター制限・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py         — momentum/value/volatility 等
    - feature_exploration.py     — 将来リターン・IC・統計
    - __init__.py
  - data/
    - pipeline.py                — （存在想定）データ取得/前処理ユーティリティ
    - stats.py                   — zscore 等ユーティリティ
  - utils/
    - logging_setup.py           — ログ設定ユーティリティ
    - process_priority.py        — プロセス優先度 / affinity 設定
    - __init__.py

外部に置かれる想定ファイル/ディレクトリ:
- .env / .env.local
- data/ (DB ファイル・PID/flag ファイルを格納)
  - data/monitoring.db
  - data/paper_trading.db
  - data/kabusys.duckdb
  - data/execution.pid
  - data/stop_requested.flag
  - data/kill.flag
- logs/（ログ出力先）

---

## よくある操作まとめ

- .env を作る: python -m kabusys.config_setup
- 設定チェック: python -m kabusys.validate_config
- 実行エンジン起動: python -m kabusys.run_execution
- 監視ループ起動: python -m kabusys.run_monitoring
- ペーパートレード検証: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
- 停止（即時要求）: touch data/stop_requested.flag
- Kill Switch を手動クリア（危険なので注意）: rm data/kill.flag

---

この README はソースコードのコメントと docstring を元に作成しています。実際の運用では config/*.yaml や外部データ（prices_daily など）を正しく用意する必要があります。必要に応じて各モジュールの docstring や実装コメントを参照してください。