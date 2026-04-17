# KabuSys

バージョン: 0.1.0

日本株向けの自動売買システムのコアライブラリです。発注エンジン、監視・アラート、ポートフォリオ構築、研究用ファクター計算、AI を用いたニュースセンチメント評価など、実運用を意識したコンポーネント群を含みます。

主な設計方針
- 本番データとペーパートレード（テスト）を明確に分離（DB 等）
- ルックアヘッドバイアス回避（時刻参照の扱いに注意）
- フェイルセーフ（API 失敗時も安全にフォールバック）
- 単体関数は副作用を持たない設計を意識（研究・ポートフォリオ計算等）

---

## 機能一覧

- Execution（発注系）
  - ExecutionEngine を起動してブローカーへの注文実行（本番 / ペーパートレード）
  - BrokerClientFactory による本番/モックの切り替え
  - OrderRepository / OrderManager / RiskManager / Reconciler 等

- Monitoring（監視系）
  - SystemMonitor: プロセス生存、CPU/メモリ/ディスク、データ鮮度を監視
  - TradeMonitor: 注文滞留・約定価格異常を検出
  - RiskMonitor: ドローダウンやポジション上限の監視・アラート記録
  - MonitoringEngine: 上記をまとめてポーリング、Kill Switch 評価・LINE 通知（AlertManager）

- Portfolio（ポートフォリオ構築）
  - 候補選定、等配分/スコア加重、セクター制限、ポジションサイズ計算（単元株丸め等）

- Research（調査/ファクター）
  - momentum / volatility / value ファクター計算（DuckDB ベース）
  - 将来リターン計算、IC 計算、ファクター統計サマリー

- AI（LLM を用いた補助）
  - news_nlp: ニュースを集約して OpenAI でセンチメント評価→ai_scores へ書き込み
  - regime_detector: MA200 とマクロニュースを組み合わせて市場レジーム判定

- Tools
  - paper_verification_report: ペーパートレード DB から検証レポートを生成

- 設定 / ユーティリティ
  - config_setup: .env 作成ウィザード（対話式）
  - validate_config: 環境変数 / config/*.yaml の事前検証 CLI
  - process_priority: プロセス優先度・CPU affinity ユーティリティ

---

## セットアップ手順

前提: Python 3.9+（プロジェクトの Python バージョン要件に合わせてください）

1. リポジトリをクローンし、ワークディレクトリを移動
   - git clone <repo>
   - cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil requests openai
   - 任意: PyYAML（config の YAML 検証を行う場合）
     - pip install PyYAML

   （requirements.txt がない場合は上記の主要パッケージをインストールしてください）

4. データディレクトリ作成
   - mkdir -p data

5. 初期 .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードで必要な環境変数を入力して .env を生成します。

6. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - すべて OK なら問題なし。`--strict` を付けると警告もエラー扱いになります。

7. （任意）DuckDB / SQLite の初期化は各起動スクリプトが冪等に行います（init_monitoring_db）。データベースファイルが存在しない場合は自動生成されます。

注意:
- OpenAI を用いる機能（news_nlp, regime_detector）を使う場合は環境変数 OPENAI_API_KEY を設定してください。
- psutil によるプロセス優先度設定は権限が必要な場合があります（Linux の nice 値や Windows の優先度）。

---

## 使い方

主要なエントリポイント（パッケージモードで実行）

- 監視ループ起動（Monitoring）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - python -m kabusys.run_monitoring

  備考:
  - run_monitoring は常に本番用の sqlite_path を使用して監視ログを記録します（KABUSYS_ENV に依存しない）。
  - 停止は data/stop_requested.flag を作成することで行えます（あるいは Ctrl+C）。

- 実行エンジン起動（Execution）
  - KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使用し、ペーパートレード用 DB（data/paper_trading.db 等）に記録します。
  - python -m kabusys.run_execution

  備考:
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中は data/execution.pid に PID が書かれます（run_execution が管理）。
  - Kill Switch（data/kill.flag）を監視して停止する仕組みがあります。

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- .env の対話式作成 / 更新
  - python -m kabusys.config_setup

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数が優先されます）

- 各モジュールのプログラム的利用例（Python REPL / スクリプト内）
  - AI ニューススコアを実行:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key="...")  ※ conn は duckdb.connect(...)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")
  - ファクター計算:
    - from kabusys.research import calc_momentum
    - records = calc_momentum(duckdb_conn, date(2026,4,1))

---

## 環境変数（主要）

下記は主要な環境変数とデフォルト値 / 説明です。正確な一覧は kabusys.config.Settings を参照してください。

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- OPENAI_API_KEY — OpenAI を使う機能で必要
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db) — 監視ログ
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — paper_trading 時の専用 DB
- PAPER_FILL_MODE (instant | partial | never | reject) — ペーパートレードの約定挙動
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — AlertManager（LINE 通知）
- LOG_LEVEL (DEBUG/INFO/...) — ログレベル
- KILL_FLAG_CLEAR_ON_START (0/1) — 起動時に kill.flag を自動クリアするか（本番は 0 推奨）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（デフォルト 60）

ファイルベースのフラグ / PID:
- data/kill.flag — Kill Switch（Kill をトリガする理由テキストが書き込まれる）
- data/stop_requested.flag — run_* スクリプトが検出すると安全に停止・起動スキップ
- data/execution.pid または settings.pid_file_path — 実行エンジン PID 管理

---

## 動作上の注意点 / 補足

- run_monitoring は監視ログとして sqlite を更新します。init_monitoring_db によるスキーマ作成・マイグレーションを行います。
- run_execution は紙上のペーパートレード時に完全に別 DB を使用するよう設計されています（本番 DB と分離）。
- OpenAI API 呼び出しはリトライ・バックオフを実装していますが、API キーやレート制限に注意してください。
- process_priority.set_process_priority を起動時に呼んでいます。権限により設定できないと警告でスキップされます。
- DuckDB 経由のファクター計算は prices_daily / raw_financials 等のテーブルを前提とします。データ準備が必要です。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                — 環境変数読み込み / Settings
- config_setup.py          — .env 対話ウィザード
- validate_config.py       — 設定検証 CLI
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
- run_execution.py         — ExecutionEngine 起動スクリプト

サブパッケージ:
- ai/
  - __init__.py
  - news_nlp.py            — ニュースを LLM でスコアリングして ai_scores へ書込
  - regime_detector.py     — マーケットレジーム判定
- monitoring/
  - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
- execution/
  - (execution 関連の実装: EngineConfig, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager, BrokerFactory 等)
  - run_execution.py を参照
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- monitoring_db, tools, utils, research, portfolio 等が含まれます
- tools/
  - paper_verification_report.py

data/（実行時に使用されるディレクトリ）
- monitoring.db（デフォルト）
- paper_trading.db（ペーパートレード用）
- kabusys.duckdb（デフォルトの DuckDB）
- kill.flag / stop_requested.flag / execution.pid

---

## よくある操作例

1. .env を作って設定を検証:
   - python -m kabusys.config_setup
   - python -m kabusys.validate_config

2. ペーパートレードでエンジン起動（KABUSYS_ENV=paper_trading）:
   - export KABUSYS_ENV=paper_trading
   - python -m kabusys.run_execution

3. 監視プロセスを起動（常駐）:
   - python -m kabusys.run_monitoring
   - 一時的なポーリング間隔変更:
     - MONITOR_POLL_INTERVAL=10 python -m kabusys.run_monitoring

4. Paper Trading レポート:
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はコードベースの主要機能と運用上の注意をまとめたものです。実際にデプロイ・運用する際は config/*.yaml（存在する場合）や環境ごとの運用手順書に従ってください。必要があれば、各モジュールの詳細ドキュメントや API 仕様の追加を支援します。