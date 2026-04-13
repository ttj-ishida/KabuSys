# KabuSys

KabuSys は日本株自動売買システムのライブラリ群です。本リポジトリには、バックテスト／リサーチ用のファクター計算、ポートフォリオ構築ロジック、発注エンジン周辺ユーティリティ、監視・アラート機能、AI を使ったニュースセンチメント評価等のコンポーネントが含まれます。

以下はコードベースに基づく README.md です。

---

## プロジェクト概要

- 日本株自動売買システムのコア機能群をモジュール化したパッケージ。
- DuckDB / SQLite を用いた価格データ・ログ永続化、OpenAI を用いたニュース NLP、発注エンジンの補助ロジック、監視（Monitoring）やアラート（LINE）送信、ストリームリットによる監視ダッシュボードなどを含む。
- 成分は概ね「research」「portfolio」「execution」「monitoring」「ai」「utils」「tools」などのモジュールで構成され、実運用（live）・ペーパートレーディング（paper_trading）・開発（development）を環境変数で切り替え可能。

---

## 機能一覧（主なもの）

- research
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン・IC・統計サマリーの算出
- portfolio
  - 候補選定、等重/スコア重みの計算
  - セクター制限適用、レジーム乗数の計算
  - 発注株数決定（position sizing）と投下資金スケーリング
- ai
  - news_nlp: OpenAI（gpt-4o-mini）を使ったニュースセンチメント付与 → ai_scores に書き込み
  - regime_detector: ETF（1321）MA とマクロニュースを合成して市場レジーム判定
- execution（発注周辺）
  - Order 管理、Reconciler（再開時の状態同期）
  - Broker クライアントの抽象化（本番/モックを切替）
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor
  - MonitoringDB（SQLite）へのログ永続化
  - KillSwitch（flag ファイルで ExecutionEngine 停止指示）
  - AlertManager（LINE プッシュ通知）
  - Streamlit ダッシュボード（監視用）
- tools
  - paper_verification_report: ペーパートレーディング結果の検証レポート生成

---

## セットアップ手順（ローカル）

推奨 Python バージョン: 3.10+

1. リポジトリをクローン、作業ディレクトリを作成
   - git clone / 展開後、プロジェクトルート（pyproject.toml または .git がある場所）を確認します。

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit
   - 実運用では requirements.txt を用意している場合はそれを使用してください。

4. 環境変数 / .env
   - プロジェクトは起動時に自動でプロジェクトルートの `.env` を読み込みます（.env.local は上書き）。
     - 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な環境変数（例）:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI機能を使う場合必須）
     - LINE_CHANNEL_ACCESS_TOKEN（通知を有効にする場合）
     - LINE_USER_ID（通知先）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - PID_FILE_PATH（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH（デフォルト: data/kill.flag）
     - PAPER_FILL_MODE（paper_trading の模擬約定挙動: instant | partial | never | reject）
     - LOG_LEVEL（DEBUG/INFO/...）

5. データディレクトリの作成
   - mkdir -p data

---

## 使い方（主要スクリプト・コマンド）

パッケージ内モジュールとして実行できます（プロジェクトルート or 仮想環境が有効な状態で）。

- ExecutionEngine（運用/ペーパー）
  - python -m kabusys.run_execution
  - 動作時に Settings.env を見て、KABUSYS_ENV=paper_trading のときは paper_sqlite_path（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を利用します。
  - 起動時に PID ファイルを書き、プロセス優先度を "high" に設定します。

- Monitoring（監視ポーリング）
  - python -m kabusys.run_monitoring
  - デフォルトポーリング間隔は 60 秒。環境変数で上書き:
    - MONITOR_POLL_INTERVAL=30
  - 監視は常に（KABUSYS_ENV にかかわらず）本番用 `sqlite_path` を使用して監視ログを記録します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH を指定している場合は省略可）
  - 出力例: 稼働率、注文成功率、送信率、レイテンシの P95 などを人間向けに表示し、PASS/FAIL を判定します。

- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ローカルで監視 DB を読み取り専用で開きダッシュボードを表示します。

- AI 関連
  - kabusys.ai.score_news: raw_news → OpenAI を使って ai_scores へスコアを書き込みます。実行には OPENAI_API_KEY が必要。
  - kabusys.ai.regime_detector.score_regime: market_regime を判定して DuckDB に書き込みます（OPENAI_API_KEY が必要。ただしマクロ記事が無ければ LLM 呼び出しをスキップし macro_sentiment=0.0）。

---

## 主要な環境変数（要点）

- KABUSYS_ENV: development | paper_trading | live
  - paper_trading の場合、発注処理はモック/分離 DB（PAPER_TRADING_SQLITE_PATH）で動作。
- JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD: 必須（Settings で未設定なら例外）
- OPENAI_API_KEY: AI 機能（news_nlp / regime_detector）利用時に必要
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト: data/kabusys.duckb）
- SQLITE_PATH: 監視ログ用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH, KILL_FLAG_PATH: ExecutionEngine / KillSwitch に関連
- PAPER_FILL_MODE: instant | partial | never | reject

注意: Settings モジュールはプロジェクトルートの `.env` / `.env.local` を自動読み込みします（OS 環境変数が優先）。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 以下の主要モジュール一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py  — 環境設定＆.env ローダ
  - run_monitoring.py  — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py   — ExecutionEngine 起動スクリプト
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py        — ニュースの OpenAI によるセンチメント評価
  - regime_detector.py — 市場レジーム判定
- src/kabusys/research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- src/kabusys/portfolio/
  - __init__.py
  - portfolio_builder.py
  - risk_adjustment.py
  - position_sizing.py
- src/kabusys/execution/
  - order_manager.py
  - reconciler.py
  - (その他発注関連コンポーネントが存在)
- src/kabusys/monitoring/
  - __init__.py
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- src/kabusys/tools/
  - __init__.py
  - paper_verification_report.py
- src/kabusys/utils/
  - __init__.py
  - process_priority.py

（上記は主要ファイルの抜粋です。実際はさらに細分化されたモジュールがあります。）

---

## 実運用上の注意点 / 実装上の特徴

- Monitoring（監視）は KABUSYS_ENV に関係なく production の sqlite_path を使用する設計です。監視ログは本番 DB に常に書き込まれます。
- ExecutionEngine は KABUSYS_ENV によって paper_trading の場合は専用の paper DB を使用し、本番 DB と完全に分離されます。
- OpenAI の呼び出しはレート制限や一時的エラーに対してエクスポネンシャルバックオフの再試行を行う実装がありますが、API キーが未設定のまま呼ぶと例外になります。AI 機能はフェイルセーフで失敗時は 0.0 でフォールバックする箇所もあります。
- process priority / cpu affinity は psutil 経由で OS に依存して設定します。権限不足などで失敗しても警告ログを出して継続します。
- SQLite / DuckDB に対するマイグレーション（軽微な ALTER）を起動時に行う箇所があります（冪等実行）。

---

## 例: よく使うコマンドまとめ

- 監視ループ起動（デフォルト 60 秒）
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- Execution 起動（環境設定に応じて本番/ペーパー切替）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper 検証レポート（2026-04-01～2026-04-11 の例）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定する場合: --db /path/to/data/paper_trading.db

- Streamlit ダッシュボード起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

## 貢献 / 追加情報

- コードはモジュール毎に純粋関数（副作用がない）と副作用を伴う I/O 層を分離する設計を意識しています（例: portfolio モジュールはメモリ内計算に限定）。
- 新しい機能やバグ修正は PR ベースでお願いします。自動テスト・CI の設定があればそれに従ってください。

---

以上がこのコードベースの README.md です。必要であれば、環境変数のサンプル .env.example、requirements.txt の推奨セット、デプロイ手順（systemd ユニットなど）を追加で作成します。どれを優先しますか？