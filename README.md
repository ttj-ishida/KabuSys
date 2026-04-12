# KabuSys — README (日本語)

KabuSys は日本株向けの自動売買・リサーチ・監視ツール群のコードベースです。
この README はリポジトリ内の主要スクリプト／モジュールの概要、セットアップ、実行方法、ディレクトリ構成をまとめたものです。

要点
- Python ベースで、発注エンジン / 監視（Monitoring） / ポートフォリオ構築 / リサーチ / AI (ニュース NLP / レジーム検出) を含みます。
- DuckDB（時系列・ファクタ計算用）と SQLite（監視 / 注文ログ用）を組み合わせたデータ設計。
- Paper Trading モードと Live モードを切替可能（環境変数 KABUSYS_ENV）。
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント・マクロセンチメント評価機能あり（APIキー必須）。

機能一覧
- 実行エンジン（ExecutionEngine）
  - ブローカー抽象化・発注管理・リスク管理・リコンシリエーション（再起動後の同期）
  - Paper Trading モードでは MockBrokerClient を用い、paper_trading 用 DB に記録
- 監視（Monitoring）
  - システム状態（CPU/Memory/Disk/プロセス生存）監視
  - 注文滞留／約定異常検知
  - ドローダウン・ポジション上限監視と kill.flag による停止シグナル生成
  - LINE によるアラート送信（AlertManager）
  - Streamlit ダッシュボード（監視内容の可視化）
- ポートフォリオ構築（Portfolio）
  - 候補選定、等配分／スコア配分、リスク調整（セクター上限・レジーム乗数）、株数算出（単元丸め）
- リサーチ（Research）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC（情報係数）等の解析ユーティリティ
- AI 関連
  - ニュース記事を LLM でスコアリングして ai_scores に保存（news_nlp）
  - マクロ＋MA200 を組み合わせた市場レジーム判定（regime_detector）
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools.paper_verification_report）

前提要件（推奨）
- Python 3.10+
- 必要パッケージ（代表例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- 実行環境により追加が必要な場合あり（例: OS の権限で process priority の設定が失敗することがあります）

セットアップ手順（例）
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS)
   - .venv\Scripts\activate (Windows)

3. 依存パッケージをインストール
   - （requirements.txt がない場合）最低限:
     - pip install duckdb psutil requests openai streamlit
   - 実運用ではその他の内部モジュール依存に応じた追加パッケージが必要になることがあります。

4. データディレクトリ作成
   - mkdir -p data

5. 環境変数設定（.env / .env.local）
   - リポジトリルートに .env を置くと自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主な環境変数（デフォルト値は右側に記載）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - JQUANTS_REFRESH_TOKEN — 必須（J-Quants 用）
     - KABU_API_PASSWORD — 必須（kabuステーション API）
     - OPENAI_API_KEY — AI 機能利用時に必須
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知利用時
     - SQLITE_PATH — 監視 DB（data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイル（data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（data/paper_trading.db）
     - PID_FILE_PATH — ExecutionEngine の PID ファイル（data/execution.pid）
     - KILL_FLAG_PATH — kill.flag（data/kill.flag）
     - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
     - PAPER_FILL_MODE — paper_trading の約定モード（instant/partial/never/reject、デフォルト "instant"）
   - .env の書式は shell の export/KEY=val 等に準拠。config.py の自動読み込みロジックを参照してください。

使い方（主要スクリプト）
- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 概要:
    - MONITOR_POLL_INTERVAL でポーリング間隔を指定（秒）。デフォルト 60。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用します。
    - 実行時にプロセス優先度を "high" に設定しようとします（権限がない場合は警告のみ）。
- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - 概要:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH（既定: data/paper_trading.db）に記録するため本番 DB と分離されます。
    - 実行時に設定される RiskManager / OrderManager / Reconciler 等を組み立て、ExecutionEngine.run_session() を実行します。
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH より優先）
  - デフォルト DB: data/paper_trading.db
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System タブを表示します。
- AI 関連をプログラムから呼ぶ
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=None)  # api_key 未指定なら環境変数 OPENAI_API_KEY を参照
  - regime_detector の score_regime(conn, target_date, api_key=None) も同様
  - 注意: OpenAI API キー必須。API エラーはフェイルセーフ的に扱われる部分がありますが、APIキーが無ければ例外になります。

主要な挙動・注意点
- DB 初期化
  - run_monitoring/run_execution の起動時に monitoring DB 用のテーブル作成（init_monitoring_db）が行われます（冪等）。
  - マイグレーション: 必要に応じて既存テーブルに列を追加する処理を含みます（例: trade_logs に latency_ms を追加）。
- PID / Kill flag
  - ExecutionEngine は起動時に pid_file を書き、SystemMonitor はその PID ファイルを読みプロセス生存確認を行います。
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります（存在時は再書き込みしない）。
  - Settings.kill_flag_clear_on_start を 1 にすると起動時に kill.flag をクリアします。
- Paper Trading
  - 実行エンジンは KABUSYS_ENV=paper_trading の場合、paper_trading 用の SQLite を使用しブローカー呼び出しはモック化されます（本番 DB と完全分離）。
- AI モジュール
  - OpenAI 呼び出しはリトライや JSON 検証のロジックを実装しているものの、API の挙動に依存します。API レスポンスの検証に失敗した場合はスコアを取得できない（空）扱いになります。
- プロセス優先度
  - 起動スクリプトは set_process_priority("high") を呼びます。権限がない場合は警告のみで継続します。

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数読み込み / Settings クラス
  - run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール
  - monitoring/
    - __init__.py
    - monitoring_db.py             — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py            — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py             — 滞留注文・約定異常検出
    - risk_monitor.py              — ドローダウン・ポジション上限監視
    - kill_switch.py               — kill.flag の作成・評価
    - alert_manager.py             — LINE Push 通知ラッパー
    - monitoring_engine.py         — 各 Monitor を束ねるループ
    - streamlit_dashboard.py       — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - ... (Engine・Broker 関連)
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                  — ニュース NLP（OpenAI 呼び出し + ai_scores 書込）
    - regime_detector.py           — マクロ + MA200 によるレジーム判定
  - data/
    - pipeline.py (など)           — DuckDB/price データ取得ユーティリティ
  - utils/
    - process_priority.py          — psutil を使った優先度・affinity 設定ユーティリティ

開発メモ / トラブルシューティング
- .env 読み込み
  - config._find_project_root によりプロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local をロードします。
  - テスト等で自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB が見つからない/読み取り専用エラー
  - Streamlit は read-only URI モードで開こうとします。MonitoringEngine が DB を作成していない場合は先に run_monitoring を起動してください（または手動で SQLite を用意）。
- OpenAI の利用
  - OPENAI_API_KEY を環境変数に設定してください。API 呼び出し回数／コストに注意してください（batching とトークン制限を考慮した実装あり）。
- 権限
  - process priority の変更 / CPU affinity の設定は OS 権限に依存します。権限不足時はログに WARNING が出て処理は継続します。

ライセンス / 貢献
- この README はコードベースの説明用テンプレです。実運用／商用利用時はコードのライセンスと組織内ルールに従ってください。
- バグ報告・機能提案・プルリクエストはリポジトリの issue / PR を利用してください。

以上がリポジトリの概要と基本的な使い方です。細かい実装や API の挙動については各モジュール（monitoring/*.py、execution/*.py、ai/*.py、portfolio/*.py、research/*.py）内の docstring を参照してください。必要であれば、各モジュールごとの詳細ドキュメントやサンプルを追加で作成します。