# KabuSys

日本株向け自動売買システムのコードベース。戦略・ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、AI を使ったニュースセンチメント評価、研究用ファクター計算などを含むモジュール群です。

バージョン: 0.1.0

---

## 概要

KabuSys は、取引戦略からポジションサイズ計算、注文管理、監視・アラート、テスト用のペーパートレード分離など、実運用を意識した構成の自動売買システムです。設計方針として以下を重視しています。

- 環境変数ベースで設定を管理（.env をサポート）
- 本番/ペーパーの DB 分離（ペーパートレード時は別 SQLite を使用）
- 監視用コンポーネントで安全停止（Kill Switch）やリスク監視を実装
- DuckDB を用いた研究／ファクター計算
- OpenAI（gpt-4o-mini 等）を用いたニュース NLP / レジーム判定（オプション）
- ロギングは統一的に設定（Console + 日次ローテートファイル）

---

## 主な機能一覧

- 実行（Execution）
  - BrokerClientFactory によるブローカークライアント抽象化（paper_trading ではモックを使用）
  - OrderManager / OrderRepository / Reconciler / RiskManager / ExecutionEngine
  - PID ファイルと停止フラグによる制御

- 監視（Monitoring）
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / プロセス生存監視
  - TradeMonitor: 注文滞留や約定異常検出
  - RiskMonitor: ドローダウン・ポジション上限の監視
  - KillSwitch と AlertManager による自動停止および通知
  - monitoring DB（SQLite）への永続化

- ポートフォリオ構築（Portfolio）
  - 候補選定、等重／スコア加重配分、リスクベースの株数決定
  - セクターキャップ、レジーム乗数の適用

- 研究（Research）
  - DuckDB ベースでのファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC 計算、統計サマリ等

- AI（任意）
  - ニュースのセンチメントを LLM で評価し ai_scores に書き込み
  - マクロ + MA200 比率で市場レジーム判定（LLM を併用）

- ツール
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成スクリプト

---

## セットアップ手順

前提:
- Python 3.10 以上（PEP 604 の `X | Y` 型注釈を使用）
- git リポジトリのルートに配置されている想定

1. リポジトリをチェックアウトする

   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成（推奨）

   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール

   主要な依存パッケージ例:
   - duckdb
   - psutil
   - openai (AI 機能を使う場合)
   - PyYAML（config の検証を行う場合）

   pip でインストール例:

   ```
   pip install duckdb psutil openai PyYAML
   ```

   （プロジェクトに requirements.txt がある場合はそれを使ってください）

4. 環境変数（.env）の作成

   対話ウィザードで .env を生成できます:

   ```
   python -m kabusys.config_setup
   ```

   生成後、設定検証を行います:

   ```
   python -m kabusys.validate_config
   ```

   validate_config は `--strict` を付けると警告も失敗扱いになります。

5. ログディレクトリ / data ディレクトリの作成（自動で作られますが手動でも可）

   ```
   mkdir -p logs data
   ```

---

## 主要環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

運用 / 動作制御:
- KABUSYS_ENV — 実行環境: development | paper_trading | live （default: development）
- LOG_LEVEL — ログレベル（default: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 時のみ使用）
- OPENAI_API_KEY — OpenAI API を使う場合に必須
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒, default: 60）

停止制御 / PID:
- PID_FILE_PATH / KILL_FLAG_PATH — デフォルトは data 配下のファイルパス

例（.env の最小例）:

```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

注意: .env は絶対にバージョン管理にコミットしないでください。

---

## 使い方

主なコマンド / 実行スクリプト

- 実行エンジンの起動（本番 / ペーパー両対応）

  ```
  python -m kabusys.run_execution
  ```

  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使われ、データは PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に保存されます。
  - 実行中は PID ファイル（data/execution.pid）を作成します。
  - 停止は data/stop_requested.flag を作成するか、実行プロセスに SIGINT（Ctrl+C）を送ることで停止します。

- 監視ループ起動

  ```
  python -m kabusys.run_monitoring
  ```

  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可能（デフォルト: 60）。
  - 監視は常に本番用 sqlite_path を使って記録します（環境に依らず monitoring DB を使用）。
  - 監視ループも data/stop_requested.flag により終了できます。

- 設定ウィザード（.env 作成）

  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）

  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート生成

  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db --from 2026-04-01 --to 2026-04-11
  ```

- AI 関連（Python API として利用）
  - ニューススコアリング:

    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026, 4, 10), api_key="YOUR_OPENAI_KEY")
    ```

  - レジームスコア:

    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 4, 10), api_key="YOUR_OPENAI_KEY")
    ```

注意点:
- AI 機能を利用するには OPENAI_API_KEY を設定する必要があります。
- AI 呼び出しは外部 API の失敗に備えたリトライとフォールバックを備えていますが、API 利用料が発生します。

---

## 停止 / Kill Switch

- ExecutionEngine を外部から停止したい場合は監視側が data/kill.flag を書き込む仕組み（KillSwitch）を持っています。run_execution は起動時に kill flag を確認し、存在すれば起動しません。
- 手動で強制停止したい場合は data/stop_requested.flag を作成してください（run_execution / run_monitoring の両方がチェックしています）。

例:

```
# 停止リクエストを出す
mkdir -p data
echo "stop" > data/stop_requested.flag

# kill flag を手動でセット（Execution 停止シグナル）
echo "Reason for kill" > data/kill.flag
```

---

## ディレクトリ構成（主要ファイル）

プロジェクトルートの `src/kabusys` を起点に主要モジュール:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動ロード / Settings クラス
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - risk_manager.py
    - reconciler.py
    - broker_factory.py
    - ...（ブローカー抽象や Mock 実装）

  - monitoring/
    - monitoring_db.py        — SQLite テーブル初期化 + CRUD ヘルパ
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
    - news_nlp.py
    - regime_detector.py

  - utils/
    - logging_setup.py        — 共通ログ設定（Console + 日次ファイル）
    - process_priority.py     — プロセス優先度 / CPU affinity 設定

  - tools/
    - paper_verification_report.py

- その他:
  - data/                    — デフォルト DB / PID / flag の保存先（実行時に作成）
  - logs/                    — ログファイル出力先（設定で変更可）
  - config/                  — 各種 yaml 設定テンプレート（system_config.yaml 等）

---

## 開発・運用のヒント

- 設定の検証は必ず行ってください（validate_config）。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨します。validate_config は live の場合に追加警告を出します。
- ローカルでの検証は paper_trading モードで行い、PAPER_TRADING_SQLITE_PATH に記録される DB を解析してください。
- DuckDB を使った研究モジュール（research）は本番 DB にアクセスしませんが、prices_daily / raw_financials 等のテーブルが必要です。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。

---

## ライセンス / 責任範囲

本 README はコードベースの説明を目的としています。自動売買はリスクを伴います。実運用の前に十分な検証・監査を行ってください。

---

必要であれば、README に含める具体的な .env.example や system_config.yaml テンプレート、運用手順（サービス化 / systemd / Supervisor など）も作成します。どの情報を追加したいか教えてください。