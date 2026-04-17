# KabuSys

日本株向け自動売買システム（ライブラリ / 実行コンポーネント群）

このリポジトリは、取引エンジン（ExecutionEngine）、監視コンポーネント（MonitoringEngine）、ポートフォリオ構築・リスク調整ロジック、研究用ファクター計算、ニュース NLP（OpenAI）連携などから構成される自動売買システムのパーツ群を含みます。

---

## プロジェクト概要

- 主目的：日本株の自動売買を支えるモジュール群（発注、監視、ポートフォリオ構築、リサーチ、AIによるニュース評価など）を提供する。
- 設計方針：
  - DB（SQLite / DuckDB）を利用したデータ永続化と分析
  - 実行環境（本番 / ペーパー）を環境変数で切り替え
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント / マクロセンチメント評価（任意）
  - 監視コンポーネントがプロセス・注文・ドローダウン等を監視し、必要に応じて停止フラグを書き込む（kill switch）

---

## 主な機能一覧

- Execution（発注系）
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - ブローカークライアント（本番 or モック：KABUSYS_ENV=paper_trading で分離）
  - OrderManager / OrderRepository / Reconciler（再起動時の同期・復旧）
  - RiskManager（発注制約、回路遮断など）

- Monitoring（監視系）
  - SystemMonitor（CPU / メモリ / ディスク、Execution プロセス存在確認、データ鮮度）
  - TradeMonitor（滞留注文、約定価格異常）
  - RiskMonitor（ドローダウン、ポジション上限）
  - KillSwitch（条件成立時に data/kill.flag を書き込み、Execution の停止を促す）
  - AlertManager（LINE Push によるアラート送信）
  - Streamlit ダッシュボード（監視ダッシュボード表示）

- Portfolio（銘柄選定・配分）
  - 候補選定、等金額 / スコア加重配分
  - セクター集中制限、レジーム乗数
  - 株数決定（単元株丸め、aggregate cap、リスクベース等）

- Research（リサーチ）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）算出、統計サマリー

- AI
  - news_nlp: raw_news を OpenAI で評価して ai_scores に書き込み
  - regime_detector: ETF（1321）MA とマクロニュースを組み合わせて市場レジーム判定

- Tools
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）

---

## セットアップ手順

1. Python 環境
   - Python 3.9+ を想定（使用するパッケージの互換性に依存します）

2. 依存パッケージのインストール（例）
   - pip install duckdb psutil openai requests streamlit
   - (またはプロジェクト用 requirements.txt を用意して pip install -r requirements.txt)

3. 環境変数 / .env
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を配置すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数（最低限必要なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - KABUSYS_ENV — 実行環境: development / paper_trading / live （デフォルト: development）
     - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE アラートを使う場合
     - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH — ペーパー取引用 SQLite（paper_trading 時に使用, デフォルト: data/paper_trading.db）
     - DUCKDB_PATH — DuckDB パス（デフォルト: data/kabusys.duckdb）
     - PAPER_FILL_MODE — paper_trading の約定モード (instant|partial|never|reject)（デフォルト: instant）
     - LOG_LEVEL — ログレベル（DEBUG|INFO|...）

   - 例 .env（必須値は適宜セットしてください）:
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     KABUSYS_ENV=development
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb

4. データディレクトリ
   - data/ 以下に DB や pid / flag を格納します。例:
     - data/monitoring.db
     - data/paper_trading.db
     - data/kabusys.duckdb
     - data/execution.pid
     - data/kill.flag
     - data/stop_requested.flag

   実行スクリプトは必要に応じてデータベースを初期化します（init_monitoring_db を呼び出すため、monitoring DB のスキーマは自動作成されます）。

---

## 使い方

- 監視ループの起動
  - 実行ファイル: src/kabusys/run_monitoring.py
  - 簡単な起動:
    python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - 0 以下や不正値は無視され、デフォルト 60 秒にフォールバックします。
  - 監視は常に本番用 sqlite_path を使います（KABUSYS_ENV に依存しません）。
  - 停止方法: data/stop_requested.flag ファイルを作成するとループが検知して終了します（あるいは Ctrl-C）。

- Execution（発注エンジン）起動
  - 実行ファイル: src/kabusys/run_execution.py
  - 起動:
    python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）にデータを記録します（本番 DB と完全に分離）。
  - 起動前に data/stop_requested.flag が存在する場合は起動を行わず終了します。
  - 実行中は data/execution.pid に PID を書きます。停止は data/stop_requested.flag を作成するか kill でプロセスを止めてください。

- Streamlit ダッシュボード（監視 UI）
  - 実行ファイル: src/kabusys/monitoring/streamlit_dashboard.py
  - 起動例:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み込み、Portfolio / Positions / Orders / System の情報を表示します。DB は read-only で開かれます（URI に ?mode=ro を付加）。

- Paper Trading 検証レポート
  - スクリプト: src/kabusys/tools/paper_verification_report.py
  - 実行例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション `--db` で DB パスを指定できます（指定がなければ PAPER_TRADING_SQLITE_PATH 環境変数、さらに無ければ data/paper_trading.db が使われます）。

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY または関数に api_key を渡す）。
  - ニューススコアリング: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - API 呼び出しはリトライ・バックオフを実装しており、失敗時はフェイルセーフ（スコア 0 等）で継続する設計です。

- 停止 / Kill Switch
  - RiskMonitor / KillSwitch によりドローダウン・ポジション上限等の条件で data/kill.flag を書き込みます。Execution 側はこのファイルの存在を検出すると安全に停止するよう設計されています。
  - kill.flag のパスは Settings.kill_flag_path（デフォルト: data/kill.flag）で変更可能。
  - KillSwitch は冪等に書き込む（既存なら上書きしない）。

---

## 主要な設定（Settings）

Settings クラス（src/kabusys/config.py）でアプリ設定を取得できます。主なプロパティ：

- jquants_refresh_token
- kabu_api_password
- kabu_api_base_url (default: http://localhost:18080/kabusapi)
- line_channel_access_token / line_user_id
- duckdb_path (default: data/kabusys.duckdb)
- sqlite_path (default: data/monitoring.db)
- paper_sqlite_path (default: data/paper_trading.db)
- paper_fill_mode (instant|partial|never|reject)
- pid_file_path (default: data/execution.pid)
- kill_flag_path (default: data/kill.flag)
- kill_flag_clear_on_start (0/1)
- cpu_threshold_pct / memory_threshold_pct / disk_threshold_pct
- env (development / paper_trading / live)
- log_level

.env の自動読み込み：
- プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を読み込みます（OS 環境変数を保護）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）でスコアリング
    - regime_detector.py — マクロ + MA によるレジーム判定
  - monitoring/
    - monitoring_db.py — 監視用 SQLite 層（スキーマ定義・永続化API）
    - system_monitor.py — システム状態 / データ鮮度監視
    - trade_monitor.py — 注文滞留 / 約定異常監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — LINE Push API 経由の通知
    - monitoring_engine.py — 各 Monitor を束ねるループ
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - （ブローカー関連、order_repository 等がここに存在）
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 株数決定（ロット丸め / aggregate cap）
    - risk_adjustment.py — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - data/（実行時に使用 / 作成される想定）
    - monitoring.db
    - paper_trading.db
    - kabusys.duckdb
    - execution.pid
    - kill.flag
    - stop_requested.flag
  - utils/
    - process_priority.py — プロセス優先度と CPU affinity 設定ユーティリティ

（上記は主要ファイルの抜粋です。実装詳細は各モジュールの docstring を参照してください。）

---

## 動作上の注意点 / 運用メモ

- paper_trading モードは本番データベースと完全分離されるよう設計されています。運用時は KABUSYS_ENV を正しく設定してください。
- OpenAI を利用する機能は API キーが必須です。API 呼び出し時のエラーは堅牢に処理されるよう設計されていますが、コストとレート制限に注意してください。
- run_monitoring.py / run_execution.py は実行開始時にプロセス優先度を "high" に設定しようとします（権限により失敗する場合はログのみ）。
- DB マイグレーションやスキーマ拡張は monitoring_db.init_monitoring_db() に一部実装されています（例: カラム追加のフェールセーフ対応）。
- alert（LINE）はトークン未設定時にスキップされます。テスト時に誤送信しないよう注意してください。
- .env のパースはシェルの export KEY=val 等に類似した構文をサポートします（クォート処理、インラインコメント処理あり）。

---

必要であれば、README に含めるサンプル .env、systemd ユニットの例、運用手順（再起動時の Reconciler の挙動や kill.flag の扱い）、よくあるトラブルシュート項目を追加できます。どの情報を追加したいか教えてください。