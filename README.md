# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README（日本語）

この README は、リポジトリ内の主要機能・起動手順・基本的な使い方・ディレクトリ構成をまとめたドキュメントです。

概要
- KabuSys は日本株向けの自動売買・研究・監視ツール群を含むプロジェクトです。
- 主なコンポーネント:
  - ExecutionEngine：注文発行・リスク管理・注文管理の実行エンジン
  - Monitoring：システム稼働・注文状態・リスクを定期監視してアラート／Kill Switch を運用
  - Portfolio：銘柄選定、重み算出、ポジションサイジングなどポートフォリオ構築ロジック
  - Research：DuckDB 上でファクター計算・特徴量解析を行う研究用モジュール
  - AI：ニュースの NLU によるセンチメント評価・市場レジーム判定（OpenAI を利用）
  - Tools：ペーパートレード検証レポート生成などのユーティリティスクリプト
  - Utils：ログ設定・プロセス優先度設定 等のユーティリティ

機能一覧
- 環境設定ウィザード（.env の対話的作成）: python -m kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml の事前チェック）: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト:
  - 本番／ペーパートレードを環境変数 KABUSYS_ENV で切り替え
  - paper_trading では MockBroker を使用し paper DB（data/paper_trading.db）へ記録
  - 実行コマンド: python -m kabusys.run_execution
- Monitoring 起動スクリプト:
  - System / Trade / Risk の各監視をポーリングし、kill flag を書き込む等の制御を実行
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 実行コマンド: python -m kabusys.run_monitoring
- 監視用 DB（SQLite）初期化（冪等）: init_monitoring_db
- Paper Trading の検証レポート生成: python -m kabusys.tools.paper_verification_report
- ニュース NLP（OpenAI）による銘柄ごとのセンチメント算出（ai.news_nlp）
- 市場レジーム判定（ai.regime_detector）：ETF + マクロニュースを組合せて daily レジーム算出
- Portfolio 構築ユーティリティ（候補選定・重み付け・ポジションサイズ計算・セクター制限）

セットアップ手順（ローカル開発向け）
1. Python
   - 推奨: Python 3.10+
2. リポジトリをクローンし、仮想環境を作成して有効化
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - 主要依存例: duckdb, psutil, openai, PyYAML（設定検証で利用）
   - 例: pip install duckdb psutil openai PyYAML
   - （requirements.txt がある場合はそれを利用してください）
4. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 手動で作る場合はルートの .env.example を参考に .env を作成してください。
   - 自動ロード: 起動時に .env / .env.local が自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑制可能）
5. 設定の検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）
6. ディレクトリ（data / logs 等）の作成は多くの起動処理で自動作成されますが、必要に応じて事前に作成してください。

主な環境変数（要件とデフォルト）
- 必須:
  - JQUANTS_REFRESH_TOKEN：J-Quants API 用トークン
  - KABU_API_PASSWORD：kabuステーション API パスワード
- 選択／デフォルト:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
  - LOG_LEVEL: INFO（DEBUG 等を指定可）
  - OPENAI_API_KEY: OpenAI API を使う機能で必要（AI モジュール）
  - PAPER_FILL_MODE: ペーパートレードの約定挙動（instant/partial/never/reject、デフォルト instant）
  - MONITOR_POLL_INTERVAL: 監視ループの秒間隔（デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする（0/1、本番では 0 推奨）
- ログ:
  - デフォルトログディレクトリ: logs/
  - ログはコンソール（stdout）と日次ローテートファイル（logs/<app_name>.log）に出力

使い方（基本コマンド例）
- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 注意: 起動前に data/kill.flag（Kill Switch）や data/stop_requested.flag がないか確認
- Monitoring を起動（デフォルト 60 秒間隔）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring  （間隔を 30 秒に変更）
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- AI モジュール（例: ニューススコアリング）をスクリプトから呼ぶ
  - Python セッション内で:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

停止 / Kill Switch / フラグファイル
- プロセスの安全停止はフラグファイルで制御します:
  - data/kill.flag : ExecutionEngine 停止用 Kill Switch（監視が判定して書き込む）
  - data/stop_requested.flag : run_monitoring / run_execution が検知する停止要求フラグ
  - PID ファイル:
    - data/execution.pid（ExecutionEngine 用）
- 注意: 本番環境 (KABUSYS_ENV=live) では KILL_FLAG_CLEAR_ON_START=1 の設定は危険です（自動クリアされます）。

内部的な動作（要点）
- Monitoring は SystemMonitor / TradeMonitor / RiskMonitor をまとめて実行し、必要に応じて kill.flag を書き込む、アラート通知を行う設計です。
- Monitoring 用の SQLite スキーマは init_monitoring_db により冪等に作成・マイグレーションされます（system_status, trade_logs, positions, risk_logs, dashboard 等）。
- ExecutionEngine は環境に応じて本番 DB / paper_trading DB を切り分けます（paper_trading では専用 DB を使用）。
- ロギングは共通ユーティリティで統一（stdout + 日次ファイルローテーション）。
- プロセス優先度は起動時に高優先度に設定されます（セットに失敗した場合は警告のみ）。

ディレクトリ構成（主要ファイル/モジュール）
- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理、.env の自動ロード
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート
  - utils/
    - logging_setup.py           — 共通ログ設定ユーティリティ
    - process_priority.py        — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py           — 監視用 SQLite の永続層（テーブル作成・読み書き）
    - monitoring_engine.py       — 各 Monitor の統合ループ
    - system_monitor.py          — システム状態 / データ鮮度監視
    - risk_monitor.py            — ドローダウン・ポジション上限監視
    - kill_switch.py             — Kill Switch（flag 書き込み）
    - ... (TradeMonitor / AlertManager 等の実装ファイル)
  - portfolio/
    - portfolio_builder.py       — 候補選定・重み計算
    - position_sizing.py         — 株数計算・aggregate cap
    - risk_adjustment.py         — セクター制限・レジーム乗数
  - research/
    - factor_research.py         — Momentum/Volatility/Value 等の計算（DuckDB）
    - feature_exploration.py     — forward returns / IC / 統計サマリ
  - ai/
    - news_nlp.py                — ニュースを OpenAI でスコアリング
    - regime_detector.py         — レジーム判定（ETF + マクロニュース）
  - execution/                    — (注文実行関連のモジュール群: broker_factory 等)
  - data/                         — （ランタイムの DB / flag / pid 保存場所）
  - logs/                         — ログファイル

注意事項 / ベストプラクティス
- 本番（live）では設定を慎重に確認し、KILL_FLAG_CLEAR_ON_START=0、ログレベルや DB パス等を確認してください。
- OpenAI API を使う機能は API キー（OPENAI_API_KEY）が必須です。無料トライアルのレートやコストに注意してください。
- paper_trading を使えば本番口座に影響を与えずに検証できます。paper_trading の挙動は .env の PAPER_FILL_MODE 等で制御します。
- DuckDB による research モジュールは大量データの分析向けです。DuckDB ファイルパス（DUCKDB_PATH）を適切に設定してください。
- ログディレクトリ作成に失敗するとファイル出力が無効化されます（コンソール出力は維持されます）。必要に応じて権限やパスを確認してください。

サポート / 開発メモ
- 単体の機能をテストしたい場合は各モジュールの import 可能な関数を使って Python から直接実行できます（例: research.calc_momentum、ai.score_news 等）。
- 設定の自動読み込みはプロジェクトルートを .git / pyproject.toml で判定します。パッケージ配布後に動かす場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して読み込みを制御してください。

以上がこのコードベースの概要と基本的な使い方です。運用・開発を進める際は config/*.yaml（存在する場合）や各モジュールの docstring を参照してください。必要があれば README にさらに「運用手順」「デプロイ手順」「監視メトリクス仕様」などの詳細を追加しますので、その旨をお知らせください。