# KabuSys — 日本株自動売買システム（README）

このリポジトリは日本株自動売買システム「KabuSys」のコードベースの一部を含みます。  
ここではプロジェクトの概要、主な機能、セットアップ方法、実行方法、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要
KabuSys は日本株の自動売買 / 研究 / 監視を行うためのモジュール群です。主な関心点は次のとおりです。

- 取引実行（ExecutionEngine、OrderManager、BrokerClientFactory 等）
- 監視（SystemMonitor、TradeMonitor、RiskMonitor、MonitoringEngine、AlertManager）
- ポートフォリオ構築（銘柄選定、配分、ポジションサイズ計算）
- 研究用ファクター計算（momentum, value, volatility 等）
- AI を使ったニュースセンチメント（OpenAI を用いた news NLP）
- Paper Trading（本番 DB と分離した検証ワークフロー）
- レポート・ダッシュボード（streamlit ダッシュボード、paper verification レポート）

設計方針として「外部状態（本番口座等）への不要なアクセスをしない」「ルックアヘッドバイアスを避ける」等が徹底されています。

---

## 主な機能一覧
- 設定管理（kabusys.config.Settings）
  - .env / .env.local の自動読み込み（プロジェクトルートに .git または pyproject.toml がある場合）
  - 必須環境変数の検査（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）
  - KABUSYS_ENV = development / paper_trading / live の切替
- 監視機能（kabusys.monitoring）
  - システム監視（CPU/MEM/DISK、プロセス存否、データ鮮度）
  - 注文監視（滞留注文、約定異常価格）
  - リスク監視（ドローダウン、ポジション上限）と kill.flag の出力
  - LINE による通知（AlertManager）
  - SQLite に監視ログを永続化（monitoring_db）
  - streamlit ダッシュボード（read-only で monitoring DB を表示）
- 実行エンジン（kabusys.execution）
  - OrderManager、OrderRepository、Reconciler 等の実装（発注、状態同期、再起動時の復旧）
  - paper_trading 環境では MockBroker を利用し DB を分離
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等金額／スコア重み配分、ポジションサイズ計算、セクターキャップ・レジーム乗数
- 研究用モジュール（kabusys.research）
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI 機能（kabusys.ai）
  - ニュース記事から銘柄ごとのセンチメントを生成し ai_scores に保存（OpenAI）
  - マクロニュース＋ETF MA200 乖離を組み合わせた市場レジーム判定
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
  - streamlit ベースの監視ダッシュボード

---

## セットアップ手順（ローカル開発向け）
以下は最小セットアップ手順の例です。プロジェクトルートから実行してください。

1. リポジトリをクローン
   - git clone <repository-url>

2. Python 仮想環境の作成（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - requirements.txt があれば: pip install -r requirements.txt  
   - 主要な依存（本プロジェクトで使われている想定）:
     - duckdb
     - psutil
     - requests
     - streamlit
     - openai
   - 例: pip install duckdb psutil requests streamlit openai

4. 実行方法（開発時）
   - パッケージをソースパスで使う場合:
     - export PYTHONPATH=src  （Windows: set PYTHONPATH=src）
     - あるいはプロジェクトルートで editable インストール: pip install -e .

5. 環境変数の設定
   - プロジェクトルートに .env / .env.local を配置すると自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）。
   - 必須/主要環境変数例:
     - JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
     - KABU_API_PASSWORD — kabuステーション API（必須）
     - OPENAI_API_KEY — OpenAI を使う場合に必要
     - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
     - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 DB（paper_trading 環境で利用）
     - MONITOR_POLL_INTERVAL — 監視ループのポーリング秒数（デフォルト 60）
   - .env のフォーマットは普通の KEY=VALUE、コメントやクォートもある程度サポートされます。

---

## 使い方（主要スクリプト / コマンド）

以下は代表的な起動方法です。PYTHONPATH を忘れずに設定するか、pip install -e . をしてください。

1. 監視ループを起動（Monitoring）
   - デフォルト: 本番 sqlite_path を使用（KABUSYS_ENV に関係なく監視 DB は production path を参照）
   - コマンド:
     - PYTHONPATH=src python -m kabusys.run_monitoring
   - オプション:
     - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（例: export MONITOR_POLL_INTERVAL=30）

2. 実行エンジン（ExecutionEngine）起動
   - Paper Trading（モックブローカー）で起動する例:
     - export KABUSYS_ENV=paper_trading
     - PYTHONPATH=src python -m kabusys.run_execution
   - 本番で起動する場合は KABUSYS_ENV=live（注意: 本番 API キー等の設定必須）
   - paper_trading の場合、デフォルトで data/paper_trading.db が使用されて本番 DB と分離されます。

3. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report \
       --from 2026-04-01 --to 2026-04-11 \
       --db data/paper_trading.db
   - --db を省略した場合は環境変数 PAPER_TRADING_SQLITE_PATH、それもなければ data/paper_trading.db が使われます。

4. 監視ダッシュボード（Streamlit）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - (ここで -- は streamlit に渡す引数とスクリプト内 argparse を分けるためのものです)
   - ダッシュボードは読み取り専用で monitoring DB を参照します。DB が存在しない場合は MonitoringEngine を先に起動してください。

5. AI 機能（ニュース NLP / レジーム判定）
   - OpenAI API を利用するために OPENAI_API_KEY を設定してください。
   - kousu を使ってプログラム的に呼び出す関数:
     - kabusys.ai.news_nlp.score_news(duckdb_conn, target_date, api_key=None)
     - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=None)
   - CLI ラッパーはありませんが、スクリプト・バッチ処理からこれらを呼べます。

注意点:
- Settings モジュールは起動時に .env の自動読み込みを行います（プロジェクトルートが見つからない場合はスキップ）。
- paper_trading 環境は本番 DB と完全に分離されるよう設計されています（SQLite のパスが切り替わる）。

---

## 主要ファイル / ディレクトリ構成
以下はコードベースの主要なファイル構成（抜粋）です。パッケージ名は kabusys/ 以下です。

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数・設定管理（.env 自動ロード、Settings）
    - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py               — ExecutionEngine 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py — Paper Trading 検証レポート
    - monitoring/
      - __init__.py
      - monitoring_db.py             — SQLite による監視ログ層（init / CRUD）
      - monitoring_engine.py         — 各 Monitor を束ねるエンジン
      - system_monitor.py            — CPU/MEM/DISK, PID, データ鮮度チェック
      - trade_monitor.py             — 滞留注文 / 約定異常チェック
      - risk_monitor.py              — ドローダウン / ポジション制限監視
      - kill_switch.py               — kill.flag 書き込みロジック
      - alert_manager.py             — LINE Push 通知
      - streamlit_dashboard.py       — Streamlit ダッシュボード
    - execution/
      - order_manager.py             — 発注ロジックの外向け API
      - order_repository.py          — SQLite ベースの注文格納（ファイルは別）
      - reconciler.py                — 起動時の注文/ポジション再同期
      - ...（broker_factory, execution_engine 等、実行系の他モジュール）
    - portfolio/
      - portfolio_builder.py         — 候補選定・等重/スコア重み
      - position_sizing.py           — 株数決定・aggregate cap 等
      - risk_adjustment.py           — セクターキャップ・レジーム乗数
      - __init__.py
    - research/
      - factor_research.py           — momentum/value/volatility ファクター
      - feature_exploration.py       — forward returns / IC / summary
      - __init__.py
    - ai/
      - news_nlp.py                  — ニュース NLP（OpenAI 呼び出しのバッチ処理）
      - regime_detector.py           — マクロ + MA200 によるレジーム判定
      - __init__.py
    - utils/
      - process_priority.py          — プロセス優先度 / CPU affinity の設定ユーティリティ
      - __init__.py
    - portfolio/, monitoring/, research/ etc. （上に示した各モジュール群）

（上記は本リポジトリから抽出した主要ファイルです。実際の配下にはさらに細かいモジュールが存在します。）

---

## データファイルの既定パス
- DuckDB: data/kabusys.duckdb（環境変数: DUCKDB_PATH で上書き可能）
- 監視用 SQLite: data/monitoring.db（環境変数: SQLITE_PATH）
- Paper Trading SQLite: data/paper_trading.db（環境変数: PAPER_TRADING_SQLITE_PATH）
- PID ファイル: data/execution.pid（Settings.pid_file_path）
- Kill flag: data/kill.flag（Settings.kill_flag_path）

monitoring_db.init_monitoring_db() がテーブル作成・簡易マイグレーション（カラム追加）を行います。

---

## 開発・運用上の注意
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行います。テストや特殊環境で自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- KABUSYS_ENV により動作モードが変わります。paper_trading を使うと MockBrokerClient が使われ、DB は data/paper_trading.db に保存されます（本番 DB と完全分離）。
- SystemMonitor は実行プロセスの PID ファイルを監視します。start/stop の際は pid_file の運用に注意してください。
- OpenAI を使う機能は API のレートや応答形式に依存します。API キーの安全管理、レート制御を行ってください。
- 運用時のアラートは LINE push を利用できます。LINE のトークン／ユーザー ID を設定してください（AlertManager）。
- 重要な永続化は SQLite（監視） / DuckDB（研究データ）で行われます。バックアップや権限に注意してください。

---

## よくあるコマンドまとめ
- 監視起動:
  - PYTHONPATH=src python -m kabusys.run_monitoring
- 実行エンジン（本番または paper）起動:
  - export KABUSYS_ENV=paper_trading
  - PYTHONPATH=src python -m kabusys.run_execution
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

この README はコードベースに基づく概要であり、実際の運用に際しては環境固有の設定（各種 API キー、ネットワーク、プロセス管理、永続化ポリシー等）を十分に確認してください。追加のドキュメント（PortfolioConstruction.md, StrategyModel.md 等）がある場合はそちらも参照すると理解が深まります。