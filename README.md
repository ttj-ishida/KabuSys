README — KabuSys (日本語)
========================

概要
----
KabuSys は日本株の自動売買／研究／監視を目的とした軽量な Python パッケージ群です。本リポジトリは主に次の機能を提供します。

- 実行エンジン（ExecutionEngine）による発注・リスク管理・再同期（reconcile）
- 監視（MonitoringEngine）: システム状態・注文滞留・リスク監視、LINE 通知、kill flag 発行
- ポートフォリオ構築ユーティリティ（候補選定・重み付け・ポジションサイジング・セクター制限）
- リサーチ（ファクター計算、特徴量探索、IC 計算）
- AI ベースのニュースセンチメント（OpenAI を用いたニュース NLP）と市場レジーム判定
- Paper Trading 用の分離 DB / レポート出力ツール
- Streamlit ベースの監視ダッシュボード

主要な設計方針:
- データ処理は DuckDB, 監視ログは SQLite（data/*.db）へ保存
- Paper Trading は本番 DB と論理的に分離
- 外部 API（OpenAI, kabuステーション 等）は設定に応じて接続
- ルックアヘッドバイアス回避やフェイルセーフ重視の実装

機能一覧
--------
- run_execution.py: ExecutionEngine 起動スクリプト（KABUSYS_ENV に応じて paper/live 切替）
  - ブローカークライアント生成（Mock を含む）
  - OrderManager / RiskManager / Reconciler の組み立てとセッション実行
- run_monitoring.py: SystemMonitor の単独ポーリング起動
  - MONITOR_POLL_INTERVAL でポーリング間隔を調整可能（デフォルト 60 秒）
  - 監視ログは常に本番 SQLite パスを使用
- monitoring package:
  - SystemMonitor: CPU/メモリ/Disk/プロセス PID・データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常の検出
  - RiskMonitor: ドローダウン・ポジション数制限の監視と dashboard 更新
  - KillSwitch: フラグファイル（data/kill.flag）を書き込むことで ExecutionEngine に停止シグナル
  - AlertManager: LINE Push による通知（クールダウン管理）
  - streamlit_dashboard.py: Streamlit で可視化
- ai package:
  - news_nlp.score_news: raw_news を集約して OpenAI でセンチメントを算出し ai_scores に書込
  - regime_detector.score_regime: ETF の MA とマクロニュースセンチメントを合成して regime を判定
- portfolio package:
  - 銘柄選定、等金額/スコア重み、リスク調整（セクターキャップ・レジーム乗数）、株数算出（単元丸め、aggregate cap）
- research package:
  - ファクター計算（momentum / volatility / value）、将来リターン、IC、統計サマリ
- tools:
  - paper_verification_report.py: Paper Trading DB を解析して検証レポート出力

セットアップ手順
----------------

前提:
- Python 3.10+（コードは typing 機能や最新ライブラリを利用）
- 必要な外部パッケージ: duckdb, psutil, openai, requests, streamlit（用途に応じてインストール）

例: 仮想環境作成と依存インストール
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（requirements.txt がない場合は個別に）
   - pip install duckdb psutil openai requests streamlit

3. データディレクトリ作成
   - mkdir -p data

環境変数 / .env
- 自動読み込み: config.py はプロジェクトルート（.git または pyproject.toml）から .env / .env.local を自動読み込みします。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 主要な環境変数（例）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 外部 API 認証用（必須なプロパティあり）
  - OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時に必須）
  - PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject、デフォルト instant）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 専用 DB（デフォルト data/paper_trading.db）
  - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager のためのトークン/宛先
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, 等

例 .env（最小）
- KABUSYS_ENV=development
- OPENAI_API_KEY=sk-...
- KABU_API_PASSWORD=your_pass
- JQUANTS_REFRESH_TOKEN=...
- LINE_CHANNEL_ACCESS_TOKEN=
- LINE_USER_ID=

使い方
------

1) 実行エンジン（本番 / paper_trading）
- Paper Trading モードで起動（環境変数で切替）
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
  - run_execution は設定により paper_trading の場合 data/paper_trading.db を使用し MockBroker を利用します。

- 本番モードで起動
  - export KABUSYS_ENV=live
  - python -m kabusys.run_execution

- 注意:
  - 実行前に .env 等で必要な API キーやパスを設定してください。
  - 起動時に PID ファイル (Settings.pid_file_path, デフォルト data/execution.pid) が作成されます。kill.flag を使って停止シグナルを送ります（Monitoring 側がフラグを作成）。

2) 監視ループ（SystemMonitor 単体）
- MONITOR_POLL_INTERVAL でポーリング間隔を指定可能（秒、デフォルト 60）
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring

- run_monitoring は監視用 DB（Settings.sqlite_path）に接続して system_status 等を記録します。Monitoring は KABUSYS_ENV に依らず本番 sqlite_path を使います。

3) Streamlit ダッシュボード
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- ダッシュボードは読み取り専用 URI で SQLite を開きます。MonitoringEngine を先に起動してデータを生成してください。

4) Paper Trading 検証レポート
- 単発の解析レポートを標準出力に出します。
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または指定 DB を使う:
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

5) AI モジュール
- news_nlp.score_news / regime_detector.score_regime を利用する場合は OPENAI_API_KEY を設定してください。API 呼び出しはリトライ・バックオフを備えていますが、料金・レート制限に注意してください。

設定（主要点の補足）
- MONITOR_POLL_INTERVAL: 監視間隔（秒）。0 以下や不正値はデフォルト 60 秒にフォールバック。
- PAPER_FILL_MODE: paper_trading 時の約定挙動（instant/partial/never/reject）。不正値はエラーを投げます。
- KILL_FLAG_PATH: KillSwitch が書き込むファイルパス（デフォルト data/kill.flag）。存在すると ExecutionEngine に停止シグナル扱い。
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に既存 kill.flag を削除するか（"1" で有効）。
- PID ファイル: ExecutionEngine は起動時に PID を保存。SystemMonitor はこの PID をチェックしてプロセス生存確認を行います。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                      — Settings / .env 自動読み込みロジック
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — SystemMonitor ポーリングスクリプト

subpackages:
- ai/
  - news_nlp.py                  — ニュースを OpenAI でスコアリングして ai_scores に書込
  - regime_detector.py           — 市場レジーム判定
- monitoring/
  - monitoring_db.py             — SQLite スキーマ初期化と簡易永続層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - reconciler.py
  - order_manager.py
  - order_repository.py (参照あり)
  - ... （その他 broker / engine 実装）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - process_priority.py          — プロセス優先度 / CPU affinity セット

データ / DB（デフォルトパス）
- data/monitoring.db              — 監視ログ（SQLite）
- data/paper_trading.db           — Paper Trading 専用 SQLite（KABUSYS_ENV=paper_trading 時に使用）
- data/kabusys.duckdb             — DuckDB（ファクター計算等で参照）

運用上の注意
-------------
- Paper Trading 用 DB は本番 DB と完全に分離するよう設計されています。運用時は必ず環境変数でパスを確認してください。
- OpenAI 利用箇所は API 失敗に対してフォールバック（多くの場合 0.0）する実装ですが、API キーの漏洩やコストに注意してください。
- Monitoring はデフォルトで本番 sqlite を参照します。検証で監視機能を使う場合も sqlite_path を適切に設定してください。
- PID / kill.flag の扱いに注意：kill.flag は一度書き込むと ExecutionEngine を停止させます。KILL_FLAG_CLEAR_ON_START を利用して起動時の自動クリアを検討してください。

貢献
----
コードの追加やバグ修正、ドキュメント改善歓迎です。Pull Request にて変更点と簡単な説明を付けてください。

ライセンス
----------
（本リポジトリにライセンスファイルが含まれる想定です。適切なライセンスを明示してください。）

以上。README に含める追加の例や、deploy / systemd / docker の起動例が必要であれば教えてください。