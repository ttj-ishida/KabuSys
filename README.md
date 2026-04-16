# KabuSys

日本株向け自動売買システムのコードベース（抜粋）。本 README ではプロジェクトの概要、主要機能、セットアップと実行手順、使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は日本株の自動売買およびそれに付随する監視・検証・リサーチ機能を提供する Python モジュール群です。  
主な目的は以下です。

- 売買シグナルに基づく発注エンジン（ExecutionEngine）
- 発注状態・ポジションの復旧（Reconciler）
- システム稼働状況・注文異常・リスク監視（Monitoring）
- Paper Trading 用の分離された検証環境
- ニュース NLP を使った銘柄センチメント評価（OpenAI）
- ファクター計算やリサーチユーティリティ（DuckDB ベース）
- Streamlit ダッシュボードによる監視可視化
- 検証レポート生成ツール（Paper Trading レポート）

コードは純粋関数的なファイル（ポートフォリオ構築、リスク調整、ポジションサイズ算出など）と、DB/外部 API と連携する実行系・監視系に分かれています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine を起動して発注ワークフローを実行
  - BrokerClientFactory による本番／Paper Trading（MockBrokerClient）切替
  - Reconciler による再起動後の注文・ポジション同期
  - OrderManager / OrderRepository による注文レコード管理、重複防止

- Monitoring
  - SystemMonitor: CPU/MEM/DISK、Execution プロセス監視、データ鮮度チェック
  - TradeMonitor: 滞留注文（stale）、約定価格異常の検知
  - RiskMonitor: ドローダウン監視、ポジション数上限チェック（ハイウォーターマーク管理）
  - KillSwitch: しきい値超過時に data/kill.flag を書き込み ExecutionEngine 停止を促す
  - AlertManager: LINE Messaging API を使ったプッシュ通知（クールダウン管理）
  - Streamlit ベースの監視ダッシュボード

- AI / Research
  - news_nlp.score_news: OpenAI（gpt-4o-mini）でニュースを銘柄別にセンチメント評価し ai_scores に書込
  - regime_detector.score_regime: ETF の MA とマクロニュースを組み合わせて市場レジーム判定を行い market_regime に書込
  - research モジュール: ファクター計算（モメンタム、ボラティリティ、バリュー等）、将来リターン、IC 計算、統計サマリー

- Tools
  - paper_verification_report: Paper Trading DB を解析して稼働率 / 注文成功率 / レイテンシ等の検証レポートを出力

---

## セットアップ手順

前提: Python 3.9+（タイプヒントに依存）。DuckDB/psutil/requests/OpenAI ライブラリ等を使用します。

1. リポジトリをクローン／展開し、プロジェクトルートへ移動。

2. 依存ライブラリをインストール（例）:
   pip を使う場合の例:
   ```
   pip install duckdb psutil openai requests streamlit
   ```
   必要に応じて仮想環境を作成してください。

3. 環境変数設定:
   - プロジェクトルートに `.env` / `.env.local` を置くことで自動ロードされます（デフォルトで OS 環境変数 → .env.local → .env の順で読み込み）。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   重要な環境変数（抜粋）:
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合に必須）
   - KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
     - paper_trading 時は paper 用 DB（PAPER_TRADING_SQLITE_PATH）を使用
   - PAPER_FILL_MODE: paper_trading の約定モード ("instant" | "partial" | "never" | "reject")
   - SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE）用
   - LOG_LEVEL: ログレベル ("INFO" 等)
   - PID_FILE_PATH, KILL_FLAG_PATH: 各種フラグ・PID 管理パス

   例（.env の一部）:
   ```
   KABUSYS_ENV=development
   SQLITE_PATH=data/monitoring.db
   DUCKDB_PATH=data/kabusys.duckdb
   OPENAI_API_KEY=sk-...
   LINE_CHANNEL_ACCESS_TOKEN=xxxx
   LINE_USER_ID=Uxxxxxxxxxxxx
   ```

4. data ディレクトリを作成（必要に応じて）:
   ```
   mkdir -p data
   ```

注意: SQLite / DuckDB ファイルは初回起動時にテーブル作成や簡単なマイグレーションを行います（init_monitoring_db）。

---

## 使い方

以下は代表的な実行方法です。プロジェクトルートをカレントにして実行してください（`src` がパッケージルートになる構成の場合、python 実行時にパスを適切に通すか、パッケージをインストールしてください）。

1. 監視ループを起動（Monitoring）
   - スクリプト: `src/kabusys/run_monitoring.py`
   - 実行例:
     ```
     python -m kabusys.run_monitoring
     ```
   - 特記事項:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
     - 監視は設定にかかわらず本番の sqlite_path（Settings.sqlite_path）を使用します。
     - 起動時にプロセス優先度を "high" に設定しようとします（psutil を利用）。

2. Execution エンジンを起動
   - スクリプト: `src/kabusys/run_execution.py`
   - 実行例:
     ```
     python -m kabusys.run_execution
     ```
   - 特記事項:
     - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し、Paper Trading 用の SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト `data/paper_trading.db`）を使って本番 DB と分離します。
     - ExecutionEngine の PID は `data/execution.pid`（デフォルト）に書き込まれます。停止信号は `data/stop_requested.flag`（コード内参照）や `data/kill.flag`（KillSwitch）でやり取りされます。
     - `Settings.kill_flag_clear_on_start` が 1 の場合、起動時に kill.flag を自動で削除する振る舞いが設定可能です。

3. Streamlit ダッシュボード（監視可視化）
   - ファイル: `src/kabusys/monitoring/streamlit_dashboard.py`
   - 実行例:
     ```
     streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
     ```
   - 説明: read-only モードで SQLite DB を開き、Overview / Positions / Orders / System タブを提供します。

4. Paper Trading 検証レポート生成
   - スクリプト: `src/kabusys/tools/paper_verification_report.py`
   - 実行例:
     ```
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     ```
     または DB 指定:
     ```
     python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
     ```
   - 出力: 稼働率、注文成功率、送信率、P95 レイテンシなどを集計して標準出力にレポートを表示します。

5. AI / レジーム判定 / ニュース NLP
   - news_nlp.score_news(conn, target_date, api_key=None) と regime_detector.score_regime(conn, target_date, api_key=None) を呼び出して利用します。どちらも OpenAI API キー（env または引数）を必要とします。
   - 注意: これらはライブラリ関数として提供され、CLI ラッパーは本リポジトリの抜粋に含まれていません。テスト時は API コール部分を差し替えて利用します。

---

## ファイル・フラグ管理（運用上の注意）

- 停止・強制停止フラグ類:
  - data/stop_requested.flag: run_monitoring / run_execution が監視する停止フラグ（存在するとループを終了）
  - data/kill.flag: KillSwitch が書き込むフラグ。ExecutionEngine 停止要求に利用
  - data/execution.pid: ExecutionEngine の PID（存在チェックでプロセス生存確認を行う）

- DB の分離:
  - 本番監視 DB: Settings.sqlite_path（デフォルト `data/monitoring.db`）
  - Paper Trading DB: Settings.paper_sqlite_path（デフォルト `data/paper_trading.db`）
  - DuckDB（時系列/ファクターデータ）: Settings.duckdb_path（デフォルト `data/kabusys.duckdb`）

- 自動 .env 読み込み:
  - OS 環境変数 > .env.local > .env の順で読み込み
  - プロジェクトルートは `.git` または `pyproject.toml` から自動検出
  - 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 以下の主要モジュール一覧（抜粋）です。

- kabusys/
  - __init__.py (パッケージ定義, __version__)
  - config.py (Settings: 環境変数管理, .env 自動ロード)
  - run_monitoring.py (監視ループ起動スクリプト)
  - run_execution.py (ExecutionEngine 起動スクリプト)

  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py (エンジン本体; 抜粋では参照あり)
    - broker_factory.py, broker_api.py (ブローカ抽象)

  - monitoring/
    - monitoring_db.py (SQLite テーブル作成・永続化 API)
    - system_monitor.py (CPU/メモリ/ディスク/データ鮮度/プロセス検査)
    - trade_monitor.py (滞留注文・約定異常)
    - risk_monitor.py (ドローダウン・ポジション上限監視)
    - kill_switch.py (kill.flag 書き込み)
    - alert_manager.py (LINE 送信)
    - monitoring_engine.py (各モニタを束ねる)
    - streamlit_dashboard.py (ダッシュボード)

  - portfolio/
    - portfolio_builder.py (候補選定・スコア順ソート)
    - position_sizing.py (株数算出ロジック、ロット調整、集約キャップ)
    - risk_adjustment.py (セクター制限、レジーム乗数)

  - research/
    - factor_research.py (モメンタム/ボラ/バリュー算出)
    - feature_exploration.py (将来リターン、IC、統計)

  - ai/
    - news_nlp.py (ニュースを LLM でスコアリング)
    - regime_detector.py (MA と マクロニュースの LLM を合成)

  - data/  （実行時に生成・利用することが多い）
    - monitoring.db（SQLite）
    - paper_trading.db（Paper Trading 用 SQLite）
    - kabusys.duckdb（DuckDB）
    - stop_requested.flag / kill.flag / execution.pid

  - tools/
    - paper_verification_report.py (Paper Trading 検証レポート CLI)

---

## 運用上の注意事項（補足）

- Paper Trading と本番 DB は完全に分離するよう設計されています。KABUSYS_ENV に `paper_trading` を指定した場合、paper 用 SQLite を使用します。
- OpenAI を利用する機能は API キー依存です。API 呼び出しはリトライ・フォールバックロジックが組み込まれていますが、コストやレート制限に注意してください。
- Monitoring コンポーネントは、システムリソースや Execution の健康状態を監視し、必要なら kill.flag を出力します。kill.flag の存在は Execution 側で停止判定に使われます。フラグの書き込みは冪等に設計されています。
- AlertManager の LINE 通知はクールダウン（デフォルト 30 分）を持ちます。トークン・ユーザID が未設定の場合はログに記録して送信をスキップします。
- process priority（優先度）と CPU affinity は psutil に依存します。権限不足や未対応 OS の場合は警告ログを出してスキップします。
- DB スキーマは init_monitoring_db により初回自動作成・簡単なマイグレーション（カラム追加）を行います。

---

この README はコードベースの抜粋から作成しています。実際に運用する際はリポジトリに含まれる他のモジュール（execution_engine、broker 実装、orders DB 管理部等）およびセキュリティ設定やバックアップポリシーを併せて確認してください。必要ならば起動スクリプトの systemd / supervisor などによるプロセスマネージメント、ログローテーション、監視アラートの受信テストを行ってください。