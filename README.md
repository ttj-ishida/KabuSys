# KabuSys

KabuSys は日本株向けの自動売買・研究・監視ツール群をまとめた Python パッケージです。本リポジトリには、注文実行エンジン、監視デーモン、ポートフォリオ構築ユーティリティ、ファクター計算・リサーチ用モジュール、LLM を使ったニュース NLP / レジーム判定などが含まれます。

以下は本コードベースの概要、主要機能、セットアップ・起動方法、使い方、ディレクトリ構成の説明です。

注意: 本 README はコード中の docstring / コメント・振る舞いに基づいて作成しています。実運用前に必ず設定値・ API キー・DB のバックアップを確認してください。

---

## プロジェクト概要

- 日本株自動売買システムの構成要素群（Execution / Monitoring / Research / Portfolio / AI）を提供します。
- 実行エンジンはブローカークライアントを用いて注文を行い、監視モジュールはシステム状態・注文状態・リスク指標を SQLite に永続化して監視・アラートを行います。
- 研究用モジュールは DuckDB を用いてファクター計算・将来リターン計算・IC計算等を行います。
- AI モジュール（OpenAI）を使ったニュースセンチメント評価やマクロセンチメントを用いた市場レジーム判定をサポートします（APIキー必須）。
- Paper Trading（テスト用）モードを用意しており、本番 DB と分離して動作可能です。

---

## 主な機能一覧

- Execution
  - ExecutionEngine を起動して注文管理を行う（再起動時のリコンシリエーション機能あり）。
  - Paper Trading モード（KABUSYS_ENV=paper_trading）では MockBrokerClient を使用し、data/paper_trading.db に記録して本番 DB と分離。
  - リスク管理（RiskManager）、注文状態管理（OrderManager）等を備える。

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス生存・データ鮮度を定期記録。
  - TradeMonitor: 注文滞留・約定異常価格を検出。
  - RiskMonitor: ドローダウン・ポジション上限を監視しリスクイベントを記録。
  - MonitoringEngine: 各 Monitor をまとめてポーリング、KillSwitch により異常時に停止フラグを立てる。
  - AlertManager: LINE Messaging API によるプッシュ通知（クールダウン管理あり）。
  - Streamlit ベースの監視ダッシュボード（読み取り専用）。

- Research / Portfolio
  - ファクター計算（momentum / volatility / value）: DuckDB を用いた純粋関数実装。
  - 将来リターン計算、IC（情報係数）計算、ファクター統計サマリ。
  - ポートフォリオ構築ユーティリティ（候補選択、重み計算、位置サイズ決定、セクター上限適用、レジーム乗数）。

- AI
  - news_nlp: OpenAI（gpt-4o-mini）を使ったニュースのセンチメント集計 → ai_scores テーブルへ保存。
  - regime_detector: ETF の MA200 乖離とマクロニュースセンチメントを合成して日次の市場レジーム判定を行う。
  - API 呼び出しはリトライ・バックオフ・フェイルセーフ実装あり。

- ツール
  - paper_verification_report: Paper Trading DB を解析して検証レポートを出力（稼働率、注文成功率、レイテンシ等）。

---

## セットアップ手順

前提:
- Python 3.10+（型ヒントに `|` を使用しているため）を推奨します。
- 仮想環境 (venv) を作成してから作業してください。

例:
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Unix/macOS) または .venv\Scripts\activate (Windows)

2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使ってください）

3. 環境変数の設定
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（デフォルト）。
   - 読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（Settings クラスで参照されるもの）
- 必須（実行内容による）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意 / 推奨:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
  - OPENAI_API_KEY: news_nlp / regime_detector 用
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db） — Monitoring DB（monitoring は環境にかかわらず本番 sqlite_path を使用）
  - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db） — Paper Trading 用 DB
  - PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の注文応答モード）
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

4. データディレクトリ
   - data/ 配下に DB・フラグファイル等を配置します。自動的に作成される箇所もありますが、パーミッション等は確認してください。

---

## 使い方（主要コマンド・起動方法）

- ExecutionEngine を起動
  - 目的: 注文実行・リスナー等を起動
  - 環境変数例: KABUSYS_ENV=paper_trading を指定すると Paper Trading モードとなり、専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用します。
  - 実行:
    - python -m kabusys.run_execution
  - 動作:
    - process priority を high に設定し、DB に接続して各コンポーネント（BrokerClient / OrderRepository / RiskManager / ExecutionEngine）を起動します。
    - 起動時に data/stop_requested.flag が存在する場合は起動をスキップします。
    - 停止は data/stop_requested.flag の作成で監視され、Engine.stop() を呼んで安全に停止します。
    - PID は data/execution.pid に記録される（Settings.pid_file_path）。

- Monitoring を起動
  - 目的: 定期ポーリングでシステム・注文・リスク監視・ログ永続化を行う
  - 実行:
    - python -m kabusys.run_monitoring
  - オプション / 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）。不正値・0 以下はデフォルトにフォールバック。
  - 動作:
    - SystemMonitor / TradeMonitor / RiskMonitor 等を利用して SQLite（monitoring DB）にログを残します。
    - 停止はプロジェクトルート/data/stop_requested.flag の存在で検知してループ終了します。
    - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使います（監視ログのファイル名は Settings.sqlite_path）。

- Streamlit ダッシュボード（読み取り専用）
  - 実行:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明:
    - 読み取り専用で SQLite を開き、ダッシュボード表示（Overview / Positions / Orders / System）

- Paper Trading 検証レポート
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - オプション例:
      - --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
    - 環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを指定可能（--db が優先）

- AI モジュール（OpenAI）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡して銘柄ごとのニュースセンチメントを ai_scores テーブルに書き込む。
    - api_key を渡すか環境変数 OPENAI_API_KEY を設定する必要あり。
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - DuckDB 接続を渡して market_regime テーブルに判定結果を書き込む。
  - 注意:
    - OpenAI API 呼び出しはリトライ・バックオフ・失敗時フェイルセーフ（0.0 など）を備えていますが、APIキーと API 利用料・レート制限に注意してください。

- 停止／Kill Switch 周り
  - ExecutionEngine を外部から停止させたい場合は data/kill.flag（KillSwitch / AlertManager 連携）を書き込む仕組みがあります。
  - run_execution/run_monitoring では data/stop_requested.flag の存在で終了処理を行います。

---

## 開発・テストのヒント

- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml がある階層）に .env / .env.local があれば自動で環境変数を読み込みます（OS 環境変数の上書きは .env.local の override により制御）。
  - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1。

- DB 初期化
  - monitoring DB のスキーマは init_monitoring_db() によって冪等に作成されます。monitoring 起動時に自動で初期化されます。

- ログレベル
  - LOG_LEVEL 環境変数で制御できます（Settings.log_level）。

- モジュールを直接呼び出してユニットテスト可能
  - 例えば research.calc_momentum / calc_volatility 等は DuckDB 接続と日付を渡して純粋関数として実行できます（テスト容易）。

---

## 主要ファイル・ディレクトリ構成（抜粋）

以下はソースツリー（src/kabusys）内の主要ファイルと簡単な説明です。パッケージは src 配下にあります。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定読み取り（.env 自動ロード含む）
    - Settings クラスで主要な構成項目を取得
  - run_monitoring.py
    - SystemMonitor をポーリングするデーモンエントリ
  - run_execution.py
    - ExecutionEngine を起動するエントリ（Paper Trading 切替あり）
  - tools/
    - paper_verification_report.py
      - Paper Trading DB の検証レポート生成スクリプト
  - ai/
    - news_nlp.py
      - ニュースを OpenAI でスコアリングして ai_scores に保存
    - regime_detector.py
      - マクロニュース + ETF MA200 を用いた市場レジーム判定
  - monitoring/
    - monitoring_db.py
      - SQLite スキーマ定義 & MonitoringDB（読み書きラッパ）
    - system_monitor.py
      - CPU/メモリ/ディスク・プロセス・データ鮮度監視
    - trade_monitor.py
      - 注文滞留・約定異常監視
    - risk_monitor.py
      - ドローダウン・ポジション上限監視
    - kill_switch.py
      - kill.flag 書き込みユーティリティ
    - alert_manager.py
      - LINE 通知クライアント
    - monitoring_engine.py
      - 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py
      - Streamlit 監視ダッシュボード（読み取り専用）
  - portfolio/
    - portfolio_builder.py
      - 候補選定・重み計算
    - position_sizing.py
      - 株数決定・投下資金スケール・単元丸め
    - risk_adjustment.py
      - セクター上限適用・レジーム乗数
  - research/
    - factor_research.py
      - momentum / volatility / value 等のファクター計算（DuckDB）
    - feature_exploration.py
      - 将来リターン・IC・ファクター統計等
  - execution/
    - order_manager.py
      - 注文状態機械の外向き API
    - reconciler.py
      - 起動時の注文・ポジション同期ロジック
    - （その他 broker_factory, execution_engine, order_repository 等が存在）
  - utils/
    - process_priority.py
      - プラットフォーム依存性を吸収してプロセス優先度や CPU affinity を設定

（上記はコードベースの主要モジュールの抜粋です。実際のリポジトリにはさらに細かなファイル群が含まれます。）

---

## 参考（よく使うコマンド）

- ExecutionEngine 起動（Paper Trading）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Monitoring 起動（ポーリング間隔 30 秒に変更）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または DB 指定: --db data/paper_trading.db

- OpenAI を使うスクリプト実行時
  - 環境変数: OPENAI_API_KEY=sk-xxxxx

---

## 注意点 / 運用上の留意事項

- 本番運用時は KABUSYS_ENV を必ず確認してください（live と paper_trading の違いに注意）。
- API キー（OpenAI、Kabu API 等）は安全に管理してください。
- データベースファイル（data/*.db）は定期的にバックアップを取ってください。
- monitoring は本番の sqlite_path を使います。Paper Trading DB は paper_sqlite_path で別ファイルに保持されます。
- AI 呼び出し（OpenAI）は課金対象かつレート制限があります。エラー時のフォールバックは組み込まれていますが、運用ポリシーを決めてください。

---

この README はコード内の docstring とコメントに基づく概要ドキュメントです。各モジュールの詳細な API や内部ロジックを確認するには該当ファイルの docstring / コメントを参照してください。必要であれば各モジュールごとの詳細ドキュメント（使用例・API 仕様・ユニットテスト例）も作成できます。希望があればどのモジュールを優先してドキュメント化するか教えてください。