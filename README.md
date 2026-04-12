# KabuSys

日本株向けの自動売買システム（プロトタイプ）。  
このリポジトリは取引実行ロジック、監視機構、ポートフォリオ構築ユーティリティ、調査用ファクター計算、LLM を使ったニュースセンチメント評価などを含みます。

バージョン: 0.1.0

※ 本 README は src/kabusys 以下のコードに基づいて作成しています。

---

主な内容
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（起動コマンド例）
- ディレクトリ構成（主要ファイル説明）
- 環境変数一覧（主要な設定）

---

プロジェクト概要
- KabuSys は日本株自動売買のためのコンポーネント群です。
- 実売買を行う ExecutionEngine、監視/アラートを行う MonitoringEngine、ポートフォリオ構築 / ポジションサイズ計算、リサーチ（ファクター計算・特徴量探索）、LLM を使ったニュース NLP（センチメント）やレジーム判定などを備えます。
- 設計方針として、DuckDB や SQLite によるデータ永続化（分析・監視用）と、外部 API 呼び出し（kabuステーション / J-Quants / OpenAI）を分離するようになっています。
- Paper Trading モードをサポートし、本番 DB と分離して動作できます。

機能一覧（抜粋）
- 実行関連
  - ExecutionEngine（発注フロー、リスク管理、リコンシリエーション）
  - Broker クライアントの抽象化（実ブローカー / MockBroker）
- 監視・運用
  - SystemMonitor: プロセス状態・CPU/メモリ/ディスク・データ新鮮度監視
  - TradeMonitor: 注文滞留・約定異常の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視、kill.flag による停止指示
  - AlertManager: LINE Push によるアラート送信（クールダウン管理）
  - Streamlit ダッシュボード（監視 DB の可視化）
- ポートフォリオ構築
  - 候補選定、等重・スコア重み、セクター制限、レジーム乗数、ポジションサイズ計算（単元株丸め、aggregate cap）
- リサーチ / 特徴量
  - Momentum / Volatility / Value ファクター計算（DuckDB 上で SQL + Python）
  - 将来リターン計算、IC（Information Coefficient）算出、統計サマリ
- AI（OpenAI）
  - ニュースのセンチメントスコア化（gpt-4o-mini を利用想定、JSON モード）
  - マクロニュース + ETF MA200 乖離による市場レジーム判定
- ユーティリティ
  - 環境設定読み込み（.env / .env.local の自動読み込み、プロジェクトルート検出）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - Paper Trading 向けの検証レポート生成ツール

セットアップ手順（ローカル開発向け）
1. 推奨 Python バージョン
   - Python 3.10 以上（型注釈で | を使用しているため）

2. リポジトリをクローン
   - git clone <repo-url>
   - プロジェクトルートは .git または pyproject.toml を基準に検出されます。

3. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

4. 必要パッケージをインストール
   - 主要な依存例:
     - duckdb
     - psutil
     - requests
     - streamlit (ダッシュボードを使う場合)
     - openai (LLM 呼び出しを使う場合)
   - 例:
     - pip install duckdb psutil requests streamlit openai

   ※ requirements.txt がある場合はそれを利用してください（本コードスニペットには同ファイルの記載がありません）。

5. 環境変数 / .env
   - プロジェクト開始時に自動で .env / .env.local をプロジェクトルートから読み込みます（OS 環境変数が優先されます）。
   - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 重要な環境変数（抜粋）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能を使う場合必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - PAPER_FILL_MODE (paper_trading 時の約定挙動: instant|partial|never|reject) — デフォルト "instant"
     - PAPER_TRADING_SQLITE_PATH（Paper Trading 用 DB、デフォルト data/paper_trading.db）
     - SQLITE_PATH（監視 DB: data/monitoring.db）
     - DUCKDB_PATH（分析 DB: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信用）
     - PID_FILE_PATH（既定: data/execution.pid）
     - MONITOR_POLL_INTERVAL（監視ループ間隔秒、デフォルト 60）

使い方（起動例）
- 実行エンジン（ExecutionEngine）を起動する
  - KABUSYS_ENV によって動作が変わります。
    - paper_trading: MockBroker を使用し、PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）
    - live: 実ブローカーを利用（KABU API 設定が必要）
  - 実行:
    - python -m kabusys.run_execution

- 監視ループを起動する
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒）
  - 監視は KABUSYS_ENV にかかわらず production の sqlite_path を使用します（監視 DB は本番 DB を想定）
  - 実行:
    - python -m kabusys.run_monitoring
  - 例（30秒間隔）:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - またはカレントディレクトリから:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db <path>

- Paper Trading 検証レポート生成ツール
  - python -m kabusys.tools.paper_verification_report
  - 期間フィルタ:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（例: ニュースセンチメント）
  - OpenAI API キー（OPENAI_API_KEY）が必要
  - プログラムからは kabusys.ai.score_news を呼ぶことで ai_scores テーブルへ書き込みが行われます。

重要な注意点 / 実運用時の振る舞い
- run_monitoring は監視用 DB（settings.sqlite_path）を常に使用します。監視データは環境に依存しない本番 DB を想定しています。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用の SQLite に記録します（本番 DB と分離）。
- process priority / cpu affinity の設定には psutil が必要で、権限によっては設定に失敗する場合があります（警告ログのみ）。
- AI 呼び出しは外部 API に依存し、失敗時はフェイルセーフ（多くのケースでスコア 0.0 にフォールバック、または処理スキップ）となるよう設計されています。
- .env のパースは一般的な形式（export KEY=val, quoted values, inline comments）をサポートします。

主要な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- PAPER_FILL_MODE: instant | partial | never | reject （paper_trading 用）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- MONITOR_POLL_INTERVAL: 監視ループ間隔（秒、デフォルト 60）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

ディレクトリ構成（主要ファイル / モジュール）
- src/kabusys/
  - __init__.py — パッケージ情報（__version__）
  - config.py — 環境変数 / .env ロード・Settings クラス
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite による監視ログ永続化層（init / MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の書き込み（ExecutionEngine 停止）
    - alert_manager.py — LINE push による通知（クールダウン）
    - monitoring_engine.py — 各 Monitor を束ねる実行ループ
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py, order_repository.py, reconciler.py, ... — 発注管理・リコンシリエーション等
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - position_sizing.py — 発注株数決定（単元丸め / aggregate cap）
  - research/
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン計算、IC、統計サマリ
  - ai/
    - news_nlp.py — raw_news → ai_scores（OpenAI を使ったニュースセンチメント）
    - regime_detector.py — マクロ + ETF MA200 乖離によるレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート（CLI）
  - data/ (想定：データファイル置き場)
    - kabusys.duckdb （DuckDB）
    - monitoring.db / paper_trading.db （SQLite）

開発 / 検証に便利なコマンド例
- Lint / フォーマット（プロジェクトに合わせて追加してください）
- unit tests（テストフレームワークによりコマンドが変わります）

最後に（運用上のヒント）
- Paper Trading を行う場合、PAPER_TRADING_SQLITE_PATH を明示的に設定し、本番 DB と物理的に分離してください。
- OpenAI などの外部 API はレートリミットや一時的エラーがあるため、環境変数・ログ・リトライ設定（該当モジュール内の定数）を確認してください。
- 監視は常に監視 DB（settings.sqlite_path）を参照する設計です。監視対象 DB のパス設定に注意してください。

もし README に追加したい情報（requirements.txt、Dockerfile、運用手順、より詳しい設定例など）があれば教えてください。追記して整備します。