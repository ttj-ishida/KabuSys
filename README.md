KabuSys
=======

日本株自動売買システムの軽量コア実装（モジュール群の抜粋）。  
この README はリポジトリ内の主要モジュールから自動生成的にまとめた利用説明書です。

主な目的
-------
- 戦略に基づく銘柄選定・配分・株数決定（portfolio）
- 注文管理・実行・再同期（execution）
- 監視・アラート・自動停止判定（monitoring）
- リサーチ用ファクター計算・検証ユーティリティ（research）
- ニュースの LLM ベース解析によるセンチメント（ai）
- Paper Trading 用の分離 DB と検証レポート（tools）

機能一覧
--------
- 環境設定管理（kabusys.config.Settings）
  - .env / .env.local の自動読み込み機能（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
  - KABUSYS_ENV: development / paper_trading / live の切替
- 実行エンジン起動スクリプト（run_execution.py）
  - 本番 / Paper Trading を切り替え可能。Paper Trading 時は MockBroker + data/paper_trading.db を使用
  - 実行時にプロセス優先度を上げる
- 監視エンジン起動スクリプト（run_monitoring.py）
  - System / Trade / Risk の監視をポーリングして監視ログを SQLite に保存
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可（デフォルト 60 秒）
  - 監視は KABUSYS_ENV に関わらず本番用 sqlite_path を使用
- 監視コンポーネント
  - SystemMonitor: CPU/メモリ/ディスク、プロセス PID、価格データ鮮度をチェック
  - TradeMonitor: 滞留注文、約定異常価格を検出
  - RiskMonitor: ドローダウンやポジション上限を監視、ダッシュボード更新・リスクログ記録
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine 停止シグナルを発行
  - AlertManager: LINE Messaging API による通知（クールダウン管理）
  - Streamlit ベースの監視ダッシュボード（streamlit_dashboard.py）
- Portfolio モジュール
  - 候補選定、等配分・スコア配分、セクター制限、レジーム乗数、株数決定（単元丸め・aggregate cap）
- Research / AI
  - DuckDB を用いたファクター計算（momentum / volatility / value）
  - 将来リターン・IC 計算、ファクター統計
  - news_nlp: OpenAI を使ったニュースセンチメント集計 → ai_scores テーブルへ書込
  - regime_detector: ETF + マクロニュースを合成して市場レジーム判定 → market_regime へ書込
- Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）
  - 稼働率、注文成功率、送信率、P95 レイテンシ等の集計と PASS/FAIL 判定

前提・依存
----------
（実装ファイルから推測される主要依存）
- Python 3.10+（型注釈や構文に基づく推定）
- duckdb
- psutil
- requests
- streamlit（ダッシュボード）
- openai（AI モジュール）
- sqlite3（標準ライブラリ）
その他、requirements.txt があればそれを使用してください。

セットアップ手順
----------------
1. リポジトリをクローン / チェックアウト
2. 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - 可能なら requirements.txt を用いる: pip install -r requirements.txt
   - 無ければ最低限: pip install duckdb psutil requests streamlit openai
4. データディレクトリ作成
   - mkdir -p data
5. 環境変数の設定
   - .env または .env.local をプロジェクトルートに配置すると自動で読み込まれます（OS 環境変数が優先）。
   - 自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

主要な環境変数（要設定）
------------------------
- KABUSYS_ENV
  - 値: development | paper_trading | live
  - デフォルト: development
- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- OPENAI_API_KEY（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信に使用、未設定なら送信スキップ）
- SQLITE_PATH（監視用 SQLite。デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（Paper Trading 用 DB。デフォルト: data/paper_trading.db）
- DUCKDB_PATH（DuckDB ファイル。デフォルト: data/kabusys.duckdb）
- MONITOR_POLL_INTERVAL（監視ポーリング秒数。デフォルト: 60）
- PAPER_FILL_MODE（paper_trading の MockBroker の成立方式。instant|partial|never|reject。デフォルト: instant）
- LOG_LEVEL（DEBUG|INFO|...。デフォルト: INFO）
- PID_FILE_PATH / KILL_FLAG_PATH（ファイルパスの上書き）

使い方（主要な実行コマンド）
------------------------

- 実行エンジン（ExecutionEngine）を起動
  - 本番/検証は KABUSYS_ENV で切替:
    - 本番想定: KABUSYS_ENV=live python -m kabusys.run_execution
    - Paper Trading: KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行はスレッドでエンジンを起動し、data/stop_requested.flag や data/kill.flag を検知すると停止処理を行います。
  - 実行前に kill flag をクリアしたい場合:
    - python -c "from kabusys.config import Settings; import pathlib; pathlib.Path(Settings().kill_flag_path).unlink(missing_ok=True)"

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL を環境変数で上書き可（例: MONITOR_POLL_INTERVAL=30）

  注意: run_monitoring は KABUSYS_ENV に関わらず Settings.sqlite_path（本番パス）を使用します。

- Streamlit ダッシュボード（ローカルで監視 DB を参照）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または DB パスを指定: python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI 機能（ニューススコアリング / レジーム判定）
  - OPENAI_API_KEY を設定のうえ、該当モジュールを呼び出す
  - 例（プログラム内から）:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key=os.environ["OPENAI_API_KEY"])

監視/停止シグナル
----------------
- data/kill.flag: KillSwitch による ExecutionEngine 停止要因。存在するとエンジンに停止シグナルを送ります。
- data/stop_requested.flag: run_execution / run_monitoring の外部停止フラグ（スクリプトは存在を検知して終了します）。
- PID ファイル: ExecutionEngine 起動時にデータ/pid ファイルを記録し、SystemMonitor は PID 存在確認でプロセス生存チェックをします。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py — パッケージ定義
- config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings クラス）
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

サブパッケージ（主なファイル）
- ai/
  - news_nlp.py — ニュースを OpenAI でスコアリングし ai_scores に書き込む
  - regime_detector.py — ETF MA + マクロニュースでレジーム判定
- monitoring/
  - monitoring_db.py — SQLite テーブル初期化・読み書きクラス（MonitoringDB）
  - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・PIDチェック
  - trade_monitor.py — 注文滞留・約定異常検出
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — 停止フラグ管理
  - alert_manager.py — LINE push 通知
  - monitoring_engine.py — 監視コンポーネント束ねるエンジン
  - streamlit_dashboard.py — Streamlit ダッシュボード
- portfolio/
  - portfolio_builder.py — 候補選定、配分重み計算
  - position_sizing.py — 発注株数計算、aggregate cap, lot 切捨て
  - risk_adjustment.py — セクター制限、レジーム乗数
- research/
  - factor_research.py — momentum/volatility/value ファクター
  - feature_exploration.py — 将来リターン、IC、統計サマリー
- execution/
  - order_manager.py — 注文作成/キャンセル等の外向き API
  - reconciler.py — 再起動時のブローカー照合・ポジション差分検出
  - （ExecutionEngine 等の他コンポーネントは該当ディレクトリに存在）
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

データファイル（デフォルト）
- data/monitoring.db — 監視ログ SQLite（Settings.sqlite_path）
- data/paper_trading.db — Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）
- data/kabusys.duckdb — DuckDB（Settings.duckdb_path）
- data/execution.pid — ExecutionEngine の PID（デフォルト PID ファイル）
- data/kill.flag, data/stop_requested.flag — 停止フラグ

設計上の注意点
--------------
- 設定の自動読み込みは .env / .env.local をプロジェクトルートから探します。プロジェクトルートの検出は .git または pyproject.toml に基づきます。
- run_monitoring は監視用の SQLite を常に Settings.sqlite_path（本番）で開きます。テスト目的で別 DB を使う場合はコード側でパスを書き換えてください。
- AI 機能は外部 API（OpenAI）に依存し、API 失敗時はフェイルセーフ（デフォルトスコアやスキップ）で処理継続するよう設計されています。
- Paper Trading は本番 DB と分離して data/paper_trading.db を使用します（KABUSYS_ENV=paper_trading）。

トラブルシューティング（よくある点）
-----------------------------------
- .env の自動読み込みを期待しているが環境変数が読み込まれない
  - プロジェクトルートが見つからない (.git / pyproject.toml が無い) と自動ロードはスキップされます。
  - テスト時などで自動ロードを無効にしている場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を確認。
- OpenAI の呼び出しで失敗するとスコア取得が行われない
  - OPENAI_API_KEY が設定されているか確認。API レスポンスの 429/5xx は内部でリトライ処理を行いますが、最終的に失敗すると部分的にスキップされます。
- monitor/engine が stop flag を検知してすぐ終了する
  - data/stop_requested.flag の存在をチェックしているため、不要なら削除してください。

ライセンス・貢献
----------------
この README はコードベースの説明用です。リポジトリに LICENSE ファイルがあればそれに従ってください。バグ報告や機能提案は Issue を作成してください。

最後に
------
この README はコード内のドキュメンテーションコメントに基づいて要点をまとめています。実運用前には必ず設定（.env）、依存関係、DB のバックアップ方針、LINE/OpenAI 等の API キー管理を確認してください。