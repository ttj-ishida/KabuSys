# KabuSys README

以下はこのリポジトリ（KabuSys）の概要、主要機能、セットアップ手順、使い方、ディレクトリ構成です。

注意：README はソースコードのコメント・実装に基づいて作成しています。実行には Python 環境と外部ライブラリ、API キーなどが必要です。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を目的としたモジュール群です。主な要素は次の通りです。

- ExecutionEngine：発注・注文管理・リスク管理を行う実行エンジン（ライブ／ペーパートレーディング対応）
- Monitoring：システム稼働状態、注文状況、リスク指標を定期的に監視・ログ保存し、アラートや KillSwitch（停止フラグ）を扱う
- Portfolio：銘柄選定、重み付け、ポジションサイズ決定、セクター制限などのポートフォリオ構築ユーティリティ
- Research：DuckDB 上のマーケットデータからファクター計算・将来リターンや IC の算出などを行う
- AI：ニュース記事の NLP によるセンチメントスコアリングや市場レジーム判定（OpenAI を利用）
- Tools：Paper Trading の検証レポート等のユーティリティスクリプト

設計方針として、可能な限り副作用を避け、DB（SQLite / DuckDB）や外部 API を切り分けているため、研究・検証用途でも安全に使えるようになっています。

---

## 機能一覧（ハイライト）

- 実行（Execution）
  - ブローカークライアントを抽象化（ライブ／モック切替）
  - OrderManager / RiskManager / Reconciler による発注・再同期処理
  - 起動時の再同期（Reconciler）

- 監視（Monitoring）
  - SystemMonitor：CPU/メモリ/ディスク、プロセス生存、データ鮮度監視
  - TradeMonitor：滞留注文・約定異常価格の検出
  - RiskMonitor：ドローダウン・ポジション上限の監視とリスクログ
  - KillSwitch：リスク条件で ExecutionEngine 停止指示（flag ファイル）
  - AlertManager：LINE へのプッシュ通知（クールダウン管理）
  - Streamlit ダッシュボード（監視データの可視化）

- ポートフォリオ構築（Portfolio）
  - 候補選定、等金額/スコア加重、リスクベースのポジション決定
  - セクター集中制限、レジーム乗数

- リサーチ（Research）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン算出、IC（Spearman）や統計サマリー

- AI（OpenAI 利用）
  - ニュース記事を銘柄ごとに集約して LLM でセンチメント評価（ai_scores へ書込）
  - マクロニュース × ETF MA200 乖離を合成した市場レジーム判定（market_regime へ書込）
  - API 呼び出しはリトライ等のフェイルセーフ設計

- Tools
  - Paper Trading 検証レポート生成スクリプト（期間指定でレポート出力）

---

## 必要要件（例）

最低限の依存（実際はプロジェクトに requirements.txt がある想定）：

- Python 3.9+（ソースに合わせて適宜）
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボード利用時）
- （必要に応じて）sqlite3 は標準ライブラリで利用

インストール例：
- requirements.txt が無い場合の一時的なインストール例：
  pip install duckdb psutil requests openai streamlit

---

## セットアップ手順

1. リポジトリをクローン／配置する。

2. Python 仮想環境を作る（推奨）：
   python -m venv .venv
   source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール：
   pip install -r requirements.txt
   （requirements.txt がない場合は上記パッケージ群を個別に pip install）

4. 環境変数の準備：
   - リポジトリルートに .env を作成して必要なキーを設定します。
   - 自動読み込みはデフォルトで有効（.env, .env.local をロード）。無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. 必須の環境変数（Settings 参照）
   - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
   - KABU_API_PASSWORD — kabu ステーション API 用（必須）
   - OPENAI_API_KEY — OpenAI を使う機能（news_nlp / regime_detector）を使う場合は必須
   - その他（任意/デフォルトあり）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, など

6. データディレクトリの作成：
   - デフォルトで data/ 以下の sqlite や duckdb を参照します。必要に応じて作成・パスの確認をしてください。

---

## 実行方法 / 使い方

### 1) 監視ループの起動（Monitoring）
- 目的：SystemMonitor（プロセス生存・リソース・データ鮮度）を定期実行して SQLite にログを保存するデーモン的なスクリプト。

コマンド例：
  python -m kabusys.run_monitoring

挙動・設定：
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（デフォルト 60 秒）。
- Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して DB に接続します。
- 起動時にプロセス優先度を "high" に設定しようとします（psutil を利用）。権限不足時は警告を出してスキップ。

停止方法：
- data/stop_requested.flag を作成するとループは検知して終了します。
- また KeyboardInterrupt（Ctrl+C）で終了します。

### 2) ExecutionEngine 起動（実取引 / ペーパートレーディング）
- 目的：発注エンジンを起動してシグナルに基づき発注・リスク管理を実行します。

コマンド例：
  python -m kabusys.run_execution

挙動・設定：
- KABUSYS_ENV=paper_trading に設定すると MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db）に記録して本番 DB と分離します。
- 起動時に stop_requested.flag の存在を確認し、存在する場合は起動せず終了します。
- 実行中は data/execution.pid に PID を書きます。監視側（SystemMonitor）はこの PID ファイルを確認してプロセス生存を判定します。
- 停止は data/stop_requested.flag を書くか、KillSwitch が data/kill.flag を書くことで行えます（KillSwitch は監視モジュールから条件に応じて書き込みます）。

### 3) Streamlit ダッシュボード（監視データの可視化）
起動例：
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- SQLite DB を読み取り専用で開き、Positions / Orders / System / Overview を表示します。
- DB が存在しない場合はエラー表示（MonitoringEngine を先に起動してください）。

### 4) Paper Trading 検証レポート生成ツール
- モジュール： kabusys.tools.paper_verification_report

コマンド例：
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db /path/to/data/paper_trading.db

- PAPER_TRADING_SQLITE_PATH 環境変数で DB パスを指定できます（デフォルト: data/paper_trading.db）。
- 検証項目：稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ等を集計し PASS/FAIL を出力します。

### 5) AI モジュール（ニュース NLP / レジーム判定）
- ニューススコア付与：
  - 関数： kabusys.ai.news_nlp.score_news(conn: duckdb.DuckDBPyConnection, target_date: date, api_key: Optional[str])
  - 動作：raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）でスコアリングして ai_scores テーブルへ書き込む
  - 必要：OPENAI_API_KEY（引数でも渡せる）

- レジーム判定：
  - 関数： kabusys.ai.regime_detector.score_regime(conn: duckdb.DuckDBPyConnection, target_date: date, api_key: Optional[str])
  - 動作：ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成し market_regime に書き込む
  - 必要：OPENAI_API_KEY（引数でも渡せる）

注意：これらは DuckDB 接続を受け取り SQL でデータを読んだ上で OpenAI を呼び出します。API 呼び出しはリトライやクリップなどを実装しており、失敗時は安全側のフォールバックを採用します。

---

## 重要な環境変数（主なもの）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabu API 用（必須）
- OPENAI_API_KEY: OpenAI を使う場合に必須
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring.db）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 専用 SQLite（デフォルト data/paper_trading.db）
- PID_FILE_PATH: execution.pid のパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60。無効値はデフォルトにフォールバック）
- PAPER_FILL_MODE: ペーパートレードでの約定モード（instant / partial / never / reject、デフォルト instant）

その他はソース内の Settings クラスのプロパティ参照ください。

自動 .env ロード：
- ルートに .env / .env.local があれば自動で読み込まれます（ただし OS 環境変数が優先）。
- 無効化： KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主要ファイルの説明）

（パスは src/kabusys をルートとした相対）

- __init__.py
  - パッケージメタ情報（__version__ 等）

- config.py
  - 環境変数 / Settings 管理、.env 自動ロードロジック

- run_monitoring.py
  - SystemMonitor をポーリングで回す起動スクリプト

- run_execution.py
  - ExecutionEngine を起動するスクリプト（paper_trading なら MockBroker）

- execution/
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, execution_engine など（発注・リスク管理・リコンシリエーション）

- monitoring/
  - monitoring_db.py: SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py / trade_monitor.py / risk_monitor.py: 各種監視ロジック
  - monitoring_engine.py: 各 Monitor を束ねるループ処理
  - kill_switch.py: kill.flag を書くユーティリティ
  - alert_manager.py: LINE push 通知
  - streamlit_dashboard.py: Streamlit ベースの可視化

- portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 発注株数算出、単元丸め、aggregate cap
  - risk_adjustment.py: セクターキャップ、レジーム乗数

- research/
  - factor_research.py: Momentum/Volatility/Value の計算
  - feature_exploration.py: 将来リターン・IC・統計サマリ計算

- ai/
  - news_nlp.py: ニュースの LLM スコアリング（ai_scores への書込み）
  - regime_detector.py: 市場レジーム判定（market_regime への書込み）

- tools/
  - paper_verification_report.py: ペーパートレードの検証レポート作成スクリプト

- utils/
  - process_priority.py: プラットフォーム差分を吸収したプロセス優先度 / CPU affinity 設定

- data/
  - 実行時に生成されるファイルの既定場所（data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag, data/stop_requested.flag 等）

---

## 運用上の注意 / ベストプラクティス

- 本番環境では KABUSYS_ENV=live を指定してください。paper_trading では DB を分離します。
- run_monitoring は監視 DB（SQLITE_PATH）に接続します。監視は常に sqlite_path（本番）を参照します。テスト用に切り替える場合は env を調整してください。
- run_execution は stop_requested.flag の存在をチェックします。外部から停止する場合は stop flag を使うか kill.flag を利用してください（kill.flag は KillSwitch による自動書き込み）。
- OpenAI を利用する機能は API キー保持と使用料に注意してください。API 呼び出しはリトライ処理と安全側フォールバックを組み込んでいますが、料金発生に注意してください。
- psutil によるプロセス優先度／CPU affinity 操作は権限が必要になる場合があります（権限不足時は警告を出してスキップ）。

---

## 開発・テスト

- モジュール単位でのユニットテストを作成することを推奨します。AI 呼び出しや外部 API 呼び出しはモック化してテストしてください（コード中にモックしやすい設計がなされています）。
- DB に対する書き込みは初期化関数 init_monitoring_db を使って冪等にテーブルを作成できます。マイグレーション的な簡易処理も実装されています（カラム追加等）。

---

必要であれば、README に含める実行例（環境変数スニペット）、requirements.txt の推定内容、各モジュールの詳細な API ドキュメントを追加できます。どの情報を追加したいか教えてください。