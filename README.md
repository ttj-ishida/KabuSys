# KabuSys

日本株向けの自動売買 / 研究基盤ライブラリ群。  
戦略構築・ポートフォリオ計算・発注エンジン（ExecutionEngine）・監視・AIベースのニュース解析等のコンポーネントを含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 実行・使い方
- 環境変数（主要）
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株の自動売買システムのためのモジュール群です。  
  - 発注エンジン（ExecutionEngine）・ブローカークライアント抽象化・オーダー管理・リスク管理
  - 監視サブシステム（System / Trade / Risk）と Kill Switch
  - ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出・セクター制限）
  - リサーチ用途（ファクター計算、特徴量探索、IC計算）
  - AI ユースケース（ニュースのセンチメント解析、レジーム判定）
  - 運用ツール（.env 作成ウィザード、設定検証、Paper Trading 検証レポート）

主な機能一覧
- Execution
  - 実際のブローカー／モックブローカー（paper_trading）を切り替え可能
  - リスク制御（最大ポジション比率、利用率、ドローダウン等）
  - 発注ログ（SQLite）と分析 DB（DuckDB）への保存
- Monitoring
  - CPU/メモリ/ディスク・プロセス生存確認・データ鮮度チェック
  - Trade / Risk 監視、Kill Switch（データに基づく停止フラグ生成）
  - ログと監視メトリクスは SQLite（monitoring.db）へ永続化
- Portfolio
  - 候補選定・等重／スコア重み付け・リスクベースの株数算出
  - セクターキャップ、レジーム乗数
- Research
  - Momentum / Volatility / Value ファクター算出（DuckDB）
  - 将来リターン、IC（Spearman）や統計サマリ
- AI
  - ニュースセンチメント（OpenAI 利用）を ai_scores テーブルへ保存
  - マクロニュース + ETF MA による日次レジーム判定
  - API コールはリトライ・フェイルセーフ設計（失敗時は安全側にフォールバック）
- ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール

---

セットアップ手順（ローカル開発環境の例）
1. Python 環境（推奨: 3.10+）を用意
2. 仮想環境作成・有効化
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate
3. 依存パッケージをインストール（プロジェクトに requirements.txt がない場合は以下を参考）
   - pip install duckdb psutil openai pyyaml
   - （実行環境によっては追加で sqlite3 は標準搭載）
4. リポジトリルートで開発モードインストール（任意）
   - pip install -e .
5. 初期設定
   - python -m kabusys.config_setup
     - .env を対話式で生成・更新します（J-Quants トークン、kabu API パスワード等を入力）
   - python -m kabusys.validate_config
     - 設定に不備がないか検証します
6. データディレクトリ作成（必要なら）
   - デフォルト DB 等は data/ 以下を参照します。自動で作成される箇所もありますが、権限等の問題で手動作成する場合があります。

補足（主要依存）
- duckdb: 分析向け DB（prices_daily / raw_financials 等を扱う）
- psutil: システムモニタリング・プロセス優先度設定
- openai (OpenAI Python SDK): ニュース解析 / レジーム判定で使用（APIキー必須）

---

使い方（主要な実行スクリプト・モジュール）

1) 環境設定ウィザード
- python -m kabusys.config_setup
  - .env の初期作成・更新を対話式で行います。

2) 設定検証
- python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いになります。

3) ExecutionEngine 起動（発注エンジン）
- python -m kabusys.run_execution
  - KABUSYS_ENV により挙動が変わります:
    - paper_trading: MockBrokerClient を使用し、本番 DB と分離して data/paper_trading.db を使用
    - live / development: settings.sqlite_path（デフォルト data/monitoring.db）等を使用
  - 実行時、data/execution.pid に PID を書き出す設計
  - data/stop_requested.flag が存在すると起動をスキップまたは停止します
  - 起動前に KILL_FLAG_CLEAR_ON_START 環境変数が 1 のとき kill.flag を自動クリア（本番では 0 推奨）

4) Monitoring 起動（監視ポーリング）
- python -m kabusys.run_monitoring
  - 監視ループで SystemMonitor.check_once() を定期実行します（デフォルト 60 秒）
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒）
  - 監視は「本番 sqlite_path」を使用（KABUSYS_ENV に依存せず）
  - 停止は data/stop_requested.flag の作成で行います

5) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD --db <path>
  - 簡単に Paper Trading のパフォーマンス指標（稼働率 / 注文成功率 / レイテンシ等）を出力します
  - デフォルト DB: data/paper_trading.db または 環境変数 PAPER_TRADING_SQLITE_PATH

6) AI / Research 関数（ライブラリ利用例）
- kabusys.ai.score_news（DuckDB 接続 + target_date + OPENAI_API_KEY）
- kabusys.ai.regime_detector.score_regime（同上）
- kabusys.research.calc_momentum/calc_volatility/calc_value（DuckDB 接続 + target_date）
- これらはライブラリとしてインポートして使います（スクリプト化されている関数もあります）。

主要な環境変数（要点）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH: 分析用 DB（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（1/0）

運用ファイル（デフォルトパス）
- data/monitoring.db (SQLite) — 監視ログ・trade_logs 等
- data/paper_trading.db (SQLite) — ペーパートレード専用ログ（paper_trading モード）
- data/kabusys.duckdb (DuckDB) — 価格・ファクター・ニュース等の分析用 DB
- data/execution.pid — ExecutionEngine の PID（設定により変わる）
- data/kill.flag — Kill Switch による停止フラグ（存在すれば ExecutionEngine を停止させる）
- data/stop_requested.flag — 外部からの停止リクエスト（run_* スクリプトが検出して終了）

ログ
- デフォルトは logs/<app_name>.log（日次ローテーション、30日保持）
- コンソール出力は stdout に出力されます
- setup_logging(app_name="execution") 等で統一的にログが設定されます

---

ディレクトリ構成（抜粋 / 主要ファイルと説明）
- src/
  - kabusys/
    - __init__.py
    - config.py
      - 環境変数・.env 自動ロード・Settings クラス
    - config_setup.py
      - .env 対話式ウィザード
    - validate_config.py
      - 起動前の設定検証 CLI
    - run_execution.py
      - ExecutionEngine 起動スクリプト
    - run_monitoring.py
      - SystemMonitor ポーリングループ起動スクリプト
    - execution/
      - execution_engine.py (エンジン本体)
      - order_manager.py / order_repository.py / reconciler.py / risk_manager.py
      - broker_factory.py (実ブローカー/モックの切替)
    - monitoring/
      - monitoring_db.py (SQLite 永続化層)
      - system_monitor.py / trade_monitor.py / risk_monitor.py
      - monitoring_engine.py / alert_manager.py / kill_switch.py
    - portfolio/
      - portfolio_builder.py (候補選定・重み)
      - position_sizing.py (株数算出)
      - risk_adjustment.py (セクター上限・レジーム)
    - research/
      - factor_research.py (ファクター算出)
      - feature_exploration.py (forward returns, IC, summary)
    - ai/
      - news_nlp.py (ニュースセンチメント -> ai_scores)
      - regime_detector.py (レジーム判定)
    - utils/
      - logging_setup.py (ログ設定ユーティリティ)
      - process_priority.py (プロセス優先度設定)
    - tools/
      - paper_verification_report.py (Paper Trading レポート)
    - data/ (アプリ実行時に使用するデフォルトディレクトリ: DB / flags / pid 等)
- pyproject.toml / setup.cfg 等（配布・依存管理に応じて存在）

---

運用上の注意
- 本番（KABUSYS_ENV=live）では env と config を慎重に管理してください。validate_config で live 用のガードチェックを行います。
- kill.flag（自動 Kill Switch）や stop_requested.flag による停止は冪等に実装されていますが、運用手順はドキュメント化しておくことを推奨します。
- OpenAI API を利用する機能は API コスト・レート制限に注意してください。失敗時はフォールバックする実装ですが、プライシングやレートに応じた運用設計が必要です。
- DuckDB / SQLite のファイルパスは .env で自由に変更可能です。production と paper_trading は DB を分離する設計です。

---

問題報告 / 貢献
- バグ報告や機能要望は Issue を作成してください。プルリクエストは歓迎します。  
- 実際の取引連携部分（kabu API）や本番運用可否については、事前に十分な検証を行ってください。

---

以上がこのコードベースの概要と運用ガイドです。必要なら「起動例のコマンド」「.env サンプル」「よくあるエラーと対処法」など詳細ドキュメントも追加で作成します。どの情報を優先して追加しますか？