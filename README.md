# KabuSys

日本株向け自動売買システムのミニマル実装（リポジトリ抜粋）。  
この README は提供されたコードベース（src/kabusys 以下）をもとに、プロジェクト概要、機能、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は、日本株の自動売買／リサーチ／モニタリングのためのモジュール群です。主な設計方針は次のとおりです。

- 発注ロジックと監視ロジックを分離（ExecutionEngine / MonitoringEngine）
- DuckDB を用いた分析・リサーチ（prices_daily / raw_financials 等）
- SQLite を用いた監視ログ・トレードログ（monitoring.db / paper_trading.db）
- Paper Trading（擬似ブローカー）対応（KABUSYS_ENV により切り替え）
- OpenAI（LLM）を利用したニュース NLP／レジーム判定機能（任意）
- フェイルセーフ設計（API エラーは基本的にフェイルオープン）

バージョン情報:
- パッケージ: `kabusys`
- __version__ = "0.1.0"

---

## 主な機能一覧

- Execution
  - ExecutionEngine による注文実行（本番 or paper_trading）
  - RiskManager、OrderManager、Reconciler 等による発注管理
  - PID ファイル管理、停止フラグ監視（data/stop_requested.flag など）

- Monitoring
  - SystemMonitor: CPU/MEM/DISK・プロセス稼働・データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常など監視（trade_logs）
  - RiskMonitor: ドローダウン／ポジション上限監視
  - MonitoringEngine: 定期ポーリングとアラート発行、KillSwitch 連携

- Data / Research
  - DuckDB ベースのファクター計算（モメンタム・ボラティリティ・バリュー）
  - forward returns / IC 計算、ファクター統計サマリー

- Portfolio
  - 候補選定、等分／スコア加重、ポジションサイズ計算、セクター制約、レジーム乗数など

- AI
  - news_nlp: OpenAI を使ったニュースのセンチメントスコアリング（ai_scores へ書込）
  - regime_detector: マクロ＋ETF MA200 乖離から市場レジーム判定

- ユーティリティ
  - 環境設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール（tools.paper_verification_report）
  - ロギング設定ユーティリティ（utils.logging_setup）
  - プロセス優先度設定（utils.process_priority）

---

## 環境変数（主要）

Settings クラスで読み込まれる代表的な環境変数とデフォルト:

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）

- 実行環境
  - KABUSYS_ENV — `development` / `paper_trading` / `live`（デフォルト: development）

- DB パス
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）

- ログ / 制御
  - LOG_LEVEL — ログレベル（デフォルト: INFO）
  - LOG_DIR — ログ保存先（デフォルト: logs/）
  - PID_FILE_PATH — 実行エンジンの PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch 用フラグ（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（"1" で有効）

- Monitoring 固有
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）

- AI
  - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合に必要）

- その他
  - PAPER_FILL_MODE — paper_trading の成行/部分約定挙動（instant/partial/never/reject）

自動的に `.env` / `.env.local` を読み込む機能あり（プロジェクトルートが推定可能な場合）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

例（.env の一部）:
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

---

## セットアップ手順（開発用）

1. Python 環境作成（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール（代表的なパッケージ）
   - pip install duckdb psutil openai
   - PyYAML を使う場合（validate_config の YAML 検証）:
     - pip install pyyaml

   ※ requirements.txt はリポジトリ抜粋に含まれていないため、実行に必要なパッケージを上記から用意してください。

3. データディレクトリ作成（不足ファイルは自動生成される場合あり）
   - mkdir -p data logs

4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - もしくは手動で `.env` に必要な環境変数を設定

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も fail にしたい場合: python -m kabusys.validate_config --strict

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env を生成/更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 挙動: KABUSYS_ENV=paper_trading の場合、MockBroker を使い data/paper_trading.db に記録（本番 DB と分離）

- 監視モニタ起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）
  - 監視は常に監視用 sqlite_path（Settings.sqlite_path）を使用（環境に関わらず本番 path を使う設計）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可能）

- AI 機能（プログラムから呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI キーは引数または OPENAI_API_KEY 環境変数で指定
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

停止制御:
- 手動停止フラグ: `data/stop_requested.flag` が存在すると run_monitoring / run_execution のループが終了します。
- Kill Switch: 監視側が条件を満たした場合 `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを与えます。
- `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアします（本番では通常 0 を推奨）。

ログ:
- logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）に日次ローテーションで出力されます。
- ログ出力はコンソール stdout とファイルの両方（ファイル作成に失敗した場合はコンソールのみ）に出力されます。

プロセス優先度:
- スクリプト起動時に set_process_priority("high") が呼ばれます（psutil を使い OS に依存して設定）。権限不足などで失敗する場合は警告ログに留まります。

---

## 注意点 / 運用上のポイント

- .env は絶対にリポジトリにコミットしないこと（API キー等の秘匿情報を含む）。
- KABUSYS_ENV を `live` に設定する際は validate_config の警告を必ず確認すること（LINE 通知設定や Kill Switch の設定など）。
- OpenAI を使う機能は API キーが必須。失敗時はフェイルセーフで続行する実装が多いが、期待通りのスコアが得られない可能性あり。
- Paper Trading 用データベースは `data/paper_trading.db` に分離されるため、本番データと混在しない。
- DuckDB を使う研究系モジュールは大きなデータを高速に処理できるが、テーブル定義（prices_daily, raw_financials, raw_news 等）を事前に準備する必要あり。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数・設定読み込みロジック
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースの LLM によるセンチメントスコア処理
  - regime_detector.py — 市場レジーム判定
  - __init__.py (score_news エクスポート)
- monitoring/
  - monitoring_db.py — SQLite 用永続層（テーブル初期化・読み書き）
  - system_monitor.py — システム状態監視
  - trade_monitor.py — （用意されている）トレード監視（抜粋では省略）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — Kill Switch ロジック（flag ファイル操作）
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - alert_manager.py —（抜粋では省略）アラート送信管理
- execution/
  - execution_engine.py — ExecutionEngine コア（抜粋）
  - broker_factory.py — ブローカークライアント生成
  - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 発注周りの実装
- portfolio/
  - portfolio_builder.py — 候補選定、重み計算
  - position_sizing.py — 株数・割当計算
  - risk_adjustment.py — セクター上限・レジーム乗数
  - __init__.py
- research/
  - factor_research.py — momentum/value/volatility ファクター計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - __init__.py
- monitoring/（上記）
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成ツール
- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity 設定

データ / ログ（リポジトリ外または data/ logs/）
- data/
  - monitoring.db（デフォルトの監視 SQLite）
  - paper_trading.db（paper_trading 用）
  - kill.flag / stop_requested.flag / execution.pid など制御ファイル
- logs/
  - execution.log, monitoring.log, ...（日次ローテート）

---

## 開発・拡張ポイント（参考）

- DuckDB スキーマ（prices_daily, raw_financials, raw_news 等）を整備すれば research/ と ai/ 機能が利用可能。
- broker クライアントの実装次第で実売買連携が可能（現状は kabuステーション API を想定）。
- テスト容易性のため、OpenAI 呼び出しやプロセス制御箇所は差し替え（モック）を想定した実装になっています。

---

必要であれば、この README を基に具体的なセットアップ手順（requirements.txt、テストの実行方法、Docker 化など）や各モジュールの API ドキュメントを追記します。どの部分を詳述しますか？