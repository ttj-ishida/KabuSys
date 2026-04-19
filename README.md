# KabuSys — README (日本語)

KabuSys は日本株向けの自動売買・リサーチ基盤です。本リポジトリには以下の主要機能・ユーティリティが含まれます：戦略用ファクター計算・特徴量解析、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、AI を用いたニュースセンチメント取得など。

以下はこのコードベースの概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成です。

---

## プロジェクト概要
- 目的：日本株の自動売買システムと研究ツール群を提供する。
- コンポーネント：
  - ExecutionEngine（発注エンジン、paper_trading 対応）
  - Monitoring（システム稼働・注文・リスクを監視し、Kill Switch を発動可能）
  - Portfolio モジュール（候補選定・重み計算・ポジションサイズ決定・リスク調整）
  - Research（ファクター計算・将来リターン・IC 計算など）
  - AI モジュール（ニュースセンチメント、レジーム判定：OpenAI を利用）
  - ツール類（.env ウィザード、設定検証、Paper Trading 検証レポート等）

---

## 主な機能一覧
- 設定管理
  - .env の自動読み込み / 対話式ウィザード（kabusys.config_setup）
  - 設定検証ツール（kabusys.validate_config）
- 実行（Execution）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - BrokerClient 抽象化（環境に応じて実クライアント or モックを使用）
  - リスク管理 (RiskManager), 注文管理 (OrderManager), 照合 (Reconciler)
- 監視（Monitoring）
  - SystemMonitor：CPU/メモリ/ディスク/データ鮮度/プロセス健全性
  - TradeMonitor：滞留注文、約定異常等の検出（trade_logs を利用）
  - RiskMonitor：ドローダウン監視・ポジション数上限監視、Dashboard の更新
  - KillSwitch：条件により data/kill.flag を書き込み ExecutionEngine の停止シグナル発行
  - MonitoringEngine：各 Monitor を束ねて定期実行、通知（AlertManager 経由）
- 研究（Research）
  - momentum / volatility / value ファクター計算（DuckDB を使用）
  - 将来リターン計算、IC（Spearman）算出、統計サマリ
- AI（OpenAI）
  - ニュースを LLM（gpt-4o-mini）でセンチメント評価し ai_scores テーブルへ保存
  - 市場レジーム判定（ETF の MA とマクロニュースの LLM 評価を統合）
  - OpenAI API へのリトライ・バリデーション・部分書き込みを実装
- ユーティリティ
  - ロギング設定（コンソール + 日次ローテートログ）
  - プロセス優先度 / CPU affinity 設定
  - Paper Trading 向け検証レポート生成ツール

---

## セットアップ手順（ローカル開発向け）
前提：
- Python 3.10 以上（型アノテーションの union 型表記などを使用）
- 任意の仮想環境（venv / pyenv など）

1. レポジトリをクローンしてワークディレクトリへ移動
   - git clone ... ; cd <repo>

2. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必要パッケージ（代表例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証用に任意）
   - 例:
     - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt がある場合はそれを使用してください）

4. 環境変数設定（.env 作成推奨）
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合:
     - OPENAI_API_KEY
   - 主要な環境変数（デフォルト値あり）:
     - KABUSYS_ENV (development|paper_trading|live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
     - LOG_LEVEL — デフォルト: INFO
     - KILL_FLAG_CLEAR_ON_START — デフォルト: 0

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を指定すると警告も失敗（exit 1）扱いになります

6. データディレクトリ等の作成
   - data/ や logs/ は自動で作成されますが、権限等で失敗する場合は手動作成してください。

---

## 使い方（起動・ツール）
各モジュールは Python のモジュール実行で起動できます。

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）へ記録します。
    - 実行時に data/stop_requested.flag を監視し、存在すればエンジン停止します。
    - 実行中は data/execution.pid に PID を書きます。

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）
    - 監視は本番 sqlite_path を参照（KABUSYS_ENV にかかわらず本番 DB を使用）
    - 停止は data/stop_requested.flag の作成で検知

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- AI 関連（プログラム内 API）
  - kabusys.ai.score_news(duckdb_conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=None)
  - いずれも api_key を省略すると環境変数 OPENAI_API_KEY を参照

注意点：
- .env は絶対にリポジトリにコミットしないでください（機密情報が含まれるため）
- MONITOR_POLL_INTERVAL は整数秒。1 未満・不正値はデフォルト 60 秒にフォールバック
- KILL/STOP フラグ：
  - KillSwitch は data/kill.flag を書き込んで ExecutionEngine の停止を促します（kill.flag を書くのは Monitoring 側の判断）
  - run_* スクリプトは data/stop_requested.flag を監視して自発終了する仕組みがあります

---

## 環境変数（主要）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- OpenAI:
  - OPENAI_API_KEY（AI 機能を使う場合）
- 起動・ログ:
  - KABUSYS_ENV (development|paper_trading|live)
  - LOG_LEVEL (DEBUG|INFO|...)
  - LOG_DIR（ログ保存先、デフォルト logs/）
  - MONITOR_POLL_INTERVAL（監視ポーリング秒数）
- DB パス:
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト data/paper_trading.db）
- Kill Switch:
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動でクリアするか、1=クリア）

自動 .env 読み込み：
- リポジトリルートにある .env / .env.local を自動で読み込みます（OS 環境変数を優先）。
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主なファイル）
（プロジェクトルートを src/ として示します）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理、自動 .env 読み込み
  - config_setup.py                — 対話式 .env ウィザード
  - validate_config.py             — 起動前設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                   — ニュース NLP スコアリング（OpenAI 利用）
    - regime_detector.py            — 市場レジーム判定（MA + マクロ LLM）
  - monitoring/
    - monitoring_db.py              — SQLite 用永続化層
    - system_monitor.py
    - trade_monitor.py              — （trade 関連の監視ロジック）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py              — （通知送信ロジック：LINE 等）
  - execution/
    - execution_engine.py           — ExecutionEngine 実装
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - utils/
    - logging_setup.py              — ログ設定ユーティリティ
    - process_priority.py           — プロセス優先度 / CPU affinity
  - data/ (ランタイム生成)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - kill.flag / stop_requested.flag / execution.pid など

（上記は抜粋です。詳細は各モジュールの docstring を参照してください。）

---

## 開発・デバッグのヒント
- ログはデフォルトで stdout と logs/<app_name>.log（日次ローテーション）に出力されます。
- Monitoring のポーリング間隔は MONITOR_POLL_INTERVAL で調整できます（単位: 秒）。
- 実行エンジンは stop/kill フラグによる外部制御を想定しています。運用時は flag ファイルの扱いに注意してください。
- DuckDB は分析（research）向け。prices_daily / raw_financials / raw_news 等のテーブルを準備すると research 機能が動作します。
- AI 機能は OpenAI API へ実ネットワークコールを行います。テスト時は該当関数の内部呼び出しをモックできます（コード内に patch しやすい実装あり）。

---

## ライセンス / 貢献
- 本 README にライセンス情報は含めていません。リポジトリの LICENSE を参照してください。
- バグ報告や機能提案は issue を作成してください。

---

README はここまでです。各モジュールやスクリプトの具体的な使用方法や引数は、該当ファイルの docstring / ヘルプ（python -m <module> --help）を参照してください。必要であれば、起動例・.env のテンプレート・デプロイ手順（systemd / supervisor / Docker）などの運用ドキュメントも作成しますので、その旨をお知らせください。