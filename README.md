# KabuSys — README

簡単な概要、セットアップ、使い方、ディレクトリ構成をまとめた README です。

概要
- KabuSys は日本株向けの自動売買 / 研究 / モニタリング用のコンポーネント群です。
- 主な目的:
  - ExecutionEngine による発注・リスク管理（本番 / paper_trading 切替対応）
  - 監視 (MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor) とアラート送信（LINE）
  - リサーチ（ファクター計算、特徴量探索）
  - ニュースの LLM ベース評価（OpenAI を利用したセンチメントスコア）
  - Paper Trading 検証用のレポート生成とダッシュボード表示

主な特徴
- 環境切替: KABUSYS_ENV により development / paper_trading / live を切替可能
  - paper_trading 時は MockBrokerClient を使用し、paper 用 SQLite（data/paper_trading.db）へ記録して本番 DB と分離
- モニタリング:
  - システム状態（CPU/メモリ/ディスク）や Execution プロセスの存在確認
  - 注文の滞留や約定異常価格の検出
  - ドローダウン／ポジション上限の監視と kill.flag による停止シグナル送出
  - LINE へのアラート送信（AlertManager）
  - Streamlit ダッシュボードで可視化
- リサーチ:
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB を利用）
  - 将来リターン、IC（Information Coefficient）計算など
- AI:
  - raw_news を LLM（gpt-4o-mini）で評価して銘柄別スコアを生成し ai_scores テーブルへ保存
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定
- ポートフォリオ構築:
  - 候補選定、重み計算、リスク調整（セクターキャップ、レジーム乗数）、株数計算（単元丸め・集約上限）

セットアップ手順（開発環境想定）
1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 本リポジトリに requirements.txt がない場合は少なくとも以下を入れてください:
     - duckdb, psutil, requests, openai, streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

3. 環境変数の準備
   - プロジェクトルートの .env / .env.local を利用可能（config.py が自動でロード）
   - 自動ロードを無効化したい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な環境変数（一部）:
     - KABUSYS_ENV = development | paper_trading | live (デフォルト: development)
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY (AI 機能を使う場合必須)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート用）
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
     - PAPER_FILL_MODE = instant|partial|never|reject（paper_trading の約定動作）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔[秒], デフォルト 60）
     - LOG_LEVEL（DEBUG/INFO/...）

4. データディレクトリ
   - data/ 配下に DB ファイルや PID / フラグを配置します（存在しない場合はプロセスが作成します）。
   - 主要ファイル:
     - data/monitoring.db （SQLite、監視ログ）
     - data/paper_trading.db （paper_trading 用）
     - data/kabusys.duckdb （DuckDB）
     - data/execution.pid （ExecutionEngine が書く PID）
     - data/kill.flag（KillSwitch 発動フラグ）
     - data/stop_requested.flag（run_* スクリプトの外部停止用）

実行方法（代表的なコマンド）
- 監視ループの起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒）。例: export MONITOR_POLL_INTERVAL=30
  - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用します（監視は常に本番 DB を参照）。

- ExecutionEngine の起動（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録して本番と分離します。
  - 起動時に data/stop_requested.flag が存在すると起動を中止します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数の代替）
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード起動（監視 DB を可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI / レジーム判定 等の関数はモジュールとしてインポートして利用可能:
  - kabusys.ai.score_news, kabusys.ai.regime_detector.score_regime

停止 / フラグについて
- 外部からプロセスを優雅に止めたい場合は data/stop_requested.flag を作成すると run_monitoring / run_execution が検知して終了します。
- ExecutionEngine を緊急停止したい場合、KillSwitch により data/kill.flag を書き込むことで停止シグナルを送ります（KillSwitch は監視系が判定して書き込みます）。
- kill.flag は冪等: 既にあれば上書きしません。clear() で削除できます（あるいはファイル削除）。

設定上の注意
- process priority の設定は psutil に依存します。権限不足や未対応 OS では設定がスキップされます。
- OpenAI API を使う処理は API キー必須（OPENAI_API_KEY）。レスポンスのパースや API エラー時にはフェイルセーフ（0.0 等）で継続する設計です。
- DuckDB / SQLite に対するクエリは日時のルックアヘッドバイアスを避ける実装（target_date 未満の条件等）を意識しています。
- Paper Trading 時の約定動作は PAPER_FILL_MODE により制御されます（instant / partial / never / reject）。

ディレクトリ構成（主要ファイル・モジュールと役割）
- src/kabusys/
  - __init__.py — パッケージ初期化（バージョン等）
  - config.py — 環境変数 / 設定の管理（.env の自動ロードロジック含む）
  - run_monitoring.py — SystemMonitor をポーリングする起動スクリプト
  - run_execution.py — ExecutionEngine を起動するスクリプト（paper_trading 切替対応）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポートジェネレータ
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py — 市場レジーム判定（ETF ma200 + マクロ NLP）
  - monitoring/
    - monitoring_db.py — SQLite の監視用永続化層（テーブル作成 / CRUD）
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・プロセス監視
    - trade_monitor.py — 注文滞留・約定異常の検出
    - risk_monitor.py — ドローダウン・ポジション上限監視、ダッシュボード更新
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
    - alert_manager.py — LINE API へのアラート送信
    - kill_switch.py — kill.flag の作成 / 管理ロジック
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py — 発注フロー / Order State Machine 外向 API
    - reconciler.py — 起動時の注文・ポジション再同期処理
    - （他：broker_factory, execution_engine, order_repository 等が想定）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・集約上限処理
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

サンプル .env（最小例）
- KABUSYS_ENV=development
- JQUANTS_REFRESH_TOKEN=your_jquants_token
- KABU_API_PASSWORD=your_kabu_password
- OPENAI_API_KEY=sk-...
- LINE_CHANNEL_ACCESS_TOKEN=...
- LINE_USER_ID=...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- PAPER_FILL_MODE=instant
- MONITOR_POLL_INTERVAL=60

よくある操作 / トラブルシュート
- 監視が DB に書き込めない / DB が開けない
  - ファイルパス（DUCKDB_PATH / SQLITE_PATH）やファイルパーミッションを確認してください。
- OpenAI 周りで 429 やタイムアウトが多い
  - レート制限に達している可能性があります。API リトライ / バックオフは組み込まれているものの、API 利用量を抑えるかキーを分散してください。
- process priority の変更に失敗するログが出る
  - 権限不足やプラットフォーム非対応の可能性があります（警告ログのみで処理は継続）。

補足
- 各モジュール（monitoring_db や ai, research など）は単体テスト性を重視した設計（純粋関数や接続注入）になっています。ユニットテストを書くことで安全に動作確認できます。
- 本 README はコードの主要な部分に基づいています。追加の実行オプションやコンポーネント（broker の詳細実装や ExecutionEngine の引数 等）は実装ファイルを参照してください。

必要であれば、README に以下の追記を行います:
- 依存関係の具体的な requirements.txt 例
- .env.example ファイルの完全なテンプレート
- 起動・デバッグ時のログ設定例（LOG_LEVEL の扱い）
- 実運用時のデプロイ / サービス化（systemd ユニット例）