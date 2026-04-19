KabuSys — 日本株自動売買システム（リポジトリの概要）
  
このリポジトリは日本株向けの自動売買システム KabuSys のコアモジュール群を含みます。  
主に以下の機能を提供します：戦略用のファクター計算、ポートフォリオ構築、発注エンジン（本番/ペーパー分離）、監視・アラート、AI を使ったニュース／レジーム判定、運用支援ツール（検証レポート生成・設定ウィザード等）。

プロジェクトの主な特徴（機能一覧）
- Execution エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード用の専用 SQLite DB（data/paper_trading.db）へ記録して本番と分離。
  - プロセス優先度の設定、PID ファイル管理、停止フラグ読み取り対応。
- Monitoring エンジン（run_monitoring.py / monitoring/*.py）
  - System / Trade / Risk 各モニタを定期実行し監視ログを SQLite に永続化。
  - Kill Switch（条件に応じて data/kill.flag を書き込んで Execution を停止）やアラート送信トリガを備える。
  - MONITOR_POLL_INTERVAL 環境変数で監視ポーリング間隔を変更可能（デフォルト 60 秒）。
- ポートフォリオ構築（portfolio/*）
  - 候補選定、等配分／スコア加重配分、ポジションサイズ計算（単元丸め、各種上限・スケーリングロジック）。
  - セクターキャップ適用、レジーム乗数（calc_regime_multiplier）等のリスク調整関数。
- リサーチ（research/*）
  - DuckDB を用いたファクター計算（モメンタム / バリュー / ボラティリティ）や将来リターン・IC 計算、特徴量サマリ。
- AI ユーティリティ（ai/*）
  - ニュースの NLP による銘柄別センチメント（OpenAI API を利用）と ai_scores への書き込み。
  - マクロニュース＋ETF MA200 を統合した市場レジーム判定（score_regime）。
  - OpenAI 呼び出しは API キー（OPENAI_API_KEY）を必要とする。
- 設定支援ツール
  - 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
  - 起動前設定検証 CLI（python -m kabusys.validate_config）
- 運用支援ツール
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

前提（推奨環境）
- Python 3.10 以上（型記法に | を使用）
- 必要パッケージ（代表例）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config 検証で YAML を検査する場合、任意）
- システムによりプロセス優先度や CPU affinity の設定で管理者権限が必要になる場合があります。

セットアップ手順
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - optional: pip install pyyaml

   （プロジェクトに requirements.txt があればそれを使ってください）

4. .env の初期作成（対話ウィザード）
   - python -m kabusys.config_setup
     - 対話に従い必須値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を設定してください。
     - OpenAI を利用する場合は OPENAI_API_KEY を環境変数か .env に設定してください（config_setup は OPENAI_API_KEY を直接扱いませんが、環境変数で渡せます）。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 問題があれば表示されるエラー/警告に従って修正してください。
   - --strict を指定すると警告も失敗扱いになります（exit(1)）。

データベース / ログ初期配置
- デフォルトの DB / ファイルパス（.env で上書き可）
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - PID / フラグ / ログ:
    - data/execution.pid（Execution 用の PID）
    - data/stop_requested.flag（外部からの停止要求検出用）
    - data/kill.flag（Kill Switch 用）
    - logs/（ログ出力ディレクトリ、setup_logging が作成）

使い方（起動例・主要コマンド）
- Execution Engine（発注実行）
  - python -m kabusys.run_execution
  - 説明:
    - KABUSYS_ENV により本番 / ペーパーが切り替わる（paper_trading の場合は専用 DB と MockBroker）。
    - 起動時に既存の stop flag があると起動せず終了します。
    - 実行中は data/execution.pid に PID を書きます。停止は stop flag（data/stop_requested.flag）や kill.flag に依存。

- Monitoring（監視ループ）
  - python -m kabusys.run_monitoring
  - 説明:
    - SystemMonitor を定期的に実行して system_status 等を monitoring DB に保存します。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定（例: export MONITOR_POLL_INTERVAL=30）。
    - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用します（監視は常に本番 DB の状態を監視する想定）。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 失敗時は exit code が 1（--strict で警告も失敗扱い）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別 DB を指定できます。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能。

- AI 機能（ニューススコア / レジーム判定）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime などをアプリケーションから呼び出します。
  - 実行には OPENAI_API_KEY の設定が必要です（関数引数で渡すことも可）。
  - API 呼び出しはリトライやフェイルセーフロジックを備えています（失敗時は安全側のデフォルトで継続）。

運用上の注意点
- Kill Switch / stop flag:
  - kill.flag（data/kill.flag）は監視で発動し、存在すれば ExecutionEngine に停止シグナルを送ります。起動時に KILL_FLAG_CLEAR_ON_START を 1 にしていると自動クリアされますが、本番では 0 を推奨します。
  - stop_requested.flag（data/stop_requested.flag）を作成すると run_execution / run_monitoring のループが検知して優雅に終了します。
- ログ:
  - ロギングは logs/<app_name>.log に日次ローテーションで出力（デフォルト 30 日保持）。ログディレクトリの作成に失敗した場合はコンソール出力のみになります。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等で実行され、必要なテーブル・カラムがない場合に追加（例: peak_value, latency_ms の追加）します。

主要ディレクトリ構成（src/kabusys 以下の重要ファイル）
- __init__.py
- config.py — 環境変数/.env ロード、Settings クラス
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前チェック CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

- execution/   — 発注エンジン関連（BrokerFactory, ExecutionEngine, OrderManager 等）
- monitoring/
  - monitoring_db.py — SQLite 永続化層
  - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py, alert_manager.py ...
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — モメンタム/バリュー/ボラティリティ等
  - feature_exploration.py — forward returns / IC / 統計サマリ
- ai/
  - news_nlp.py — ニュースセンチメント（OpenAI）
  - regime_detector.py — 市場レジーム判定（OpenAI + ETF MA）
- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度設定ユーティリティ
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト
- data/ （実行時に使用／生成される想定）
  - monitoring DB、paper_trading DB、PID / flag / logs など

開発者向けメモ
- DuckDB 接続を受けて SQL と Python を組み合わせた計算を行う設計です。prices_daily, raw_financials, raw_news 等のテーブルを前提にしています。
- AI 呼び出し部分は外部 API（OpenAI）への依存があり、テスト時は _call_openai_api をモックする設計になっています。
- 設定の自動読み込みは .env / .env.local をプロジェクトルートから自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- ローカル開発では KABUSYS_ENV=development を使うと多くの部分が安全に動作（発注は行われない設計）します。

問い合わせ / 貢献
- バグ報告・改善提案は Issue を作成してください。Pull Request は歓迎します。
- 主要な変更（DB スキーマや API 仕様変更）は README と対応するスクリプトのコメントに明示してください。

以上で README.md の内容になります。実行前に .env（必須環境変数 JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等）を正しく設定し、python -m kabusys.validate_config で確認することを強く推奨します。