# KabuSys

日本株向けの自動売買システム（ライブラリ兼実行スクリプト群）の簡易リポジトリ説明書です。  
この README はコードベース（src/kabusys 以下）の主要コンポーネントの概要、セットアップ、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能群を持つモジュール群です。

- 注文管理・発注エンジン（ExecutionEngine / OrderManager / Reconciler）
- リスク管理（RiskManager / RiskMonitor）
- 監視（SystemMonitor / TradeMonitor / MonitoringEngine）
- ポートフォリオ構築（候補選定・重み付け・株数計算）
- 研究用モジュール（ファクター計算、特徴量解析）
- ニュース NLP によるセンチメントスコアリング（OpenAI 使用）
- Paper Trading（本番 DB と完全分離での検証）
- モニタリング用 Streamlit ダッシュボード
- 検証レポート生成ツール（Paper Trading 向け）

設計思想としては、DB（SQLite / DuckDB）に記録して永続化しつつ、外部 API 呼び出しは明確に分離、フェイルセーフ（API失敗時でも継続）に配慮しています。

---

## 機能一覧（主なもの）

- 実運用向け/検証向け（paper_trading）で異なる DB / ブローカーを使用可能
- ExecutionEngine：発注・状態管理・再起動時のリコンシリエーション
- MonitoringEngine：プロセス稼働、CPU/メモリ/Disk、注文滞留、約定異常、ドローダウン監視
- KillSwitch：基準を満たすと flag ファイルを書き込み ExecutionEngine を停止
- AlertManager：LINE Push によるアラート送信（クールダウン制御）
- portfolio モジュール：銘柄選定、重み付け、ポジションサイズ計算、セクター制約
- research：DuckDB を利用したファクター計算/将来リターン/IC など
- ai.news_nlp：OpenAI を用いたニュースのセンチメントスコアを ai_scores に書込
- ai.regime_detector：マクロニュース + ETF MA200 で市場レジーム判定
- streamlit ダッシュボード：監視データの可視化
- tools.paper_verification_report：Paper Trading の検証レポート作成

---

## 前提条件 / 依存ライブラリ（主なもの）

- Python 3.9+
- duckdb
- psutil
- requests
- openai（news_nlp / regime_detector 使用時）
- streamlit（ダッシュボード実行時）

インストール例：
pip install duckdb psutil requests openai streamlit

（プロジェクト用 requirements.txt があればそちらを利用してください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし作業ディレクトリを src の上に置く（またはパッケージとして扱う）
2. 仮想環境を作成・有効化：
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
3. 依存ライブラリをインストール：
   pip install duckdb psutil requests openai streamlit
4. （任意）プロジェクトルートに .env または .env.local を用意：
   - .env は OS 環境変数で未設定のキーのみ読み込まれる
   - .env.local は既存 OS 環境変数を上書きする（protected を除く）
   自動読み込みは既定で有効。無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. data ディレクトリや PID/flag 用ディレクトリは実行時に自動生成されますが、必要に応じて作成してください。
   例: mkdir -p data

---

## 主要な環境変数（主なもの）

- KABUSYS_ENV: 実行環境を指定。development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、MockBroker を使い DB は paper_trading 用 SQLite を使用
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須な場合）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須な場合）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector で必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject、デフォルト: instant）
- PID_FILE_PATH: Execution PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が書き込む flag（デフォルト: data/kill.flag）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env 自動読み込みを無効化
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）

Settings クラス（kabusys.config.Settings）が詳細を管理しています。必須項目が未設定だと起動時に ValueError を投げます。

---

## 実行方法

各スクリプトはパッケージとして実行できます（src が PYTHONPATH に含まれる状態を想定）。

1. ExecutionEngine（実際の発注エンジン）
   - 本番環境（デフォルト）:
     KABUSYS_ENV=live python -m kabusys.run_execution
   - Paper Trading（MockBroker + data/paper_trading.db に記録）:
     KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - 実行中の停止は data/stop_requested.flag（内部的に参照）や kill.flag によって制御されます。
   - 実行前に kill.flag をクリアするには Settings.kill_flag_clear_on_start を有効にするか、手動で削除してください。

2. Monitoring（SystemMonitor のポーリング）
   - ポーリングループ起動:
     python -m kabusys.run_monitoring
   - ポーリング間隔を環境変数で上書き:
     MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - 監視は常に本番の sqlite_path（Settings.sqlite_path）を使います（KABUSYS_ENV に依存しません）。

3. Streamlit ダッシュボード（監視可視化）
   - 実行例:
     streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ダッシュボードは monitoring DB を読み取り専用で開きます（起動中の MonitoringEngine が DB を書き込みます）。

4. Paper Trading 検証レポート生成
   - 例:
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パスはオプション --db で指定可能（デフォルト: data/paper_trading.db または 環境変数 PAPER_TRADING_SQLITE_PATH）。

5. AI 関連（ニューススコアリング / レジーム判定）
   - OpenAI API キーが必要（OPENAI_API_KEY または関数引数で提供）
   - ai.news_nlp.score_news(conn, target_date, api_key) や ai.regime_detector.score_regime(conn, target_date, api_key) をコードから呼び出します。
   - 実行は DuckDB 接続（kabusys.config.Settings.duckdb_path）を渡して行います。

---

## 停止 / フラグファイル

- data/stop_requested.flag: run_execution.py / run_monitoring.py がループ終了判定で参照（存在すると終了）
- data/kill.flag: KillSwitch が異常検出時に書き込み、ExecutionEngine 停止を促す。存在する場合エンジンは起動しない（起動時にクリアする設定あり）。
- data/execution.pid: ExecutionEngine が起動時に PID を書き込み、SystemMonitor は PID ファイルの有無・生存チェックを行う。

---

## DB / マイグレーション

- Monitoring DB スキーマは kabusys.monitoring.monitoring_db.init_monitoring_db で冪等的に作成されます。実行時に必要なテーブル・インデックスを作成します。
- 既存テーブルにカラムがなければ ALTER TABLE で追加する簡単なマイグレーションロジックを含みます（例: trade_logs.latency_ms, dashboard.peak_value）。
- DuckDB は時系列価格・財務データなどの大規模分析向けに使用します（research / ai モジュールが参照）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py — パッケージ初期化、バージョン定義
  - config.py — 環境変数・設定の読み込みロジック（.env 自動読み込み、Settings クラス）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度／CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite を使った監視ログの永続化層（CRUD）
    - system_monitor.py — CPU/メモリ/Disk/プロセス/データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の書込ロジック
    - alert_manager.py — LINE API を通じた通知（クールダウン付き）
    - monitoring_engine.py — 各 Monitor を束ねてポーリングするエンジン
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py — 発注の高レベル API / 状態遷移管理
    - reconciler.py — 起動時の自動復旧（ブローカーとの照合）
    - ...（OrderRepository 等の実装が含まれる想定）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・リスク制限
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム/ボラティリティ/バリュー計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py — ニュースセンチメントスコア（OpenAI 呼出し）→ ai_scores 書込
    - regime_detector.py — マクロ + MA200 を使った日次レジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI

---

## 開発メモ / 注意点

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を起点）を探索して行われます。テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Settings は起動時に値の妥当性チェック（列挙型チェック・数値レンジ等）を行います。不正値があると起動時に例外が発生します。
- Paper Trading モードは本番 DB と完全分離を意図しています（settings.is_paper を用いて paper_sqlite_path を使用）。
- OpenAI 関連の処理は外部 API に依存するため、API キーがない場合は該当処理を呼ばないか、エラー処理を行ってください。モジュール内では失敗時にフォールバックする設計です（多くは 0.0 やスキップ）。
- process_priority（高優先度設定）や CPU affinity はプラットフォーム依存です。アクセス権限がない場合は警告を出してスキップします。
- monitoring のポーリング間隔は MONITOR_POLL_INTERVAL で変更可能。0 や負数が指定されるとデフォルト（60秒）にフォールバックします。

---

## よくある操作例

- Monitoring の即時1回実行（テスト用）
  - MonitoringEngine を使ったユニット/スクリプトレベルの実行は MonitoringEngine.run_once() を呼ぶことで行えます（コードレベル）。
- Paper Trading レポート作成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

必要であれば README に実際のコマンド例（systemd サービス定義、Dockerfile、CI 設定例）や、より詳細な環境変数の表（説明・既定値・必須/任意）を追加できます。どの情報を優先して深掘りしたいか教えてください。