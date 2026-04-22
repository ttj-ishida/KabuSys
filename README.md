KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買・リサーチ・監視ユーティリティ群（KabuSys）の一部実装です。
README はローカル開発・デプロイ向けの概要、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

主なポイント
- Python パッケージとして構成されており、各種起動スクリプトを python -m kabusys.<module> で実行します。
- SQLite（監視用）と DuckDB（分析用）をデフォルトで data/ 以下に保存します。
- .env 自動読み込み機能を持ち、config_setup で対話的に .env を作成できます。
- Paper Trading（ペーパートレード）と Live（本番）を環境変数で切り替え可能。
- OpenAI を用いたニュース NLP / レジーム判定機能を含みます（APIキー必須）。

機能一覧
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番/ペーパーどちらでも動作。KABUSYS_ENV=paper_trading の場合は MockBroker を使い paper DB に記録。
  - プロセス優先度設定、PID ファイル管理、停止フラグ対応。
- Monitoring 起動スクリプト（run_monitoring.py）
  - SystemMonitor をポーリングして system_status 等を記録。MONITOR_POLL_INTERVAL で間隔を設定可能。
  - 停止フラグ stop_requested.flag による終了検出。
- 設定ウィザード（config_setup.py）
  - 対話的に .env を作成・更新。
- 設定検証 CLI（validate_config.py）
  - .env と config/*.yaml の存在や基本整合性チェック。--strict オプションあり。
- Paper Trading 検証レポート生成（tools/paper_verification_report.py）
  - ペーパートレード用 SQLite から安定性・約定率・レイテンシ等のレポートを出力。
- ポートフォリオ構築（portfolio/*）
  - 候補選定、重み計算、セクターキャップ、ポジションサイズ算出などの純粋関数群。
- リサーチ（research/*）
  - DuckDB 上でファクター計算（Momentum/Volatility/Value）、特徴量探索、IC 計算などを実装。
- AI モジュール（ai/*）
  - news_nlp: ニュースを集約して OpenAI に投げ、銘柄ごとのセンチメントを ai_scores に格納。
  - regime_detector: ETF（1321）MA200 とマクロニュースを組み合わせて市場レジームを判定・保存。
- 監視永続化層（monitoring/monitoring_db.py）と各種 Monitor（system_monitor, trade_monitor, risk_monitor）
  - system_status / trade_logs / positions / risk_logs / dashboard テーブルを管理。

前提・依存
- Python 3.9+
- 必要パッケージ（代表例）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（validate_config で YAML の中身検証を使う場合）
- SQLite は標準ライブラリで動作
- ログはデフォルトで logs/ に出力（TimedRotatingFileHandler）

セットアップ手順（ローカル開発）
1. リポジトリをクローンし、作業ディレクトリを移動
   - 例: git clone ... && cd <repo>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存をインストール（例）
   - pip install -r requirements.txt
   ※ requirements.txt がない場合は上記の主要依存を個別にインストール:
     pip install duckdb psutil openai PyYAML

4. .env を作成
   - 対話式に作る: python -m kabusys.config_setup
   - もしくは .env.example を参考に .env を手動作成
   - .env の自動ロード:
     - デフォルトではプロジェクトルートにある .env / .env.local を自動で読み込みます。
     - テスト時など自動ロードを抑制したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
- OPENAI_API_KEY（AI 機能を使う場合必須）
- PAPER_FILL_MODE（paper_trading 時の約定モード: instant/partial/never/reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔（秒）、run_monitoring 用、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START（本番環境での Kill Flag 自動クリア、0/1）

使い方（起動・主要コマンド）
- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合、MockBroker を使い PAPER_TRADING_SQLITE_PATH に記録。
    - 起動時に data/execution.pid（デフォルト）を書き、停止は data/stop_requested.flag または data/kill.flag により制御。

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（秒）。
  - 監視は本番 sqlite_path を参照（環境に関係なく本番 DB を使用する設計）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH の上書き）

AI 機能（news_nlp / regime_detector）
- OpenAI API key が必要（OPENAI_API_KEY または各関数の api_key 引数）。
- news_nlp.score_news(conn, target_date, api_key=None) は DuckDB 接続を受け取り ai_scores テーブルに書き込みます。
- regime_detector.score_regime(conn, target_date, api_key=None) は market_regime テーブルに書き込みます。
- API エラーはリトライやフェイルセーフ（スコア 0.0 など）で扱われる設計です。

停止・Kill Switch
- monitoring/kill_switch.py により、ドローダウンやポジション上限超過時に data/kill.flag を書き込んで ExecutionEngine を停止させる仕組みがあります。
- 手動停止は data/stop_requested.flag を作成することで run_monitoring/run_execution のループを抜けさせられます。
- 起動時に kill.flag を自動クリアしたい場合は KILL_FLAG_CLEAR_ON_START=1 を .env に設定できますが、本番では 0 を推奨します。

ログ
- デフォルト: logs/<app_name>.log（日次ローテーション、30日保持）
- コンソールは stdout に出力されます。LOG_DIR でログディレクトリを変更可能。
- setup_logging(app_name="...") で統一的に設定されます。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数/設定管理（.env 自動ロード・Settings クラス）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数算出、aggregate cap ロジック
    - risk_adjustment.py — セクターキャップ、レジーム乗数
    - __init__.py
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン、IC、統計サマリー
    - __init__.py
  - ai/
    - news_nlp.py — ニュースを集約して OpenAI でスコアリング
    - regime_detector.py — レジーム判定ロジック
    - __init__.py
  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化・DB ラッパー
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （存在する場合）発注監視（ファイル内未示）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - monitoring_engine.py — 複数 Monitor のオーケストレーション
    - kill_switch.py — フラグファイルで Execution を停止するロジック
  - utils/
    - logging_setup.py — ログ一括設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
    - __init__.py
  - monitoring/monitoring_db.py — DB テーブル定義（system_status, trade_logs, positions, risk_logs, dashboard）

補足 / 実運用上の注意
- KABUSYS_ENV=live の設定時は本番向けの注意喚起が出ます。LINE 通知設定等を必ず確認してください。
- .env を絶対に Git にコミットしないでください（config_setup のヘッダにも記載）。
- DuckDB / SQLite のパスは .env で変更可能。Paper Trading は専用 SQLite（PAPER_TRADING_SQLITE_PATH）で本番 DB と分離する設計になっています。
- OpenAI を使う処理は外部 API 呼び出しのため、レスポンスの堅牢性確保のためにリトライ・バリデーション処理が実装されています。API 利用料やレート制限に注意してください。

ライセンス・貢献
- このリポジトリ内でのライセンス情報やコントリビュートルールはルートの LICENSE / CONTRIBUTING を参照してください（本 README には含まれていません）。

質問や補足があれば、どの箇所を詳しく記載したいか教えてください。必要に応じてサンプル .env、起動スクリプトの具体的な環境変数例、systemd / Supervisor 用のサービス定義テンプレートなども作成できます。