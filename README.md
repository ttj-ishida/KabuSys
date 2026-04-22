# KabuSys

日本株自動売買システムのコードベース（抜粋）。  
この README はプロジェクトの概要、主な機能、セットアップ手順、実行方法、ディレクトリ構成を日本語でまとめたものです。

※ 本リポジトリは複数のコンポーネントで構成され、実運用では環境変数設定・機密情報管理・DB分離などの運用上の注意が必要です。

---

## プロジェクト概要

KabuSys は日本株の自動売買（売買シグナル生成・ポートフォリオ構築・発注・監視・リスク管理）を目的としたモジュール群です。  
主な設計方針：

- 設定は .env（および .env.local）で管理。起動時に自動読み込み（無効化可能）。
- Paper trading（ペーパートレード）モードと Live（本番）モードを切り替え可能。Paper trading は本番 DB と分離された専用 SQLite を使用。
- DuckDB を解析用データベースに使用し、prices_daily / raw_financials 等のテーブルからファクターを計算。
- OpenAI（LLM）を利用したニュース NLP / レジーム判定モジュールを内包（APIキー必須）。
- Monitoring（監視）系は SQLite にログを永続化し、Kill Switch による発注停止など安全機能を持つ。

---

## 主な機能一覧

- 実行コンポーネント
  - ExecutionEngine 起動スクリプト（run_execution.py）
    - 本番/ペーパーの切替、BrokerClientFactory によるブローカ接続、リスク管理、リコンサイル等
- 監視コンポーネント
  - SystemMonitor / TradeMonitor / RiskMonitor を組合せる MonitoringEngine（run_monitoring.py）
  - monitoring DB（SQLite）へのログ永続化、Kill Switch（data/kill.flag）による停止
- ポートフォリオ構築
  - 銘柄選定、ウエイト計算（等金額/スコア加重）、ポジションサイジング、セクター制約、レジーム乗数
- リサーチ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 特徴量探索（将来リターン、IC、統計サマリ等）
- AI（OpenAI）連携
  - ニュースセンチメントスコアリング（news_nlp）
  - 市場レジーム判定（regime_detector）
- ユーティリティ
  - 設定ウィザード（config_setup.py）: .env の対話式作成
  - 設定検証 CLI（validate_config.py）
  - ログ設定ユーティリティ、プロセス優先度設定ユーティリティなど
- ツール
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）

---

## セットアップ手順（ローカル開発向け）

前提：
- Python 3.10 以上を推奨（| 型ヒント等を使用）
- 仮想環境の利用を推奨（venv / pipenv / poetry 等）

1. リポジトリをクローンして作業ディレクトリへ移動
   - 省略

2. 仮想環境作成・有効化、依存パッケージのインストール  
   代表的な依存パッケージ（抜粋）:
   - duckdb
   - psutil
   - openai
   - PyYAML（設定検証の YAML チェックに任意）
   - （その他プロジェクト固有の依存がある場合は requirements.txt を用意してください）

   例:
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb psutil openai PyYAML
   ```

3. .env の作成（推奨：対話ウィザードを使う）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは .env を生成します。生成後、必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を設定してください。

   自動読み込み:
   - 起動時に .env / .env.local を自動で読み込みます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

4. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告を厳格に扱う場合:
   python -m kabusys.validate_config --strict
   ```

5. 必要に応じて DB の初期化（監視 DB はスクリプト実行時に自動でテーブル作成されますが、手動確認可能）
   - monitoring は run_* スクリプト起動時に init_monitoring_db が走り、テーブルを作成します。

---

## 使い方（起動 / 実行例）

- 実行ファイルはパッケージモジュールとして実行できます。

1. 監視ループ起動（run_monitoring）
   - デフォルトのポーリング間隔: 60 秒
   - 環境変数で上書き: MONITOR_POLL_INTERVAL（秒。1 以上）
   - 実行:
     ```
     python -m kabusys.run_monitoring
     ```
   - 停止:
     - プロセスに Ctrl+C（KeyboardInterrupt）
     - またはプロジェクトルートの data/stop_requested.flag を作成（監視ループはフラグを検知して終了）

2. エンジン起動（ExecutionEngine — run_execution）
   - Paper trading モード（KABUSYS_ENV=paper_trading）の場合は MockBrokerClient を使用し、データは data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）に記録されます（本番 DB と分離）。
   - 実行:
     ```
     python -m kabusys.run_execution
     ```
   - 停止:
     - data/stop_requested.flag を作成すると起動中の実行エンジンが検知して停止します。
     - 実行中は data/execution.pid を生成します。

3. .env 関連（主な環境変数）
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
   - PAPER_FILL_MODE: instant | partial | never | reject （ペーパートレードの約定動作）
   - OPENAI_API_KEY: LLM を使う機能で必須
   - LOG_LEVEL, LOG_DIR など

4. Paper Trading 検証レポート
   - tools/paper_verification_report.py を利用してペーパートレード DB の統計を出力できます。
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   # DB パスを明示する場合:
   python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
   ```

5. AI / LLM 機能
   - news_nlp.score_news, regime_detector.score_regime 等は OpenAI API を呼び出します。OPENAI_API_KEY を設定してください。
   - LLM 呼び出しは失敗時にフォールバックやリトライロジックを備えていますが、APIキー未設定の場合は例外になります。

---

## 運用上の注意 / オペレーション

- Kill Switch:
  - KillSwitch は監視結果に基づき data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送信します（Execution 側は kill.flag をチェックして停止処理を行う想定）。
  - 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨（自動クリアは危険）。
- ログ:
  - ログは標準出力（stdout）とファイル出力（logs/<app_name>.log、日次ローテート・30 日保持）に出力されます。
  - logging は kabusys.utils.logging_setup.setup_logging を各起動スクリプトで呼び出して統一管理しています。
- プロセス優先度:
  - run_execution / run_monitoring 起動時に set_process_priority("high") が呼ばれます。権限によっては設定できない場合があります（警告ログ）。
- DB 分離:
  - Paper trading 用 SQLite は paper_sqlite_path に分離されます。production の監視 DB（SQLITE_PATH）と混同しないでください。
- 環境の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動読み込みします。無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## 主要ファイル / ディレクトリ構成

（抜粋。src/kabusys 以下の主なファイルを列挙）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings クラス（.env 自動読み込み含む）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI 経由のセンチメント）
    - regime_detector.py     — 市場レジーム判定（LLM + ma200）
  - portfolio/
    - portfolio_builder.py   — 銘柄選定・重み計算
    - position_sizing.py     — 発注株数決定・スケーリング・単元丸め
    - risk_adjustment.py     — セクター制約・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py     — モメンタム/ボラ/バリュー計算（DuckDB 使用）
    - feature_exploration.py — IC / 将来リターン / 統計
    - __init__.py
  - monitoring/
    - monitoring_db.py       — SQLite テーブル定義と DB 操作ラッパ
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （抜粋外）取引監視（滞留注文等）
    - risk_monitor.py        — ドローダウン / ポジション制限監視
    - monitoring_engine.py   — 各 Monitor を束ねるループ
    - kill_switch.py         — kill.flag 書込みユーティリティ
    - alert_manager.py       — （抜粋外）通知管理
  - execution/
    - execution_engine.py    — ExecutionEngine 本体（抜粋外）
    - broker_factory.py      — BrokerClientFactory（抜粋外）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
    - __init__.py

- データ / ランタイムファイル（プロジェクトルート想定）
  - data/kabusys.duckdb (デフォルト DUCKDB_PATH: data/kabusys.duckdb)
  - data/monitoring.db (デフォルト SQLITE_PATH)
  - data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - data/kill.flag
  - data/stop_requested.flag
  - data/execution.pid
  - logs/<app_name>.log

---

## よくある操作例（まとめ）

- .env を作る（ウィザード）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視をデフォルト間隔で起動
  ```
  python -m kabusys.run_monitoring
  ```

- 監視のポーリング間隔を 30 秒に変更して起動
  ```
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- エンジンを起動（ペーパートレードは .env で KABUSYS_ENV=paper_trading に）
  ```
  python -m kabusys.run_execution
  ```

- Paper Trading レポート出力
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

## 注意事項 / 補足

- 本 README はコード抜粋を基に作成しています。実際の運用では execution・trade_monitor・alert_manager 等の実装や Broker クライアント、依存パッケージのバージョンを確認してください。
- OpenAI を利用する機能は API コストとレイテンシに注意して運用してください。APIキーは適切に保護してください。
- 本番運用（KABUSYS_ENV=live）の場合は特に kill flag やログ設定、LINE 通知などの設定を十分確認してください（validate_config が補助します）。

---

必要であれば、README にさらに次の情報を追加できます：
- requirements.txt の内容
- CI / デプロイ手順（systemd / Docker など）
- サンプル .env.example
- 各モジュールの API 使用例（関数レベル）  

追加希望があれば教えてください。