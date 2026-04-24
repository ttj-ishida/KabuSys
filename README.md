# KabuSys

日本株自動売買システムのコアライブラリ群（読み取り専用の README）。  
この README はリポジトリ内の主要スクリプト・モジュールから自動作成した要約ドキュメントです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームのコア機能を集めたパッケージです。  
主な責務は次のとおりです。

- 注文実行エンジン（ExecutionEngine）とブローカー連携
- 監視（Monitoring）・アラート・Kill Switch
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- 研究用モジュール（ファクター計算・特徴量解析）
- AI を使ったニュースセンチメント / レジーム判定
- Paper Trading 用の検証ツール（レポート生成）
- 環境変数管理・対話式 .env ウィザード・設定検証 CLI

設計方針として、実行用コード（発注）と研究用コードは適切に分離され、SQLite / DuckDB を使ったローカル DB による永続化を行います。

---

## 主な機能一覧

- Execution
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading なら MockBroker で paper_trading DB を使用。
  - ブローカーファクトリ、オーダーマネージャ、リスク管理、再照合（reconciler）等の実装を組み合わせて運用。

- Monitoring
  - run_monitoring.py: SystemMonitor をポーリングする監視ループ起動スクリプト。MONITOR_POLL_INTERVAL による間隔設定可能。
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine、KillSwitch、AlertManager。
  - 監視結果は SQLite（monitoring.db）に永続化。

- Portfolio Construction
  - 銘柄選定（select_candidates）、重み計算（等重・スコア重み）、ポジションサイジング、セクターキャップ、レジーム乗数。

- Research
  - ファクター計算（momentum, volatility, value）
  - 特徴量探索（forward returns, IC, summary）

- AI
  - news_nlp: OpenAI を使ったニュースのセンチメント集約・ai_scores への書き込み
  - regime_detector: マクロニュース＋ETF MA による市場レジーム判定

- Tools
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率・約定率・レイテンシなど）

- 設定管理
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env と config/*.yaml の事前検証 CLI

---

## セットアップ手順（ローカル開発向け）

前提
- Python 3.10 以降（型ヒントの union operator `|` を使用）
- SQLite は標準ライブラリ、DuckDB は外部パッケージ

推奨手順（例）

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （requirements.txt があれば `pip install -r requirements.txt` を利用）

3. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成（.env.example を参考に）

4. 設定の検証
   - python -m kabusys.validate_config
   - 重要チェックを厳格にする場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリの作成（必要に応じて）
   - logs/ や data/ は自動作成されることが多いですが、権限等の理由で手動作成しておくと安全です。

注意事項
- OpenAI を使う機能を利用する場合は環境変数 OPENAI_API_KEY を設定してください。
- プロセス優先度設定（psutil）や CPU affinity は OS によって権限が必要な場合があります（管理者権限）。
- .env は絶対にリポジトリにコミットしないでください。

---

## 必須 / 主な環境変数一覧

必須
- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

運用設定（代表的なもの）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - paper_trading のとき run_execution は paper_trading 用 DB を使い、本番 DB と分離します
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- LOG_DIR — ログ保存先ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）

監視・制御
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH — 実行プロセスの PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch のフラグ（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（"1" で有効、デフォルト: "0"）

Paper Trading に関する
- PAPER_FILL_MODE — "instant" | "partial" | "never" | "reject"（paper trading の約定モード）

（その他、config/*.yaml やモジュール固有の環境変数があります。validate_config.py で検出できます）

---

## 使い方（代表的なコマンド）

- .env の対話式作成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も FAIL）: python -m kabusys.validate_config --strict

- 監視ループの起動
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - run_monitoring は常に Settings.sqlite_path（本番 sqlite_path）を使う点に注意

- 実行エンジン起動
  - python -m kabusys.run_execution
  - Paper Trading で起動（MockBroker 使用・DB 分離）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

停止 / 制御
- 実行中プロセスを穏やかに停止するにはプロジェクトルートの data/stop_requested.flag を作成します（スクリプトが検知してループを終了）。
- Kill Switch（強制停止シグナル）は data/kill.flag に文字列を書き込みます。KillSwitch.clear() で削除可能。

ログ
- ログは標準出力に加え logs/<app_name>.log に日次ローテーションで保存（デフォルト 30 日保持）。
- ログ設定は kabusys.utils.logging_setup.setup_logging で一貫して行われます。

---

## プログラム的な利用

このパッケージはライブラリとしても利用できます。例:

- AI ニューススコアリング（プログラム呼び出し）
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key="...")

- 研究用ファクター計算
  - from kabusys.research import calc_momentum, calc_volatility, calc_value

- ポートフォリオ構築関数
  - from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py — パッケージエントリ（version）
  - config.py — 環境変数・Settings 管理（.env の自動読み込み含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI

  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

  - utils/
    - logging_setup.py — ロギング設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

  - monitoring/
    - monitoring_db.py — SQLite を使った監視ログ永続化（テーブル初期化・API）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （取引監視：滞留注文・約定異常など）※実装あり
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — フラグファイルによる停止シグナル管理
    - monitoring_engine.py — 各 Monitor と KillSwitch を束ねる
    - alert_manager.py — （通知管理：LINE 等）※実装あり

  - execution/
    - execution_engine.py — 実行エンジン本体（EngineConfig, run_session など）
    - broker_factory.py — ブローカークライアント生成
    - order_manager.py — オーダー管理
    - order_repository.py — 注文永続化
    - reconciler.py — 注文・ポジションの再照合
    - risk_manager.py — 実行時リスク管理

  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算
    - risk_adjustment.py — セクター制約・レジーム乗数

  - research/
    - factor_research.py — ファクター計算（momentum, volatility, value）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
    - __init__.py — 研究用 API エクスポート

  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）集約・ai_scores 書き込み
    - regime_detector.py — マクロ＋ETF MA によるレジーム判定
    - __init__.py

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成

  - monitoring/（DB スキーマ・ロジックは monitoring_db.py にまとまる）

- data/
  - stop_requested.flag — （存在すると run_* が停止）
  - execution.pid — ExecutionEngine の PID ファイル（既定）
  - kill.flag — Kill Switch 用フラグファイル

- logs/
  - <app_name>.log — ログファイル（デフォルト日次ローテート）

---

## 運用上の注意 / ベストプラクティス

- 本番（KABUSYS_ENV=live）では Kill Switch と LINE 通知等の設定を確実に行うこと（validate_config.py が注意喚起を出します）。
- Paper Trading はデータベースが分離されるため安全に検証できます。実行時は KABUSYS_ENV=paper_trading を指定してください。
- OpenAI 呼び出しは失敗やレート制限を考慮してリトライ・フォールバック実装がありますが、API キーの漏洩に注意してください。
- ログ・DB ファイルはバックアップ・権限管理を行ってください。
- process priority / affinity の設定は必要に応じて無効化や権限確認を行ってください（psutil を利用）。

---

この README はコードの docstring / usage コメントを基に記述しています。より詳細な設計やアルゴリズム説明（PortfolioConstruction.md、StrategyModel.md 等）はリポジトリ内のドキュメントを参照してください。質問や追加で欲しいセクションがあれば教えてください。