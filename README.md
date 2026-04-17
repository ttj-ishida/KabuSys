# KabuSys — README

概要
---
KabuSys は日本株向けの自動売買・研究・監視を目的とした軽量なPythonコードベースです。  
主な役割は以下の通りです。

- Execution Engine：ブローカーとのやり取りによる発注／注文管理（paper_trading モードあり）
- Monitoring：システム状態／注文／リスクを監視してログ・アラート・Kill Switch を提供
- Research：DuckDB 上の価格・財務データからファクターや統計指標を計算
- AI：ニュースを LLM でスコアリングしてセンチメント／レジーム判定に利用
- Tools：Paper Trading 検証レポート生成などの補助ツール

主要な設計方針として「本番データとテスト（paper_trading）の分離」「ルックアヘッドバイアス回避」「フェイルセーフ（API失敗時のフォールバック）」が重視されています。

機能一覧
---
- Execution
  - 実売買／paper_trading（MockBroker）切替
  - OrderManager / OrderRepository による注文状態管理
  - Reconciler による起動時の自動リコンシリエーション
  - RiskManager による取引リスク制御
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセス状態/データ鮮度監視
  - TradeMonitor：滞留注文、約定異常価格検出
  - RiskMonitor：ドローダウン・ポジション上限監視
  - KillSwitch：条件に応じて停止フラグを書き込み（Execution 停止）
  - AlertManager：LINE Push による通知（クールダウン管理）
  - Monitoring DB（SQLite）と Streamlit ダッシュボード
- Research / Portfolio
  - ファクター計算（momentum/volatility/value）
  - 将来リターン・IC 計算・統計サマリー
  - 銘柄選定、等重／スコア重み、ポジションサイズ計算、セクター制限、レジーム乗数
- AI
  - news_nlp: OpenAI（gpt-4o-mini）を使ったニュースセンチメント集計と ai_scores への書き込み
  - regime_detector: ETF MA200 とマクロニュースを組み合わせた市場レジーム判定
- ユーティリティ
  - 環境設定ロード（.env / .env.local、自動ロードの有効/無効化）
  - プロセス優先度・CPU affinity 設定ユーティリティ

セットアップ手順
---
前提
- Python 3.10+（コード内で | 型ヒントなどを利用）
- システムに sqlite3（標準ライブラリ）とデータを格納するためのディレクトリ権限

推奨パッケージ（少なくとも以下が必要）
- duckdb
- psutil
- openai
- requests
- streamlit

例: 仮想環境作成と依存インストール
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

2. 必要パッケージをインストール（プロジェクトに requirements.txt がある場合はそれを利用）
   - pip install duckdb psutil openai requests streamlit

3. パッケージとしてインストール（任意）
   - pip install -e .

データディレクトリ作成
- data ディレクトリを作る（デフォルトDB等を配置）
  - mkdir -p data

環境変数
- 自動ロード: プロジェクトルートの .env / .env.local を自動で読み込みます（OS 環境変数が優先）。
- 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化します。

主な環境変数（Settings 参照）
- 必須（実行環境による）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行制御 / パス
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading のときは ExecutionEngine は MockBroker を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に書き込む
  - SQLITE_PATH: 監視用 SQLite データベース（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト: data/paper_trading.db）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
  - PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject。デフォルト: instant）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（未設定時は通知をスキップ）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）。環境変数から上書き可。

備考
- Monitoring（run_monitoring）は KABUSYS_ENV に関わらず「本番 sqlite_path」（Settings.sqlite_path）を使用して監視ログを保存します。
- Execution（run_execution）は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使い本番 DB と完全分離されます。

使い方（実行例）
---
1) 監視ループ起動
- デフォルトポーリング（60秒）で SystemMonitor を回します。
- コマンド:
  - python -m kabusys.run_monitoring
- ポーリング間隔を変更するには環境変数を設定:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 停止:
  - プロジェクトの data/stop_requested.flag が存在するとループは正常終了します（スクリプトは起動時に stop フラグを確認します）。

2) Execution エンジン起動
- コマンド:
  - python -m kabusys.run_execution
- paper_trading モード（MockBroker）で起動するには:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
- 実行中の停止:
  - data/stop_requested.flag を作成するとエンジンは停止処理を始めます。
- 実行時に data/execution.pid に PID を書きます（pid_file は Settings で変更可）。

3) Streamlit ダッシュボード
- Monitoring DB を読み取り専用で表示する UI。
- 起動例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

4) Paper Trading 検証レポート（ツール）
- SQLite（paper_trading.db）を集計して簡易レポートを出力します。
- 使い方:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH も利用可）。

5) AI / リサーチ API（Python から直接呼ぶ）
- ニューススコアリング（例）:
  - from datetime import date
  - import duckdb
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect("data/kabusys.duckdb")
  - score_news(conn, date(2026,4,1), api_key="YOUR_OPENAI_KEY")
- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, date(2026,4,1), api_key="YOUR_OPENAI_KEY")

注意点
- OpenAI 呼び出しは APIキーが必要です。api_key 引数または環境変数 OPENAI_API_KEY を設定してください。
- AI モジュールは失敗時にフォールバック動作（0.0 など）するよう設計されていますが、API 料金やレート制限に注意してください。

ディレクトリ構成（主要ファイル）
---
src/kabusys/
- __init__.py — パッケージ定義、__version__
- config.py — 環境変数読み込み / Settings クラス（.env 自動ロード、必須チェック）
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 切替）
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
- monitoring/
  - monitoring_db.py — SQLite スキーマ初期化 / 永続化 API（MonitoringDB）
  - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - trade_monitor.py — 滞留注文・約定価格異常監視
  - risk_monitor.py — ドローダウン／ポジション上限監視
  - kill_switch.py — kill.flag 書込みロジック（Execution 停止）
  - alert_manager.py — LINE プッシュ通知
  - monitoring_engine.py — 複数 Monitor を束ねるループ（テスト用 run_once, 本番 run）
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - order_manager.py — OrderManager（注文作成・同期など）
  - order_repository.py — SQLite ベースの注文永続化（別ファイルに存在）
  - reconciler.py — 起動時の注文／ポジション照合
  - ...（ブローカーファクトリ等）
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 発注株数決定・スケーリング
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — momentum/volatility/value の計算（DuckDB）
  - feature_exploration.py — 将来リターン、IC、統計サマリー
- ai/
  - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に保存
  - regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント）
- tools/
  - paper_verification_report.py — Paper trading 検証レポート CLI

補足・運用上のヒント
---
- 監視対象の DB（DuckDB / SQLite）は適切にバックアップしてください。
- paper_trading を用いることで本番 DB と完全に分離して検証できます。paper_trading 時は PAPER_TRADING_SQLITE_PATH を指定して運用してください。
- Kill Switch（データベースのリスクログや drawdown 等に応じて）を適切にテストし、誤発動しない閾値設定を行ってください。
- .env や .env.local で機密情報（APIキー等）を管理する際はファイルのアクセス権に注意してください。
- streamlit ダッシュボードは読み取り専用モード（URI に ?mode=ro）で接続するため、監視 DB への干渉を避けられます。

ライセンス・貢献
---
このリポジトリに付随するライセンスや貢献規約がある場合はプロジェクトルートの LICENSE / CONTRIBUTING を確認してください。

その他
---
不明点や追加したい機能（たとえば銘柄別 lot_size 対応、より柔軟な通知チャネル、細かなポジション管理など）があれば設計意図に沿って拡張できます。README に書かれていない内部APIや詳細実装（特に OrderRepository、BrokerAPI の具体実装など）はコード内コメントをご参照ください。