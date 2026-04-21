# KabuSys

日本株向け自動売買システムのモジュール群。ポートフォリオ構築、発注エンジン、監視、研究（因子・特徴量探索）、AI を用いたニュースセンチメント／レジーム判定などの機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の責務を持つコンポーネントを含むパッケージ群です。

- ExecutionEngine: ブローカークライアント経由での発注管理・リスク管理・照合処理
- Monitoring: システム稼働・データ鮮度・注文状態・リスク指標の監視／アラート（kill switch）
- Portfolio Construction: 候補選定、重み付け、ポジションサイズ計算、セクター制約、レジーム乗数
- Research: DuckDB を使ったファクター計算・将来リターン計算・IC や統計サマリ
- AI モジュール: OpenAI を用いたニュースのセンチメントスコアリング、マクロニュースからの市場レジーム判定
- CLI ユーティリティ: .env 初期化ウィザード、設定検証、Paper Trading 検証レポート生成 等

設計のポイント:
- DuckDB（分析）と SQLite（監視・発注ログ）を併用
- 環境変数 / .env による設定管理（自動ロード機能あり）
- Paper Trading と Live を明確に分離
- OpenAI を使う処理は APIキー必須で、安全なフォールバック処理を備える

---

## 主な機能一覧

- run_execution: ExecutionEngine 起動（本番 / ペーパートレード切替）
- run_monitoring: SystemMonitor のポーリングループ起動（監視・Kill Switch 評価など）
- config_setup: .env の対話式生成ウィザード
- validate_config: .env / config/*.yaml の起動前チェック CLI
- tools.paper_verification_report: Paper Trading の検証レポート生成
- portfolio.*: 候補選定・重み計算・ポジションサイズ計算・リスク調整
- research.*: Momentum / Volatility / Value 等のファクター計算、将来リターン、IC、統計サマリ
- ai.news_nlp: ニュースを LLM で評価し ai_scores テーブルへ書き込み
- ai.regime_detector: MA とマクロセンチメントを合成して市場レジーム判定

---

## 必要条件

- Python 3.10+
- 主要依存ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定 YAML の検証に使用）
- その他: SQLite は標準で利用可。OpenAI API を利用する場合は API キーが必要。

（プロジェクトには requirements.txt は含まれていないため、上記を環境に合わせてインストールしてください。）

例:
python -m pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローン / コピーして、プロジェクトルートへ移動。

2. Python 仮想環境を作成・有効化（推奨）。
   - python -m venv .venv
   - source .venv/bin/activate または .venv\Scripts\activate

3. 必要パッケージをインストール（上記参照）。

4. .env の作成
   - 対話式ウィザードを実行:
     - python -m kabusys.config_setup
   - もしくは .env.example を参照して手動で `.env` を作成。
   - .env はプロジェクトルートに置く想定（config_setup がデフォルトで生成）。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 必須環境変数や config/*.yaml の構文チェックを行います。
   - --strict を付けると警告も失敗（exit 1）扱いになります。

6. データディレクトリ作成
   - デフォルトでは `data/` に SQLite DB や PID/flag ファイルを作成します。必要に応じて環境変数でパスを上書きしてください。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 実行環境。development / paper_trading / live （デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード時の SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- OPENAI_API_KEY: OpenAI を使う処理で必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（1: 有効、0: 無効）

注意:
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。テスト目的で自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方

- 設定ウィザード
  - python -m kabusys.config_setup
  - 対話的に .env を生成・更新します。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗にします。

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_sqlite_path（デフォルト: data/paper_trading.db）に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - プロセス優先度を high に設定します。PID ファイル（デフォルト: data/execution.pid）を使用。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL によりポーリング間隔を変更可（秒、デフォルト 60）。
  - 監視は .env の環境にかかわらず本番 sqlite_path を使用してログを永続化します。
  - 停止は data/stop_requested.flag を作成することで行えます（監視が検知して終了）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）
  - 出力例: 稼働率、注文成功率、送信率、P95 レイテンシなどを表示し PASS/FAIL を判定。

- AI 処理（ニュース/レジーム）
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続と target_date（date オブジェクト）を渡す。api_key が None の場合は環境変数 OPENAI_API_KEY を参照します。
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 同上。OpenAI を利用するため API キー必須。

- 停止 / Kill Switch
  - Kill Switch は検出条件を満たすと `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送ります。
  - 手動で停止フラグを立てる場合は `data/stop_requested.flag` を作ると run_execution/run_monitoring のループが検知して終了します。

---

## 開発者向けメモ

- ロギング:
  - kabusys.utils.logging_setup.setup_logging(app_name="...") を全メインスクリプトから呼び出し、コンソール + 日次ローテートファイルに統一的に出力します。
  - ログディレクトリは LOG_DIR 環境変数で上書き可能（デフォルト: logs/）。

- プロセス優先度 / CPU affinity:
  - kabusys.utils.process_priority.set_process_priority / set_cpu_affinity を利用。
  - Windows / POSIX の差分を吸収していますが、権限不足時は警告を出して継続します。

- DB 初期化:
  - monitoring の起動時に init_monitoring_db が呼ばれ、必要なテーブル／マイグレーションを自動で実行します。

- DuckDB を使った分析処理は副作用を持たない（読み取り）設計を重視しています。AI 関連の書き込みは ai_scores / market_regime など明示的な箇所に限定されています。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- config_setup.py
- validate_config.py
- run_execution.py
- run_monitoring.py

サブパッケージ:
- ai/
  - news_nlp.py
  - regime_detector.py
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py (参照されるが省略)
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- tools/
  - paper_verification_report.py
  - __init__.py
- monitoring/
  - (上記の monitoring モジュール群)
- utils/
  - logging_setup.py
  - process_priority.py
  - __init__.py

プロジェクトルート:
- .env (作成推奨)
- data/ (DB, PID, flag 等を保存)
- logs/ (ログファイル)

---

## よくある運用フロー（例）

1. .env を作成（config_setup）
2. 設定を検証（validate_config）
3. duckdb・sqlite のデータ格納先を整備（データ投入は別途）
4. run_monitoring をデーモンで起動してシステム状態を監視
5. run_execution を起動して当日の取引セッションを実行（paper_trading では分離 DB に記録）
6. 必要に応じて tools.paper_verification_report で Paper Trading の結果を評価

---

## 注意事項 / セーフガード

- KABUSYS_ENV=live の場合は特に注意して設定を行ってください。validate_config は live 時にいくつかの警告を出します。
- .env は機密情報を含むため、絶対にリポジトリにコミットしないでください。
- OpenAI API を使う処理は料金が発生します。テスト時はモックや API キー無しでの挙動を考慮してください（score_news/score_regime は API キー未設定で ValueError を出します）。
- run_execution/run_monitoring は stop flag / kill flag をフラグファイルで制御します。運用時の自動化（systemd / supervisor / cron など）と組み合わせて利用してください。

---

問題や不明点があれば、どの機能についての README を充実させたいか（例: ExecutionEngine の仕様、DB スキーマ詳細、API 使用例など）を教えてください。README を追加で拡張して記載します。