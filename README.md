# KabuSys — 日本株自動売買システム（README）

このリポジトリは日本株向けの自動売買システム KabuSys の一部実装を含みます。トレード実行エンジン、監視・アラート、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント）連携などの主要コンポーネントが含まれます。

以下は開発者・運用者向けの概要、機能一覧、セットアップ方法、使い方、ディレクトリ構成と運用上の注意点です。

※記載はソースコード（src/kabusys/**）の内容に基づきます。

概要
- KabuSys は日本株自動売買のためのモジュール群。
- 実行（ExecutionEngine）、監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）、ポートフォリオ構築、ファクター計算・リサーチ、AI を使ったニュースセンチメント評価等を提供します。
- 設定は環境変数または .env / .env.local から読み込みます（自動ロード機構あり）。

主な機能一覧
- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）。KABUSYS_ENV により paper_trading 用 DB・モックブローカーを使用可。
  - OrderManager / OrderRepository / Reconciler による発注管理・再同期。
  - リスク管理（RiskManager）や発注レート制御等（設定に依存）。
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセス状態・データ鮮度監視。
  - TradeMonitor：滞留注文・約定異常価格検出。
  - RiskMonitor：ドローダウン・ポジション数監視とダッシュボード更新。
  - MonitoringEngine：各モニタのポーリングとアラート連携。
  - AlertManager：LINEプッシュ通知（トークン未設定時はログのみ）。
  - streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）。
- Portfolio / Position sizing
  - 候補選定（select_candidates）、等重・スコア重み付け、ポジションサイズ計算、セクターキャップ、レジーム乗数。
- Research
  - ファクター計算（momentum / volatility / value）、将来リターン計算、IC 計算、統計サマリー等（DuckDB を利用）。
- AI
  - news_nlp: raw_news をまとめて OpenAI（gpt-4o-mini）へ送り銘柄ごとのセンチメントを ai_scores に書き込む（score_news）。
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM センチメントを合成して market_regime を算出（score_regime）。
- ユーティリティ
  - process_priority：プロセス優先度・CPU affinity 設定ユーティリティ。
  - .env 自動ロード（config.Settings）と必須環境変数検査。

前提・必要環境
- Python 3.10+
- SQLite（標準ライブラリ）
- 以下の Python パッケージ（最低限）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- OS: Linux / macOS / Windows（プロセス優先度設定は OS ごとに差異あり）

セットアップ手順（開発環境）
1. リポジトリをクローンしプロジェクトルートへ移動
   - git clone ...  
   - cd <project-root>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt があればそちらを使ってください）

4. data ディレクトリを作成
   - mkdir -p data

設定環境変数（主なもの）
- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
  - paper_trading の場合、MockBrokerClient を使用し paper_sqlite_path（既定 data/paper_trading.db）を使用
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（未設定であれば通知はスキップ）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant / partial / never / reject。デフォルト instant）
- SQLITE_PATH: monitoring DB のパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper 用 SQLite（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH / KILL_FLAG_PATH 等（監視系フラグ・PID ファイル）

.env 自動ロード
- プロジェクトルート（.git または pyproject.toml を探索）から .env と .env.local を自動で読み込みます。
- ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

使い方（主要なスクリプト・実行例）
- 実行方法の注意：パッケージとしてインポートできるように Python のパスを設定して実行するか、ルートから python -m を使ってください。
  例: project-root で python -m kabusys.run_monitoring

1) 監視ループ（SystemMonitor 単体で起動）
- 目的：システム状態をポーリングして monitoring.db に記録する
- 実行例:
  - python -m kabusys.run_monitoring
  - または python src/kabusys/run_monitoring.py
- オプション:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き（デフォルト 60）
- 停止:
  - プロセスは data/stop_requested.flag の存在をチェックして終了します。停止させたい場合はそのファイルを作成してください。

2) 実行エンジン（ExecutionEngine）
- run_execution.py は ExecutionEngine を起動します。KABUSYS_ENV に応じて mock/本番ブローカーを選択。
- 実行例:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution
- 停止:
  - 同様に data/stop_requested.flag の存在を確認して安全停止します。
- 注意:
  - Paper trading 時は paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離します。

3) Paper Trading 検証レポート
- src/kabusys/tools/paper_verification_report.py にて検証レポートを生成できます。
- 実行例:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで別 DB を指定可能（デフォルトは PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db）

4) Streamlit ダッシュボード（監視）
- 起動例（プロジェクトルートから）:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- ダッシュボードは monitoring DB を読み取り専用で開き、ポジション・オーダー・システムステータス・リスクログ等を表示します。

5) AI 機能（ニュース NLP / レジーム検出）
- AI を使う機能は OpenAI API キー（OPENAI_API_KEY）が必要です。
- Python API 例:
  - from kabusys.ai.news_nlp import score_news
  - import duckdb, datetime
  - conn = duckdb.connect('data/kabusys.duckdb')
  - score_news(conn, datetime.date(2026,4,1), api_key='sk-...')

- regime_detector:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key='...')

運用に関するファイル/フラグ
- data/stop_requested.flag
  - run_monitoring/run_execution がループ停止を検知するために使用（作成すると安全に停止する）。
- data/kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）
  - KillSwitch が検知条件を満たしたときに書き込まれる。ExecutionEngine に強制停止指示を送る目的で使用。
- data/execution.pid
  - 実行エンジンが PID を出すファイル。SystemMonitor はこの PID を見てプロセス生存をチェックする。

注意事項 / 運用メモ
- Settings は .env / .env.local を自動でロードします。OS 環境変数は .env の設定に上書きされません（.env.local は上書き可能）。
- Monitoring の初期化は各スクリプト内で行われる（init_monitoring_db を自動呼び出し）。初回実行時に適切な data ディレクトリとファイルアクセス権を確認してください。
- Paper trading モードは本番 DB と明確に分離する設計です。運用時は環境変数を確認してください。
- AI 呼び出しは外部 API へのネットワーク依存・課金が発生します。API キーとレート制限に注意してください。失敗時はフェイルセーフ（スコア 0.0 等）で継続する実装になっている箇所が多いです。
- process_priority.set_process_priority("high") を各メインスクリプトで呼び出しています。権限により失敗する場合があり、その場合は警告ロギングに留まります。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数/.env ロードと Settings クラス
  - run_monitoring.py — SystemMonitor のポーリングループ起動
  - run_execution.py — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite 用永続化層（init + MonitoringDB クラス）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — LINE push 実装
    - monitoring_engine.py — 各 Monitor を束ねる（テスト/本番ループ）
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py, order_repository.py, reconciler.py, ...（発注管理・再同期）
    - run_execution.py（起動は上位）
  - portfolio/
    - portfolio_builder.py — 候補抽出・重み付け
    - position_sizing.py — 株数決定・キャップ/丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — 将来リターン/IC/統計
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA + LLM）
  - tools/
    - paper_verification_report.py — Paper trading 用検証レポート

開発・テスト上のヒント
- DuckDB 上のテーブル（prices_daily / raw_financials / raw_news / news_symbols / ai_scores / market_regime 等）はリサーチ/AI 機能で参照されます。これらのテーブルを整備してから関数を実行してください。
- settings（kabusys.config.Settings）からアプリ設定にアクセスできます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使い .env 自動ロードを無効化すると再現性の高いテストが可能です。
- AI 呼び出しはテスト時に _call_openai_api を unittest.mock.patch 等で差し替えて外部通信を回避してください（コード側でその想定あり）。

最後に
- この README はソースコードの現在の状態に基づく導入ガイドです。実運用ではブローカー API の認証情報、資金管理、法令順守、リスク管理プロセスを十分に整備してください。

必要ならば README をもとに .env.example（推奨設定項目一覧）や運用手順（Systemd サービス定義、Dockerfile 等）を追加で作成します。必要項目を教えてください。