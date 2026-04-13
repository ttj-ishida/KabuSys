# KabuSys

日本株自動売買システム（ライブラリ／実行スクリプト群）

このリポジトリは、トレーディング実行エンジン、監視（Monitoring）、ポートフォリオ構築、ファクターリサーチ、AI ベースのニュース解析等を含むモジュール群を提供します。設計は本番安全性（DB 分離、冪等処理、フェイルセーフ）を重視しています。

注意: この README は提供されたコードベース（src/kabusys）に基づく要約です。実運用前にテスト環境で動作確認を行ってください。

## 主な特徴（機能一覧）

- Execution
  - ExecutionEngine を介した発注フロー（OrderManager、OrderRepository、Reconciler 等）。
  - paper_trading 環境では MockBroker を使用し、本番 DB と分離して `data/paper_trading.db` を利用。
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine。
  - system_status / trade_logs / risk_logs / positions / dashboard の永続化用 SQLite 層（MonitoringDB）。
  - kill.flag による外部停止（KillSwitch）と LINE 通知（AlertManager）。
  - Streamlit ダッシュボード（read-only）で監視データ可視化。
- Portfolio Construction
  - 候補選定、等分配／スコア加重、ポジションサイズ計算、セクターキャップ、レジーム乗数等の純粋関数群。
- Research
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー）と特徴量解析（IC, forward returns）。
- AI（OpenAI 統合）
  - ニュースを LLM（gpt-4o-mini）でセンチメント評価し ai_scores に保存（news_nlp）。
  - マクロニュース＋ETF MA200 を使った市場レジーム判定（regime_detector）。
  - API 呼び出しはリトライやフォールバックを備えフェイルセーフに実装。
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）。

## システム要件（推奨）

- Python 3.10+
- 主要依存（抜粋）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- SQLite（標準ライブラリの sqlite3 を使用）

インストール方法はプロジェクトに合わせて requirements.txt や pyproject.toml を使ってください。手早く依存を入れる例:

```
python -m pip install "duckdb" "psutil" "requests" "openai" "streamlit"
```

あるいは開発インストール:

```
python -m pip install -e .
```

（プロジェクト配布時に pyproject.toml/setup.cfg があればそちらに従ってください）

## 環境変数（主要なもの）

- 共通
  - KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
  - PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動削除する場合は `1`
- 認証・外部 API
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
- DB パス
  - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 専用 SQLite（デフォルト: data/paper_trading.db）
- Paper Trading 特有
  - PAPER_FILL_MODE: mock ブローカーの約定挙動（instant | partial | never | reject）。デフォルト: instant
- Monitoring
  - MONITOR_POLL_INTERVAL: SystemMonitor のポーリング間隔（秒）。デフォルト: 60
- その他
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env/.env.local をロードする仕組みを無効化します。

.env の自動ロード：
- プロジェクトルート（.git または pyproject.toml を基準）を探索し、`.env`（既存の OS 環境変数を上書きしない）と`.env.local`（上書き可）を順に読み込みます。
- オートロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

2. 依存インストール
   - pip install -r requirements.txt （存在すれば）
   - または必要なパッケージを個別にインストール（前節参照）

3. .env ファイル作成（リポジトリルート）
   - .env.example がある場合は参照して作成してください。必要な最低限の例:

```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=your_openai_key
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
```

4. データディレクトリ作成
   - mkdir -p data

5. DuckDB / SQLite の初期化は各モジュール起動時に必要なテーブルが作成されます（init_monitoring_db などが冪等で作成）。

## 使い方（主要スクリプト）

- ExecutionEngine（取引実行）起動:

```
python -m kabusys.run_execution
```

挙動:
- KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使い MockBroker を採用。本番 DB と分離されます。
- プロセス起動直後にプロセス優先度を High に設定しようとします（psutil による試行で失敗しても継続）。
- 起動中は duckdb/SQLite の接続を行い、ExecutionEngine.run_session() を実行します。

- Monitoring（system polling）起動:

```
python -m kabusys.run_monitoring
```

オプション:
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
挙動:
- Monitoring は KABUSYS_ENV に関わらず production sqlite_path（Settings.sqlite_path）を使用します（監視 DB は本番 DB を参照する想定）。

- Streamlit ダッシュボード（ローカルで監視データを確認）:

```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- Paper Trading 検証レポート生成ツール:

```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または DB パス指定
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

出力:
- 稼働率、注文成功率、送信率、P95 レイテンシなどを集計して PASS/FAIL 判定を行います。基準値はソース内の定数で定義されています。

- AI 機能の利用（プログラムから呼ぶ）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

  いずれも DuckDB 接続（DuckDBPyConnection）を受け取り、内部で OpenAI API を呼び出します。api_key を引数で渡すか環境変数 OPENAI_API_KEY を設定してください。

## 監視・停止（kill flag）

- KillSwitch は RiskMonitor の判定（ドローダウン超過、ポジション上限超過など）により `KILL_FLAG_PATH`（デフォルト data/kill.flag）に理由文字列を書き込みます。ExecutionEngine はこのフラグを見て停止する想定です（ExecutionEngine 側でフラグを確認する実装がある場合）。
- 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すれば ExecutionEngine 起動時に kill.flag を自動消去する挙動があります（Settings で制御）。

## デフォルトパス（主なもの）

- DuckDB: data/kabusys.duckdb
- Monitoring SQLite: data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db
- PID ファイル: data/execution.pid
- kill.flag: data/kill.flag

## ディレクトリ構成（抜粋・説明）

src/kabusys/
- __init__.py
  - パッケージ宣言と __version__
- config.py
  - 環境変数の読み込み・Settings クラス（.env 自動ロードの実装、各種設定）
- run_execution.py
  - ExecutionEngine 起動スクリプト（プロセス優先度設定、DB接続、依存組立て）
- run_monitoring.py
  - SystemMonitor のポーリング起動スクリプト
- execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, broker_factory.py ...
  - 発注・状態管理・ブローカー抽象化・リコンシリエーション等
- monitoring/
  - monitoring_db.py: SQLite スキーマ定義 + MonitoringDB（読み書きラッパ）
  - system_monitor.py: CPU/メモリ/Disk/データ鮮度/プロセス監視
  - trade_monitor.py: 注文滞留・約定異常検知
  - risk_monitor.py: ドローダウン・ポジション数監視
  - kill_switch.py: kill.flag 書き込み・管理
  - alert_manager.py: LINE 通知（push）
  - monitoring_engine.py: 各 monitor を束ねるエンジン
  - streamlit_dashboard.py: Streamlit ベースの監視 UI（read-only）
- portfolio/
  - portfolio_builder.py: 候補選定、重み計算
  - position_sizing.py: 株数計算・上限・lot 単位で丸め
  - risk_adjustment.py: セクター制限・レジーム乗数
- research/
  - factor_research.py: momentum/volatility/value の計算（DuckDB）
  - feature_exploration.py: forward returns / IC / summary
- ai/
  - news_nlp.py: ニュース記事の LLM スコアリング（ai_scores へ書込）
  - regime_detector.py: マクロ×ETF MA200 でレジーム判定
- tools/
  - paper_verification_report.py: Paper Trading 的検証レポート生成スクリプト
- utils/
  - process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティ

（上記はコードベースから抽出した主要ファイルの説明です。実際のファイル数やサブモジュールはリポジトリ全体を参照してください）

## 運用上の注意点・設計上の留意点

- Monitoring は Settings.env に関わらず monitoring DB（Settings.sqlite_path）を参照するよう設計されています。監視データは本番 DB をターゲットにする想定です。
- Paper Trading は本番と DB を完全分離する設計です（Settings.is_paper が true の場合は paper_sqlite_path を使用）。
- OpenAI API 呼び出しは外部依存かつコストがかかるため、API キーの管理と呼び出し頻度に注意してください。news_nlp/regime_detector はリトライ・フォールバックロジックを備えますが、API 呼び出しの失敗時はスコアを 0（中立）とするなどフェイルセーフ設計になっています。
- DB マイグレーション処理は簡易にコード内で扱っています（monitoring_db.init_monitoring_db がカラム追加等を実施）。既存データのバックアップを取ってから運用してください。
- プロセス優先度設定（set_process_priority）は OS により動作が異なり権限が必要な場合があります。失敗してもログに警告が出て続行します。

---

必要であれば、README に含める実行例の追加（systemd ユニット / Dockerfile / docker-compose / テスト手順 等）や、各モジュールの README（Execution, Monitoring, AI）を個別に作成します。どの追加情報を優先するか教えてください。