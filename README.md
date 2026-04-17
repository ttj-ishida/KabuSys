# KabuSys

日本株向け自動売買フレームワーク（プロトタイプ）  
このリポジトリは、戦略・発注・監視・リサーチ・AI連携などの機能を備えた総合自動売買システムのコードベースです。モジュールはできるだけ純粋関数／疎結合に設計されており、Paper Trading と Live 環境を分離して運用できます。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動方法 / ツール）
- 環境変数（主要項目）
- ディレクトリ構成（抜粋）
- 注意事項 / 運用メモ

---

プロジェクト概要
- KabuSys は日本株向けの自動売買システムの骨格を提供します。
- コンポーネント例：
  - ExecutionEngine（発注・リスク管理・注文管理・リコンシリエーション）
  - Monitoring（システム監視・注文監視・リスク監視・アラート）
  - Research（ファクター計算、特徴量探索）
  - Portfolio（候補選定・ウェイト計算・サイズ決定・リスク調整）
  - AI（ニュースNLPによるセンチメント評価、市場レジーム判定）
  - Tools（Paper Trading 検証レポート、Streamlit ダッシュボード）
- SQLite / DuckDB を使ってデータ永続化（デフォルトは data/ 以下）。

---

主な機能一覧
- 実行系（Execution）
  - Broker 抽象化（本番 / モックの切替）
  - OrderManager（注文作成・同期）
  - Reconciler（起動時の自動復旧）
  - RiskManager（発注前チェック等）
- 監視（Monitoring）
  - SystemMonitor：CPU / メモリ / ディスク / プロセス有無 / データ鮮度チェック
  - TradeMonitor：滞留注文・約定異常検出
  - RiskMonitor：ドローダウンやポジション上限監視
  - KillSwitch：危険検出時に data/kill.flag を作成して Execution を停止
  - AlertManager：LINE によるプッシュ通知（任意）
  - Streamlit ダッシュボード（監視状況表示）
- ポートフォリオ構築（Portfolio）
  - 候補選定（スコア、等分配）
  - ポジションサイジング（リスクベース、上限、丸め）
  - セクター制約・レジーム乗数
- リサーチ（Research）
  - ファクター計算（Momentum、Volatility、Value）
  - 将来リターン・IC 計算・統計サマリー
- AI（OpenAI）
  - ニュースを LLM でスコア化して ai_scores に保存
  - マクロニュース + ETF MA200 を元に市場レジーム判定
- ツール
  - paper_verification_report：Paper Trading の検証レポート生成
  - streamlit_dashboard：監視ダッシュボード（Streamlit）

---

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repository-url>
2. Python 環境準備（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install --upgrade pip
   - 必要な主な依存（例）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt がある場合はそれを使用してください。）
4. 開発用パス設定
   - ソースは src/ 配下にあるため、実行時に PYTHONPATH=src を指定するか、パッケージとしてインストールします。
   - 簡易実行例:
     - export PYTHONPATH=src
     - python -m kabusys.run_monitoring
   - あるいはパッケージとしてインストール:
     - pip install -e .

5. データディレクトリ
   - デフォルトで data/ 以下に DB や PID / フラグファイルを作成します（自動作成されますがアクセス権に注意）。

---

使い方（起動・各ツール）

1) 監視ループ起動（Monitoring）
- 用途: システム / 注文 / リスクの定期ポーリング
- 実行:
  - export PYTHONPATH=src
  - python -m kabusys.run_monitoring
- オプション / 環境変数:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
  - 監視は KABUSYS_ENV に関係なく Settings.sqlite_path（本番 sqlite_path）を使用します（意図的設計）。
- 停止: プロジェクトルート/data/stop_requested.flag ファイルを作成するとループが検知して終了します。

2) 実行エンジン起動（Execution）
- 用途: 発注エンジンの起動（ExecutionEngine をバックグラウンドスレッドで実行）
- 実行:
  - export PYTHONPATH=src
  - python -m kabusys.run_execution
- KABUSYS_ENV の扱い:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PaperTrading 用の別 SQLite（デフォルト data/paper_trading.db）を使用します。本番 DB と分離されます。
- 起動時の停止フラグ:
  - data/stop_requested.flag が存在する場合は起動しません。
- PID:
  - data/execution.pid にプロセス PID を書く仕組み（プロセス存在チェックに利用）。stale PID の検出・削除処理あり。

3) Streamlit ダッシュボード
- 起動例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - read-only で SQLite を開き、Overview / Positions / Orders / System を表示します。

4) Paper Trading 検証レポート
- 実行:
  - export PYTHONPATH=src
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB:
  - デフォルトは data/paper_trading.db。--db でパス指定可。
- 指標:
  - 稼働率、注文成功率、送信率、レイテンシ（P95）などを集計し PASS/FAIL を判定します。

5) AI 関連（ニュースNLP / レジーム判定）
- 前提:
  - OpenAI API キー（環境変数 OPENAI_API_KEY または関数引数）
- news_nlp.score_news / regime_detector.score_regime で DuckDB 接続と target_date を渡して実行します。
- LLM 呼び出しはリトライ・フォールバック実装あり（失敗時は安全側の値で継続する設計）。

---

主要な環境変数（Settings を参照）
- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabus API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE）用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant / partial / never / reject、デフォルト: instant）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START などの監視関連設定
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（閾値）

設定ファイルの自動ロード
- プロジェクトルート（.git または pyproject.toml を基準）にある .env および .env.local を自動で読み込みます（OS 環境変数優先）。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

ディレクトリ構成（抜粋、src/kabusys 配下）
- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings 管理
  - run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py         — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py            — SQLite 永続化レイヤ
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
    - (その他：broker_factory, execution_engine, order_repository 等)
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
  - data/ (実行時に生成されることが多い)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 環境用)
    - kill.flag, stop_requested.flag, execution.pid など

---

注意事項 / 運用メモ
- 監視（run_monitoring）は常に Settings.sqlite_path（監視 DB）を使う設計です。一方、実行エンジンは KABUSYS_ENV に応じて paper_sqlite_path を使うため Paper 環境は本番 DB と分離されます。
- KillSwitch による停止は data/kill.flag の作成で行います。KillSwitch は複数のリスクシグナル（ドローダウン / ポジション上限など）でトリガーされます。
- レコードスキーマ・マイグレーションは monitoring_db.init_monitoring_db にて簡易対応（カラム追加等の簡単なマイグレーション処理あり）。
- OpenAI 連携は API キーに課金が発生します。実運用ではレートやコスト、エラー制御に注意してください。
- process_priority.set_process_priority はプラットフォーム差分を吸収しますが、権限不足により設定できない場合があります（警告ログを出してスキップします）。

---

貢献 / 拡張ポイント（例）
- 銘柄ごとの lot_size を stocks マスタで管理して position_sizing を拡張
- 発注・約定ロジックの高度化（スリッページ見積り、部分約定戦略）
- Streamlit ダッシュボードの UI 強化（チャート、履歴比較）
- DuckDB を使った定期的なバッチ集計パイプライン
- テストカバレッジの整備（単体テスト / CI）

---

この README はリポジトリ内のソースコード（src/kabusys 配下）を参照して作成しました。具体的な実行時の詳細や依存バージョンはプロジェクトの requirements.txt / pyproject.toml があればそちらを参照してください。必要であれば README に含めるコマンド例や .env.example のテンプレートを追加で作成します。必要な項目を教えてください。