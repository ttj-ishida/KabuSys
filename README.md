# KabuSys

日本株向けの自動売買システムの一部実装（ライブラリ／起動スクリプト群）。  
このリポジトリは、実運用を想定した実行エンジン、監視（Monitoring）、ポートフォリオ構築・サイズ計算、リサーチ（ファクター計算）および AI を用いたニューススコアリング等のコンポーネントを含みます。

※ 本 README はソースツリー（src/kabusys 以下）の実装に基づいて作成しています。

## プロジェクト概要
- 実アプリケーション（ExecutionEngine）とそれを監視する Monitoring コンポーネントを含む。
- Paper Trading（ペーパートレード）モードと Live（本番）モードを切り替えて動作可能。
- DuckDB を分析用 DB、SQLite を監視ログ / 発注ログ用に使用（Paper Trading は専用 SQLite を使用して本番 DB と分離）。
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価や市場レジーム判定の機能を持つ（API キー必須）。
- ログ出力やプロセス優先度、Kill Switch（停止フラグ）など運用に配慮したユーティリティを備える。

## 主な機能一覧
- ExecutionEngine 起動スクリプト（run_execution）
  - Broker クライアントファクトリ（Paper と Live を分離）
  - OrderManager / RiskManager / Reconciler の組み立てと実行
  - 停止フラグ（data/stop_requested.flag）検出時の安全停止
  - PID ファイル管理（data/execution.pid）
- Monitoring（監視）
  - SystemMonitor：CPU / メモリ / ディスク / データ鮮度・プロセス稼働検査
  - TradeMonitor：発注ログ・約定検査（滞留注文・約定異常の検出）
  - RiskMonitor：ドローダウン・ポジション上限の監視、リスクログ記録
  - KillSwitch：一定条件で data/kill.flag を書き込み、Execution を停止
  - MonitoringEngine：上記 Monitor を定期実行しアラート発報
- ポートフォリオ構築（pure functions）
  - 候補選定（select_candidates）、重み計算（等金額・スコア加重）
  - セクターキャップ適用、レジーム乗数（calc_regime_multiplier）
  - ポジションサイズ計算（リスクベース・等配分等）と単元株丸め
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクターを DuckDB の prices_daily / raw_financials から計算
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ
- AI（OpenAI）モジュール
  - news_nlp: raw_news から銘柄単位にテキストを集約 → LLM に渡して銘柄ごとのスコアを ai_scores に書き込み
  - regime_detector: ETF（1321）MA200 乖離とマクロニュースの LLM 評価を合成して日次の market_regime を算出
  - 再試行・バックオフ・レスポンス検証等の耐障害性実装あり
- ユーティリティ
  - 設定ウィザード（python -m kabusys.config_setup）で .env 作成支援
  - 設定検証 CLI（python -m kabusys.validate_config）
  - ロギング設定ユーティリティ（logs に日次ローテート）
  - プロセス優先度 / CPU affinity の設定ユーティリティ
- ツール
  - Paper Trading 用検証レポート生成スクリプト（python -m kabusys.tools.paper_verification_report）

## セットアップ手順（ローカル開発向け）
以下は最低限のセットアップ手順例です。実運用時はセキュリティ・監視・バックアップ等を適切に整えてください。

1. Python 環境
   - Python 3.9+ を推奨（duckdb / psutil / openai 等が必要）
   - 仮想環境を作成して有効化することを推奨（venv / poetry / pipx 等）

2. 依存ライブラリのインストール（例）
   - pip install duckdb psutil openai pyyaml
   - 必要に応じて他ライブラリ（例えば unittest.mock を使ったテスト環境など）を追加

   例:
   ```
   python -m pip install duckdb psutil openai pyyaml
   ```

   注意:
   - PyYAML は `validate_config` の YAML 検証を行う場合に必要です。インストールされていない場合は警告が出て検証はスキップされます。
   - OpenAI SDK のバージョン差異により例外型名などが変わる可能性があります。実稼働では SDK の指定バージョンを明確に管理してください。

3. プロジェクトルートの準備
   - リポジトリルート（.git または pyproject.toml を含むディレクトリ）が自動検出されます。
   - data/ や logs/ はスクリプト実行時に自動作成されますが、権限等に注意してください。

4. 環境変数の設定（.env）
   - 対話式ウィザードで作成できます:
     ```
     python -m kabusys.config_setup
     ```
   - 重要な必須項目:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - OpenAI を使う機能を利用する場合:
     - OPENAI_API_KEY（任意として設定。AI 機能を使うときは必須）
   - その他主な変数（デフォルトはカッコ内）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH (data/kabusys.duckdb)
     - SQLITE_PATH (data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
     - LOG_LEVEL (INFO 等)
     - KILL_FLAG_CLEAR_ON_START (0|1) — 本番では 0 を推奨
   - .env の自動読み込み:
     - 通常は .env/.env.local を自動読み込みします（OS 環境変数が優先）。
     - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告も失敗扱いになります。

## 使い方（起動コマンド）
パッケージとしてインポート可能な形式なので、モジュールを直接 `-m` で起動します。

- Execution エンジン（発注エンジン）起動:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
  - 実行中に同ファイルが作られると安全に停止します。

- Monitoring（監視ループ）起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト: 60）。
  - Monitoring は環境にかかわらず本番 sqlite_path（settings.sqlite_path）を参照して監視ログを記録します。

- .env 対話的設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db オプションで SQLite パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も参照します。

- ライブラリ的に利用する（例: AI スコアリング）
  - Python から直接呼び出し:
    ```py
    from kabusys.ai.news_nlp import score_news
    # duckdb_conn: DuckDB 接続, target_date: datetime.date
    score_news(duckdb_conn, target_date, api_key="YOUR_OPENAI_KEY")
    ```

## 主要設定（Environment variables）
（実装上明示されているもの、代表的なものを抜粋）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境:
  - KABUSYS_ENV: development | paper_trading | live

- DB & ファイル:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0|1) — 起動時に kill.flag を自動クリアするか

- ログ:
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
  - LOG_DIR（デフォルト: logs/）

- Monitoring:
  - MONITOR_POLL_INTERVAL（秒、run_monitoring で使用）

- OpenAI:
  - OPENAI_API_KEY（AI 機能を使う場合必須）

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要なモジュールと役割です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env ロード / Settings 実装
  - config_setup.py          — .env 対話ウィザード CLI
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - execution/               — 発注エンジン関連（Engine, OrderManager, RiskManager 等）
  - monitoring/
    - monitoring_db.py       — SQLite 永続層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI + ETF）
  - utils/
    - logging_setup.py       — ロギング設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

データ・ログ出力先（デフォルト）:
- data/monitoring.db (SQLite)
- data/paper_trading.db (Paper Trading 用 SQLite)
- data/kabusys.duckdb (DuckDB)
- logs/<app_name>.log（TimedRotatingFileHandler 日次ローテート）

## 運用上のポイント / トラブルシューティング
- Paper Trading と Live の DB は分離してください。PAPER_TRADING_SQLITE_PATH を設定して、テストと本番 DB の混在を避けます。
- OpenAI を使う機能は API キーが必須です。キー未設定時は ValueError が発生します（呼び出し関数による）。
- validate_config は PyYAML 未インストール時に YAML 検証をスキップします（警告のみ）。
- process priority / cpu affinity の設定は OS の権限によって失敗することがあります（警告ログが出てスキップされます）。
- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）と stop_requested.flag（データディレクトリ内の stop ファイル）は異なる目的で使われます。Monitoring の KillSwitch は kill.flag を書き込み、ExecutionEngine は kill.flag を検出して停止します。stop_requested.flag は run_* スクリプトの簡易停止トリガーとして利用されています。
- ログディレクトリ作成に失敗したときはファイルロギングが無効になり、コンソール出力のみになります。権限やマウント先を確認してください。

## 開発メモ
- config.py はプロジェクトルートを .git や pyproject.toml から探して .env を自動読み込みします（CWD 非依存）。
- 多くのコンポーネントは DuckDB 接続や sqlite3.Connection を外部から受け取る設計でテストしやすくなっています（副作用を最小化）。
- AI 呼び出し部分はリトライとレスポンス検証を行い、失敗時はフォールバック（スコア 0.0 またはスキップ）してシステム全体の停止を防ぐ実装です。

---

README に記載していない詳細（内部の関数仕様や追加オプション等）は各モジュールの docstring / コメントを参照してください。必要であれば、特定モジュールの詳しいドキュメントも作成します。