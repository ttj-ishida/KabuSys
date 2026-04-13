KabuSys — 日本株自動売買システム
================================

このドキュメントは、配布されたコードベース（src/kabusys 以下）を使い始めるための README です。プロジェクト概要、主要機能、セットアップ手順、実行方法、ディレクトリ構成と主要コンポーネントの説明を日本語でまとめています。

プロジェクト概要
--------------
KabuSys は日本株の自動売買を目的としたシステム群（アルファ生成 / ポートフォリオ構築 / 注文エンジン / 監視 / 解析 / AI 補助）です。  
主要な設計方針として次を掲げています。

- 各機能はモジュール化されており、テスト可能な純粋関数（ポートフォリオ、リスク調整等）と、DB/ブローカーとの接続層が明確に分離されています。
- Paper trading（KABUSYS_ENV=paper_trading）時はブローカーをモック化し、本番 DB と分離して記録します。
- 監視（Monitoring）は別プロセスで常時ポーリングしてログを永続化し、アラート・kill スイッチなどを提供します。
- OpenAI を用いたニュース NLP / レジーム判定機能を備えます（API キー必須）。

主な機能一覧
--------------
- ポートフォリオ構築
  - 候補選定、等重・スコア重みの計算、ポジションサイズ計算、セクター上限・レジーム乗数
- リサーチ
  - ファクター（モメンタム / バリュー / ボラティリティ）計算、将来リターン、IC 計算、統計サマリ
- AI（OpenAI）
  - ニュースのセンチメントスコアリング（ai_scores への書き込み）
  - マーケットレジーム判定（ma200 + マクロニュースセンチメント）
- 注文実行層（Execution）
  - OrderManager / OrderRepository / Reconciler / ExecutionEngine（発注・再同期・リスク管理）
- 監視（Monitoring）
  - SystemMonitor（プロセス・CPU/メモリ/ディスク・データ鮮度）、TradeMonitor（滞留注文・約定異常）、RiskMonitor（ドローダウン・ポジション上限）、MonitoringDB（SQLite 永続化）、AlertManager（LINE Push）、KillSwitch、Streamlit ダッシュボード
- ユーティリティ
  - process priority / cpu affinity 設定、.env 自動読み込みロジック、DB 初期化・マイグレーション支援
- CLI / スクリプト
  - 実行/監視起動スクリプト、paper trading 検証レポート生成ツール等

前提・依存
----------
最低限動かすための主要依存（例）:
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能）
- requests (LINE 通知)
- streamlit（ダッシュボード）
（プロジェクト配布に requirements.txt があればそれを使ってください）

例:
    pip install duckdb psutil openai requests streamlit

環境変数 / 設定
----------------
設定は環境変数（またはプロジェクトルートの .env / .env.local）から読み込まれます。.env 自動ロードはデフォルトで有効です（無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

主要な環境変数（抜粋）:
- KABUSYS_ENV: 起動環境（development | paper_trading | live）。デフォルト: development
  - paper_trading の場合、MockBroker を使い PAPER_TRADING_SQLITE_PATH に記録します。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用のトークン（必須な箇所あり）
- KABU_API_PASSWORD: kabu ステーション API 用パスワード（必須な箇所あり）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector で必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）用。未設定なら通知は行われずログのみ
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: Monitoring 用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH / KILL_FLAG_PATH: プロセス監視・kill flag 用パス
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant | partial | never | reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）

セットアップ手順
----------------
1. リポジトリをクローン／チェックアウトし、仮想環境を作る（推奨）。
2. 依存パッケージをインストール:
   - 例: pip install -r requirements.txt
   - もしくは最低限: pip install duckdb psutil openai requests streamlit
3. 必要な環境変数を設定:
   - プロジェクトルートに .env を作成するか、環境に export してください。
   - 例 (.env):
       KABUSYS_ENV=development
       OPENAI_API_KEY=sk-...
       KABU_API_PASSWORD=...
       JQUANTS_REFRESH_TOKEN=...
       LINE_CHANNEL_ACCESS_TOKEN=...
       LINE_USER_ID=...
4. データディレクトリを作成:
       mkdir -p data
   DB は起動時に自動で作成／マイグレーションされます（init_monitoring_db を通じて）。

主な実行方法（使い方）
--------------------

- 監視ループを起動（常時ポーリングして monitoring DB にログを残す）:
    python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60）。
  - 実行時にプロセス優先度を High に設定しようとします（psutil が必要）。

- 注文実行エンジンを起動:
    python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading DB に記録します（本番 DB と完全分離）。
  - 起動時に監視テーブルが存在することを保証するため init_monitoring_db が呼ばれます。

- Streamlit ダッシュボード（監視 UI）:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only モードで SQLite を開き、Positions / Orders / System / Overview を表示します。

- Paper Trading 検証レポート生成:
    python -m kabusys.tools.paper_verification_report
  - オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 簡易的に監視 DB（または paper trading DB）から稼働率、注文成功率、レイテンシ等を集計し PASS/FAIL 判定を出力します。

- AI: ニューススコアリング（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - OpenAI API キー（引数または環境変数 OPENAI_API_KEY）が必要です。

- Kill flag 管理
  - KillSwitch は data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
  - 手動でクリアする場合はファイル削除、もしくは KillSwitch.clear() を呼び出します。
  - 実行時に Settings.kill_flag_clear_on_start を使って起動時に自動クリアするオプションがあります。

注意事項 / 実装上のポイント
-----------------------
- 設定読み込み:
  - config.Settings はプロジェクトルート（.git または pyproject.toml）を基に .env / .env.local を自動読み込みします。CWD に依存しない設計。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は冪等にテーブルと基本的なカラムを作成し、既存 DB に対して必要カラムを追加する簡易マイグレーションを行います（例: latency_ms, peak_value の追加）。
- Paper trading:
  - PAPER_FILL_MODE = instant/partial/never/reject の取り扱いに注意してください（不正な値は Settings でエラー）。
- OpenAI 呼び出し:
  - news_nlp / regime_detector は OpenAI を利用し、429/ネットワークエラー/5xx に対して指数バックオフでリトライします。API 失敗時はフェイルセーフ（スコア 0.0 等）で継続する設計です。
- プロセス優先度:
  - 実行スクリプトは起動時に set_process_priority("high") を呼びます。psutil の権限や OS により設定に失敗することがあります（ログに警告）。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py                  — パッケージ定義、バージョン
- config.py                    — 環境設定 / .env 自動ロード / Settings クラス
- run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py             — ExecutionEngine 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py                 — ニュースのセンチメントを OpenAI で評価・ai_scores に書込
  - regime_detector.py         — レジーム判定（ma200 + マクロニュース）
- monitoring/
  - monitoring_db.py           — SQLite 永続化層（テーブル作成・永続化 API）
  - system_monitor.py          — CPU/Memory/Disk/プロセス/DuckDB データ鮮度チェック
  - trade_monitor.py           — 注文滞留・約定異常チェック
  - risk_monitor.py            — ドローダウン / ポジション上限監視
  - kill_switch.py             — kill.flag 書込みユーティリティ
  - alert_manager.py          — LINE Push 実装（クールダウン管理）
  - monitoring_engine.py      — 各 Monitor を束ねるポーリングエンジン
  - streamlit_dashboard.py    — Streamlit ダッシュボード（UI）
- portfolio/
  - portfolio_builder.py       — 候補選定・重み計算
  - position_sizing.py         — 発注株数算出（lot 単位・リスク・上限管理）
  - risk_adjustment.py         — セクターキャップ・レジーム乗数
- research/
  - factor_research.py         — Momentum/Value/Volatility ファクター計算（DuckDB）
  - feature_exploration.py     — 将来リターン / IC / 統計サマリ
- execution/
  - order_manager.py           — Order 管理（状態遷移、DB 保存、送信ロジック）
  - reconciler.py              — 起動時の注文・ポジション再同期
  - （その他ブローカー、Engine などのモジュール）
- tools/
  - paper_verification_report.py — Paper trading 検証レポート生成 CLI
- utils/
  - process_priority.py        — プロセス優先度 / CPU affinity 設定ユーティリティ
- data/ (実行時に DB 等を格納する想定のディレクトリ)
  - monitoring.db (デフォルト)
  - paper_trading.db (paper_trading 用)
  - kabusys.duckdb (DuckDB)

開発／デバッグのヒント
--------------------
- モード切替:
  - KABUSYS_ENV を切り替えることで paper_trading と live の挙動差（DB・ブローカー実装）を切り替えられます。
- ローカルで OpenAI を使う場合は環境変数 OPENAI_API_KEY をセットしてください。テスト時は API 呼び出し箇所をモック化できます（news_nlp._call_openai_api / regime_detector._call_openai_api）。
- monitoring_db.init_monitoring_db() は監視用テーブルを作るため、安全に何度でも呼べます。起動時に自動実行されます。
- streamlit ダッシュボードは監視 DB を read-only で開くため、MonitoringEngine を動かしていないとデータは表示されません。

ライセンス・貢献
----------------
（この README では省略しています。配布リポジトリに LICENSE ファイルがある場合はそちらを参照してください。）

最後に
------
まずは .env を整え、data ディレクトリを作成し、run_monitoring / run_execution をそれぞれ起動してシステム全体の動作を確認してください。paper_trading モードで安全に検証→レポート生成 → 実運用モードへ移行することを推奨します。問題があれば該当モジュールのログ（logging）を確認し、またコード内の docstring に設計意図・注意点が詳述されています。