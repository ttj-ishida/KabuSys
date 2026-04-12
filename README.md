# KabuSys

日本株向けの自動売買 / 監視ライブラリ群および実行スクリプト群のリポジトリ。  
この README はコードベース（src/kabusys 以下）の概要、セットアップ、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つモジュール群で構成されています。

- 注文実行（ExecutionEngine、OrderManager、ブローカーファクトリ等）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- ポートフォリオ構築（候補選定、重み算出、ポジションサイズ計算、セクター制限等）
- 研究用ユーティリティ（ファクター計算、IC 計算、forward returns 等）
- AI 補助（ニュースのセンチメントスコアリング、マーケットレジーム判定。OpenAI を利用）
- ツール（Paper Trading の検証レポート生成、Streamlit ダッシュボード）

いくつかの実行スクリプト（エントリポイント）を提供しており、本番／ペーパートレードを切り替えて動かすことができます。

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - ブローカー抽象化（BrokerClientFactory）により実運用／モックの切替
  - 起動時リコンシリエーション（Reconciler）

- Monitoring
  - 定期ポーリング監視ループ（src/kabusys/run_monitoring.py）
  - SystemMonitor：プロセス生存、CPU/メモリ/ディスク、データ鮮度監視
  - TradeMonitor：滞留注文・約定異常の検出
  - RiskMonitor：ドローダウン・ポジション上限監視と kill flag 出力
  - AlertManager：LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）

- Portfolio
  - 候補選定 / 等分配・スコア加重配分
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、aggregate cap）

- Research / Data
  - DuckDB を用いたファクター計算（momentum, volatility, value）
  - forward returns / IC / 統計サマリー（外部依存を極力抑制）

- AI（OpenAI）
  - ニュースセンチメント（news_nlp.score_news）
  - マーケットレジーム判定（ai.regime_detector.score_regime）
  - API キーを環境変数または引数で供給。失敗時はフォールバック動作を備える。

- Tools
  - Paper Trading 検証レポート（src/kabusys/tools/paper_verification_report.py）
    - 指定期間の稼働率・注文成功率・レイテンシ等を集計して判定出力

---

## セットアップ手順

前提: Python 3.10+（typing の構文等に準拠）。以下は一般的なセットアップ手順例です。

1. リポジトリのクローン / 移動
   - ソースは `src/kabusys` 配下にあります。プロジェクトルートは `.git` または `pyproject.toml` によって自動検出されます。

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール（pip）
   - 必要な主要パッケージ（コード内参照）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボードを使う場合)
   - 例:
     - pip install duckdb psutil requests openai streamlit

   ※requirements.txt が無い場合は上記を参考にしてください。プロジェクトに合わせてバージョンを固定してください。

4. データディレクトリ作成
   - デフォルトの DB / PID ファイル等は `data/` 配下に置かれます。必要に応じて作成してください。
     - mkdir -p data

5. 環境変数の設定
   - 必須（実運用時）
     - JQUANTS_REFRESH_TOKEN — J-Quants API トークン
     - KABU_API_PASSWORD — kabu ステーション API パスワード
   - OpenAI を使う場合
     - OPENAI_API_KEY — OpenAI API キー
   - 実行環境切替
     - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
   - 監視関連 / 各種上書き
     - SQLITE_PATH: デフォルト data/monitoring.db
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
     - PID_FILE_PATH / KILL_FLAG_PATH / PAPER_FILL_MODE / LOG_LEVEL / など（コード参照）

   - .env 自動読み込み:
     - プロジェクトルートに `.env` / `.env.local` があれば自動で読み込まれます。
     - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

6. DB 初期化
   - Monitoring 用の SQLite スキーマはスクリプト実行時に自動で作成されます（init_monitoring_db）。

---

## 使い方

実行はモジュールとして起動できます。プロジェクトルート（.git がある場所）から実行することを想定しています。

- 監視ループを起動（Monitoring Engine）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60）。
  - python -m kabusys.run_monitoring
  - 補足:
    - 起動時にプロセス優先度を "high" に設定（Linux/Windows の差分を吸収）
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して記録されます

- 注文実行（ExecutionEngine）
  - KABUSYS_ENV による動作:
    - paper_trading: MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録（本番 DB と分離）
    - development / live: 本番 sqlite_path を使用
  - python -m kabusys.run_execution

- Streamlit ダッシュボード（監視結果の可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 既に MonitoringEngine が稼働している前提で read-only モードで開きます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db / 環境変数 PAPER_TRADING_SQLITE_PATH を使用可能

- AI 関連（プログラム呼び出し）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)
  - どちらも api_key を引数で渡すか環境変数 OPENAI_API_KEY を設定してください。失敗時のフェイルセーフ（スコア 0 等）を持ちます。

- 監視の Kill Switch
  - RiskMonitor が閾値を超えると `KILL_FLAG_PATH`（デフォルト data/kill.flag）へ理由を書き込み、ExecutionEngine に停止シグナルを送ります。
  - Execution 起動時に `kill_flag_clear_on_start` が有効なら起動時にクリアできます（Settings 参照）。

---

## 代表的な環境変数一覧（主なもの）

- 必須 / 重要
  - JQUANTS_REFRESH_TOKEN — J-Quants トークン（必須）
  - KABU_API_PASSWORD — kabu ステーション API パスワード（必須）

- 実行モード
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
  - PAPER_FILL_MODE — paper_trading のモック約定モード（instant|partial|never|reject。デフォルト: instant）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 sqlite パス（デフォルト: data/paper_trading.db）

- DB / ファイルパス
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - DUCKDB_PATH — DuckDB データパス（デフォルト: data/kabusys.duckdb）
  - PID_FILE_PATH — ExecutionEngine PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — kill flag（デフォルト: data/kill.flag）

- 監視 / ログ
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）

- OpenAI
  - OPENAI_API_KEY — OpenAI API キー（ai.news_nlp / ai.regime_detector で使用）

- 自動 .env 読込制御
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動ロードを無効化

---

## 注意点 / 実装メモ

- .env のパースはプロジェクト内部実装で多少のシェル風構文（export プレフィックス、クォート、コメント）に対応しています。
- Monitoring の SQLite スキーマは実行時に自動作成・マイグレーション（カラム追加）を行います。冪等です。
- run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様です（監視は本番 DB に記録するため）。
- run_execution は KABUSYS_ENV=paper_trading のとき DB を分離します（paper_trading 用 DB を使用）。
- process priority / CPU affinity は psutil を使って設定します。権限不足や未対応 OS の場合は警告を出してスキップします。
- OpenAI 呼び出しはネットワークエラーやレート制限を考慮して指数バックオフでリトライする実装があります。レスポンスのバリデーションを厳格に行います。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                          — 環境変数 / 設定管理
- run_monitoring.py                  — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py                   — ExecutionEngine 起動スクリプト

- ai/
  - __init__.py
  - news_nlp.py                       — ニュースセンチメント（OpenAI 利用）
  - regime_detector.py                — レジーム判定（MA + マクロセンチメント）

- monitoring/
  - __init__.py
  - monitoring_db.py                  — SQLite 永続化層（schema / MonitoringDB）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py

- execution/
  - order_manager.py
  - reconciler.py
  - (その他 execution 関連モジュール: broker_factory, order_repository 等)

- portfolio/
  - portfolio_builder.py
  - risk_adjustment.py
  - position_sizing.py
  - __init__.py

- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py

- tools/
  - __init__.py
  - paper_verification_report.py

- utils/
  - __init__.py
  - process_priority.py

（上記は主なファイルを抜粋したものです。詳細は src/kabusys 配下をご参照ください）

---

## 例: 最小限の起動手順（ローカル検証用）

1. 仮想環境作成・アクティベート
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

3. 環境変数設定（開発用の最低限）
   - export KABUSYS_ENV=development
   - export JQUANTS_REFRESH_TOKEN=your_token
   - export KABU_API_PASSWORD=your_password
   - export OPENAI_API_KEY=sk-...
   - mkdir -p data

4. 監視ループ起動（別ターミナルで）
   - python -m kabusys.run_monitoring

5. Execution をテスト起動（paper_trading を使う場合）
   - export KABUSYS_ENV=paper_trading
   - python -m kabusys.run_execution

6. Streamlit ダッシュボード
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

## よくある質問（FAQ）

- Q: paper_trading と本番の DB は分離されていますか？  
  A: はい。KABUSYS_ENV=paper_trading のとき run_execution は `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）を使用します。監視は別に本番用 sqlite_path を使うため注意してください。

- Q: MONITOR_POLL_INTERVAL を 0 にできる？  
  A: 0 または 0 以下の値は不正とみなされ、デフォルト（60秒）にフォールバックします。

- Q: OpenAI API キーが無いとどうなりますか？  
  A: AI 機能はエラーを返したり（呼び出し側で例外処理）、AI モジュール内でフォールバック（macro_sentiment=0.0 等）する実装があります。実行時に必須項目かを確認してください（score_news / score_regime はキーが無いと ValueError を投げます）。

---

必要であれば README にサンプル .env ファイル（.env.example）やさらに詳細な起動オプション、ユニットテスト方法、CI 設定例なども追加できます。追加希望があれば教えてください。