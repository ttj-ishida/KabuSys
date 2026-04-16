KabuSys — 日本株自動売買システム
==============================

このリポジトリは日本株自動売買システム KabuSys の内部モジュール群です。戦略・ポートフォリオ構築・発注エンジン・監視・AI 補助（ニュース NLP / レジーム判定）・研究用ユーティリティなどを含みます。本 README はローカルでのセットアップ、主要スクリプトの実行方法、ディレクトリ構成の概要を示します。

要点
- Python パッケージとして利用可能（src パッケージ構成）
- 簡易 DB に SQLite（監視用 / ペーパートレード用）と DuckDB（時系列・ファクター計算用）を使用
- 環境変数／.env ファイルを使った設定管理（自動ロードあり）
- Paper Trading（KABUSYS_ENV=paper_trading）時は実ブローカーから分離された専用 DB を使用
- 監視・アラートは LINE Push、監視ダッシュボードは Streamlit で可視化

主な機能一覧
- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカー抽象化（本番 / モック切替）
  - 発注管理（OrderManager, OrderRepository, Reconciler）
  - リスク管理（RiskManager）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/データ鮮度/実行プロセス監視
  - TradeMonitor: 注文の滞留・約定価格異常検出
  - RiskMonitor: ドローダウン / ポジション上限監視、kill flag 生成
  - AlertManager: LINE への一方向プッシュ通知（クールダウンあり）
  - MonitoringEngine: 上記モニタを束ねてポーリング
  - Streamlit ダッシュボード（監視データの可視化）
- Research / Portfolio
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算・IC 計算・特徴量解析
  - ポートフォリオ構築（候補選定・等重／スコア重み付け）
  - ポジションサイズ決定（単元丸め・資金制約・スケーリング）
- AI
  - news_nlp.score_news: OpenAI を使ったニュースセンチメントスコアリング
  - regime_detector.score_regime: ETF MA とマクロニュースから日次レジーム判定
- Tools
  - paper_verification_report: ペーパートレード DB を解析して検証レポートを出力

前提 / 必要パッケージ
- Python 3.9+
- 外部ライブラリ（最低限）
  - psutil
  - duckdb
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- 必要に応じて pip 等でインストールしてください：
  pip install psutil duckdb requests openai streamlit

設定と環境変数
- .env / .env.local の自動読み込み
  - プロジェクトルート（.git または pyproject.toml を検出）を基準に .env を自動ロードします。
  - OS 環境変数 > .env.local > .env の順に優先されます。
  - テスト等で自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

主な環境変数（よく使うもの）
- KABUSYS_ENV: 起動モード。可能値: development / paper_trading / live（デフォルト: development）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- PAPER_FILL_MODE: ペーパートレード時の約定振る舞い（instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START などの監視関連パスや挙動

セットアップ手順（ローカル）
1. リポジトリをクローンし、ワークツリー上で作業
2. 仮想環境を作成・有効化（推奨）
   python -m venv .venv
   source .venv/bin/activate
3. 必要パッケージをインストール
   pip install psutil duckdb requests openai streamlit
   （requirements.txt がある場合はそれを利用）
4. data ディレクトリを作成（スクリプト実行時に自動作成されることもあるが手動作成を推奨）
   mkdir -p data
5. .env を作成（.env.example を参考に環境変数を設定）
   例:
     KABUSYS_ENV=development
     OPENAI_API_KEY=sk-...
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb

実行方法（主要スクリプト）
- 監視ループ（SystemMonitor 単体起動）
  - モジュール実行：
    python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を上書き：
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止：プロジェクトルートの data/stop_requested.flag ファイルを作成するとループを抜けます。

- 実行エンジン（ExecutionEngine）起動
  - モジュール実行：
    python -m kabusys.run_execution
  - Paper Trading モード:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    （paper_trading 時は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録）

- Streamlit ダッシュボード（監視可視化）
  - 起動：
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ブラウザでダッシュボードを開いて監視メトリクスを確認できます（DB は読み取り専用で開かれます）。

- ペーパートレード検証レポート
  - 実行：
    python -m kabusys.tools.paper_verification_report
  - 期間指定：
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定：
    python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

運用上のファイル／フラグ
- data/stop_requested.flag: run_monitoring / run_execution がこのファイルを検知すると安全終了します。
- data/execution.pid: ExecutionEngine の PID（run_execution が利用）
- data/kill.flag: KillSwitch が書き込む停止フラグ（ExecutionEngine に停止指示するための永続化フラグ）
- 各種 DB（デフォルトパス）は Settings クラス経由で取得されます（kabusys.config.Settings）

開発者向けポイント
- 設定管理
  - kabusys.config.Settings に主要な設定プロパティがまとまっています。未設定必須値は _require() で ValueError を投げます。
  - 自動 .env 読み込みはプロジェクトルートを探索して .env/.env.local を読み込みます。
- DB 初期化・マイグレーション
  - monitoring_db.init_monitoring_db(conn) が監視用テーブル作成と簡易マイグレーション（カラム追加）を行います（冪等）。
- モジュール API（主なエントリ）
  - kabusys.monitoring.MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor / AlertManager
  - kabusys.execution.OrderManager / Reconciler
  - kabusys.portfolio.*（ポートフォリオ構築）: select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
  - kabusys.research.*（ファクター計算・IC 等）
  - kabusys.ai.score_news / regime_detector.score_regime
- OpenAI 連携
  - news_nlp.score_news / regime_detector.score_regime は OPENAI_API_KEY を参照（または関数引数で API キーを渡せます）。
  - API 呼び出しはリトライやフェイルセーフ実装あり（失敗時はスキップして続行する設計）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py (パッケージ定義)
  - config.py (設定／.env 読み込み)
  - run_monitoring.py (SystemMonitor ポーリングループ)
  - run_execution.py (ExecutionEngine 起動)
  - tools/
    - paper_verification_report.py (ペーパートレード検証レポート)
  - ai/
    - news_nlp.py (ニュース NLP スコアリング)
    - regime_detector.py (市場レジーム判定)
  - monitoring/
    - monitoring_db.py (SQLite 永続化層)
    - system_monitor.py, trade_monitor.py, risk_monitor.py
    - monitoring_engine.py, alert_manager.py, kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py, reconciler.py, ...（ブローカー抽象・注文管理等）
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - research/
    - factor_research.py, feature_exploration.py
  - utils/
    - process_priority.py (プロセス優先度 / CPU affinity ユーティリティ)

運用上の注意
- 実行時に process priority の設定（set_process_priority("high")）を試みますが、権限不足やプラットフォーム非対応の場合は警告を出して継続します。
- Monitoring は KABUSYS_ENV に依らず監視用の本番 sqlite_path を使用します（監視ログは一元管理）。
- Paper Trading は本番 DB と完全分離された sqlite（PAPER_TRADING_SQLITE_PATH）を使用。PAPER_FILL_MODE による約定挙動（instant/partial/never/reject）を設定可能です。
- kill.flag を用いた停止は確実なシャットダウンを保証するものではありません。運用時は PID ファイルやログで状況を確認してください。
- OpenAI キーは秘匿情報のため .env/.env.local に直接置くか、CI/ランタイム環境のシークレットとして管理してください。

トラブルシューティング
- DB が開けない / テーブルがない:
  - run_monitoring.run や init_monitoring_db() 実行でテーブル作成されます。手動で DB を確認してください。
- OpenAI 呼び出しが失敗する:
  - OPENAI_API_KEY の設定、ネットワーク、API レート制限を確認。実装はリトライとフェイルセーフがあるため、失敗しても処理は継続します（スコア 0 やスキップ）。
- LINE 通知が届かない:
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID の設定を確認。AlertManager はトークン未設定時に送信をスキップします。

ライセンス / 貢献
- 本プロジェクトのライセンス表記・貢献ガイドはリポジトリルートに置いてください（ここには含めていません）。

付録: よく使うコマンド例
- 監視ループ（60秒間隔）
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- 実行エンジン起動（ペーパートレード）
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Streamlit ダッシュボード起動
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- ペーパートレード検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

必要な追加情報や、README に追記したい項目（例: 実際のブローカー導入手順、CI 設定、詳細設計ドキュメントへのリンクなど）があれば教えてください。README をそれに合わせて拡張します。