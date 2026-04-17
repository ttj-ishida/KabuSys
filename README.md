# KabuSys

日本株自動売買システムのコードベース（抜粋）。この README はリポジトリ内の主要コンポーネントと起動 / 検証手順をまとめた日本語ドキュメントです。

要点：
- ExecutionEngine（発注実行）と Monitoring（監視）は分離されている
- Paper Trading / Live / Development 環境を切り替え可能（KABUSYS_ENV）
- DuckDB / SQLite を使った時系列・監視データ管理
- OpenAI を利用したニュース NLP / レジーム判定機能を含む

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能を提供するモジュール群を含むシステムです。

- 発注エンジン（ExecutionEngine）: ブローカークライアントを通じて注文を作成・管理
- 監視（Monitoring）: システム状態、注文滞留、ドローダウン等を定期的にチェックしてログ・アラート・KillSwitch を管理
- ポートフォリオ構築（Portfolio）: 候補選定、重み付け、ポジションサイズ計算、セクター制限等
- リサーチ（Research）: ファクター計算・特徴量探索・将来リターン・IC 解析
- AI（ai）: ニュースのセンチメントスコアリング、レジーム判定（OpenAI利用）
- ユーティリティ: 環境設定読み込み、プロセス優先度設定、Streamlit ダッシュボード等

設計上の特徴：
- 環境変数（.env）を利用した設定（自動ロード機能あり）
- Paper Trading のために本番データベースと完全分離された専用 SQLite を利用可能
- 監視は本番 sqlite_path を常に参照（KABUSYS_ENV に依存しない）

---

## 主な機能一覧

- Execution
  - 発注作成、注文状態管理、再起動時のリコンシリエーション（Reconciler）
  - RiskManager による各種発注制限
  - BrokerClientFactory による実ブローカー / モック切替（KABUSYS_ENV=paper_trading）
- Monitoring
  - SystemMonitor: CPU/MEM/DISK、Execution プロセス存在、価格データ鮮度を監視
  - TradeMonitor: 注文滞留・約定異常の検出
  - RiskMonitor: ドローダウン／ポジション上限の監視
  - KillSwitch: 閾値超過時に flag ファイルを書き Execution を停止させる
  - AlertManager: LINE Push による通知（トークン未設定時はログのみ）
  - Streamlit ダッシュボード（簡易可視化）
- Portfolio
  - 候補選定、等配分・スコア加重の重み計算
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ算出（単元株丸め／利用可能現金に応じたスケーリング）
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 参照）
  - 将来リターン、IC、統計サマリ等
- AI
  - news_nlp: raw_news を集約して OpenAI API に投げ、銘柄ごとの ai_score を生成
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM スコアを合成して市場レジーム判定
- Tools
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率・成功率・レイテンシ等）

---

## セットアップ手順

前提
- Python 3.10+ を推奨（型注釈に | 演算子を使用）
- DuckDB、psutil、requests、openai、streamlit などの依存が必要

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - Unix/macOS: source .venv/bin/activate

2. 必要パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt` を使用）

3. プロジェクトルートに .env を作成（.env.example を参考に）
   - Settings は自動でプロジェクトルートの .env/.env.local を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
   - 必要な主要環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - DUCKDB_PATH（時系列 DB、デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH（Paper Trading 用 DB）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（AlertManager 用）
     - PAPER_FILL_MODE（paper_trading の注文約定モード: instant|partial|never|reject）

4. data ディレクトリを作成（実行中に自動作成される箇所もあるが、初期ファイルを準備）
   - mkdir -p data

5. （オプション）Paper Trading 環境の準備
   - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使い paper_sqlite_path に記録されます

注意:
- Monitoring は KABUSYS_ENV にかかわらず sqlite_path（本番用）を参照します。
- Execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path を使用します（本番 DB と分離）。

---

## 使い方（起動・運用）

基本的にモジュール単位でスクリプトを実行します。

1. 監視ループ起動（Monitoring）
   - 実行スクリプト: src/kabusys/run_monitoring.py
   - 環境変数:
     - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
   - 起動例:
     - python -m kabusys.run_monitoring
   - 停止:
     - 実行プロセスに SIGINT（Ctrl-C）で停止
     - またはプロジェクトルートの data/stop_requested.flag を作成すると次のポーリングで終了

2. 発注エンジン起動（Execution）
   - 実行スクリプト: src/kabusys/run_execution.py
   - KABUSYS_ENV によりブローカー動作が切り替わる:
     - paper_trading: MockBrokerClient を使用し data/paper_trading.db に記録
     - live/development: 実ブローカークライアントを使用（設定に応じて）
   - 起動例:
     - python -m kabusys.run_execution
   - 停止:
     - 実行中に data/stop_requested.flag を作成するとエンジン停止処理を実行
     - KillSwitch（監視側）により data/kill.flag が書かれるとさらに停止を誘発可能

3. Streamlit ダッシュボード（監視可視化）
   - ファイル: src/kabusys/monitoring/streamlit_dashboard.py
   - 起動例:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 監視 DB を read-only で開き表示

4. Paper Trading 検証レポート生成
   - スクリプト: src/kabusys/tools/paper_verification_report.py
   - 使い方:
     - python -m kabusys.tools.paper_verification_report
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - オプション --db で SQLite パスを指定（PAPER_TRADING_SQLITE_PATH 環境変数でも可）

5. AI 機能
   - news_nlp.score_news(conn, target_date, api_key=None)
   - regime_detector.score_regime(conn, target_date, api_key=None)
   - 実行には OPENAI_API_KEY が必要（引数で渡すことも可能）
   - OpenAI API のリトライやレスポンスバリデーションを備えるが、APIキー未設定時はエラーになる

運用上の注意:
- kill.flag / stop_requested.flag / execution.pid 等は data/ 配下に置かれ、監視・停止フローで参照されます。
- Settings.kill_flag_clear_on_start を利用すると起動時に既存の kill.flag を自動でクリアする設定が可能です（環境変数で制御）。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主要ファイル・モジュールの一覧（今回提供されたコードベースを基にした要約）。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / .env 読み込み・Settings
  - run_monitoring.py              — SystemMonitor ポーリングループ起動
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート生成
  - utils/
    - __init__.py
    - process_priority.py          — プロセス優先度／CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py             — monitoring SQLite レイヤ（init + CRUD）
    - monitoring_engine.py         — 複数 Monitor を束ねるループ
    - system_monitor.py            — CPU/MEM/DISK/プロセス/データ鮮度監視
    - trade_monitor.py             — 注文滞留・約定異常監視
    - risk_monitor.py              — ドローダウン・ポジション上限監視
    - kill_switch.py               — kill.flag の作成 / 管理
    - alert_manager.py             — LINE 通知
    - streamlit_dashboard.py       — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - order_record.py
    - execution_engine.py
    - broker_factory.py
    - ...                          — ブローカ周り・リスク管理等（抜粋）
  - portfolio/
    - portfolio_builder.py         — 候補選定・等重・スコア重み
    - risk_adjustment.py           — セクターキャップ、レジーム乗数
    - position_sizing.py           — 株数算出・aggregate cap
    - __init__.py
  - research/
    - factor_research.py           — momentum/volatility/value 等
    - feature_exploration.py       — 将来リターン、IC、統計
    - __init__.py
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（OpenAI 経由）
    - regime_detector.py           — レジーム判定（MA200 + LLM）
  - data/                           — 実行時 DB / flag / pid 等（リポジトリ外 / 作成されることが多い）

---

## 環境変数の主な一覧（重要なもの）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用。デフォルト 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

---

## 運用上の補足

- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は冪等にテーブル作成および簡易マイグレーション（カラム追加）を行います。
- フェイルセーフ:
  - LLM 呼び出しはリトライや結果検証を行い、失敗時は合理的なデフォルト（0.0 等）で継続します。
- テスト:
  - OpenAI 呼び出し箇所はユニットテスト時に差し替え可能（モジュール内関数を patch する前提の実装）。
- 権限:
  - process priority の設定は実行ユーザーの権限によって失敗する可能性があります（警告ログのみ）。

---

必要に応じて README に追記します（例: 実際の requirements.txt の内容、より詳細な開発フロー、CI / デプロイ手順など）。補足してほしい項目があれば教えてください。