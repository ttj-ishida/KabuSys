README
======

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を行うための小規模なフレームワークです。本リポジトリには以下の主要機能が実装されています。

- 発注エンジン（ExecutionEngine）：シグナルに基づく発注処理、リスクゲート、Push ドレイン、再同期（Reconciliation）
- 監視（MonitoringEngine / SystemMonitor 等）：プロセス・リソース・データ鮮度・注文滞留・リスク監視、LINE 通知、Streamlit ダッシュボード
- ポートフォリオ構築：候補選定、重み付け、ポジションサイジング、セクター制限、レジーム調整
- リサーチ：ファクター計算（モメンタム、ボラティリティ、バリュー）、特徴量探索（IC、将来リターンなど）
- AI サポート：ニュースセンチメント（OpenAI）を使った銘柄スコアリング、マクロニュースによるレジーム判定
- DB 層：DuckDB（時系列・リサーチ用）、SQLite（監視・発注ログ用）

主な設計方針
- ルックアヘッドバイアスに注意して時刻/日付の扱いを明示的にする
- 本番/ペーパートレードを明確に分離（paper_trading では専用 DB を使用）
- クラッシュ耐性（2段階永続化、リコンシリエーション）
- フェイルセーフ：API 失敗時は安全側のデフォルトで継続（例：AI 呼び出し失敗 → スコア 0）

機能一覧
--------
- Execution
  - Signal を読み発注（OrderManager / RiskManager / BrokerClientFactory 経由）
  - 発注の2相永続化、OrderSent の再同期サポート
  - Reconciler による再起動後の自動リコンシリエーション
  - Paper trading モード（MockBrokerClient）で本番 DB と完全分離
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス起動状態 / データ鮮度の監視
  - TradeMonitor: 注文滞留・約定異常価格の検出
  - RiskMonitor: ドローダウン / ポジション数上限の監視
  - KillSwitch: 条件到達時に flag ファイルを書いて Execution を停止させる
  - AlertManager: LINE Push による通知（クールダウン制御）
  - Streamlit ダッシュボード（読み取り専用）
- Portfolio
  - 銘柄候補選定、等重/スコア重み付け、リスクベースのポジションサイズ計算
  - セクターキャップ、レジーム乗数
- Research
  - DuckDB 上でのファクター計算（momentum/volatility/value）
  - 将来リターン、IC 計算、統計サマリー
- AI
  - news_nlp.score_news: raw_news をまとめ OpenAI に送信して ai_scores を更新
  - regime_detector.score_regime: ETF MA とマクロセンチメントを合成して market_regime を更新

動作要件（主な依存）
--------------------
- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボードを使う場合)
- 標準ライブラリ: sqlite3, logging, datetime 等

セットアップ手順
----------------

1. リポジトリをクローンして仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -r requirements.txt
   （requirements.txt がない場合は上の依存を個別に pip install してください）

3. 環境変数 / .env
   - プロジェクトルートに .env または .env.local を置くと自動読み込みされます（OS 環境変数が優先）。
   - 自動読み込みを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

主要な環境変数（デフォルト付き）
- KABUSYS_ENV: 起動環境。development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants トークン
- KABU_API_PASSWORD: （必須）kabu API パスワード（本番で使用）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（未設定時は送信をスキップ）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject、デフォルト: instant）
- PID_FILE_PATH: Execution 用 PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: KillSwitch のフラグファイル（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするフラグ（"1" で有効）

使い方
------

一般的な実行例

- 監視プロセスの起動（ポーリングループ）
  - MONITOR_POLL_INTERVAL 環境変数（秒）で間隔上書き可能（デフォルト 60 秒）
  - 実行:
    - python -m kabusys.run_monitoring
    - または python src/kabusys/run_monitoring.py
  - 特記事項:
    - 起動時にプロセス優先度を "high" に設定しようとします（失敗しても継続）
    - KABUSYS_ENV に関わらず monitoring は sqlite_path（本番）を使います
    - kill.flag の存在は Execution 停止シグナルとして扱われます

- ExecutionEngine（発注エンジン）の起動
  - 実行:
    - python -m kabusys.run_execution
    - または python src/kabusys/run_execution.py
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録して本番 DB と分離します
    - 起動時にプロセス優先度を "high" に設定
    - 起動時 Reconciler による同期 / 自動復旧を行う設計
    - PID ファイル（Settings.pid_file_path）を使ってプロセスの在不在判定を行います

- Streamlit ダッシュボード（読み取り専用）
  - 実行:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only モードで SQLite を URI 読み取り専用で開きます。MonitoringEngine が先に起動していることを想定

- AI / リサーチ関数の利用
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続（conn）を渡し、OPENAI_API_KEY を環境変数または api_key 引数で指定します
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - 同様に OpenAI API を利用してレジームを判定して market_regime テーブルへ書き込み

- データベース初期化
  - 監視用 SQLite スキーマは init_monitoring_db(conn) で冪等に作成されます。run_monitoring / run_execution 内で自動的に呼ばれます。

Kill switch（停止フラグ）
- KillSwitch は data/kill.flag に理由テキストを書き込み、ExecutionEngine に停止を促します
- Kill flag は KillSwitch.clear() や ExecutionEngine 起動時の設定で削除できます（設定: KILL_FLAG_CLEAR_ON_START）
- 既に flag がある場合は上書きされません（冪等）

ペーパートレードについて
- KABUSYS_ENV=paper_trading とすると:
  - MockBrokerClient を使って外部ブローカーにアクセスしない
  - SQLite は PAPER_TRADING_SQLITE_PATH を使い、本番の SQLITE_PATH と分離
  - PAPER_FILL_MODE により約定振る舞いを制御（instant / partial / never / reject）

ログと優先度
- 起動スクリプトは logging.basicConfig(level=logging.INFO) を用いるため、LOG_LEVEL 環境変数で Settings.log_level を調整できます
- set_process_priority("high") を試みますが、権限不足等で失敗する可能性があります（例外はログで警告に留められます）

ディレクトリ構成
----------------
（主要ファイルと簡単な説明）

- src/kabusys/
  - __init__.py              — パッケージ初期化、バージョン
  - config.py                — 環境設定読み込み（.env 自動ロード、Settings）
  - run_monitoring.py        — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite スキーマと MonitoringDB ラッパー
    - system_monitor.py      — システム・データ鮮度チェック
    - trade_monitor.py       — 注文滞留・約定異常チェック
    - risk_monitor.py        — ドローダウン・ポジション数監視
    - kill_switch.py         — kill.flag 書込みロジック
    - alert_manager.py       — LINE 通知（クールダウン管理）
    - monitoring_engine.py   — 全モニターを束ねるエンジン
    - streamlit_dashboard.py — Streamlit 監視ダッシュボード（読み取り専用）
  - execution/
    - execution_engine.py    — 発注エンジンの主要ロジック
    - order_manager.py       — 発注状態遷移 / broker 呼び出しの外向け API
    - reconciler.py          — 再起動時の注文/ポジション同期
    - order_repository.py    — （別ファイル）SQLite の発注 DB ラッパー
    - broker_*               — ブローカークライアント実装（Factory 等）
    - risk_manager.py        — 実行時のリスクゲート
  - portfolio/
    - portfolio_builder.py   — 候補選定、等重/スコア重み付け
    - position_sizing.py     — 株数計算、aggregate cap のスケーリング
    - risk_adjustment.py     — セクター制限、レジーム乗数
  - research/
    - factor_research.py     — momentum/volatility/value ファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - ai/
    - news_nlp.py            — ニュースセンチメントの LLM 呼び出しと書き込みロジック
    - regime_detector.py     — マクロニュース + MA によるレジーム判定

補足 / 運用上の注意
-------------------
- DB バックアップ・アクセス制御は運用環境で適切に設定してください。監視 DB（SQLite）は単一ファイルなので同時書き込みやバックアップタイミングに注意が必要です。
- OpenAI 等の外部 API を利用する機能はレート制限・障害を考慮した実装になっていますが、API キーの管理とコストに注意してください。
- process priority / cpu affinity の変更は実行環境（OS / 権限）によって効果が異なります。権限不足の場合はログで通知されます。
- Paper trading を使う場合でも、テストと本番の DB / 設定が確実に分離されていることを確認してください。

ライセンス・貢献
----------------
- 本リポジトリのライセンス情報があればここに追記してください。
- バグ報告・プルリクエストは歓迎します。まず Issue を立ててください。

以上。必要であれば各コマンドや設定ファイルのサンプル（.env.example）や運用手順書を追加で作成します。どの部分を詳しく書いてほしいか教えてください。