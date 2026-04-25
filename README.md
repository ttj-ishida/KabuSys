KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システム（KabuSys）の一部コンポーネント群を含みます。
ここに含まれるコードは、システム監視・発注実行・ポートフォリオ構築・研究用ファクター計算・ニュースNLP（LLM）評価などの機能を提供します。

要点
- 設定は .env（環境変数）で管理。対話式ウィザードで作成可能。
- 実行環境は KABUSYS_ENV（development / paper_trading / live）で切替。paper_trading は本番 DB と分離してモックブローカーを用います。
- 監視（Monitoring）と実行（Execution）は別プロセスとして起動可能。ログは標準出力とファイル（logs/）へ出力。
- DuckDB を分析用に、SQLite を監視・注文履歴用に使用。

主な機能一覧
- 環境設定
  - 対話式 .env 生成・更新: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
- 実行系
  - ExecutionEngine 起動スクリプト: src/kabusys/run_execution.py
  - paper_trading モードでは MockBroker を使用し data/paper_trading.db に記録
- 監視系
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - run_monitoring.py によるポーリング監視（MONITOR_POLL_INTERVAL で周期指定可能）
  - Kill Switch（条件で data/kill.flag を書き込み、ExecutionEngine 停止を指示）
- ポートフォリオ構築
  - 候補選定、重み計算、ポジションサイズ算出、セクター上限やレジーム補正
- 研究用モジュール
  - DuckDB を用いたファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- AI（LLM）連携
  - ニュース記事を OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores テーブルへ書込む
  - 市場レジーム判定（ETF + マクロニュース + LLM）
- ユーティリティ
  - ログ設定ユーティリティ（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

セットアップ手順（開発環境）
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - requirements.txt がある場合はそれを使用（存在しない場合は下記を個別に）
   - pip install duckdb psutil openai
   - 開発で YAML 検証を使う場合: pip install PyYAML

4. .env の作成
   - 対話式ウィザードを実行:
     - python -m kabusys.config_setup
   - もしくは .env を手動作成（必須変数の例）
     - JQUANTS_REFRESH_TOKEN=your_token
     - KABU_API_PASSWORD=your_password
     - KABUSYS_ENV=development
     - （オプション）DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_LEVEL など
   - 自動ロード: プロジェクトルートの .env / .env.local は自動で読み込まれます（無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告を厳密エラー扱いする場合は --strict を付与

使い方（主要コマンド）
- 実行エンジン起動（本番 or paper_trading に応じた挙動）
  - python src/kabusys/run_execution.py
  - 解説:
    - KABUSYS_ENV=paper_trading の場合、モックブローカーを使い PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に取引ログを書きます。
    - 実行中は実行 PID を data/execution.pid に書きます。
    - data/stop_requested.flag が存在すると起動を中止または実行中に停止します。

- 監視プロセス起動
  - python src/kabusys/run_monitoring.py
  - 解説:
    - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒）。
    - 監視 DB は settings.sqlite_path（デフォルト data/monitoring.db）を使用（Monitoring は環境にかかわらず本番 sqlite_path を参照します）。
    - 停止: data/stop_requested.flag を作成すると監視ループが終了します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で変更可）

- AI 関連（プログラム的に呼び出す例）
  - ニュースセンチメント評価:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

重要な環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- 実行環境
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- DB / ファイルパス
  - DUCKDB_PATH — 分析用 DuckDB（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch が書き込む flag（デフォルト: data/kill.flag）
- ログ
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
  - LOG_DIR — ログ出力ディレクトリ（デフォルト: logs/）
- 監視
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

停止・Kill Switch の仕組み
- 停止要求（手動）
  - data/stop_requested.flag を作成すると run_monitoring / run_execution が検出して停止または起動を中止します。
- Kill Switch（自動）
  - リスク監視が定義条件（ドローダウン・ポジション上限など）を満たすと、KillSwitch が data/kill.flag に理由を記述して書き込み、ExecutionEngine 側でそれを検出して安全停止処理を行う設計です。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

ログについて
- ログは stdout とファイル（logs/<app_name>.log）へ出力されます（日次ローテーション、30日保持）。
- setup_logging(app_name="execution") のように起動スクリプトで統一的に設定します。
- LOG_DIR 環境変数でログ保存先を変更可能。ディレクトリ作成に失敗した場合はコンソールのみの出力になります。

ディレクトリ構成（主なファイル・モジュール）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理、自動 .env 読込
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI 連携）
    - regime_detector.py      — 市場レジーム判定（ETF + LLM）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（監視用テーブル）
    - system_monitor.py       — システム・データ鮮度監視
    - trade_monitor.py        — （実装参照）取引監視（滞留注文等）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - monitoring_engine.py    — 各 Monitor の統合ループ
    - kill_switch.py          — Kill Switch 実装
    - alert_manager.py        — （実装参照）アラート通知管理
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み付け
    - position_sizing.py      — 発注株数決定、資金配分ロジック
    - risk_adjustment.py      — セクター上限・レジーム補正
  - research/
    - factor_research.py      — ファクター計算（momentum/value/volatility）
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - monitoring/monitoring_db.py — 監視 DB スキーマ初期化・操作（重複）

補足・注意点
- Paper Trading と Live は DB を分離しているため、paper_trading で実行しても本番 DB を汚しません（paper_sqlite_path を使用）。
- LLM（OpenAI）呼び出しには OPENAI_API_KEY が必要です。API 呼び出しはリトライやフォールバック設計が組み込まれていますが、APIキーが無いと該当処理は動作しません。
- .env や APIキーは機密情報のため Git にコミットしないでください（config_setup のヘッダにも注意書きあり）。
- 実際の取引ロジック（ExecutionEngine の詳細や BrokerClient など）は本READMEで全てを網羅していません。該当実装ファイルを参照してください。

開発・運用フロー（例）
1. .env を作成（python -m kabusys.config_setup）
2. 設定検証（python -m kabusys.validate_config）
3. DuckDB / SQLite データ準備（データロードスクリプト等を実行）
4. 監視プロセス起動（本番前に監視を開始して状態を確認）
   - python src/kabusys/run_monitoring.py
5. 実行エンジン起動
   - python src/kabusys/run_execution.py
6. Paper Trading 結果確認・検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

お問い合わせ・拡張
- モジュール単位で分割されているため、新しい戦略・ブローカー実装・アラートチャネル等は既存インターフェースに合わせて追加できます。
- 研究用・分析用のスクリプトは DuckDB を使うため、大規模データの集計に向いています。

以上が本コードベースの概要と使い方です。リポジトリ内の各モジュールヘッダ・docstring に詳細実装方針や設計注記が書かれているので、該当ファイルを参照して下さい。