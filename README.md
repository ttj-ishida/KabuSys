KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買および運用監視を目的とした小規模なモジュール群です。  
本リポジトリはトレード実行（ExecutionEngine）、監視（MonitoringEngine）、ファクター計算 / リサーチ、AI ベースのニュースセンチメント評価、ポートフォリオ構築ユーティリティなどのコンポーネントを含みます。  
設計方針として「実行系とリサーチ系の分離」「DB はローカルファイル（SQLite / DuckDB）」「外部 API 呼び出しは最小限でフェイルセーフにする」を採用しています。

主な機能
-------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / Paper Trading を切り替え可能（KABUSYS_ENV）
  - ブローカークライアントのファクトリ、リスク管理、オーダー管理、リコンシリエーション機能を備える
  - Paper Trading 時は専用 SQLite（data/paper_trading.db）にログ保存
- MonitoringEngine（run_monitoring.py）
  - システム状態（CPU/メモリ/ディスク）、データ鮮度、注文滞留、約定異常、ドローダウン等を定期チェック
  - kill.flag による ExecutionEngine 停止シグナル出力・LINE 通知（AlertManager）との連携
  - Streamlit ベースの監視ダッシュボード用スクリプトあり
- ポートフォリオ構築ユーティリティ（portfolio/*）
  - 候補選定、等配分／スコア加重、ポジションサイズ計算、セクター制限、レジーム乗数
- リサーチ / ファクター計算（research/*）
  - モメンタム、ボラティリティ、バリュー等のファクター計算、IC 計算、将来リターン計算
  - DuckDB を用いて prices_daily / raw_financials などのテーブルを参照して純粋関数で実装
- AI モジュール（ai/*）
  - ニュース NLP（OpenAI）で銘柄別センチメントを算出し ai_scores テーブルへ書き込み
  - 市場レジーム判定（ETF MA + マクロニュースセンチメントを合成）
  - API 呼び出しはリトライ・バックオフ・バリデーションを組み込みフェイルセーフに設計
- ツール
  - Paper Trading の検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

セットアップ
----------
1. 推奨: Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（最低限）
   - pip install duckdb psutil requests streamlit openai
   - （SQLite は Python 標準ライブラリに含まれます）

   ※ 実際のプロジェクトでは requirements.txt / pyproject.toml を用意してください。  
   ※ duckdb はリサーチ用途、psutil はプロセス／システム情報取得、streamlit はダッシュボード、openai はニュース NLP / レジーム判定用です。

3. 実行時の PYTHONPATH
   - 開発中はプロジェクトルートから以下のように src をパスに含めて実行します:
     - PYTHONPATH=src python -m kabusys.run_monitoring
     - Windows PowerShell: $env:PYTHONPATH="src"; python -m kabusys.run_monitoring

4. 環境変数 / .env
   - 設定は環境変数またはプロジェクトルートの .env / .env.local で行います。
   - 自動読み込みの振る舞い:
     - OS 環境 > .env.local > .env の優先順位で読み込まれます。
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます。
   - 主要な環境変数:
     - KABUSYS_ENV: 実行環境（development / paper_trading / live）
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須な箇所あり）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須な箇所あり）
     - OPENAI_API_KEY: OpenAI API キー（ai の機能を使う場合）
     - PAPER_FILL_MODE: paper_trading 時の約定モード（instant / partial / never / reject）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite パス（デフォルト: data/paper_trading.db）
     - SQLITE_PATH: 監視 DB（data/monitoring.db）、Monitoring は環境に関わらず本番 sqlite_path を使用
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PID_FILE_PATH / KILL_FLAG_PATH: 実行制御用ファイルパス
     - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

使い方（コマンド例）
-----------------
- 監視ループを起動
  - PYTHONPATH=src python -m kabusys.run_monitoring
  - 環境変数で間隔を上書き: MONITOR_POLL_INTERVAL=30 PYTHONPATH=src python -m kabusys.run_monitoring

- 実行エンジンを起動（本番／紙トレ切替）
  - 本番: KABUSYS_ENV=live PYTHONPATH=src python -m kabusys.run_execution
  - Paper Trading: KABUSYS_ENV=paper_trading PYTHONPATH=src python -m kabusys.run_execution
    - Paper Trading は data/paper_trading.db に記録され、本番 DB と分離される

- Paper Trading 検証レポートを生成
  - PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db。--db オプションで変更可。

- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI / レジーム判定・ニューススコアリング
  - モジュール関数を呼び出して使用（OpenAI API キー必須）
  - 例: kabusys.ai.score_news(conn, target_date, api_key=...)

運用に関する注意点
----------------
- Monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（本番の monitoring DB）を使用します。
- Paper Trading は settings.is_paper=True のときに settings.paper_sqlite_path（data/paper_trading.db）を使い本番データと完全分離されます。
- run_execution/run_monitoring 実行時にプロセス優先度を "high" に設定する試みを行います（psutil により OS に依存）。権限不足や未対応 OS では警告が出ますが続行します。
- kill.flag（デフォルト data/kill.flag）を書き込むことで ExecutionEngine 停止を指示します。KillSwitch はドローダウンやポジション上限を検知した場合にフラグを書き込みます。
- OpenAI 等の外部 API を利用する機能はネットワーク障害や API エラーに対しリトライ・フェイルセーフを実装していますが、本番利用時は API レートやコストに注意してください。

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数および .env 自動ロード / Settings クラス
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- run_execution.py
  - ExecutionEngine の起動スクリプト（paper_trading 切替あり）

サブパッケージ:
- ai/
  - news_nlp.py        — ニュースを OpenAI でスコアリング、ai_scores へ書き込み
  - regime_detector.py — ETF MA + マクロニュースでレジーム判定
- monitoring/
  - monitoring_db.py   — SQLite テーブル作成 / DB 操作ラッパー
  - system_monitor.py  — CPU/メモリ/ディスク/データ鮮度 / PID チェック
  - trade_monitor.py   — 注文滞留・約定異常チェック
  - risk_monitor.py    — ドローダウン・ポジション上限監視
  - kill_switch.py     — kill.flag 管理
  - alert_manager.py   — LINE 通知（push）
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - order_manager.py
  - reconciler.py
  - （ブローカー / order_repository 等の実装が存在する前提）
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
  - process_priority.py — プロセス優先度・CPU affinity ユーティリティ

補足
----
- DB 初期化: run_monitoring/run_execution の起動時に init_monitoring_db() が呼ばれ、監視用テーブル群を冪等的に作成します。
- 型注釈・設計ドキュメント参照: 各モジュールに関数の目的・仕様・エッジケースの説明コメントが付与されています。コード内コメントを参照して実装や拡張の際の設計意図を確認してください。

貢献・拡張
----------
- requirements.txt / pyproject.toml を追加して依存管理を明確にしてください。
- BrokerClientFactory / ブローカー API 実装はプロジェクト固有の箇所です。Paper / Live の実装を用意してください。
- テスト: 単体テスト・統合テストを追加して、API 呼び出しのモックや DB 操作の検証を行ってください。

以上。必要であれば、README に記載する具体的な .env.example や起動スクリプトの systemd ユニット例、Dockerfile / docker-compose 例も作成します（要望に応じて追加します）。