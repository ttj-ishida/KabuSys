# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買システム「KabuSys」の実装です。バックテスト・銘柄選定・ポジションサイズ算出・発注エンジン・監視・AI を用いたニューススコアリングなどの主要機能を含みます。

---

## プロジェクト概要

KabuSys は以下のような責務を持ちます。

- ファクター計算・特徴量探索（research）
- ポートフォリオ構築（portfolio）
- 発注ロジック・発注エンジン（execution）
- 監視・アラート・Kill Switch（monitoring）
- ニュース NLP によるセンチメントスコア生成（ai）
- 運用支援ツール（config ウィザード、設定検証、ペーパートレード検証レポート）
- DuckDB（分析用）と SQLite（監視 / ペーパートレード用）を併用

設計上のポイント：
- 本番とペーパートレードを明確に分離（KABUSYS_ENV により挙動切替）
- LLM 呼び出しは失敗時にフォールバックするフェイルセーフ設計
- ロギング・プロセス優先度・PID / フラグファイルによる起動/停止制御

---

## 主な機能一覧

- research:
  - momentum, volatility, value 等のファクター計算（DuckDB を利用）
  - 将来リターン・IC（情報係数）計算、ファクター統計
- portfolio:
  - 候補選定、等配分／スコア加重、リスク調整（セクター上限）
  - ポジションサイズの計算（単元株丸め、aggregate cap）
- execution:
  - 発注エンジン（実ブローカー or MockBroker によるペーパートレード）
  - リスク管理（制限・レートリミット等）
- monitoring:
  - システム状態監視（CPU/メモリ/ディスク、データ鮮度）
  - トレード監視（滞留注文、約定異常など）
  - リスク監視（ドローダウン、ポジション上限）
  - Kill Switch（条件で data/kill.flag を書き込み ExecutionEngine を停止）
- ai:
  - ニュースを LLM（OpenAI）で評価し銘柄ごとの ai_scores を作成
  - マクロニュースと ETF MA に基づく市場レジーム判定（bull/neutral/bear）
- ツール:
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成（tools.paper_verification_report）

---

## セットアップ手順（開発者向け）

前提: Python 3.9+ を想定（DuckDB / psutil 等の依存あり）。

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（例）
   ```bash
   pip install duckdb psutil openai PyYAML
   ```
   - PyYAML は `validate_config` の YAML 検証に利用（必須ではない）。
   - OpenAI SDK は ai モジュール使用時に必要。
   - 実行環境に応じて追加パッケージが必要になる可能性があります。

4. 環境変数（.env）を用意
   - 対話式ウィザードで生成可能：
     ```bash
     python -m kabusys.config_setup
     ```
   - 手動で `.env` を作る場合（代表的な項目）:
     ```
     KABUSYS_ENV=development           # development | paper_trading | live
     JQUANTS_REFRESH_TOKEN=your_token
     KABU_API_PASSWORD=your_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     KILL_FLAG_CLEAR_ON_START=0
     ```
   - ペーパートレード用 DB を使用する場合:
     - KABUSYS_ENV=paper_trading に設定すると、Execution は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用します。

5. 設定検証（任意）
   ```bash
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict
   ```

---

## 実行・使い方

起動スクリプトはモジュールとして呼び出します（推奨）。各スクリプトはプロセス優先度を "high" に設定し、ログを出力します。

- ExecutionEngine を起動（本番 or paper_trading に応じて DB を切り替え）
  ```bash
  python -m kabusys.run_execution
  ```
  - 起動時に data/execution.pid が使用されます。
  - 既に data/stop_requested.flag が存在する場合は起動を行わず終了します。
  - 終了（停止）させたい場合は監視側から kill.flag を書き込むか、手動で engine.stop() を呼ぶ手段で行います（運用手順に従ってください）。

- Monitoring を起動（定期的に SystemMonitor を回す）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で秒数を上書きできます。
    - 例: `MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring`
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存せず常に sqlite_path）。
  - 停止はプロジェクトルート/data/stop_requested.flag を作成するとループが検知して終了します。

- ペーパートレード検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB は引数 `--db`、または環境変数 PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）。

- AI（ニューススコアリング / レジーム判定）
  - OpenAI API キーを環境変数に設定: `OPENAI_API_KEY=sk-...`
  - ニューススコアリング（プログラムから呼ぶ例）:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    count = score_news(conn, date(2026, 4, 10), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
    ```
  - レジーム判定:
    ```python
    from datetime import date
    from kabusys.ai.regime_detector import score_regime
    # duckdb接続を渡して score_regime を呼ぶ
    ```

---

## フラグ / PID / ログの取り扱い

- ファイル:
  - logs/<app_name>.log — 日次ローテーションでログ出力（logs ディレクトリ）
  - data/kill.flag — Kill Switch が発動した理由を文字列として書き込み（ExecutionEngine に停止シグナル）
  - data/stop_requested.flag — run_monitoring/run_execution が検知してプロセスを停止するためのフラグ
  - data/execution.pid — ExecutionEngine の PID ファイル（起動管理に使用）
- ログレベル:
  - 環境変数 LOG_LEVEL（例: DEBUG/INFO/WARNING/ERROR）で制御
- その他:
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）

---

## 主要な環境変数（抜粋・デフォルト）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL (default: INFO)
- OPENAI_API_KEY — OpenAI を利用する場合に必須
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする (0/1)

設定ファイルと項目は `src/kabusys/config_setup.py` に詳細が記載されています。ウィザードで安全に .env を生成できます。

---

## ディレクトリ構成

概略（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py          (存在するモジュールに依存)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py          (存在するモジュールに依存)
  - execution/                 (発注関連モジュール群)
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py

プロジェクトルート（例）:
- data/                      — データベース / フラグファイルを配置（自動作成されることが多い）
- logs/                      — ログファイル
- src/
  - kabusys/...
- pyproject.toml / .git / README.md

（上記は主要ファイルの抜粋です。実際のファイル構成はリポジトリを参照してください。）

---

## 開発・運用での注意点

- 本番環境（KABUSYS_ENV=live）では kill.flag の自動クリア設定（KILL_FLAG_CLEAR_ON_START=1）は危険です。0 を推奨します。
- OpenAI を利用する機能は API キーとコストが発生します。失敗時はフォールバックする設計ですが利用方針を明確にしてください。
- run_monitoring は監視用 DB（SQLITE_PATH）を参照します。Monitoring は環境にかかわらず本番 sqlite_path を使用します。
- ペーパートレードは paper_trading 専用 DB（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と分離されます。
- ログディレクトリの作成に失敗するとファイル出力は無効化され、コンソール出力のみになります（setup_logging の仕様）。

---

## よく使うコマンドまとめ

- 環境設定ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```
- Execution 起動:
  ```bash
  python -m kabusys.run_execution
  ```
- Monitoring 起動:
  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- Paper Trading レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

もし README の内容に追加したい項目（例: 実行フロー図、設定ファイルのテンプレート、CI/CD 手順、ユニットテストの実行方法）があれば教えてください。必要に応じて追記します。