# KabuSys

日本株自動売買システムの軽量実装（ライブラリ + 起動スクリプト群）。

このリポジトリは戦略（リサーチ・ファクター）、ポートフォリオ構築、発注実行、監視、AI（ニュースセンチメント・レジーム判定）などの主要コンポーネントを含みます。各モジュールはできるだけ副作用を避け、ユニットテストしやすい純粋関数／明確な DB 層分離を心がけて設計されています。

注意: README はコードベースから推測できる仕様をまとめたものです。実運用前に必ず環境設定・検証を行ってください。

---

概要、機能、セットアップ、使い方、主要ディレクトリ構成を以下にまとめます。

## プロジェクト概要
- 自動売買のコア機能（ExecutionEngine）と監視（MonitoringEngine）を備えた日本株向けシステム。
- DuckDB を分析用データベース、SQLite を監視・発注ログ用に使用。
- Paper Trading（ペーパートレード）モードで本番 DB と分離して動作可能。
- OpenAI を使ったニュース NLP（センチメント）およびレジーム判定モジュールを搭載（API キー必要）。
- ログは標準出力と日次ローテートファイルに出力。

## 主な機能一覧
- 環境設定ウィザード（.env 作成）：kabusys.config_setup.run_wizard（python -m kabusys.config_setup）
- 設定検証 CLI：kabusys.validate_config（python -m kabusys.validate_config）
- ExecutionEngine 起動スクリプト：python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録
- Monitoring 起動スクリプト：python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
- 監視コンポーネント
  - SystemMonitor: CPU/メモリ/ディスク・プロセス生存・データ鮮度監視
  - TradeMonitor: 発注ログ・滞留オーダー・約定異常等の検出（ソースに記載の通り）
  - RiskMonitor: ドローダウン・ポジション上限監視とダッシュボード更新
  - KillSwitch: 監視結果に応じて data/kill.flag を書き込み、Execution の停止を指示
  - MonitoringEngine: 各モニタを束ねたポーリングループとアラート通知（AlertManager 経由）
- ポートフォリオ構築ライブラリ
  - 候補選定、等重／スコア重み付け、セクター上限フィルタ、ポジションサイズ計算（lot 単位の丸め、aggregate cap）
- リサーチ（factor）モジュール
  - Momentum / Volatility / Value ファクター計算（DuckDB 接続を受け SQL で計算）
  - Feature exploration（forward returns, IC, summary）
- AI モジュール
  - news_nlp.score_news: raw_news から銘柄別センチメントを OpenAI に問い合わせ、ai_scores に書き込み
  - regime_detector.score_regime: ETF の MA200 乖離 + マクロニュースで市場レジーム判定し DB に書き込み
- ツール
  - paper_verification_report: ペーパートレード DB から稼働率・成功率・レイテンシ等の検証レポートを生成

## 必要条件（目安）
- Python 3.10+
- 主要 Python パッケージ:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config 検証で YAML 内容をチェックしたい場合。未インストールでも検証はスキップされる）
- SQLite は標準ライブラリに含まれます

推奨インストール例:
  pip install duckdb psutil openai PyYAML

（プロジェクトに requirements.txt がある場合はそちらを使用してください）

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローンして作業ディレクトリへ移動
2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存ライブラリをインストール
   - pip install duckdb psutil openai PyYAML
4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成
   - 自動 .env 自動読み込みはデフォルトで有効。テストで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
5. 設定検証（起動前に必ず実行）
   - python -m kabusys.validate_config
   - 警告も FAIL にしたい場合: python -m kabusys.validate_config --strict
6. データディレクトリの準備（自動作成されることが多いが確認）
   - デフォルト DB ファイル等は data/ 以下（例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）
7. OpenAI 機能を使う場合
   - 環境変数 OPENAI_API_KEY にキーを設定（config_setupでは設定対象外のため手動で）
8. ログディレクトリ
   - デフォルト logs/。必要に応じて LOG_DIR 環境変数で変更

## 環境変数（主要）
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨／オプション:
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR（ログファイルの保存先）
- OPENAI_API_KEY（AI 機能を使用する場合）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数を上書き）
- PAPER_FILL_MODE（ペーパートレードの約定挙動: instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか: 0/1）

詳細は kabusys.config.Settings と config_setup.py の _ITEMS を参照してください。

## 使い方（主要コマンド）
- .env を作る（対話式）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading として起動するとペーパーモード（MockBroker）で data/paper_trading.db に記録されます
  - 停止: data/stop_requested.flag を作成する（run_execution は停止フラグを監視します）
- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒）。例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視ループの停止は data/stop_requested.flag を作成
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH を優先）
- AI 機能（Python から呼び出す例）
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key="...")  # duckdb_conn は duckdb.connect(...)
  - regime_detector.score_regime も同様（OPENAI_API_KEY 設定が必要）

ログ:
- setup_logging により標準出力 + 日次ローテートファイル（logs/<app_name>.log）に出力
- LOG_DIR 環境変数で変更可

停止 / Kill Switch:
- 監視モジュールは条件に応じて data/kill.flag を書き込み、ExecutionEngine 側がこれを検知して安全に停止する仕組みがあります。
- 起動時に kill.flag を自動で消去したくない場合は KILL_FLAG_CLEAR_ON_START=0（デフォルト推奨：0）

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数/設定管理
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py                — ニュースセンチメント（OpenAI と連携）
    - regime_detector.py         — 市場レジーム判定（MA200 + マクロセンチメント）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py           — SQLite DB レイヤ（初期化・読み書き）
    - system_monitor.py
    - trade_monitor.py           — （存在：参考実装がある想定）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py           — （存在：参考実装がある想定）
  - execution/
    - execution_engine.py        — エンジン本体（起動・セッション管理）
    - broker_factory.py          — BrokerClient の生成（Mock を含む）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - data/ (ランタイムで作成)
    - monitoring.db (デフォルト)
    - kabusys.duckdb (デフォルト)
    - paper_trading.db (paper_trading モード)
    - stop_requested.flag
    - kill.flag
    - execution.pid

（上記は主要ファイルの抜粋です。詳細は src/kabusys 以下を参照してください。）

## 注意点 / 実運用での留意事項
- KABUSYS_ENV=live では実際に発注が行われます。API キーやパスワードの管理、テストを十分に行ってください。
- .env は絶対にリポジトリにコミットしないでください（config_setup.py にもその注意書きがあります）。
- AI（OpenAI）への問い合わせはコストとレイテンシが発生します。API キーとレート制限・リトライ方針を理解の上で運用してください。
- duckdb/sqlite のファイルパスは Settings で変更可能です。paper_trading モードでは paper_sqlite_path が使われ、本番 DB と分離されます。
- run_monitoring は MONITOR_POLL_INTERVAL によりポーリング間隔を制御します（デフォルト60秒）。0 以下や不正値は無視されデフォルトにフォールバックします。
- process priority / CPU affinity は環境に依存します（psutil を使っていますが権限不足で設定できない場合は警告を出してスキップします）。

---

より詳しい設計意図やアルゴリズム（PortfolioConstruction.md、StrategyModel.md 等）は別ドキュメントにまとめられている想定です。実装や外部インターフェースを変更する際は、設定検証ツール（kabusys.validate_config）を活用して安全性を確認してください。

不明点や追加で README に含めたい内容（例: サンプル .env、詳細な実行ログの読み方、ユニットテスト手順など）があれば教えてください。