# KabuSys

日本株自動売買システムのワークツリー（抜粋）。  
この README はリポジトリ内の主要コンポーネントと使い方、セットアップ手順を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視を行うためのモジュール群です。  
主な役割は以下のとおりです。

- 実行エンジン（ExecutionEngine）による発注 / リスク管理 / リコンシリエーション
- 監視サブシステム（System / Trade / Risk Monitor）による稼働・注文異常検知とアラート
- ポートフォリオ構築ロジック（候補選定・重み付け・ポジションサイズ決定）
- 研究用途のファクター計算・特徴量探索
- AI（OpenAI）を用いたニュースセンチメント評価・レジーム判定
- Paper Trading 用の分離されたデータベースと検証レポートツール
- Streamlit を使った監視ダッシュボード

設計方針として、DB（SQLite / DuckDB）や外部 API へのアクセスを責務ごとに分離し、フェイルセーフや冪等性（idempotence）に配慮した実装が行われています。

---

## 機能一覧（抜粋）

- 実行 / 発注関連
  - OrderManager / OrderRepository による注文ライフサイクル管理
  - Reconciler による起動時の自動同期（ブローカーとの照合）
  - Paper Trading モード（MockBrokerClient）による本番 DB と完全分離した検証運用

- 監視（monitoring）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス監視、データ鮮度チェック
  - TradeMonitor: 注文滞留（stale orders）・約定異常価格検知
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件に基づく停止フラグ（data/kill.flag）出力
  - AlertManager: LINE Messaging API でのプッシュ通知（クールダウン管理）
  - MonitoringEngine: 上記モニタを束ねるポーリング実行ループ
  - Streamlit ダッシュボード（監視データの閲覧）

- 研究・データ処理
  - research.calc_momentum / calc_volatility / calc_value
  - research.feature_exploration: 将来リターン、IC（Information Coefficient）等
  - DuckDB を使った高速集計

- AI（OpenAI）
  - news_nlp.score_news: ニュース記事を LLM でスコアリングして ai_scores に書き込み
  - regime_detector.score_regime: MA とマクロ記事の LLM 評価を合成して市場レジーム判定

- ユーティリティ
  - process_priority: Windows / POSIX の差分を吸収したプロセス優先度 / CPU affinity 設定
  - tools/paper_verification_report: Paper Trading の検証レポート生成

---

## 前提条件

- Python 3.10+（型記法や構文から想定）
- 推奨パッケージ（主要なもの）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード使用時）
  - そのほか、開発用に pytest 等

（本リポジトリに requirements.txt がある場合はそちらを利用してください）

---

## セットアップ手順（概略）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境の作成と有効化
   - python -m venv .venv
   - source .venv/bin/activate  # Unix/macOS
   - .venv\Scripts\activate     # Windows

3. 依存関係インストール
   - pip install duckdb psutil requests openai streamlit
   - （requirements.txt があれば）pip install -r requirements.txt

4. data ディレクトリと各種ファイルの準備
   - data フォルダが存在しない場合は作成してください（監視 DB、pid/flag 保存に使用）
   - 例:
     - data/monitoring.db (SQLite、初回は実行時にテーブル作成処理が走ります)
     - data/paper_trading.db (Paper Trading 用 DB)
     - data/execution.pid (ExecutionEngine が起動時に書き込む PID)
     - data/stop_requested.flag / data/kill.flag（外部から停止指示を与えるフラグ）

5. 環境変数設定
   - プロジェクトルートの .env / .env.local を用意すると自動で読み込まれます（自動ロードはデフォルト有効）。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV
  - 有効値: development / paper_trading / live
  - デフォルト: development
  - paper_trading の場合、ExecutionEngine は MockBrokerClient を使用し、Paper 専用 DB に記録します（本番 DB と完全分離）。

- JQUANTS_REFRESH_TOKEN
  - J-Quants API トークン（必須）

- KABU_API_PASSWORD
  - kabu ステーション API 用パスワード（必須）

- OPENAI_API_KEY
  - OpenAI API キー（news_nlp / regime_detector が使用）

- DUCKDB_PATH
  - DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）

- SQLITE_PATH
  - 監視用 SQLite パス（デフォルト: data/monitoring.db）
  - 監視（Monitoring）は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（注意）。

- PAPER_TRADING_SQLITE_PATH
  - Paper Trading 用 SQLite パス（デフォルト: data/paper_trading.db）

- PAPER_FILL_MODE
  - Paper Trading の約定モード（instant / partial / never / reject）

- PID_FILE_PATH
  - ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）

- KILL_FLAG_PATH
  - KillSwitch が書き込むフラグファイル（デフォルト: data/kill.flag）

- MONITOR_POLL_INTERVAL
  - 監視ループのポーリング間隔（秒、デフォルト 60 秒）。不正値や 0/負の値はデフォルトにフォールバックします。

---

## 実行方法（コマンド例）

パッケージとして実行する場合（プロジェクトルートが PYTHONPATH に含まれていることを想定）:

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 説明: SystemMonitor をポーリングし結果を SQLite （settings.sqlite_path）に保存します。MONITOR_POLL_INTERVAL で間隔を上書き可能。

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 説明: KABUSYS_ENV に応じて本番ブローカーまたは MockBrokerClient（paper_trading）を使用します。Paper Trading は settings.paper_sqlite_path（data/paper_trading.db がデフォルト）にログを保持します。
  - 停止方法: data/stop_requested.flag を作成するとエンジン停止を促します。KillSwitch により data/kill.flag が作成されると外部的に停止シグナルになります。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション: --db PATH で DB を指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明: read-only モードで SQLite を開き、ダッシュボードを提供します。MonitoringEngine が DB を更新していることが前提です。

- AI / レジーム判定等（モジュール API）
  - news_nlp.score_news(conn, target_date, api_key=...)
  - regime_detector.score_regime(duckdb_conn, target_date, api_key=...)

（上の関数は Python API として提供されています。スクリプト化された CLI があればそれを使ってください。）

---

## データ / フラグファイルについて

- data/stop_requested.flag
  - run_execution.py / run_monitoring.py が監視している停止フラグ（存在することで安全にループを抜けます）。
- data/kill.flag
  - KillSwitch が書き込む停止指示（ExecutionEngine に外部停止命令を与える用途）。
- data/execution.pid
  - 実行エンジンが PID を書き込むファイル。SystemMonitor はこの PID を見てプロセスが生きているか判定します。
- DB ファイル
  - monitoring.db（監視ログ）・paper_trading.db（Paper Trading の注文ログ）・kabusys.duckdb（時系列データ・分析用）

---

## 実装上の注意点 / 運用メモ

- 監視 DB（SQLite）は init_monitoring_db() によりテーブルを自動作成・必要なマイグレーションを行います（冪等）。
- Monitoring は KABUSYS_ENV に関わらず settings.sqlite_path（本番監視 DB）を使用します。Paper Trading の監視も別 DB にしたい場合は運用上の考慮が必要です。
- Paper Trading モードではデータと発注先が本番と分離されます。PAPER_FILL_MODE により約定挙動を制御できます。
- OpenAI 呼び出し（news_nlp / regime_detector）は 429 やネットワーク断、5xx に対してエクスポネンシャルバックオフでリトライする設計です（ただし API キー未設定時は例外を送出します）。
- process_priority.set_process_priority() により起動直後にプロセス優先度を「high」に設定しようとします。権限や OS により設定に失敗する可能性があるため警告でスキップされます。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を探索して行われます。OS 環境変数は保護され、.env.local は上書き可能です。
- ログレベルやしきい値は環境変数で調整可能（LOG_LEVEL, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など）。

---

## ディレクトリ構成（抜粋）

以下はコードベースの主要ファイルをツリー形式で抜粋したものです。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_monitoring.py
    - run_execution.py
    - utils/
      - __init__.py
      - process_priority.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - execution_engine.py (実装ファイルが存在する想定)
      - broker_factory.py
      - broker_api.py
      - order_record.py
      - order_repository.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - pipeline.py (prices や get_last_price_date 等のパイプライン処理)
    - tools/
      - __init__.py
      - paper_verification_report.py

（実際のリポジトリにはさらに多くのモジュールや補助ファイルが存在する可能性があります。上はこのサンプルコードベースから抽出した主要ファイルです。）

---

## よくある操作例

- 監視を 30 秒間隔で動かす（環境変数指定）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading モードで実行
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

- Streamlit ダッシュボード閲覧
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading レポート生成（DB を直接指定）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db

---

## 開発 / テスト

- 単体関数群は外部依存（DB・API）を注入する設計です。ユニットテストでは sqlite/duckdb のインメモリ接続や unittest.mock で外部呼び出しを差し替えてテストしてください。
- OpenAI 呼び出しはモジュール内のラッパー関数をモックして挙動を検証できます（news_nlp._call_openai_api, regime_detector._call_openai_api 等）。

---

この README はコードベースのドキュメントとしての概要を示すもので、詳細な実装や運用手順（本番立ち上げ手順、監視アラートの LINE 設定、バックアップ/リストア手順など）は別途運用ドキュメントを参照してください。必要であれば README を拡張してサンプル .env、起動 systemd ユニット、Docker 化手順なども追加できます。