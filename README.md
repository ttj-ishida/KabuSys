# KabuSys — README

日本株自動売買システム KabuSys のコードベース README です。本リポジトリはトレード実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュース NLP）などを含むモジュール群で構成されています。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の主要機能を提供するモジュール群です。

- 発注エンジン（ExecutionEngine）: ブローカーとのやり取り、注文管理、リスク管理、注文再整合などを行う。
- 監視（Monitoring）: システム状態 / 注文状態 / リスクを定期的にチェックし、必要に応じてアラートや Kill Switch を発動する。
- ポートフォリオ構築（Portfolio）: 候補選択・重み計算・ポジションサイズ計算・セクター制限など純粋関数群。
- リサーチ（Research）: DuckDB の日次株価等データからファクター計算、将来リターンや IC 計算、統計サマリーを提供。
- AI（ニュース NLP / レジーム判定）: OpenAI を用いたニュースのセンチメント評価や市場レジーム判定。
- ユーティリティ: ロギング設定、プロセス優先度設定、.env ウィザード、設定検証ツールなど。

---

## 主な機能一覧

- Execution:
  - 発注・注文管理（OrderManager / OrderRepository）
  - リスク管理（RiskManager）
  - 発注整合（Reconciler）
  - Paper Trading と Live の DB 分離（PAPER_TRADING_SQLITE_PATH）
- Monitoring:
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス存在、データ鮮度監視
  - TradeMonitor: 注文滞留・異常約定検出（実装参照）
  - RiskMonitor: ドローダウン・ポジション上限監視（Kill Switch のトリガー）
  - MonitoringEngine: 各 Monitor を束ねたポーリングループ
- Portfolio:
  - 候補選定、等配分・スコア加重、リスクベースのポジションサイズ計算
  - セクターキャップ、レジーム乗数
- Research:
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI:
  - ニュース記事を LLM で評価し ai_scores に書き込む（news_nlp）
  - ETF MA + マクロニュースで市場レジーム判定（regime_detector）
- ツール:
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
- ユーティリティ:
  - 統一ロギング（logs/、日次ローテーション）
  - プロセス優先度 / CPU affinity 設定

---

## セットアップ手順

前提:
- Python 3.9+（コードは型ヒント・標準ライブラリの挙動に依存）
- ネットワーク接続（OpenAI を使う場合）
- システムにより追加ネイティブ依存（psutil など）

1. リポジトリをクローン / ワークディレクトリへ移動

2. 仮想環境を作成・有効化（推奨）
   - venv 例:
     ```
     python -m venv .venv
     source .venv/bin/activate  # Unix/macOS
     .venv\Scripts\activate     # Windows
     ```

3. 必要なパッケージをインストール
   - 依存ファイルがない場合は少なくとも下記を入れてください:
     ```
     pip install duckdb psutil openai
     ```
   - 開発や YAML 検証のために PyYAML を入れると validate_config の YAML 検証が動作します:
     ```
     pip install pyyaml
     ```

4. 環境変数 / .env を用意
   - リポジトリルートに `.env` を作成するか、ウィザードを使用して作成します（下記参照）。
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - OpenAI を使う機能を利用する場合: OPENAI_API_KEY を設定

5. データディレクトリを作成（必要に応じて）
   ```
   mkdir -p data logs
   ```

---

## .env 作成・検証

- 対話式ウィザードで .env を作成:
  ```
  python -m kabusys.config_setup
  ```
  引数:
  - --env-file でファイルパスを指定可能

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```
  警告をエラー扱いにする場合:
  ```
  python -m kabusys.validate_config --strict
  ```

主要な環境変数（一部、デフォルトを含む）:

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意 / デフォルト:
  - KABUSYS_ENV: development | paper_trading | live  （default: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: INFO
  - OPENAI_API_KEY: OpenAI を使う場合に必要
  - PAPER_FILL_MODE: instant | partial | never | reject （paper_trading の注文応答動作）
  - KILL_FLAG_CLEAR_ON_START: 0 | 1（本番では 0 推奨）

例（.env の抜粋）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
OPENAI_API_KEY=sk-...
LOG_LEVEL=INFO
```

---

## 使い方（主なコマンド）

- 実行エンジン起動（ExecutionEngine）
  - 本番/紙/開発の挙動は KABUSYS_ENV に依存します。paper_trading の場合は MockBroker を利用して data/paper_trading.db に記録します。
  ```
  python -m kabusys.run_execution
  ```

- 監視ループ起動（SystemMonitor のポーリング）
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト: 60）
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  デフォルト DB は `data/paper_trading.db`。`--db PATH` で上書き可。

- AI スコアリング（プログラムから呼ぶ）
  - OpenAI API キーが必要です（api_key 引数または環境変数 OPENAI_API_KEY）。
  - 例（Python から）:
    ```py
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    from datetime import date
    score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```

ログ:
- デフォルトで logs/<app_name>.log へ日次ローテーション保存（30日保持）。`kabusys.utils.logging_setup.setup_logging` が設定を行います。

停止フラグ / Kill Switch:
- 監視 / 実行エンジンは `data/stop_requested.flag` / `data/kill.flag` / `data/execution.pid` 等のファイルでプロセス制御を行います。KillSwitch がトリガー条件（ドローダウンやポジション上限）を満たすと `data/kill.flag` を書き込み、ExecutionEngine 側でこれを検知して停止する仕組みです。

---

## 重要な挙動メモ

- Monitoring は常に production の sqlite_path を使用します（KABUSYS_ENV に依存せず監視 DB を共有稼働させる方針）。
- ExecutionEngine は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を使用して本番 DB と完全に分離します。
- Paper Trading の注文挙動は PAPER_FILL_MODE（instant|partial|never|reject）で制御できます。
- OpenAI 関連機能は API レート制限や一時エラーに対して指数バックオフでリトライし、重度の失敗時にはフェイルセーフ（スコア 0 等）で継続する設計です。
- .env の自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます（テスト用）。

---

## ディレクトリ構成（抜粋）

以下は主要なモジュールのディレクトリ構成（`src/kabusys` 配下）です。実際のルートはプロジェクトの `src/` 配下に配置されています。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理、.env 自動ロード
  - config_setup.py              — .env 対話ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py           — ログ設定ユーティリティ
    - process_priority.py        — プロセス優先度/Cpu affinity
  - execution/                    — 実行関連（BrokerFactory, ExecutionEngine, OrderManager 等）
  - monitoring/
    - monitoring_db.py           — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py
    - monitoring_engine.py
    - kill_switch.py
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
  - tools/
    - paper_verification_report.py

その他:
- data/              — データファイル（SQLite、flag、pid など）
- logs/              — ログ出力先（デフォルト）

---

## 開発者向けメモ

- DuckDB 接続は多数のリサーチモジュールで使われます。prices_daily / raw_financials / raw_news 等のテーブルを前提にしているため、適切なデータ投入が必要です。
- MonitoringDB の初期化（init_monitoring_db）は冪等に実装されており、既存カラムのマイグレーション処理も含まれます。
- ロギングは全アプリケーションで共通のフォーマット・ローテーションを使用しているため、全起動スクリプトは `setup_logging(app_name=...)` を呼ぶことを推奨します。
- psutil に関連する処理は権限によって失敗する場合があるため、警告ログを出して処理をスキップする安全策が組み込まれています。

---

## ライセンス / 貢献

（この README にはライセンス情報は含めていません。リポジトリの LICENSE ファイルを参照してください。）

---

不明点や README の追加要望（例: 必須依存パッケージの正確な一覧、デプロイ手順、CI 設定、テスト方法など）があれば教えてください。README をその内容に合わせて拡張します。