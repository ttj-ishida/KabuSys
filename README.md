# KabuSys — README (日本語)

このリポジトリは日本株自動売買システム「KabuSys」のコアライブラリ群です。  
README にはプロジェクトの概要、主要機能、セットアップ／実行方法、ディレクトリ構成を日本語でまとめています。

※ ソースは src/kabusys 以下に実装されています。実行例では開発時点での最小要件として Python 3.10+ を想定しています（PEP 604 の型 | を使用）。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークで、主に以下を提供します。

- 注文管理・Execution Engine（ブローカ抽象化を通じた発注・状態管理）
- 監視（システム稼働状況、注文滞留、リスク閾値などの定期チェック）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出、セクター制約など）
- リサーチ（ファクター計算、特徴量探索、IC 計算）
- AI 連携（ニュースのセンチメント評価、マクロセンチメントを使った市場レジーム判定）
- 開発用ツール（Paper Trading 検証レポート生成、Streamlit ダッシュボード）

設計方針として、主要処理は副作用を抑えた純関数群と DB 層の分離を意識しており、紙上の検証（DuckDB 参照）と実運用（kabu API など）の分離も保たれています。

---

## 主な機能一覧

- Execution
  - 注文作成/送信/同期（OrderManager、OrderRepository、Reconciler）
  - リスク管理（RiskManager）
  - paper_trading モード（MockBroker を利用し本番 DB と分離）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス存在 / データ鮮度チェック
  - TradeMonitor: 注文滞留・約定異常価格検出
  - RiskMonitor: ドローダウン / 保有銘柄数上限監視、kill.flag による強制停止トリガ
  - AlertManager: LINE push による通知（クールダウン付き）
  - Streamlit ダッシュボード（リアルタイム確認）
- Portfolio
  - 銘柄候補選定、等重・スコア重み、リスクベースのポジションサイズ算出
  - セクターキャップ、レジーム乗数（Bull/Neutral/Bear）
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を直接参照）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリ
- AI
  - news_nlp: OpenAI（gpt-4o-mini）でニュースを銘柄別にスコア化して ai_scores に保存
  - regime_detector: ma200 とマクロニュースセンチメントの合成による日次レジーム判定
- Tools
  - paper_verification_report: Paper Trading DB から検証レポート生成
  - streamlit_dashboard: 監視 DB を可視化

---

## セットアップ手順

1. リポジトリをクローンし、開発用パスを設定

   推奨（editable install）:
   - プロジェクトルートに移動（pyproject.toml / .git があるディレクトリ）
   - Python 仮想環境を作成・有効化
   - pip install -e .（該当する場合）

   簡易的に src を PYTHONPATH に加える場合:
   - export PYTHONPATH=$(pwd)/src

2. 必要パッケージ（例）
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit
   - （sqlite3 は標準ライブラリ）
   例:
   - pip install duckdb psutil requests openai streamlit

3. 環境変数の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（OS 環境変数が優先）。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（必須/任意）:
   - JQUANTS_REFRESH_TOKEN — （必須）J-Quants API 用
   - KABU_API_PASSWORD — （必須）kabuステーション API 用
   - OPENAI_API_KEY — OpenAI 呼び出し時に使用
   - KABUSYS_ENV — one of development / paper_trading / live（デフォルト: development）
     - paper_trading の場合、MockBroker を利用し DB を data/paper_trading.db に分離します
   - PAPER_FILL_MODE — paper_trading の fill 動作（instant|partial|never|reject、デフォルト: instant）
   - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH — Paper Trading 用監視 DB（デフォルト: data/paper_trading.db）
   - PID_FILE_PATH — ExecutionEngine が書き込む PID ファイル（デフォルト: data/execution.pid）
   - KILL_FLAG_PATH — kill.flag ファイルパス（デフォルト: data/kill.flag）
   - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）

4. 初回実行前に data ディレクトリなどの作成を推奨:
   - mkdir -p data

---

## 使い方（よく使うコマンド）

前提: src を Python パスに含める、またはパッケージをインストール済み。

- ExecutionEngine（本番 / paper_trading）
  - python -m kabusys.run_execution
    - KABUSYS_ENV が `paper_trading` の場合、paper DB に接続して MockBroker を使用します。
    - 実行開始時にプロセス優先度を High に設定します。

- Monitoring（ポーリングで常時監視を実行）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に（KABUSYS_ENV に関わらず）本番 sqlite_path を参照して動作します。

- Streamlit 監視ダッシュボード（ローカル閲覧）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 関連（モジュール API）
  - ニューススコア付け:
    - from datetime import date
      from kabusys.ai.news_nlp import score_news
      score_news(conn, target_date=date(2026,4,1), api_key="...")

  - レジームスコア:
    - from kabusys.ai.regime_detector import score_regime
      score_regime(conn, target_date=date(2026,4,1), api_key="...")

  - DuckDB コネクション（python から）:
    - import duckdb
      conn = duckdb.connect("data/kabusys.duckdb")

- 開発用: MonitoringEngine を単発実行（テスト）
  - MonitoringEngine.run_once() 相当の処理は MonitoringEngine クラスが提供しており、テスト目的で各 Monitor を単発実行できます。

---

## 監視（Monitoring）の挙動・注意点

- monitoring_db.init_monitoring_db は複数テーブルを冪等で作成し、マイグレーション（列追加）も実施します。
- SystemMonitor は PID ファイルをチェックし、stale PID を検出した場合は削除してリスクログに記録します。
- KillSwitch は RiskMonitor の結果に基づき kill.flag を書き込み、ExecutionEngine に停止指示を与えます。kill.flag の既存チェックやクリアは KillSwitch が提供します。
- AlertManager は LINE Push を使った通知を行います。channel_access_token / user_id が無ければ送信はスキップされ、ログ出力のみ行われます。
- Paper Trading と本番は DB を分離する設計（settings.is_paper を参照）。

---

## 主要ファイル / ディレクトリ構成

（src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py — パッケージメタ情報（__version__ 等）
  - config.py — 環境変数/設定の読み込み・検証（.env 自動ロードの実装含む）
  - run_execution.py — ExecutionEngine 起動スクリプト（本番 / paper_trading を切替）
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py — ニュースを OpenAI に送って銘柄別センチメントを ai_scores に書き込む
    - regime_detector.py — ma200 + マクロセンチメント によるレジーム判定

  - monitoring/
    - __init__.py
    - monitoring_db.py — SQLite 監視 DB の作成・CRUD ラッパ
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の書き込み管理
    - alert_manager.py — LINE 通知（cooldown）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ベースの監視 UI

  - execution/
    - order_manager.py — 注文作成・送信の高レベル API
    - reconciler.py — 起動時の注文／ポジションリコンシリエーション（自動回復）
    - （他: broker_factory, execution_engine, order_repository 等は本コードベースに依存）

  - portfolio/
    - portfolio_builder.py — 候補選定・重量計算
    - position_sizing.py — 株数算出・ロット丸め・aggregate cap
    - risk_adjustment.py — セクター制約・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン、IC、統計サマリ
    - __init__.py

  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

  - utils/
    - __init__.py
    - process_priority.py — プロセス優先度 / CPU affinity のユーティリティ

---

## よくある運用上のポイント / トラブルシューティング

- .env の自動読み込み:
  - OS 環境変数 > .env.local > .env の順で読み込まれます。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading:
  - KABUSYS_ENV=paper_trading を指定すると paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用します。
- OpenAI API:
  - API キーは OPENAI_API_KEY で渡すか、関数呼び出し時に api_key 引数で渡します。未設定だと例外になります（AI モジュール）。
- ポーリング間隔の制御:
  - run_monitoring は MONITOR_POLL_INTERVAL で秒数指定できます。不正な値（<=0 など）の場合はデフォルト 60 秒にフォールバックします。
- PID / kill.flag：
  - ExecutionEngine は起動時に PID を書きます。monitoring 側は PID の有無や stale（存在しない PID）を検出して kill.flag の書き込みや通知を行います。
- 権限周り:
  - set_process_priority は OS によってシステム権限が必要な場合があります（AccessDenied を捕捉してログに出します）。

---

## ライセンス・貢献

（この README では省略しています。プロジェクトルートの LICENSE / CONTRIBUTING を参照してください。）

---

何か特定の操作（たとえば ExecutionEngine の詳細な起動オプションや、AI モジュールのテスト方法、DuckDB テーブル定義の説明など）を README に追加したい場合は、目的を教えてください。必要に応じてサンプルコマンドや環境変数テンプレート（.env.example 形式）も作成します。