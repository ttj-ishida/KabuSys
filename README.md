# KabuSys — README (日本語)

注意: この README は src/kabusys 以下のコードベースを元に作成しています。実行前に .env の設定や依存パッケージのインストールを行ってください。

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の一部を実装したモジュール群です。主に以下の機能群を含みます：
- ExecutionEngine（発注エンジン）とその周辺（Order 管理、Risk 管理、Reconciler 等）
- Monitoring（システム監視、トレード監視、リスク監視、Kill Switch）
- Portfolio 構築（候補選定・重み付け・ポジションサイズ計算・セクター制約）
- Research（ファクター計算、将来リターン、IC 計算、統計サマリー）
- AI 関連（ニュース NLP スコアリング、レジーム判定）
- ユーティリティ（設定ウィザード・設定検証・ログ設定・プロセス優先度設定）
- ツール（Paper Trading 検証レポート生成）

主な特徴
-------
- モジュール化された純粋関数群（portfolio, research 等）は DB に依存せずテスト容易
- DuckDB を利用したリサーチ用高速集計（prices_daily / raw_financials 等）
- OpenAI を利用したニュースセンチメント評価（AI スコアリング）と市場レジーム判定（LLM を利用）
- SQLite を使った監視ログ永続化（system_status / trade_logs / risk_logs / dashboard）
- Kill Switch による安全停止機構（条件に応じて data/kill.flag を作成）
- 起動スクリプト（run_execution / run_monitoring）でプロセス制御・ログ・DB 初期化を統一

セットアップ手順
----------------
1. リポジトリをクローンしてプロジェクトルートへ移動
   - 例: git clone <repo> && cd <repo>

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - 必須（最低限）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で YAML を検査したい場合）
   - 例:
     - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt を利用）

4. .env の準備
   - 対話式ウィザードで .env を生成/更新できます:
     - python -m kabusys.config_setup
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要:
     - .env はリポジトリにコミットしないでください（README 内にも注意書きあり）。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いで非ゼロ終了します:
     - python -m kabusys.validate_config --strict

6. DB・ディレクトリ準備
   - デフォルトでは data/ に SQLite/duckdb ファイルが置かれます（Settings で上書き可）。
   - ログは logs/ に出力されます（設定は環境変数 LOG_DIR で変更可能）。

使い方（起動・コマンド例）
-------------------------

共通: モジュールはパッケージモードで起動できます（プロジェクトルートで実行）。

1. ExecutionEngine（発注エンジン）を起動
   - python -m kabusys.run_execution
   - 動作モード:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db に記録（本番 DB と分離）
   - PID / 停止制御:
     - 実行時に data/execution.pid が使われます（Settings.pid_file_path）
     - 停止は data/stop_requested.flag を作成するか、Kill Switch による data/kill.flag によっても行われます

2. Monitoring（監視ループ）を起動
   - python -m kabusys.run_monitoring
   - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）
   - 監視は常に settings.sqlite_path（本番用監視 DB）を使用します（KABUSYS_ENV に依らず）

3. 設定ウィザード
   - python -m kabusys.config_setup

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告を失敗扱い

5. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - オプション:
     - --from YYYY-MM-DD, --to YYYY-MM-DD
     - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数で指定することも可能）

6. AI / Research の呼び出し（プログラムから）
   - ニューススコア: kabusys.ai.score_news（duckdb 接続と target_date を渡す）
   - レジーム判定: kabusys.ai.regime_detector.score_regime（duckdb 接続と target_date を渡す）
   - Research API:
     - calc_momentum / calc_volatility / calc_value（kabusys.research）
     - calc_forward_returns / calc_ic / factor_summary など

主要な環境変数（抜粋）
---------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- DB パス:
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用、デフォルト data/paper_trading.db）
- ログ:
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
  - LOG_DIR（デフォルト logs/）
- AI:
  - OPENAI_API_KEY（AI 機能利用時に必要）
- Monitoring:
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔・秒）
- Kill Switch:
  - KILL_FLAG_CLEAR_ON_START（1 にすると起動時に kill.flag を自動クリア）

注意点 / 実行上の挙動
-------------------
- run_monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（監視 DB）を使用します。
- run_execution は KABUSYS_ENV=paper_trading の場合に PAPER_TRADING_SQLITE_PATH を使用して本番 DB と切り離します。
- Kill Switch（kabusys.monitoring.kill_switch）は条件を満たした場合に data/kill.flag を書き込み、ExecutionEngine 側で検出して停止します。
- run_*.py は stop_requested.flag（data/stop_requested.flag）を検知するとループを抜けて終了します。
- ログ設定は kabusys.utils.logging_setup.setup_logging を通して統一され、console（stdout）出力と日次ローテーションログファイル（logs/<app>.log）を用います。
- process priority / CPU affinity の設定ユーティリティがあり、起動時に高優先度へ設定を試みます（psutil を使用）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数の読み込み・Settings クラス（自動 .env ロード: .env → .env.local）
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前チェック CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 対応）
- run_monitoring.py
  - Monitoring ポーリングループ起動スクリプト

- ai/
  - news_nlp.py
    - raw_news を LLM に送って銘柄ごとにセンチメントを算出し ai_scores に書き込む
  - regime_detector.py
    - ETF(1321) の MA200 乖離 + マクロニュース LLM で日次レジーム判定

- monitoring/
  - monitoring_db.py
    - SQLite スキーマの初期化・永続化ヘルパ
  - system_monitor.py
    - システム状態・データ鮮度監視
  - trade_monitor.py (存在)
    - 注文ログ監視（コードベースに含まれる想定）
  - risk_monitor.py
    - ドローダウン・ポジション上限監視
  - kill_switch.py
    - kill.flag の作成 / 管理
  - monitoring_engine.py
    - 各 Monitor を束ねるエンジン
  - alert_manager.py (存在)
    - アラート送信管理（LINE 等、コード内参照あり）

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py 等
    - 実際の発注ロジック・ブローカ抽象化・リスク管理

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - 高水準 API を __init__ でエクスポート

- research/
  - factor_research.py
  - feature_exploration.py
  - DuckDB を用いたファクター計算／IC／統計ツール

- data/
  - pipeline 等（prices_daily 等のデータ取得・前処理。コード内参照あり）

- tools/
  - paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプト

- utils/
  - logging_setup.py
  - process_priority.py
  - その他ユーティリティ

追加情報 / 推奨ワークフロー
-------------------------
- 開発時は KABUSYS_ENV=development を使い、本番用設定（KABUSYS_ENV=live）に切り替える前に validate_config を実行してください。
- Paper Trading（検証）を行う場合は KABUSYS_ENV=paper_trading を設定し、PAPER_TRADING_SQLITE_PATH を確認してください。
- AI（OpenAI）を使用する機能は API キーが必須です。API 呼び出しはリトライ・フェイルセーフが実装されていますが、API 利用に伴うレート制限やコストに注意してください。
- 監視と実行は別プロセスで運用する想定です。監視が Kill Switch を発動すると実行エンジンが停止します。stop_requested.flag による手動停止も可能です。

ライセンス・貢献
----------------
- この README ではライセンスや貢献方法については触れていません。実際のリポジトリには LICENSE や CONTRIBUTING ガイドがある場合はそちらを参照してください。

問題の報告 / 連絡
----------------
- バグや改善要望は issue を立ててください。実行時のログ（logs/<app>.log）を添えると調査がスムーズです。

以上。必要があれば README に用語解説、より詳細なデプロイ手順（systemd ユニットや Docker の例）、環境別設定サンプル（.env.example）などを追記します。どの情報がさらに欲しいか教えてください。