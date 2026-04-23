# KabuSys README (日本語)

KabuSys は日本株自動売買システム用のコアライブラリ群です。本リポジトリは取引エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AI ベースのニュース解析などのモジュールを含みます。ここでは概要、機能、セットアップ手順、使い方、ディレクトリ構成を説明します。

※ 本ドキュメントはソースコード（src/kabusys 以下）に基づいて作成しています。

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買プラットフォームのコンポーネント群です。主な目的は下記です。

- 戦略に基づく銘柄選定・ポジションサイズ計算（portfolio）
- 実際の発注を担う ExecutionEngine（本番/ペーパートレード対応）
- システム稼働状況・注文状態・リスクの継続監視とアラート（monitoring）
- DuckDB ベースでのファクター計算やリサーチ用ユーティリティ（research）
- OpenAI API を用いたニュースセンチメント解析や市場レジーム判定（ai）
- 環境設定用ウィザード・設定検証ツール・検証レポート生成スクリプト等（tools / scripts）
- 共通ユーティリティ（ログ設定、プロセス優先度など）

設計方針として、外部 API 呼び出しを明示的に扱い、ペーパートレード時は本番 DB と完全分離する等の安全策が組み込まれています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine の起動スクリプト（python -m kabusys.run_execution）
  - 本番（live）・ペーパートレード（paper_trading）モード対応（DB 分離、MockBroker）
  - プロセス優先度設定（高優先で起動）
  - 停止フラグ / PID 管理（data/execution.pid, data/stop_requested.flag 等）
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - システム稼働（CPU, メモリ, ディスク）、データ鮮度、プロセス生存を監視
  - KillSwitch（しきい値超過で data/kill.flag により ExecutionEngine に停止を指示）
  - 監視ログ永続化（SQLite）
- Portfolio
  - 候補選定、等金額・スコア重み、リスク調整（セクター上限、レジーム乗数）
  - ポジションサイズ算出（単元株丸め、最大ポジション制約、利用可能現金に対するスケール調整）
- Research
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）等の統計ユーティリティ
- AI
  - ニュース NLP（OpenAI）による銘柄別センチメント算出（ai_scores への書込み）
  - 市場レジーム判定（ETF MA + マクロニュースセンチメントの合成）
  - OpenAI の呼び出しはリトライ/バックオフ・レスポンス検証を備える
- ユーティリティ
  - ログセットアップ（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定（psutil 使用）
  - .env ウィザード（config_setup）、設定検証（validate_config）
- ツール
  - ペーパートレード検証レポート生成スクリプト（tools/paper_verification_report.py）

---

## 前提 / 必要要件

- Python 3.10 以上（| 型ヒント等を使用）
- 推奨パッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の内容検証に使用、任意）
- ネットワーク接続（OpenAI 使用時）
- kabuステーション API を使う場合はローカルまたは接続先の API が利用可能であること

（プロジェクトに requirements.txt がある場合はそちらを使ってインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン / ソース配置
   - この README は `src/kabusys` に配置されたコードを想定しています。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 必要パッケージをインストール
   - 例:
     - pip install --upgrade pip
     - pip install duckdb psutil openai
     - （PyYAML が必要なら）pip install pyyaml

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または .env を手動で作成（.env.example を参考にすること）
   - 重要な環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN （必須）
     - KABU_API_PASSWORD （必須）
     - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
     - OPENAI_API_KEY （AI 機能を使う場合必須）
     - DUCKDB_PATH（例: data/kabusys.duckdb）
     - SQLITE_PATH（例: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
     - LOG_LEVEL（任意、デフォルト INFO）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict オプションで警告もエラー扱いにできます

6. データディレクトリの準備
   - logs/（ログ保存先、setup_logging が自動作成します）
   - data/（データベース、PID/flag ファイル用）
   - 実行前に自動で作成されることが多いですが、権限等により手動作成が必要な場合があります

---

## 使い方

主要なモジュール起動方法（例）:

- ExecutionEngine を起動（本番 / ペーパートレードを env で切替）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - python -m kabusys.run_execution
  - 起動時に data/stop_requested.flag が存在すると起動を中止します
  - 実行中は data/execution.pid に PID を書き、停止は data/stop_requested.flag を作成することで行います

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）
  - 監視は常に production 用 sqlite_path を使用（環境にかかわらず）

- .env の対話式作成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH （なければ PAPER_TRADING_SQLITE_PATH 環境変数またはデフォルト data/paper_trading.db）

- AI 機能
  - ニューススコア付け: kabusys.ai.score_news（DuckDB 接続と target_date が必要）
  - 市場レジーム判定: kabusys.ai.regime_detector.score_regime
  - OpenAI API キーは環境変数 OPENAI_API_KEY または関数引数で渡す

停止 / Kill Switch / フラグ制御:

- Execution を停止したい場合:
  - data/stop_requested.flag を作成すると run_execution のポーリングループが検知して停止します
- KillSwitch:
  - 監視コンポーネントがしきい値超過を検出すると data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを与えます（Execution 側は kill.flag を定期的にチェックします）
- PID ファイル:
  - data/execution.pid（ExecutionEngine）、その他に PID を書く仕組みがあります

ログ:

- デフォルトでは logs/ ディレクトリにアプリケーション別ログファイルが日次ローテートで出力されます（例: logs/execution.log, logs/monitoring.log）
- コンソール出力は stdout に出るよう設定されています（crontab 等でのリダイレクトに適合）

環境変数の主要な一覧（抜粋）:

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/...
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant/partial/never/reject）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等

注意事項:

- KABUSYS_ENV=paper_trading 時は MockBrokerClient を使い、paper_trading 用 DB（data/paper_trading.db）に記録されます。本番 DB と分離されます。
- monitoring の初期化は実行時に DB スキーマを作成するため通常の初期化操作は不要です（init_monitoring_db が冪等に動作します）。
- OpenAI を使用する機能は API 呼び出し失敗時にフェイルセーフ（多くはスコア 0 やスキップ）で処理継続するよう設計されていますが、API キーを必ず設定してください。

---

## ディレクトリ構成（主なファイル）

（src/kabusys 配下を想定）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数/.env 自動読み込み、Settings クラス
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前設定検証ツール
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
      - ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py
      - ログ設定ユーティリティ（stdout + 日次ローテーション）
    - process_priority.py
      - プロセス優先度 / CPU affinity ユーティリティ
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (参照あり)
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (参照あり)
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - data/ (想定データディレクトリ)
    - monitoring.db
    - paper_trading.db
    - kill.flag, stop_requested.flag, execution.pid などのフラグ/PID ファイル

（上記はコード中に参照されている主なモジュールとスクリプトを抜粋したものです）

---

## 開発・運用メモ / ベストプラクティス

- 本番環境（KABUSYS_ENV=live）では特に kill flag やログレベル、LINE 通知等の設定を慎重に確認してください（validate_config は live 時に注意喚起します）。
- .env は決してリポジトリにコミットしないでください。
- ペーパートレード実行時は PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH を確認してください。
- ログディレクトリ・DB のパスに対する権限（作成・書き込み）を事前に確認してください。ログディレクトリの作成に失敗した場合、コンソール出力のみで継続します。
- OpenAI 絡みの処理は API 呼び出しに失敗してもシステム全体を崩壊させないようフォールバックがありますが、API 呼出しのコストやレート制限に注意してください。

---

必要であれば、README に追記する内容（例: 詳細な ExecutionEngine の設定項目、monitoring のアラート設定、サンプル .env）や、各モジュールの内部ドキュメント化（API 仕様の記載）を作成します。どの部分を優先して追加しますか？