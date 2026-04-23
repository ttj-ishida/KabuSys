# KabuSys

日本株自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは以下の機能を持つモジュール群を含みます：
- 注文実行エンジン（ExecutionEngine）およびその周辺（ブローカー抽象、注文管理、リスク制御）
- 監視（Monitoring）エージェント（システム・注文・リスク監視、Kill Switch）
- ポートフォリオ構築・配分ロジック（候補選定、重み付け、ポジションサイズ計算、セクター制約）
- 研究用モジュール（ファクター計算、特徴量解析）
- AI 関連（ニュース NLP によるセンチメント／レジーム判定）
- ユーティリティ（ログ設定、プロセス優先度、設定ウィザード / 検証、ツール類）

以下はこのコードベースの README（日本語）です。

---

目次
- プロジェクト概要
- 機能一覧
- 前提（依存関係）
- セットアップ手順
- 環境設定（.env）
- 使い方（起動・管理・ツール）
- 主要環境変数（抜粋）
- ディレクトリ構成
- 運用上の注意 / トラブルシューティング

---

プロジェクト概要
- KabuSys は日本株の自動売買フレームワークです。戦略（シグナル） → ポートフォリオ構築 → 発注 → モニタリング／リスク管理 の流れをサポートします。
- DuckDB を分析用（prices, financials 等）に使用し、SQLite を監視・発注ログ用に使用します（Paper Trading は発注 DB を分離可能）。
- OpenAI API を使ったニュースセンチメントやレジーム判定を組み込めます（任意）。

機能一覧
- Execution
  - 実注文/モック（paper_trading）を切り替え可能（KABUSYS_ENV）
  - 注文管理、リスクマネージャ、再整合（reconciler）等
- Monitoring
  - システムリソース監視（CPU/MEM/DISK）、データ鮮度チェック、プロセス生存判定
  - 注文ログ監視（滞留注文、約定異常検出）
  - リスク監視（ドローダウンおよびポジション上限）
  - Kill Switch（条件に応じて data/kill.flag を書き込み ExecutionEngine を停止）
- Portfolio
  - 候補選定（スコア順）、等金額／スコア加重、リスクに基づくポジションサイズ計算
  - セクター上限の適用、レジーム乗数
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB 経由、prices_daily / raw_financials を利用）
  - 将来リターン計算、IC 計算、統計サマリ
- AI
  - ニュース NLP による銘柄ベースのセンチメントスコアリング（OpenAI）
  - マクロ記事を用いた市場レジーム判定（OpenAI）
- ツール
  - Paper Trading の検証レポート出力（paper_verification_report）
- 設定管理
  - 対話式 .env ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
- ユーティリティ
  - 統一的なログ設定（stdout + 日次ローテートファイル）
  - プロセス優先度・CPU affinity 設定

前提（依存関係）
- Python 3.10+（型ヒントに union 型 | を使用するため）
- pip パッケージ（例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config/*.yaml の内容検証を行いたい場合、任意）
- SQLite は標準ライブラリで利用
- OS: Linux / macOS / Windows（ただし一部プロセス優先度はプラットフォーム依存）

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン、作業ディレクトリへ移動。
2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - 例: pip install duckdb psutil openai pyyaml
     （プロジェクトに requirements.txt があればそれを使ってください）
4. 環境変数の初期化
   - 対話式ウィザード: python -m kabusys.config_setup
     → data ベースのパスや API トークンなどを設定して .env を作成します
   - もしくは手動で .env を作成（ルートの .env / .env.local）
5. 設定検証（必須ではないが推奨）
   - python -m kabusys.validate_config
   - 本番用に厳格チェック: python -m kabusys.validate_config --strict

環境設定（.env 自動読み込み挙動）
- .env の自動ロード順序:
  - OS 環境変数 (優先)
  - .env.local（存在する場合、OSを保護して上書き可能）
  - .env
- 自動読み込みを無効にする場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- config_setup による .env には、J-Quants / kabu API トークンなどの秘密情報が含まれます。絶対に Git にコミットしないでください。

使い方（主要スクリプト）
- ExecutionEngine を起動（本番 or paper_trading は KABUSYS_ENV で制御）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い paper_trading.db（デフォルト data/paper_trading.db）へ記録
    - 起動時に data/stop_requested.flag があると起動せず終了
    - 実行中、data/stop_requested.flag を作成すると Engine に停止指示が出ます
- Monitoring を起動（ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き（デフォルト 60）
  - Monitoring は常に本番 sqlite_path（Settings.sqlite_path）を使用して監視データを記録
  - 停止: data/stop_requested.flag を作成すると監視ループが終了
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - DB デフォルト: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可能）
- AI モジュール（ニューススコア／レジーム判定）はライブラリ API を通して使用:
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime
  - OpenAI API キーは環境変数 OPENAI_API_KEY または引数で渡す

主要環境変数（抜粋とデフォルト）
- KABUSYS_ENV: 実行環境（development | paper_trading | live） — デフォルト development
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API リフレッシュトークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI を使う場合に必要
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite ファイル（監視 DB、デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading の SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- LOG_DIR: ログ出力ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（1=有効、開発向け、推奨は 0）

停止 / Kill Switch
- ExecutionEngine 停止シグナル:
  - Kill Switch は監視モジュールが条件（ドローダウン超過やポジション上限）を満たすと data/kill.flag を書き込みます。
  - ExecutionEngine 起動時に Settings.kill_flag_clear_on_start=1 が設定されていると自動で削除されることがあるので注意（本番では 0 を推奨）。
- グローバル停止フラグ:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループが検出して終了します。

ログ
- 共通のログ設定ユーティリティを利用（kabusys.utils.logging_setup.setup_logging）
- stdout に出力され、logs/<app_name>.log に日次ローテートで保存（デフォルト 30 日保持）
- ログ出力先ディレクトリが作成できない場合はコンソールのみで継続

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - config.py                  — Settings（環境変数 / .env 自動ロード）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - utils/
    - logging_setup.py         — 共通ログ設定
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py         — SQLite 監視 DB テーブル作成 + 簡易永続化 API
    - system_monitor.py        — システム / データ鮮度監視
    - trade_monitor.py         — （注文監視、ファイル中に定義あり）※実装参照
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — kill.flag の作成・評価
    - monitoring_engine.py     — 各 Monitor を束ねるエンジン
  - execution/                 — Execution 関連（ブローカー、エンジン、order_manager 等）
  - portfolio/                 — ポートフォリオ構築ロジック（builder / sizing / risk adjustment）
  - research/                  — ファクター・研究用ツール（factor_research, feature_exploration）
  - ai/
    - news_nlp.py              — ニュース NLP（OpenAI）
    - regime_detector.py       — 市場レジーム判定（OpenAI）
  - data/ (想定されるデータディレクトリ)
    - monitoring.db (SQLITE_PATH のデフォルト)
    - paper_trading.db
    - kabusys.duckdb
  - logs/                      — デフォルトログディレクトリ

（注）上記はリポジトリ内の src/kabusys 以下を要約しています。実際のファイル群はさらに細分化されています。

運用上の注意 / トラブルシューティング
- .env に秘密情報を含めるため、リポジトリにコミットしないでください。
- validate_config を常に実行して、必須環境変数の未設定やパスの問題を事前に検出してください。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を強く推奨します。
- OpenAI など外部 API 呼び出しは失敗時にフォールバック（多くはスコア 0 や SKIP）する設計ですが、API キーがないと該当機能は実行できません。
- DuckDB / SQLite のファイルパスは .env で変更可能です。複数環境（本番 / paper_trading）で DB を分離してください。
- プロセス優先度設定は psutil を用いて行います。権限がない場合は警告が出てスキップされます。

参考コマンドまとめ
- .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
- この README はコードベースの主要機能と運用手順を簡潔にまとめたものです。実際の運用前に config/*.yaml（存在する場合）や各モジュールの実装コメントを確認し、必要な権限や API キーを正しく設定してください。

問題や不明点があれば、該当モジュールの docstring やログ出力を参照してください（各モジュールに説明コメントが豊富にあります）。