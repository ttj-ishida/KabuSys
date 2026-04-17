# KabuSys

日本株自動売買システムのコアライブラリ群。ポートフォリオ構築、ポジションサイジング、監視、実行エンジン、リサーチ、AI（ニュースNLP / レジーム判定）などを含むモジュール群です。

この README はリポジトリ内の主要スクリプト・モジュールの使い方とセットアップ手順、ディレクトリ構成をまとめたものです。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 実行・使い方
- 環境変数（主要）
- ディレクトリ構成（ファイル一覧と説明）

---

プロジェクト概要
- KabuSys は日本株の自動売買を目的としたモジュール群の集合体です。
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）、リスク調整（セクターキャップ・レジーム乗数）、注文管理と実行エンジン、監視（監視DB・各種モニタ・アラート）、リサーチ（ファクター計算・特徴量探索）、ニュースNLP を用いた銘柄センチメント評価などの機能を提供します。
- 実行環境によって本番 / paper_trading を切り替え可能で、paper_trading 時は本番DBと完全に分離された専用の SQLite DB を使用します。

---

主な機能一覧
- portfolio
  - 銘柄候補選定（select_candidates）
  - 等配分・スコア加重の重み計算（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクター集中制限・レジーム乗数（apply_sector_cap / calc_regime_multiplier）
- execution
  - OrderManager、ExecutionEngine、Reconciler による注文発行・状態同期・再起動時の復旧
  - Broker クライアント抽象化（paper_trading では Mock を使用）
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor：CPU/メモリ/ディスク、データ鮮度、滞留注文・約定異常、ドローダウン・ポジション数監視
  - MonitoringDB：SQLite に監視ログを永続化（system_status / trade_logs / positions / risk_logs / dashboard）
  - AlertManager：LINE Push による通知（クールダウン管理）
  - KillSwitch：リスク条件により ExecutionEngine を停止するためのフラグファイル制御（data/kill.flag）
  - Streamlit ベース簡易ダッシュボード（監視 DB を読み取り専用で表示）
- research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- ai
  - news_nlp: raw_news から銘柄ごとのセンチメントを OpenAI に問い合わせ、ai_scores に格納
  - regime_detector: ETF（1321）の MA とマクロニュースセンチメントを合成して市場レジーム判定
- tools
  - paper_verification_report: Paper Trading DB（data/paper_trading.db デフォルト）から日次検証レポートを生成

---

セットアップ手順（開発 / 実行環境）
1. 必要な Python バージョンをインストール（3.9+ を推奨）
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - requirements.txt がある場合: pip install -r requirements.txt
   - 主な依存パッケージ（プロジェクト内で使用）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボード用)
   - 具体的なバージョンは requirements.txt を参照してください
4. 環境変数の用意
   - プロジェクトルートに .env または .env.local を置けば自動で読み込まれます（OS 環境変数が優先）
   - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
   - .env の書式は shell 形式（export KEY=val も可）。コメント・クォート等のパースに対応しています
5. データディレクトリ
   - デフォルトのデータベースパス:
     - monitoring (sqlite): data/monitoring.db
     - paper_trading sqlite: data/paper_trading.db
     - duckdb: data/kabusys.duckdb
   - 起動時に必要に応じて data ディレクトリを作成してください

---

主要な環境変数（抜粋）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使うときに必須）
- PAPER_FILL_MODE: Paper Trading の Fill モード（instant | partial | never | reject）。デフォルト: instant
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite パス（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch のフラグファイルパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

.env の自動読み込み
- プロジェクトルート（.git か pyproject.toml があるディレクトリ）から .env / .env.local を自動的に読み込みます。
- OS 環境（既存のキー）は上書きされませんが .env.local は override=True（ただし OS 環境は保護）で読み込まれます。

---

実行・使い方（代表的なコマンド）
- 監視ループ（SystemMonitor 単体のポーリング起動）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（秒）
  - python -m kabusys.run_monitoring
  - 挙動:
    - プロセス優先度を high に設定（可能な場合）
    - monitoring 用 SQLite（settings.sqlite_path）に接続してテーブルを初期化
    - DuckDB に接続し SystemMonitor.check_once を繰り返し実行
    - data/stop_requested.flag を検知するとループを終了

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB に記録（本番 DB と分離）
  - 起動時に data/stop_requested.flag が既にある場合は起動せず終了
  - ExecutionEngine はスレッドで run_session を実行し、停止フラグを検知するとエンジンへ停止命令を送る
  - 実行中は data/execution.pid に PID を書きます

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）
  - 出力: 稼働率 / 注文成功率 / 送信率 / レイテンシ（P95 等） のサマリと PASS/FAIL 判定

- Streamlit 監視ダッシュボード（可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、ダッシュボードを表示します

- AI 機能
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡してニュースセンチメントを ai_scores テーブルへ書き込む
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF（1321）とマクロニュースを使って日次の market_regime を算出して保存
  - OpenAI API を使用するため OPENAI_API_KEY の設定が必要（引数で渡すことも可能）
  - OpenAI への呼び出しはレート制限や一時エラーに対してリトライやフォールバック処理を実装済み

- KillSwitch の操作
  - KillSwitch は条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります
  - 手動でフラグをクリアするには: rm data/kill.flag（あるいは KillSwitch.clear() を呼ぶ）
  - ExecutionEngine 側は起動時に kill_flag があれば起動を中止します

---

モジュール間の運用上のポイント
- paper_trading と live（本番）は DB を分けて安全に運用する設計です。必ず KABUSYS_ENV を適切に設定してください。
- run_monitoring は監視 DB（sqlite）に常に本番のパス(settings.sqlite_path) を使います（監視は運用対象に依存）。
- Process priority や CPU affinity の設定は可能な限り行いますが、権限やプラットフォームに依存し失敗する場合はログを出してスキップします。
- DB スキーマは init_monitoring_db() により冪等に初期化／マイグレーションされます（簡易的なカラム追加処理を含む）。

---

ディレクトリ構成（主要ファイルと概要）
- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 環境変数・.env の読み込みと設定取得
  - run_monitoring.py
    - SystemMonitor のポーリングスクリプト（MONITOR_POLL_INTERVAL で間隔指定）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading 時は専用 DB / Mock Broker）
  - tools/
    - __init__.py
    - paper_verification_report.py
      - Paper Trading DB から検証レポートを生成
  - portfolio/
    - portfolio_builder.py
      - select_candidates, calc_equal_weights, calc_score_weights
    - position_sizing.py
      - calc_position_sizes（各種 allocation_method 対応）
    - risk_adjustment.py
      - apply_sector_cap, calc_regime_multiplier
    - __init__.py
  - monitoring/
    - monitoring_db.py
      - init_monitoring_db, MonitoringDB（監視ログ操作）
    - system_monitor.py
      - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・PID チェック
    - trade_monitor.py
      - TradeMonitor: 滞留注文・約定異常を検出
    - risk_monitor.py
      - RiskMonitor: ドローダウン・ポジション上限監視
    - kill_switch.py
      - KillSwitch: data/kill.flag の書き込み/検出/クリア
    - monitoring_engine.py
      - MonitoringEngine: 各モニタの連携・アラート発行・KillSwitch 評価
    - alert_manager.py
      - AlertManager: LINE Push 送信（クールダウン管理）
    - streamlit_dashboard.py
      - Streamlit ベースの監視 UI
    - __init__.py
  - research/
    - factor_research.py
      - calc_momentum, calc_volatility, calc_value（DuckDB を用いたファクター計算）
    - feature_exploration.py
      - calc_forward_returns, calc_ic, factor_summary, rank
    - __init__.py
  - ai/
    - news_nlp.py
      - raw_news を LLM で評価して ai_scores に書き込むロジック（バッチ・検証・バックオフ実装あり）
    - regime_detector.py
      - マクロニュース + ETF ma200 を使った market_regime の判定と保存
    - __init__.py
  - execution/
    - reconciler.py
      - 起動時の注文／ポジションの照合と自動復旧
    - order_manager.py
      - OrderManager（発注ワークフロー管理）
    - order_repository.py
      - SQLite を使った注文永続化（ファイルは別）
    - order_record.py
      - OrderState 等のドメインモデル
    - execution_engine.py
      - （実行エンジン本体 — ファイル断片がリポジトリ全体に存在）
    - broker_factory.py / broker_api.py
      - ブローカークライアント抽象化とファクトリ
  - data/
    - 実行時に生成されるファイル（例: data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb, data/execution.pid, data/kill.flag）
  - utils/
    - process_priority.py
      - プラットフォーム差異を隠蔽したプロセス優先度 / CPU affinity ユーティリティ

（上記はリポジトリの代表的なファイル群です。実際のファイル構成はプロジェクトツリーをご確認ください。）

---

トラブルシューティング / 運用メモ
- DB が開けない場合
  - run_monitoring / streamlit の起動時に DB path が正しいか、読み取り権限があるか確認してください。
  - streamlit は監視 DB を read-only モードで開きます—ファイル URI を用いて読み込みます。
- OpenAI 呼び出しで失敗する場合
  - OPENAI_API_KEY が設定されているか確認。API の RateLimit とネットワーク状況にも注意。
  - LLM 呼び出しはリトライ・フォールバック実装がありますが、完全失敗時は該当データのスキップや macro_sentiment=0.0 で継続する設計です。
- kill.flag / stop_requested.flag
  - 運用停止はフラグファイルを書き込むか、外部から削除して起動を制御します。誤って残さないよう注意してください。

---

ライセンス / 貢献
- （ここにライセンス情報を入れてください。例: MIT License）
- バグ報告 / 機能提案は issue を使用してください。

---

補足
- ここに記載の挙動はソースコード中のドキュメンテーションコメントに基づきまとめています。詳細な API や内部仕様は各モジュールの docstring を参照してください。
- 実運用する前に paper_trading モードで十分に検証してください（DB 分離、PAPER_FILL_MODE の理解、KillSwitch のテストなど）。

--- 

必要であれば README に含めるコマンド例や .env.example のテンプレート、より詳細なアーキテクチャ図や ER 図、開発者向けのユニットテスト実行方法なども作成します。どれを優先しますか？