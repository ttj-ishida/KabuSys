# KabuSys

日本株自動売買システムの一部を実装したコードベースの説明ドキュメント（README.md）。  
このリポジトリには、実行エンジン・監視・ポートフォリオ構築・リサーチ・AI（ニュース NLP）等の主要コンポーネントが含まれます。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成する以下の主要機能を持ちます。

- ExecutionEngine: ブローカーとの発注・注文ライフサイクル管理、リスク管理、再同期（Reconciler）
- Monitoring: システム状態・データ鮮度・注文異常・ドローダウンなどを常時監視しログ・アラート・停止指示を出す
- Portfolio construction: シグナルに基づく候補選定、重み計算、ポジションサイズ計算、セクター上限やレジーム調整
- Research: DuckDB 上の価格・財務データからファクター計算・IC評価・特徴量解析
- AI (ニュース NLP / レジーム判定): OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコア算出や市場レジーム判定
- Tools: Paper Trading の検証レポート生成、Streamlit ベースの監視ダッシュボード等
- 設定管理: 環境変数と .env(.local) を読み込む Settings モジュール

設計方針として、
- 実データベースは DuckDB / SQLite を利用し、データ参照はルックアヘッドバイアスに注意して行います。
- Paper trading（検証）と本番（live）は DB を分離して扱います。
- 外部 API（OpenAI など）呼び出しはリトライやフォールバック動作を持ちフェイルセーフを重視します。

---

## 主な機能一覧

- run_execution: ExecutionEngine 起動（本番 / paper_trading 切替）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し paper_trading 用 SQLite を使う
  - プロセス優先度設定、PID 管理、停止フラグ監視
- run_monitoring: SystemMonitor のポーリングループ（MONITOR_POLL_INTERVAL 環境変数で間隔変更）
  - system_status / trade_logs / risk_logs / dashboard / positions を管理
  - stop フラグ検出で安全に終了
- MonitoringEngine: SystemMonitor / TradeMonitor / RiskMonitor を統合してアラート・KillSwitch 判定
- AlertManager: LINE Messaging API を使った一方向プッシュ通知（クールダウン制御付き）
- KillSwitch: データ/フラグファイルにより ExecutionEngine を停止させる仕組み（kill.flag）
- portfolio: 候補選定、等分配／スコア重み、リスク調整（セクター上限、レジーム乗数）、ポジションサイズ計算（単元丸め・aggregate cap）
- research: momentum / volatility / value / forward returns / IC / factor summary 等の計算
- ai.news_nlp: raw_news をまとめて OpenAI に送信し銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込む
- ai.regime_detector: ETF 1321 の MA200 とマクロニュースセンチメントを合成して market_regime を算出・永続化
- tools.paper_verification_report: Paper Trading DB を解析して稼働率・注文成功率・レイテンシ等の検証レポートを標準出力に出力
- monitoring.streamlit_dashboard: Streamlit を用いた監視ダッシュボード（read-only 接続）

---

## セットアップ手順

前提: Python 3.9+（typing の一部機能が使われています）。環境に合わせて仮想環境を推奨します。

1. リポジトリをクローンしワークディレクトリに移動
   - 例: git clone ... ; cd <repo>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  # POSIX
   - .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   最低限の依存（主要な外部ライブラリ）:
   - duckdb
   - psutil
   - requests
   - streamlit
   - openai

   例:
   - pip install duckdb psutil requests streamlit openai

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用してください）

4. 環境変数の準備
   - プロジェクトルートに .env / .env.local を用意できます（自動ロード機能あり）。
   - 自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を利用する場合:
     - OPENAI_API_KEY を設定
   - 任意 / デフォルト値:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - SQLITE_PATH: data/monitoring.db（monitoring 用）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - DUCKDB_PATH: data/kabusys.duckdb
     - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
     - PID_FILE_PATH, KILL_FLAG_PATH, LOG_LEVEL 等

   .env 例（最低限）:
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...
   - KABUSYS_ENV=development

5. データディレクトリ作成
   - mkdir -p data

初回起動時に run_monitoring / run_execution が monitoring DB を初期化します（init_monitoring_db を呼び出すため冪等にテーブルを作成します）。

---

## 使い方

### 実行エンジン（ExecutionEngine）を起動する
- 本番モード:
  - export KABUSYS_ENV=live
  - python -m kabusys.run_execution
- Paper Trading（検証）モード（ブローカーは Mock、paper_trading DB を利用）:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

注意:
- 実行中に停止させたい場合はプロセスを終了するか、プロジェクトルートの data/stop_requested.flag を作成すると run_execution は検出して安全に停止します（同様に run_monitoring も停止します）。
- ExecutionEngine 側の自動停止（リスク条件）は kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）で行われます。KillSwitch は条件を満たすとこのファイルを書き込みます。

### 監視（Monitoring）を起動する
- 簡易起動（デフォルトポーリング間隔 60 秒）
  - python -m kabusys.run_monitoring
- ポーリング間隔を変更する:
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring

run_monitoring は Settings に基づき本番用の sqlite_path を使用して監視ログを記録します（KABUSYS_ENV にかかわらず本番 monitoring DB を使う設計）。

停止:
- プロジェクトルートの data/stop_requested.flag を作成すると run_monitoring は検出して終了します。

### 監視ダッシュボード（Streamlit）
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 監視 DB を読み取り専用で開き、ポートフォリオ値・ポジション・最近の注文・最新システムステータス等を表示します。

### Paper Trading 検証レポート
- 実行:
  - python -m kabusys.tools.paper_verification_report
- 期間を指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB パスを指定:
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

出力: 稼働率、注文成功率、送信率、P95 レイテンシ等のサマリと PASS/FAIL 判定を標準出力に表示します。

### AI（ニュース NLP / レジーム判定）の利用（プログラム的に）
- news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡して指定日付のニュースをスコアリングし ai_scores テーブルへ書き込みます。
  - api_key を明示的に渡すか環境変数 OPENAI_API_KEY をセットしてください。
- regime_detector.score_regime(conn, target_date, api_key=None)
  - DuckDB と target_date を渡して market_regime テーブルへレジーム判定結果を書き込みます。

注意点:
- OpenAI API 呼び出しはリトライやフォールバック（失敗時は 0.0）を持ちますが、API キーが未設定だと例外となります。

---

## 重要な環境変数（主なもの）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- PAPER_FILL_MODE: paper_trading の MockBroker の約定挙動（instant|partial|never|reject）
- SQLITE_PATH: 監視用 SQLite DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite DB（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB データベース（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行エンジンの PID / kill flag のパス

.env の自動読み込み:
- プロジェクトルートを .git または pyproject.toml で検出し、.env（既存の OS 環境変数を上書きしない）→ .env.local（上書き可）を自動ロードします。
- 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 停止・強制停止の仕組み

- run_monitoring / run_execution はプロジェクトルートの data/stop_requested.flag の存在を定期的に確認し、見つかれば安全に終了します。
- KillSwitch（監視側）がリスク条件を検出すると Settings.kill_flag_path（デフォルト data/kill.flag）に理由を書き込みます。ExecutionEngine 起動時はこの kill.flag を検査・クリアするオプションが実装されています（Settings.kill_flag_clear_on_start により挙動制御）。
- PID ファイル: ExecutionEngine は実行中に PID ファイル（デフォルト data/execution.pid）を書き込み、SystemMonitor はその PID ファイルを参照してプロセス稼働を検出します。

---

## ディレクトリ構成（主要ファイルと説明）

（パスは src/kabusys 以下を想定）

- __init__.py
  - パッケージ定義、バージョン
- config.py
  - Settings クラス：環境変数の読み込み・検証・デフォルト値
- run_execution.py
  - ExecutionEngine の起動スクリプト（thread でエンジンを回す）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- tools/
  - paper_verification_report.py: Paper Trading 検証レポート CLI
- monitoring/
  - monitoring_db.py: SQLite スキーマ初期化・永続化用ラッパー（MonitoringDB）
  - system_monitor.py: CPU/メモリ/Disk/データ鮮度/プロセスチェック
  - trade_monitor.py: 注文滞留 / 約定価格異常検出
  - risk_monitor.py: ドローダウン / ポジション上限チェック
  - kill_switch.py: kill.flag 書込みロジック
  - alert_manager.py: LINE Push 通知クライアント
  - monitoring_engine.py: 各 monitor を束ねる実行ループ
  - streamlit_dashboard.py: Streamlit ダッシュボード
- execution/
  - order_manager.py: 注文作成・キャンセル等の上位 API
  - reconciler.py: 起動時リコンシリエーション（注文/ポジション突合）
  - （その他：broker_factory, execution_engine, order_repository, order_record など）
- portfolio/
  - portfolio_builder.py: 候補選別・重み付け
  - position_sizing.py: 各銘柄の発注株数計算
  - risk_adjustment.py: セクター上限・レジーム乗数
- research/
  - factor_research.py: momentum/volatility/value ファクター計算
  - feature_exploration.py: 将来リターン / IC /統計サマリ
- ai/
  - news_nlp.py: ニュースをまとめて LLM に渡し ai_scores へ書き込み
  - regime_detector.py: マクロ + MA200 を合成して market_regime を算出
- utils/
  - process_priority.py: プロセス優先度・CPU アフィニティ設定ユーティリティ
- data/
  - 実行時に生成されるファイル群（monitoring.db, paper_trading.db, kabusys.duckdb, execution.pid, kill.flag, stop_requested.flag など）

---

## 開発・テスト時の注意

- Paper trading と本番 DB は明確に分離されています。KABUSYS_ENV=paper_trading を使用して検証を行ってください。
- DuckDB のクエリは prices_daily / raw_financials / raw_news などのテーブル構成を前提としています。テーブルがない場合は一部機能（factor 計算・AI モジュール）は動作しません。
- OpenAI 呼び出しはテストでモックすることを想定して設計されています（内部の _call_openai_api を patch することでテスト可能）。
- 監視・エンジン実行時はプロセス優先度の変更（psutil）を試みますが、権限不足や OS 非対応時は警告を出してスキップします。

---

## トラブルシューティング（よくある質問）

- Q: run_monitoring / run_execution がすぐ終了する
  - A: data/stop_requested.flag が存在していないか確認してください。また run_execution は起動時に stop フラグが立っていれば起動を中止します。
- Q: OpenAI を使った処理でエラーが出る
  - A: OPENAI_API_KEY を設定してください。API 呼び出しはネットワークやレート制限のためリトライ挙動がありますが、キー未設定は例外になります。
- Q: Paper Trading の検証レポートで DB が見つからない
  - A: PAPER_TRADING_SQLITE_PATH または --db オプションで正しいパスを指定してください。デフォルトは data/paper_trading.db。

---

この README はコードベースの主要点をまとめたものです。実装の詳細や追加設定項目は各モジュール（src/kabusys 以下）の docstring・コメントを参照してください。必要であれば、セットアップ手順の OS 別詳細や CI/デプロイ手順のテンプレートも作成できます。必要に応じて教えてください。