# KabuSys

日本株向け自動売買システムのリポジトリ（モジュール群の一部）。  
この README はリポジトリ内の主要スクリプト・モジュールの使い方、設定、ディレクトリ構成をまとめたものです。

注意: 実際の取引機能（本番発注）は外部サービス（kabuステーション 等）を操作します。  
本番運用時は設定や権限、テストを十分に行ってください。

---

## プロジェクト概要

KabuSys は以下の機能群を含む自動売買プラットフォーム設計を示す Python パッケージです。

- 市場データ（DuckDB）を用いたファクター計算・リサーチ（research）
- ポートフォリオ構築（候補選定・重み算出・株数算出）
- Execution Engine（発注管理・リスク管理・Reconciler 等）
- 監視（System / Trade / Risk の監視・アラート・Kill Switch）
- AI連携（OpenAI を用いたニュースセンチメント・レジーム判定）
- 運用ツール（.env ウィザード、設定検証、Paper Trading レポート生成 等）

設計方針として、データアクセスや外部 API 呼び出しを最小限に分離し、フェイルセーフや冪等性に配慮した実装がされています。

---

## 主な機能一覧

- 環境設定ウィザード（.env）の対話式作成: kabusys.config_setup.run_wizard / python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config
  - 必須環境変数チェック、config/*.yaml の存在・パースチェック（PyYAML 必要）
- ExecutionEngine 起動スクリプト: src/kabusys/run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading.db に完全分離して記録
  - 停止フラグ（data/stop_requested.flag や data/kill.flag）による制御、PID ファイル管理
- Monitoring 起動スクリプト: src/kabusys/run_monitoring.py
  - SystemMonitor・TradeMonitor・RiskMonitor のポーリングループ
  - MONITOR_POLL_INTERVAL でポーリング間隔上書き可（デフォルト 60 秒）
- 監視 DB（SQLite）永続化: monitoring_db.py（system_status / trade_logs / positions / risk_logs / dashboard）
- RiskMonitor / KillSwitch によるドローダウンやポジション上限チェックと自動キル（kill.flag 書き込み）
- AlertManager: LINE Messaging API 経由で通知（トークン未設定ならログのみ）
- Research: モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 接続で SQL 実行）
- AI モジュール:
  - kabusys.ai.news_nlp.score_news: raw_news を OpenAI でスコアリングし ai_scores に保存
  - kabusys.ai.regime_detector.score_regime: ETF ma200 とマクロ記事の LLM 評価を合成して市場レジーム判定
- 運用ツール:
  - kabusys.tools.paper_verification_report: ペーパートレード DB から検証レポートを生成

---

## セットアップ手順（開発環境）

※ プロジェクトに requirements.txt などは明示されていません。ここでは推奨パッケージを示します。

1. Python 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）

2. 必要パッケージのインストール（例）
   - pip install duckdb psutil openai requests
   - （設定検証で YAML を使う場合）pip install pyyaml

3. リポジトリルートに data ディレクトリを作成（なければ自動作成される箇所もありますが、明示的に作ると安全）
   - mkdir -p data

4. 環境変数設定（.env）
   - 推奨: python -m kabusys.config_setup を実行して対話的に .env を作成
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要なデフォルト値:
     - KABUSYS_ENV=development（選択肢: development / paper_trading / live）
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY（AI 機能を使う場合）

5. 設定検証
   - python -m kabusys.validate_config
   - すべて OK なら exit 0。警告を FAIL としたい場合は --strict を付与。

---

## 使い方（コマンド例）

- .env の作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（本番・ペーパートレード共有スクリプト）
  - python -m kabusys.run_execution
  - 動作中に停止したい場合: data/stop_requested.flag を作成するとスレッドが検知して停止します
  - 実行時の PID は data/execution.pid（設定で変更可）に書かれます
  - KABUSYS_ENV=paper_trading を設定すると paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring
  - stop には data/stop_requested.flag を使います（run_monitoring は本番 sqlite_path を参照）

- Paper Trading レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能の呼び出し（ライブラリ API）
  - news_nlp を使う:
    - from kabusys.ai import score_news
    - import duckdb, datetime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - count = score_news(conn, target_date=datetime.date(2026, 4, 1), api_key="YOUR_OPENAI_KEY")
  - regime_detector を使う:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date=datetime.date(2026,4,1), api_key="YOUR_OPENAI_KEY")
  - どちらも OPENAI_API_KEY 環境変数があれば api_key を省略できます。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- OPENAI_API_KEY: OpenAI を使う場合に必須
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動でクリアするか（0/1。production では 0 推奨）

---

## 運用上の注意

- Paper Trading と Live の DB は分離
  - run_execution は KABUSYS_ENV=paper_trading の場合、settings.paper_sqlite_path を使用します（本番 DB と分離）
- Kill Switch（data/kill.flag）
  - KillSwitch により条件を満たすと data/kill.flag に理由を書き込み、ExecutionEngine を停止する設計です
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag をクリアしますが、本番では危険（0 推奨）
- PID / stop フラグ
  - data/execution.pid に PID を書き込むことで run_monitoring がプロセス稼働を確認します。PID が死んでいる場合は stale PID として検知・削除されます
  - data/stop_requested.flag を作ると run_monitoring / run_execution のループが停止します（運用上の手動停止用）
- AI 呼び出しは料金・レート制限があるため、エラーハンドリングとリトライが組み込まれていますが、API キー管理・クォータに注意してください。
- 設定検証 CLI（validate_config）を常に運用前に実行し、警告・エラーを確認してください。

---

## ディレクトリ構成（主なファイル・モジュール説明）

src/kabusys/
- __init__.py
  - パッケージ定義（__version__ など）
- config.py
  - Settings クラス: 環境変数／.env ロード・検証ロジック
  - 自動 .env ロード（プロジェクトルートの .env / .env.local）
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前チェック CLI

- run_execution.py
  - ExecutionEngine 起動用スクリプト（PID / stop フラグ管理 / paper_trading 分離）

- run_monitoring.py
  - SystemMonitor ポーリング起動スクリプト（MONITOR_POLL_INTERVAL）

- monitoring/
  - monitoring_db.py: SQLite スキーマ初期化・永続化 API（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py: CPU/メモリ/ディスク/データ鮮度/実行プロセス監視
  - trade_monitor.py: 注文滞留・約定異常監視（OrderRepository 依存）
  - risk_monitor.py: ドローダウン・ポジション上限の監視と dashboard 書き換え
  - kill_switch.py: kill.flag 操作ロジック
  - alert_manager.py: LINE Push 通知（クールダウン管理）
  - monitoring_engine.py: 各 Monitor を束ねるエンジン

- execution/ (実装ファイルの参照のみ。コード省略)
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py 等

- portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 株数計算・制約処理
  - risk_adjustment.py: セクターキャップ・レジーム乗数

- research/
  - factor_research.py: モメンタム / ボラティリティ / バリュー係数計算（DuckDB）
  - feature_exploration.py: 将来リターン計算 / IC / 統計サマリ

- ai/
  - news_nlp.py: raw_news を OpenAI でスコアリングし ai_scores に保存
  - regime_detector.py: ma200 と LLM を合成して market_regime に書き込み

- tools/
  - paper_verification_report.py: Paper Trading DB の指標集計と Pass/Fail 判定レポート

- utils/
  - process_priority.py: プロセス優先度設定（Windows / POSIX 差分吸収）
  - ほかユーティリティ

data/
- デフォルトの DB 保存場所やフラグファイル等（例）
  - data/kabusys.duckdb (デフォルト)
  - data/monitoring.db (監視用 SQLite)
  - data/paper_trading.db (ペーパートレード用 SQLite)
  - data/kill.flag, data/stop_requested.flag, data/execution.pid

※ 上記はソースのデフォルトを反映しています。Settings クラスで経路を上書きできます。

---

## 開発者向け補足

- Settings クラスで valid な KABUSYS_ENV は development / paper_trading / live のみ。
- PAPER_FILL_MODE（ペーパートレードの約定挙動）は instant / partial / never / reject のいずれか。
- process_priority.set_process_priority を実行してプロセス優先度を上げる処理が run_* スクリプトの起動時に行われます。psutil による権限エラーは警告でスキップされます。
- monitoring_db.init_monitoring_db は冪等で、既存 DB に対するマイグレーション（カラム追加）も行います。
- DuckDB を直接操作するモジュール（research, ai 等）は DuckDB 接続オブジェクトを受け取る設計です。テスト時は in-memory やモック接続に差し替えやすくなっています。

---

## トラブルシューティング

- .env が自動読み込みされない場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定していないか確認
  - プロジェクトルートの特定は .git または pyproject.toml を基準に行います（配置場所に注意）
- OpenAI 呼び出しで 429 / タイムアウトが発生する場合:
  - レート制限に達している可能性があるため、リトライやバッチサイズを調整してください（news_nlp はバッチ 20／リトライ実装あり）
- monitoring/run_execution がすぐ終了する:
  - data/stop_requested.flag や data/kill.flag が存在していないか確認
  - KILL_FLAG_CLEAR_ON_START の設定により起動時に自動クリアされるかを確認

---

この README はコードベースの主要点をカバーしていますが、各モジュールには詳細な docstring／実装コメントがあります。実運用に際しては該当モジュールのドキュメントを参照し、十分にテストを行ってください。必要であれば各モジュールのサンプル使用例やユースケースごとの起動手順を追加で作成しますので指示ください。