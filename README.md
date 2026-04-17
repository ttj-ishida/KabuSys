# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買・研究・監視機能を備えた小規模なシステムです。  
README はコードベースから抜粋した主要コンポーネントと使い方を日本語でまとめたものです。

---

目次
- プロジェクト概要
- 主な機能
- 環境変数 (主なもの)
- セットアップ手順
- 実行方法（使い方）
- ファイル / ディレクトリ構成
- 運用時の注意点

---

プロジェクト概要
- 「KabuSys」は日本株の自動売買システムを想定したモジュール群です。
- 注文管理、リコンシリエーション、リスク監視、監視ダッシュボード、ポートフォリオ構築、ファクター計算、ニュース NLP（OpenAI）連携などの機能を提供します。
- DuckDB を用いた研究／価格データ処理、SQLite を用いた監視ログ／注文ログ保存、外部ブローカー API との連携を想定しています。
- 環境ごとに挙動を分ける設計（development / paper_trading / live）。

主な機能一覧
- ExecutionEngine 起動スクリプト（run_execution）  
  - 実取引（live）もしくは Paper Trading（paper_trading）でブローカークライアントを切り替え、注文発行・管理を行う。
  - Paper Trading 時は専用 SQLite DB に記録して本番 DB と分離。
- Monitoring（run_monitoring / MonitoringEngine）  
  - システム資源・プロセス状態・データ鮮度・注文滞留・約定異常・ドローダウン等を定期チェック。
  - 監視ログは SQLite（デフォルト: data/monitoring.db）に保存。
  - KillSwitch によるフラグファイルで ExecutionEngine 停止を指示可能。
- Dashboard（Streamlit）  
  - 監視 DB を読み取り、ポートフォリオやポジション、注文、システム状態を可視化。
- Paper Trading 検証レポート（tools/paper_verification_report.py）  
  - Paper Trading DB を集計して稼働率・注文成功率・レイテンシ等のレポートを出力。
- Portfolio 構築（portfolio/*）  
  - 候補選定、等重／スコア加重、セクター制限、ポジションサイズ計算などの純粋関数を実装。
- Research（research/*）  
  - DuckDB の価格・財務データからファクター（モメンタム・ボラティリティ・バリュー等）を計算、IC・統計を算出。
- AI 統合（ai/*）  
  - news_nlp: news テーブルを集約して OpenAI に投げ、銘柄別センチメントを ai_scores テーブルに書き込む。
  - regime_detector: ETF(1321)の MA200 乖離とマクロニュースの LLM センチメントを合成して市場レジーム判定を行い DB に保存。
- ユーティリティ  
  - process_priority: プラットフォーム差分を吸収してプロセス優先度・CPU affinity を設定。
  - monitoring_db: 監視用 SQLite の初期化・読み書きラッパー。

主要な環境変数（抜粋）
- KABUSYS_ENV: 起動環境。development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API のトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必須）
- PAPER_FILL_MODE: paper_trading 時の約定挙動（instant / partial / never / reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると .env 自動ロードを無効化

セットアップ手順（開発環境向け）
1. Python バージョン
   - 推奨: Python 3.10+（実行環境に合わせて調整してください）
2. リポジトリをクローンしてワークディレクトリへ移動
   - git clone ...
3. 仮想環境作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
4. 必要パッケージのインストール（requirements.txt が無い場合は主な依存を手動で）
   - pip install duckdb psutil requests streamlit openai
   - なお、SQLite は標準ライブラリで利用可
5. .env を用意（プロジェクトルートに .env / .env.local を配置して環境変数を設定）
   - 例（.env）:
     JQUANTS_REFRESH_TOKEN=your_jquants_token
     KABU_API_PASSWORD=your_kabu_password
     OPENAI_API_KEY=sk-xxxxxxxxxxxx
     KABUSYS_ENV=development
     PAPER_FILL_MODE=instant
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb
     LOG_LEVEL=INFO
6. データディレクトリ作成
   - mkdir -p data
   - 一部スクリプトは起動時に PID ファイルやフラグファイルを data 配下に作成します。

実行方法（使い方）

- 実行前確認
  - 必須環境変数（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等）が設定されているか確認してください。
  - KABUSYS_ENV によって動作が切り替わります。paper_trading にすると Execution は Mock ブローカーを使い、Paper 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。

- 監視ループ起動（Monitoring）
  - デフォルトでは monitoring は本番 sqlite_path（SQLITE_PATH）を参照します（環境に関わらず）。
  - ポーリング間隔を変更する場合:
    - export MONITOR_POLL_INTERVAL=30  （秒）
  - 起動:
    - python -m kabusys.run_monitoring

  - 停止:
    - プロジェクトルート/data/stop_requested.flag を作成するとポーリングループが検知して停止します（run_monitoring/run_execution と共通）。

- ExecutionEngine 起動
  - Paper Trading と本番は Settings.is_paper により DB を分離（PAPER_TRADING_SQLITE_PATH を使用）。
  - 起動:
    - python -m kabusys.run_execution
  - 強制停止・Kill Switch:
    - monitoring が kill.flag を書き込む（data/kill.flag）とエンジン停止の指示が出ます。
    - stop_requested.flag を置くことで clean shutdown を促せます。

- Streamlit ダッシュボード
  - 起動:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ローカルで監視 DB を読み取り専用で開いて表示します（MonitoringEngine が DB を作成・更新していることが前提）。

- Paper Trading 検証レポート生成
  - 既存の Paper Trading DB を集計して標準出力にレポートを出します。
  - 例:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）が必要です。関数はモジュール API を通じて呼び出します。
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - 実行は DuckDB 接続（prices_daily / raw_news / news_symbols などが整備されていること）が必要です。

設定・運用に関するポイント
- 環境の自動読み込み
  - config.Settings はプロジェクトルートに .env / .env.local があれば自動で読み込みます。OS 環境変数が優先されます。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセット。
- ロギング
  - Settings.log_level または logging.basicConfig によりログレベルを制御します。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等でテーブル作成・マイグレーション（欠損カラム追加）を行います。
- Kill / Stop フラグ
  - data/kill.flag: KillSwitch により書き込まれる停止指示（ExecutionEngine 側で検出して停止）
  - data/stop_requested.flag: 両 run_* スクリプトが監視している停止フラグ（手動で作成して停止）
- プロセス優先度
  - run_monitoring / run_execution の起動時に set_process_priority("high") を試みます。権限不足時は警告になります。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数読み込みと Settings クラス
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py — SQLite 監視ログ初期化とラッパー
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py — 注文滞留 / 約定異常検知
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の書き込み / 解除
    - alert_manager.py — LINE メッセージによる通知
    - monitoring_engine.py — Monitor 統合 / ポーリングループ
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, broker_factory.py, ... （注文処理・ブローカー連携）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/ （実行時に利用されるデフォルト DB / PID / flag の保存先）
    - monitoring.db (default SQLITE_PATH)
    - paper_trading.db (default PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb (default DUCKDB_PATH)
    - execution.pid, kill.flag, stop_requested.flag など

参考コマンドまとめ
- 監視ループ（デフォルトポーリング 60 秒）
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- ExecutionEngine（環境により DB が切り替わる）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス・貢献
- この README はコードベースの抜粋に基づくドキュメントです。実運用に用いる際は十分なテストとセキュリティ対策（API キー管理、権限、例外処理、監査）を行ってください。
- 追加のドキュメント（設計書、仕様書、API スキーマなど）がある場合はそれらに従ってください。

---

不明点や README に追記してほしい項目があれば教えてください。必要に応じてサンプル .env.example を作成したり、起動・デバッグの手順を詳しく書くこともできます。