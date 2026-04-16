README — KabuSys (日本株自動売買システム)
====================================

概要
----
KabuSys は日本株の自動売買・バックオンド運用を想定した小規模なフレームワークです。
主な機能は以下の通りです。

- 注文送信と状態管理を行う ExecutionEngine（ブローカー抽象化）
- モニタリング（システム状態・注文監視・リスク監視）とアラート
- ポートフォリオ構築（銘柄選定、重み計算、ポジションサイズ決定）
- リサーチ用ファクター計算（Momentum / Volatility / Value 等）
- ニュースNLP を使った銘柄センチメント評価（OpenAI を利用）
- 市場レジーム判定（MA + LLM）
- Paper Trading（モックブローカー）モードのサポート
- Streamlit ベースの監視ダッシュボード、検証レポート生成ツール

主な設計方針
- DB と外部 API へのアクセスは明確に分離（Paper Trading 用 DB は本番 DB と分離）。
- ルックアヘッドバイアスを避ける設計（date.today() の直接参照回避等）。
- フェイルセーフ：API 失敗時は例外を上位に広げずフォールバックする箇所が多い。
- テスト容易性を考慮して外部呼出しを差し替え可能に実装。

機能一覧
--------
- Execution
  - 発注フロー管理（OrderManager / OrderRepository）
  - 再起動時のリコンシリエーション（Reconciler）
  - リスク管理（RiskManager）
  - BrokerClientFactory による実ブローカー / Mock ブローカー切替（KABUSYS_ENV=paper_trading）
- Monitoring
  - SystemMonitor: CPU/Memory/Disk、プロセス監視、データ鮮度チェック
  - TradeMonitor: 滞留注文、約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限の監視とログ記録
  - KillSwitch: リスク条件で実行エンジン停止フラグを出力
  - AlertManager: LINE へ一方向プッシュ通知（クールダウン管理）
  - Streamlit ダッシュボード（read-only で monitoring.db を表示）
  - monitoring DB 管理と簡易マイグレーション（monitoring_db.init_monitoring_db）
- Portfolio
  - 銘柄選定・重み付け（等配分・スコア加重）
  - セクター上限適用、レジーム乗数
  - ポジションサイズ計算（単元丸め、aggregate cap）
- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算・IC（Information Coefficient）等の解析ユーティリティ
- AI
  - news_nlp.score_news: raw_news を集約して OpenAI でセンチメント評価 → ai_scores に書き込み
  - regime_detector.score_regime: MA200 とマクロニュースの LLM スコアを合成して market_regime に保存
- Tools
  - paper_verification_report: Paper Trading の検証レポート生成（期間指定可）

セットアップ手順
----------------

前提
- Python 3.9+（コードは型アノテーション等を使用）
- システムに sqlite3 が利用可能（標準）
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード使用時)
※ 実際の requirements.txt はプロジェクト側で管理してください。

例: 仮想環境作成とパッケージインストール
- Unix/macOS:
  python -m venv .venv
  source .venv/bin/activate
  pip install -U pip
  pip install duckdb psutil requests openai streamlit

環境変数 / .env
- 自動読み込み: プロジェクトルートに .env / .env.local があれば自動で読み込まれます（OS 環境変数が優先）。
- 自動読み込みを無効化する場合:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

重要な環境変数（主なもの）
- KABUSYS_ENV: 起動環境 ("development", "paper_trading", "live")。デフォルト: development
  - paper_trading の場合、MockBrokerClient を使用し paper_trading DB (data/paper_trading.db) に記録
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使用する場合）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: paper_trading の SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant/partial/never/reject）デフォルト: instant
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch の flag ファイルパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）

初期データディレクトリ
- data/ 以下に DB や PID/flag ファイルを置く設計です。実行時に存在しない場合は自動的に作成されることがあります（権限等に注意）。

使い方
------

起動スクリプト
- Execution（エンジン）起動:
  - モジュール実行:
    python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading DB に記録します。
    - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
    - PID ファイルを data/execution.pid に書きます。
- Monitoring（監視）起動:
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒、デフォルト 60）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視は一意の DB を想定）。
  - 停止にはプロジェクトルート/data/stop_requested.flag の作成でループを抜けます。

Paper Trading 検証レポート
- コマンド:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- オプション:
  --from / --to: YYYY-MM-DD 形式で期間指定
  --db: SQLite DB パス（PAPER_TRADING_SQLITE_PATH 環境変数での指定と同等）

Streamlit ダッシュボード（監視画面）
- 起動方法（開発用）:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- read-only で monitoring DB を開くため、MonitoringEngine を起動してデータを溜めておく必要があります。

AI 機能（ニューススコアリング / レジーム判定）
- news_nlp の実行例（外部呼び出しとして）:
  from kabusys.ai.news_nlp import score_news
  score_news(conn, target_date, api_key="（省略可：OPENAI_API_KEY環境変数を使用）")
- regime_detector の実行例:
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date, api_key=...)

停止・KillFlag
- KillSwitch はリスク条件で data/kill.flag を書き込みます。ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START 設定によりこれをクリアできます（Settings 参照）。

開発時の注意
- DuckDB/SQLite の接続はファイルパスで指定されます。複数プロセスで同じ SQLite を開く場合は排他や接続モードに注意してください（monitoring dashboard は read-only URI を使っています）。
- OpenAI 呼び出しをテスト時に差し替えるため、内部の API 呼び出し関数は patch しやすい構造になっています（例: news_nlp._call_openai_api）。

ディレクトリ構成（主要ファイル）
---------------------------------
src/
  kabusys/
    __init__.py                     — パッケージ情報（__version__）
    config.py                       — 環境変数 / Settings（.env 自動読み込み）
    run_execution.py                — ExecutionEngine 起動スクリプト
    run_monitoring.py               — SystemMonitor ポーリング起動スクリプト

    execution/
      order_manager.py
      order_repository.py
      order_record.py
      execution_engine.py
      broker_factory.py
      reconciler.py
      risk_manager.py
      ...（ブローカー関連、注文フロー）

    monitoring/
      monitoring_db.py               — monitoring 用 SQLite 層（テーブル作成・読み書き）
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py
      monitoring_engine.py
      streamlit_dashboard.py
      __init__.py

    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
      __init__.py

    research/
      factor_research.py
      feature_exploration.py
      __init__.py

    ai/
      news_nlp.py
      regime_detector.py
      __init__.py

    tools/
      paper_verification_report.py
      __init__.py

    data/                           — 実行時に使用するデータディレクトリ（DB, pid, flags など）

補足 / 実運用メモ
- モニタリングは監視対象（ExecutionEngine）の PID ファイルを参照してプロセス存否を検出します。PID ファイルの信頼性が重要です。
- Paper Trading モードは本番 DB と完全分離されるよう設計されています。実ブローカーと繋ぐ前に paper_trading で検証することを推奨します。
- 環境変数の不備は Settings クラスで ValueError を投げることがあります。起動前に .env を整備してください。
- monitoring_db.init_monitoring_db は既存 DB に対してカラム追加などのマイグレーション（簡易）を行いますが、複雑なスキーマ変更には注意してください。

ライセンス・コントリビューション
- 本リポジトリにライセンスファイルが含まれている場合はそちらを参照してください。
- バグ修正や機能追加の際は小さな単位で PR を送ることを推奨します。

お問い合わせ
- 実装上の疑問や改善提案があれば Issue / PR を作成してください。README の不足点や実行手順の環境依存事項（OS、Python バージョン等）は随時更新してください。

以上。必要であればサンプル .env.example を作成したり、主要コマンドの systemd / supervisor 用の unit ファイル例、docker-compose の雛形なども追加で作成します。希望があれば教えてください。