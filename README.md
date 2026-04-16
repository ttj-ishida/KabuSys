# KabuSys — README (日本語)

以下はこのリポジトリ（src/kabusys 以下に実装された日本株自動売買システム）の概要と使い方です。開発者向けの軽い導入ドキュメントとなります。

プロジェクト概要
- KabuSys は日本株向けの自動売買フレームワークです。売買エンジン（ExecutionEngine）、監視／アラート機能（Monitoring）、ポートフォリオ構築、リサーチ（ファクター算出／特徴量解析）、AI を使ったニュースセンチメント／レジーム判定などのコンポーネントを含みます。
- DuckDB を使った時系列データ処理、SQLite を使った監視ログ・注文ログの永続化、OpenAI（gpt-4o-mini を想定）でのニュース NLP 評価などを組み合わせた設計です。

主な機能一覧
- ExecutionEngine（起動スクリプト: run_execution.py）
  - ブローカークライアント経由で注文送信、OrderManager による状態管理、RiskManager によるリスクチェック、起動時のリコンシリエーション（Reconciler）などを実行。
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）に記録して本番 DB と分離。
- Monitoring（起動スクリプト: run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングして system_status, trade_logs, risk_logs, dashboard などを更新。
  - LINE 通知（AlertManager）や kill flag による ExecutionEngine 停止トリガーをサポート。
- AI モジュール
  - news_nlp.score_news: raw_news を集約して OpenAI に送り銘柄ごとのセンチメントを ai_scores に保存。
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime を算出・保存。
- Research / Portfolio
  - factor_research: Momentum / Volatility / Value ファクター算出（DuckDB）
  - research.feature_exploration: 将来リターン、IC 計算、統計サマリー
  - portfolio: 候補選定、重み付け、位置サイズ計算、セクターキャップ、レジーム乗数などの純粋関数群
- 運用補助ツール
  - tools.paper_verification_report: Paper Trading DB を集計して検証レポートを生成
  - monitoring/streamlit_dashboard.py: Streamlit による監視ダッシュボード

前提 / 必要ライブラリ
- Python 3.9+（型ヒントや新しい構文を利用）
- 必要な外部パッケージ（代表例、requirements.txt がない場合は手動でインストール）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボードを使う場合）
- 標準ライブラリ: sqlite3, threading, datetime, pathlib など

セットアップ手順（ローカル開発向け）
1. リポジトリをチェックアウトしてルートに移動（pyproject.toml または .git によりプロジェクトルートが検出されます）。
2. 仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（pip コマンド例）:
   - pip install duckdb psutil requests openai streamlit
   - （プロダクションや CI では要件固定の requirements.txt / poetry を用意してください）
4. data ディレクトリを準備:
   - mkdir -p data
5. 環境変数を設定（.env ファイルをプロジェクトルートに置くと自動読み込みされます。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）
   - 必須（Settings._require により起動時参照される）
     - JQUANTS_REFRESH_TOKEN (J-Quants 用)
     - KABU_API_PASSWORD (kabuステーション API 用)
   - 推奨 / 運用用
     - OPENAI_API_KEY (AI モジュールを使う場合)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (LINE 通知)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト INFO
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB デフォルト: data/paper_trading.db）
   - その他:
     - PAPER_FILL_MODE ("instant" | "partial" | "never" | "reject") — paper_trading の挙動
     - PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEM/DISK 閾値など（Settings クラス参照）
6. （任意）paper_trading 用 DB の初期化は Execution の起動処理や monitoring の init_monitoring_db が行うため通常は不要。

使い方（代表的なコマンド）
- 監視ループを起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は常に settings.sqlite_path（本番の monitoring.db）を使います（KABUSYS_ENV に依存しない）。
  - 終了は Ctrl+C、またはプロジェクトルート/data/stop_requested.flag を作成すると次回ポーリング前に終了処理されます。
- ExecutionEngine を起動（注文エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ書き込み、本番 DB と分離されます。
  - エンジンの PID は data/execution.pid（デフォルト）に保存され、同ファイルの存在確認でプロセス生存を判定します。
  - エンジン停止は data/stop_requested.flag を作成することで実行プロセスへ伝達できます。
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション例:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数を上書き）
- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、positions, trade_logs, system_status, risk_logs, dashboard を表示します。
- AI モジュール
  - news_nlp.score_news(conn, target_date, api_key=None) — 必ず OpenAI API キー（引数または OPENAI_API_KEY 環境変数）を指定
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、DB 内の raw_news / prices_daily 等を参照して処理します。

停止・フラグ
- 停止要求（監視ループ / 実行エンジン）
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループが検出して終了または停止処理を行います。
- Kill Switch（自動停止）
  - KillSwitch がトリガーすると data/kill.flag を書き込み、ExecutionEngine 停止のトリガーとして機能します。KillSwitch の判定は RiskMonitor の結果（ドローダウンやポジション上限）に基づきます。
- PID ファイル
  - 実行エンジンは data/execution.pid（デフォルト）へ PID を書きます。SystemMonitor はこの PID ファイルを参照してプロセスの生存確認を行います。stale PID は自動で削除されアラートログが残ります。

設定の自動読み込み
- プロジェクトルート（.git または pyproject.toml を基準）から .env と .env.local を自動読み込みします（OS 環境変数を保護）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

監視 DB のスキーマとマイグレーション
- init_monitoring_db(conn) で必要なテーブル（system_status, trade_logs, positions, risk_logs, dashboard）とインデックスを作成します（冪等）。
- 既存 DB に対して必要に応じたカラム追加（例: dashboard.peak_value、trade_logs.latency_ms）を行う簡易マイグレーション処理を含みます。

ディレクトリ構成（主要ファイル・モジュールの説明）
- src/kabusys/
  - __init__.py — パッケージメタデータ（__version__ 等）
  - config.py — 環境変数・設定読み込み・Settings クラス（.env 自動読み込みロジック含む）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト
  - ai/
    - news_nlp.py — ニュース文章の LLM センチメント評価・ai_scores 保存ロジック
    - regime_detector.py — マクロ＋ETF 指標を合成した市場レジーム判定（market_regime 保存）
  - monitoring/
    - monitoring_db.py — SQLite を使った永続化 API（MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の書き込み/管理
    - alert_manager.py — LINE push 通知（AlertManager）
    - monitoring_engine.py — 各 Monitor を束ねてポーリングする上位エンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py, reconciler.py, ... — 注文管理、リコンシリエーション等
  - portfolio/
    - portfolio_builder.py — 候補選定・スコア並べ替え
    - position_sizing.py — 発注株数計算ロジック（単元丸め、aggregate cap 等）
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value ファクター算出（DuckDB）
    - feature_exploration.py — IC/将来リターン/統計サマリー
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/ (実行時に使用 / 登録されるファイル群)
    - monitoring.db（デフォルト: SQLITE_PATH）
    - kabusys.duckdb（デフォルト: DUCKDB_PATH）
    - paper_trading.db（PAPER_TRADING_SQLITE_PATH）
    - execution.pid / stop_requested.flag / kill.flag

開発上の注意点・運用上の注意
- paper_trading モードは本番 DB と分離するため、テスト検証に便利です。paper_trading 時は PAPER_TRADING_SQLITE_PATH を確認してください。
- OpenAI API を利用するモジュールはネットワーク障害や API 制限に備えたリトライ／フォールバックを実装していますが、API キーの管理（レート制限等）と費用に注意してください。
- Settings は必須環境変数のチェックを行います。起動時に ValueError が出た場合は .env を確認してください。
- process priority / cpu affinity 設定は psutil を利用しています。権限不足やプラットフォーム非対応時は警告ログが出力されますが致命エラーにはなりません。
- DB 書き込みは多くの箇所でコミットを行います。大量イベントを処理する際はパフォーマンスに注意してください（必要に応じてバッチ化検討）。

トラブルシューティング（簡易）
- DB が見つからない / 読み取りできない: paths（DUCKDB_PATH / SQLITE_PATH）を確認、パスにアクセス権があるか確認。
- OpenAI 呼び出しで失敗する: OPENAI_API_KEY を設定、ネットワーク疎通・API レートを確認。
- PID 周りの stale 判定でプロセスが検出されない: data/execution.pid の内容を確認（数値 PID）、権限やファイル書き込みが正しいか確認。
- Streamlit で DB を読み込めない: streamlit コマンドの -- --db オプションで正しいパスを渡すか、データベースが存在し監視エンジンで初期化済みか確認。

最後に
- 本ドキュメントはリポジトリ内のコードコメント、Settings、各モジュールの docstring に基づいています。詳細な設計・アルゴリズム仕様は各モジュール内のドキュメント（ソース内コメント）を参照してください。
- 追加の運用手順（デプロイ、監視の冗長化、Secrets 管理、CI/CD）については別途作業が必要です。

必要であれば、README に含めるサンプル .env.example、requirements.txt、起動スクリプトの systemd ユニット例などのテンプレートも作成します。必要な項目を教えてください。