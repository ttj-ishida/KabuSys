# KabuSys

日本株自動売買システムのコアライブラリ群と運用用ツール群です。本リポジトリは取引実行エンジン、監視コンポーネント、ポートフォリオ構築ロジック、リサーチ／AI モジュールなどを含みます。

---

## プロジェクト概要

KabuSys は以下の機能を備えたトレーディング基盤を想定した Python パッケージです。

- 注文作成・送信・状態管理を行う ExecutionEngine（Broker 抽象化）
- 監視（System / Trade / Risk）とアラート / Kill Switch の仕組み
- ポートフォリオ構築（候補選定・重み化・ポジションサイズ算出・セクター制約）
- リサーチ用ファクター計算（モメンタム / ボラティリティ / バリュー等）
- ニュースの NLP によるセンチメント付与（OpenAI API を利用）
- 運用補助ツール（paper trading 検証レポート、Streamlit ダッシュボード等）
- 設定管理（.env 自動読み込み、環境変数ベース）

設計上、DB は SQLite（監視データ / paper_trading 用）および DuckDB（時系列価格やファイナンスデータ）を想定しています。OpenAI を使う機能は API キーが必要です。

---

## 主な機能一覧

- Execution
  - 注文作成 / 送信 / 同期（OrderManager, Reconciler）
  - Paper Trading モード（モックブローカー、paper DB に完全分離）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / 実行プロセス監視・データ鮮度チェック
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限監視（kill.flag を書き込む KillSwitch）
  - AlertManager: LINE Push による通知（クールダウン管理）
  - MonitoringEngine: 各 Monitor を束ねたポーリングループ
  - Streamlit ダッシュボード（リアルタイム／読み取り専用）
- Portfolio
  - 候補選定（スコア順）、等金額・スコア加重配分
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（risk_based / equal / score）
- Research / AI
  - ファクター計算（momentum, volatility, value）
  - 特徴量解析、IC（Information Coefficient）計算ユーティリティ
  - news_nlp: OpenAI を用いたニュースセンチメント取得と ai_scores テーブルへの書込
  - regime_detector: MA200 とマクロニュースセンチメントを合成した市場レジーム判定
- ユーティリティ
  - 設定管理（Settings）: .env 自動読み込み（.env / .env.local）、必須チェック
  - process_priority: psutil を使ったプロセス優先度 / CPU affinity 設定
  - DB 初期化・マイグレーション補助（monitoring_db.init_monitoring_db など）
- 運用ツール
  - paper_verification_report: Paper Trading の検証レポート生成ツール（CLI）
  - streamlit_dashboard: 監視ダッシュボード（Streamlit ベース）

---

## セットアップ手順

前提
- Python 3.9+
- pip（または poetry 等のパッケージ管理ツール）
- システムにより以下のライブラリをインストール

推奨パッケージ（requirements の例）
- duckdb
- psutil
- requests
- openai
- streamlit

例: pip を使う場合
```bash
pip install duckdb psutil requests openai streamlit
```

プロジェクトのルートに配置する .env（オプション）
- 本プロジェクトは実行時にプロジェクトルート（.git または pyproject.toml の位置）を探して .env/.env.local を自動読み込みします（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- .env の例:
```
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
PAPER_FILL_MODE=instant
LOG_LEVEL=INFO
```

注意:
- 必須の環境変数（コード中で _require を使っているもの）は不足時に ValueError を投げます。例えば JQUANTS_REFRESH_TOKEN や KABU_API_PASSWORD は実稼働で必要です。
- デフォルトの DB パスは data/ 以下に設定されています。適宜ディレクトリを作成してください。

ファイル/ディレクトリ作成:
```bash
mkdir -p data
```

---

## 使い方（主要コマンド・実行例）

1. ExecutionEngine を起動する（本番 / paper_trading 切替）
- 本番（デフォルト KABUSYS_ENV=development を live に切替すると live 挙動に）
```bash
export KABUSYS_ENV=live
python -m kabusys.run_execution
```

- Paper Trading（MockBroker を使い、DB は data/paper_trading.db に分離）
```bash
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution
```
ポイント:
- run_execution は起動時にプロセス優先度を "high" に設定し、SQLite と DuckDB に接続します。
- Paper Trading の場合、Settings.is_paper が True となり paper_sqlite_path を使用します。

2. 監視ループ（MonitoringEngine / SystemMonitor の単発起動スクリプト）
```bash
python -m kabusys.run_monitoring
```
オプション:
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
注意:
- run_monitoring は環境にかかわらず「本番 sqlite_path」を使用して監視ログを永続化します（monitoring 用 DB は共有で想定）。

3. Streamlit ダッシュボード（監視データ閲覧）
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- DB を読み取り専用で開きます。MonitoringEngine を先に起動してデータを用意してください。

4. Paper Trading 検証レポート生成
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
```
- 引数なしでも動作します。デフォルト DB は data/paper_trading.db。

5. AI / リサーチ機能の利用（プログラム的に）
- news_nlp.score_news(conn, target_date, api_key=...)
  - DuckDB 接続を渡してニュースセンチメントを ai_scores テーブルへ書き込みます。OPENAI_API_KEY が必要。
- ai.regime_detector.score_regime(conn, target_date, api_key=...)
  - 市場レジーム判定を market_regime テーブルに書き込む。OPENAI_API_KEY が必要。

注意点:
- OpenAI 呼び出し部は API のレート制限や一時エラーに対してリトライロジックを実装していますが、API キーと利用料は利用者の責任です。
- process_priority 設定には管理者権限が必要な場合があります（特に nice の負の値など）。

---

## 重要な環境変数（抜粋）

- KABUSYS_ENV: 実行環境 ("development", "paper_trading", "live")
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）
- PAPER_FILL_MODE: paper_trading における MockBroker の埋め方（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite パス（デフォルト data/paper_trading.db）
- SQLITE_PATH: monitoring 用 SQLite パス（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で必須）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必要な機能で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（本番 API 使用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE Push）用

設定管理について:
- .env と .env.local を自動読み込みします（OS 環境変数が優先）。.env.local は .env を上書きします。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py — パッケージ宣言（バージョン等）
  - config.py — Settings / .env 自動読み込み / 必須 env チェック
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート（CLI）
  - execution/
    - order_manager.py — 注文管理
    - reconciler.py — 起動時のリコンシリエーション
    - (その他 broker_factory, execution_engine, order_repository 等：Execution の中心)
  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化 / MonitoringDB ラッパ
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag の書込 / クリア
    - alert_manager.py — LINE Push（クールダウン管理）
    - monitoring_engine.py — まとめるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 株数算出・aggregate cap
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value の計算（DuckDB）
    - feature_exploration.py — forward returns / IC / summaries
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — レジーム判定（MA200 + macro sentiment）
  - data/ （想定：実行時 DB ファイルを配置）
    - data/kabusys.duckdb (DuckDB, デフォルト)
    - data/monitoring.db (SQLite, 監視ログ)
    - data/paper_trading.db (paper_trading 用 SQLite)

（上記は主要ファイルのみを抜粋しています。実際の submodule にさらに多くの実装ファイルがあります。）

---

## 運用上の注意 / ベストプラクティス

- 監視（run_monitoring）は production sqlite_path を参照します。環境にかかわらず同じ監視 DB を想定しているため、運用時は監視用 DB のバックアップ・権限を適切に設定してください。
- process priority の設定は psutil を利用します。設定に失敗した場合はログに警告が出ますが、処理は継続します。
- KillSwitch はデータベース上の RiskMonitor 等の結果で条件を満たした場合、flag ファイルを書き込むことで ExecutionEngine 停止を促します。ExecutionEngine は起動時に kill_flag_clear_on_start の挙動を参照してフラグをクリアできます。
- OpenAI 呼出しは料金が発生します。API キーと費用管理は運用者の責任で行ってください。テスト時はモック化して実行することを推奨します。
- Paper Trading モードは実運用と完全に DB を分離しているため、動作確認や検証に利用できます。

---

## 補足 / 開発者向け

- DuckDB / SQLite を使った SQL ベースの処理が多いので、大きなデータや分析処理は DuckDB に格納することを推奨します（prices_daily、raw_financials、raw_news 等）。
- AI 関連関数は外部 API 呼び出しを行うため、ユニットテストでは _call_openai_api を patch してモックする設計になっています（ソース内コメント参照）。
- 設計方針として「ルックアヘッドバイアス防止」のために各モジュールは date 引数や接続を呼び出し側から渡すことで deterministic に動くようになっています。テストでは日付を固定して実行してください。

---

必要であれば、README に以下を追加できます:
- 依存関係の正確な requirements.txt（バージョン固定）
- CI / テスト実行手順（pytest など）
- デプロイ / systemd サービス化の例（run_monitoring / run_execution をサービス化する場合の unit ファイル雛形）
- 各モジュールのより詳しい API ドキュメント（関数シグネチャ一覧）

追加希望があればどのセクションを拡張するか教えてください。