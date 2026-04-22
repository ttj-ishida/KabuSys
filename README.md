# KabuSys

日本株向け自動売買システムのコードベース。アルゴリズムによる銘柄選定・配分・発注、監視・リスク管理、Paper Trading 用検証ツール、AI を使ったニュース／レジーム判定などの機能を含みます。

バージョン: 0.1.0

---

## 概要（Project overview）

KabuSys は以下の主要機能で構成されたディスクロージャレイヤー + アプリケーションレイヤー群です。

- 戦略／ポートフォリオ構築（ファクター計算、候補選定、重み計算、ポジションサイズ算出）
- ExecutionEngine（発注周り：ブローカー抽象化、注文管理、リスク管理、整合処理）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine、Kill Switch）
- Paper Trading（環境分離された SQLite に発注ログを残すモード）
- AI 統合（OpenAI を用いたニュースセンチメント / 市場レジーム判定）
- 分析ツール（DuckDB を用いたファクター計算、検証レポート作成）
- 環境設定ユーティリティ（.env ウィザード・設定検証）

設計方針としては「本番と Paper Trading を明確に分離」「外部 API 呼び出しは明示的に行う」「DB パスやログ設定は環境変数で制御」となっています。

---

## 機能一覧（Features）

- 環境管理
  - .env ウィザード（kabusys.config_setup）
  - 起動前設定検証（kabusys.validate_config）
  - 環境自動読み込み（.env / .env.local、OS 環境変数優先。無効化可）
- 実行エンジン
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Paper Trading 時は MockBroker と分離 DB（data/paper_trading.db）
  - プロセス優先度設定（高優先度で起動）
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor を統合する MonitoringEngine
  - 監視ループ起動スクリプト（run_monitoring.py）
  - Kill Switch（データ/ルールに応じて data/kill.flag を書込）
  - 監視ログは SQLite（data/monitoring.db）、分析は DuckDB（data/kabusys.duckdb）
- ポートフォリオ構築
  - 候補選定、等金額／スコア加重、リスクベース配分、セクター上限適用、レジーム乗数
- 研究・分析
  - ファクター計算（momentum, volatility, value）
  - 将来リターン・IC 計算・統計サマリ
- AI（OpenAI）
  - ニュースセンチメント（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
  - リトライ・JSON 検証やサニティチェック実装
- ツール
  - Paper Trading 検証レポート生成（tools.paper_verification_report）

---

## 必要条件 / 依存（Requirements）

最低限の Python パッケージ（抜粋）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML （config/*.yaml の構文チェックを行う場合は任意）

インストール例（仮の requirements）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（実際の requirements.txt があればそれを利用してください）

---

## セットアップ手順（Setup）

1. リポジトリをクローンする:
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して依存をインストール:
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb psutil openai pyyaml
   ```

3. .env の初期作成:
   - 対話式ウィザードを使って .env を作成できます。
     ```
     python -m kabusys.config_setup
     ```
   - 生成される主なキー（.env の例）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
     - KABUSYS_ENV（development | paper_trading | live）
     - LOG_LEVEL（DEBUG/INFO/...）
     - KILL_FLAG_CLEAR_ON_START（0/1）

4. 設定検証（起動前に推奨）:
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict
   ```

5. ログディレクトリ／データディレクトリ:
   - デフォルトで `logs/` と `data/` を使用します。必要に応じて環境変数 LOG_DIR, DUCKDB_PATH, SQLITE_PATH 等で変更できます。
   - ログは `logs/<app_name>.log` に日次ローテートで保存されます。

---

## 使い方（Usage）

環境（KABUSYS_ENV）により挙動が変わります:
- development: ローカル開発・テスト用（発注なし）
- paper_trading: 模擬発注（MockBroker）・Paper Trading 用 SQLite を使用（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）
- live: 本番発注（kabuステーションを使う）

主要な実行コマンド:

- ExecutionEngine 起動（本番/ペーパートレード共通、Settings に基づいて DB を切替）
  ```
  python -m kabusys.run_execution
  ```
  - 実行時に `data/stop_requested.flag` が存在すると起動をスキップします。
  - プロセス PID は `data/execution.pid` に保存されます。
  - Paper Trading の場合は settings.is_paper が True になり専用 DB（data/paper_trading.db）を使用します。

- Monitoring 起動（システム監視ループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は常に本番用の sqlite_path（デフォルト data/monitoring.db）を使用します。
  - 停止フラグ `data/stop_requested.flag` を検知するとループを終了します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # --db オプションで DB パスを指定可能
  ```

- AI 機能（プログラムから呼び出す）
  - ニューススコア付け:
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,1), api_key="YOUR_OPENAI_KEY")
    ```
  - レジーム判定:
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,4,1), api_key="YOUR_OPENAI_KEY")
    ```

ログ／フラグ関連:
- Kill Switch 書込先: デフォルト `data/kill.flag`（Settings.kill_flag_path）
- Execution 停止フラグ: `data/stop_requested.flag`
- Execution PID: `data/execution.pid`
- 監視ログ DB: デフォルト `data/monitoring.db`
- DuckDB: デフォルト `data/kabusys.duckdb`

環境変数の主な例:
- KABUSYS_ENV=paper_trading
- MONITOR_POLL_INTERVAL=30
- PAPER_FILL_MODE=instant|partial|never|reject
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- OPENAI_API_KEY=xxx

注意:
- 本番（KABUSYS_ENV=live）では LINE 通知トークンなどの設定が重要です（validate_config でチェック）。
- KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリアしますが、本番では危険なので 0 を推奨します。

---

## ディレクトリ構成（Directory structure）

主要ファイル/サブパッケージ（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings 管理（.env 自動読み込みロジック含む）
  - config_setup.py         — .env 対話ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py         (実装あり)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py         (実装あり)
  - execution/
    - execution_engine.py     (実装あり)
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/                    — 実行時に使う場所（logs/, DB ファイル, flags）

（上記は主なファイル。詳細はリポジトリの src/kabusys 配下を参照してください）

---

## 開発・運用時の注意（Notes）

- .env の自動読み込みはデフォルトで有効。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト環境向け）。
- .env は決して Git にコミットしないでください（config_setup がヘッダで警告します）。
- Monitoring は監視ログ用 SQLite（monitoring.db）に常に書き込みます。実行環境を問わず同じ sqlite_path を使用する設計になっている箇所があるため本番 DB の扱いには注意してください（run_monitoring のドキュメント参照）。
- Paper Trading 用 DB は Paper Trading モード時に別ファイルに切り分けられます（PAPER_TRADING_SQLITE_PATH）。
- AI 機能を使う場合は OpenAI API キーが必要です。API 呼び出しはリトライやレスポンス検証を行う実装になっていますが、呼出回数・料金に注意してください。
- ログは stdout とファイルに両出力されます。ログディレクトリ書込に失敗するとファイル出力は無効化されますが、コンソール出力は継続します。

---

この README はコード内のコメントやエントリポイント（run_execution.py, run_monitoring.py, config_setup.py, validate_config.py, tools.paper_verification_report.py 等）を基にまとめています。追加の実行フローや詳細は各モジュールの docstring / 関数ドキュメントを参照してください。