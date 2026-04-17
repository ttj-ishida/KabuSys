# KabuSys

小規模な日本株自動売買システムのライブラリ／ランタイム群です。  
このリポジトリは戦略のポートフォリオ構築、注文発行・管理、監視・アラート、研究用ファクター計算、LLM を使ったニュースセンチメント・レジーム判定などのコンポーネントで構成されています。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を含みます。

- 戦略側: ファクター計算・特徴量探索、ポートフォリオ構築、ポジションサイズ計算
- 実行側: ブローカーラッパー、OrderManager、ExecutionEngine（起動／実行スレッド）
- 監視側: システム・注文・リスク監視、アラート（LINE）、監視 DB（SQLite）、Streamlit ダッシュボード
- 研究／ツール: Paper Trading 検証レポート生成、研究用ユーティリティ
- AI 統合: OpenAI を用いたニュースセンチメント（ai/news_nlp.py）や市場レジーム判定（ai/regime_detector.py）

設計方針の例:
- DuckDB を使って時系列データ（prices_daily / raw_financials など）を高速に扱う
- 監視ログは SQLite（data/monitoring.db）に永続化
- Paper Trading は本番 DB と完全に分離（data/paper_trading.db）
- 環境変数と .env / .env.local による設定管理（自動ロード。不要なら KABUSYS_DISABLE_AUTO_ENV_LOAD=1）

---

## 主な機能一覧

- ポートフォリオ構築
  - 候補選定（スコア順）、等金額／スコア加重で重み生成
  - セクター上限の適用、レジーム乗数（bull/neutral/bear）
  - ポジションサイズ決定（risk-based、equal、score）
- 注文実行・管理
  - OrderManager: 発注、重複検知、状態遷移管理
  - Reconciler: 起動時のブローカー照合（リコンシリエーション）
- 監視・アラート
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、プロセス生存チェック
  - TradeMonitor: 滞留注文・約定異常価格検知
  - RiskMonitor: ドローダウン／ポジション上限監視とリスクイベント記録
  - KillSwitch: 指定条件で停止フラグ（data/kill.flag）を作成して ExecutionEngine を停止
  - AlertManager: LINE Push による通知（クールダウン管理）
  - MonitoringEngine: これらを束ねたポーリングループ
  - Streamlit ベースの監視ダッシュボード（read-only）
- AI 機能
  - news_nlp: OpenAI でニュースを集約して銘柄ごとのセンチメントを ai_scores に書込
  - regime_detector: MA とマクロニュースを合成して日次レジーム判定を行い market_regime に書込
- ツール
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率・成功率・レイテンシ等）

---

## 必要条件（概略）

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- SQLite（組み込みのものを使用）
- ネットワーク接続（LINE や OpenAI を使う場合）

依存関係はプロジェクト側で requirements.txt を用意している想定です。なければ以下をインストールしてください（例）:

pip install duckdb psutil requests openai streamlit

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows では .venv\Scripts\activate)

2. 必要なパッケージをインストール
   - pip install -r requirements.txt  （requirements.txt がある場合）
   - または個別に: pip install duckdb psutil requests openai streamlit

3. 環境変数の設定
   - プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます（デフォルト動作）。
   - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. データディレクトリ作成
   - data ディレクトリを作成しておくと各種 PID / DB / フラグが格納されます:
     - mkdir -p data

5. 必須の環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン
   - KABU_API_PASSWORD: kabu API 用パスワード
   - OPENAI_API_KEY: OpenAI を利用する場合に必要
   - （運用上）LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート送信に使用

.env の例（最低限の例）
    JQUANTS_REFRESH_TOKEN=xxxxxxxx
    KABU_API_PASSWORD=secret
    OPENAI_API_KEY=sk-...
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

---

## 主要な環境変数と挙動

- KABUSYS_ENV: 起動環境。allowed: development, paper_trading, live
  - paper_trading: MockBroker を用い、Paper Trading 専用 DB（PAPER_TRADING_SQLITE_PATH）を使用
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）。run_monitoring が参照。デフォルト 60
  - 不正な値や 0/負数はデフォルト 60 にフォールバック
- PAPER_FILL_MODE: Paper Trading の約定モード（instant, partial, never, reject）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite path（デフォルト data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite path（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- OPENAI_API_KEY: news_nlp / regime_detector が使用
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager による通知

設定は .env / .env.local / OS 環境変数の順に読み込まれます（OS 環境変数が優先）。

---

## 使い方（実行方法）

リポジトリ内のスクリプトはパッケージモジュールとして実行可能です（各ファイルに main() が定義されています）。

- 監視プロセスの起動（SystemMonitor 単体）
  - python -m kabusys.run_monitoring
  - 動作: process priority を high に設定 → monitoring DB 初期化 → DuckDB 接続 → SystemMonitor のポーリングループ
  - オプション: 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔変更（秒）
  - 停止: data/stop_requested.flag を作成するとループは終了します（または Ctrl+C）

- ExecutionEngine（注文実行）の起動
  - python -m kabusys.run_execution
  - 動作: process priority を high に設定 → 環境に応じた SQLite を選択（paper_trading なら paper DB）→ BrokerClient を生成 → ExecutionEngine をスレッドで実行
  - paper_trading の場合、MockBrokerClient が使用され、data/paper_trading.db に記録されます
  - 停止: data/stop_requested.flag が作成されるとエンジンを止めます。ExecutionEngine は data/execution.pid を書きます

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only で SQLite を URI モードで開く（モニタ用 DB を起動中に参照）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 日付指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH を指定するか、PAPER_TRADING_SQLITE_PATH 環境変数で指定

- AI バッチ処理（プログラムから呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

注意:
- OpenAI を使う機能は API キー必須（引数か環境変数 OPENAI_API_KEY）
- 各種 DB 書き込みはトランザクションで行われる（冪等化を意識）

---

## 停止とフラグファイル

- data/stop_requested.flag
  - run_monitoring.py / run_execution.py はこのファイルの存在を確認し、存在時に安全に停止します
- data/execution.pid
  - ExecutionEngine が起動時に書き込む PID ファイル。SystemMonitor はこの PID を参照してプロセス生存を判定する
- data/kill.flag
  - KillSwitch がトリガー条件を満たしたときに作成される停止フラグ（ExecutionEngine 停止のための外部トリガー）
- Settings.kill_flag_clear_on_start
  - 環境変数 KILL_FLAG_CLEAR_ON_START=1 を設定すると、起動時に kill.flag を自動でクリアする挙動が期待されます（設定フラグとして用意）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ定義
- config.py — 環境変数 / .env ロード、Settings クラス
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

サブパッケージと主なファイル:
- ai/
  - news_nlp.py — ニュースを集約して OpenAI で銘柄別センチメントを生成
  - regime_detector.py — MA とマクロニュースを合成して市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite スキーマ初期化／永続化 API
  - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・PID チェック
  - trade_monitor.py — 滞留注文／約定異常検知
  - risk_monitor.py — ドローダウン・ポジション上限の監視
  - kill_switch.py — 停止フラグ作成ユーティリティ
  - alert_manager.py — LINE による通知
  - monitoring_engine.py — 各 Monitor を束ねる実行エンジン
  - streamlit_dashboard.py — 監視ダッシュボード
- execution/
  - reconciler.py — 再起動時の同期（リコンシリエーション）
  - order_manager.py — 注文作成 / 状態同期
  - ほか（broker_factory, execution_engine, order_repository 等が存在する想定）
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算
  - risk_adjustment.py — セクター制限・レジーム乗数
- research/
  - factor_research.py — Momentum/Value/Volatility 等のファクター計算（DuckDB 経由）
  - feature_exploration.py — 将来リターン・IC・統計サマリ等
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成ツール
- utils/
  - process_priority.py — プロセス優先度設定（Windows / POSIX 対応）
- data/ （運用で生成されるファイル置き場）
  - monitoring.db（SQLite、デフォルト）
  - paper_trading.db（Paper Trading 用）
  - kabusys.duckdb（DuckDB）
  - execution.pid, stop_requested.flag, kill.flag など

---

## 開発・運用上の注意

- Paper Trading と本番 DB は分離されています。KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB を使用するため誤って本番で発注するリスクを低減できます。
- OpenAI 呼び出しは冪等性・フェイルセーフを考慮しており、API失敗時はスコアをスキップ（0 あるいは何もしない）して処理を続行しますが、APIキーが未設定だとエラーになる箇所があります。ENV の設定を確認してください。
- MonitoringDB はマイグレーション処理を内包しています（既存テーブルにカラムがなければ追加されます）。
- process priority / cpu affinity の設定は可能ですが、権限や OS により設定が失敗するケースがあるため警告ログにとどめる実装です。
- Streamlit ダッシュボードは読み取り専用で DB を読み込むため、監視プロセスが稼働している環境で使うことを想定しています。

---

不足している点や README に追加したい情報（例: 実際の API クレデンシャルの配置方法、CI 手順、単体テストの実行方法など）があれば教えてください。必要に応じて README にサンプル .env.example や起動スクリプトの systemd ユニット例なども追記します。