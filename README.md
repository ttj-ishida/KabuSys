# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買 / 研究プラットフォームです。本リポジトリは以下の主要機能群を含みます: データパイプライン・ファクター計算、ポートフォリオ構築、発注実行エンジン（実取引 / ペーパートレード切替）、監視（モニタリング）・アラート、AI（ニュース NLP / レジーム検出）および検証・ユーティリティツール群。

---

## 主な機能一覧

- 環境設定管理
  - .env ウィザード（`kabusys.config_setup`）で対話的に作成可能
  - 自動 .env 読み込み（`.env.local` を優先）／無効化オプションあり
- 実行エンジン（ExecutionEngine）
  - 本番（kabuステーション API 経由）/ ペーパートレード（MockBroker）を切替可能（`KABUSYS_ENV`）
  - リスク管理・注文管理・約定リコンシリエーション機能
- 監視（Monitoring）
  - System / Trade / Risk の監視コンポーネントとポーリングエンジン
  - kill.flag による停止（Kill Switch）および stop フラグファイル検出
  - 監視ログは SQLite（デフォルト: `data/monitoring.db`）に永続化
- ポートフォリオ構築（純粋関数群）
  - 候補選定、等配分・スコア重み付け、セクター制限、ポジションサイズ決定（単元株丸め等）
- 研究（Research）
  - DuckDB を用いたファクター計算（モメンタム / バリュー / ボラティリティなど）
  - 特徴量探索・将来リターン・IC 計算ツール
- AI モジュール
  - ニュースに対する LLM（OpenAI）ベースのセンチメントスコア付与（`kabusys.ai.news_nlp`）
  - マクロ + ETF MA を用いた市場レジーム判定（`kabusys.ai.regime_detector`）
  - OpenAI API キー必須（環境変数 `OPENAI_API_KEY` または引数）
- ツール
  - Paper Trading の検証レポート生成（`kabusys.tools.paper_verification_report`）
- ロギング
  - 統一的ログ設定（コンソール stdout + 日次ローテートファイル、デフォルト `logs/`、30 日保持）

---

## セットアップ手順（開発 / ローカル実行向け）

1. リポジトリをクローンし、Python 仮想環境を作成・有効化します。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストールします（例: pip）。
   - 主な依存例:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（検証時の config YAML パース用、任意）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （実際の requirements.txt がある場合はそれを使用してください）

3. .env を作成します（ウィザード推奨）。
   - python -m kabusys.config_setup
   - ウィザード完了後、`python -m kabusys.validate_config` で設定を検証してください。
   - 自動ロードはプロジェクトルートの `.env` / `.env.local` を読み込みます。自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. データディレクトリの確認
   - デフォルト DB / ファイルパス:
     - DuckDB: data/kabusys.duckdb (`DUCKDB_PATH`)
     - Monitoring SQLite: data/monitoring.db (`SQLITE_PATH`)
     - Paper Trading SQLite: data/paper_trading.db (`PAPER_TRADING_SQLITE_PATH`)
     - PID / kill flag 等: data/*.pid / data/kill.flag
   - これらの親ディレクトリは自動作成されることがありますが、権限設定等に注意してください。

5. ログディレクトリ
   - デフォルト `logs/`。環境変数 `LOG_DIR` で変更可。
   - ログローテーション: 日次、30日分保持

注意: 一部機能（プロセス優先度設定、CPU affinity）は OS 権限・psutil のサポートに依存します。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- OPENAI_API_KEY: OpenAI 使用時に必要
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG / INFO / ...）
- LOG_DIR（ログ出力先）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用、任意）
- MONITOR_POLL_INTERVAL（監視ループ間隔、秒。デフォルト 60）
- PAPER_FILL_MODE（paper_trading 時の約定挙動: instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか、0/1）

設定ツール: `python -m kabusys.config_setup`（ウィザード）、検証: `python -m kabusys.validate_config`

---

## 使い方（実行方法の例）

- 監視プロセス（SystemMonitor のポーリングループを起動）
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒数で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 実行中、data/stop_requested.flag を作成するとループは安全に終了します（スクリプト内で確認）

- Execution Engine 起動（発注エンジン）
  - python -m kabusys.run_execution
  - 起動時に `KABUSYS_ENV=paper_trading` を設定すると MockBroker を使用し、`data/paper_trading.db` を用います（本番 DB と分離）。
  - 実行中に data/stop_requested.flag を作成するとエンジンが停止します。
  - PID ファイル: `data/execution.pid`（設定で変更可）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit(1)

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）

- AI 関連（ニューススコア / レジーム判定）
  - これらは DuckDB 接続と OpenAI API キーが必要:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 実行前に `OPENAI_API_KEY` を環境変数で設定するか、関数引数で渡してください。

---

## 監視・停止フロー（重要）

- Kill Switch:
  - RiskMonitor 等の判定により `KillSwitch` がデータディレクトリの `data/kill.flag` を書き込むと、ExecutionEngine に対して停止シグナルを与える仕組みがあります。
  - ExecutionEngine は起動時に `KILL_FLAG_CLEAR_ON_START` の設定に応じて kill.flag を削除するオプションがあります（本番ではデフォルト 0 を推奨）。
- stop_requested.flag:
  - `data/stop_requested.flag` を置くと run_monitoring / run_execution が検出して安全に終了します（手動停止用のファイルフラグ）。

---

## ディレクトリ構成（主要ファイル / モジュール）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite 永続化レイヤ（テーブル定義・CRUD）
    - system_monitor.py      — システム状態・データ鮮度チェック
    - trade_monitor.py       — （取引監視関連）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag の管理
    - monitoring_engine.py   — 各 Monitor を束ねるポーリングエンジン
    - alert_manager.py       — （アラート送信管理、LINE 等）
  - execution/               — 発注エンジン関連（BrokerFactory, ExecutionEngine, OrderManager, RiskManager 等）
  - portfolio/               — 銘柄選定・重み計算・位置サイズ等（純粋関数群）
  - research/                — ファクター計算・特徴量探索
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — レジーム判定（MA + マクロ NLP）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成ツール
  - data/                    — データディレクトリ（実行時に生成される。DB / flag / pid 等）

備考: 上記は主要ファイルの抜粋です。実装の詳細は各モジュールの docstring を参照してください。

---

## 動作上の注意 / トラブルシューティング

- .env の自動読み込み:
  - OS 環境変数 > .env.local > .env の順で読み込みされます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI API:
  - レート制限・一時エラーに対しては指数バックオフとリトライが実装されていますが、API キーの管理と課金に注意してください。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等にテーブルを作成し、既存 DB に対する簡易的なカラム追加マイグレーションを含みます。
- 権限:
  - process priority の設定は OS と権限に依存します。psutil による設定で失敗すると警告が出ますが、そのまま処理は継続します。
- ログ出力先の作成に失敗した場合:
  - ログディレクトリ作成に失敗するとコンソール出力のみで継続します（警告が表示されます）。

---

## 開発者向けメモ

- 各スクリプトは module-as-script で実行可能（例: python -m kabusys.run_execution）。
- DuckDB 接続は多くの研究 / AI モジュールで引数として受け取り、SQL＋Python による局所的処理を行います。
- ポートフォリオ構築 / リスクロジック等は純粋関数設計を念頭に置き、単体テストがしやすい構成です。

---

README は以上です。必要であれば、実行例（環境変数の具体的な設定例）、requirements.txt の候補、または各モジュールの簡易 API リファレンスを追加で作成します。どれが必要か指示してください。