# KabuSys

日本株向けの自動売買・検証基盤ライブラリ（プロトタイプ）。  
このリポジトリは取引の実行エンジン、監視・アラート、ポートフォリオ構築、リサーチ、AI を用いたニュースセンチメントなどのコンポーネント群を含みます。

以下はこのコードベースの概要・セットアップ・使い方・ディレクトリ構成です。

---

目次
- プロジェクト概要
- 機能一覧
- 必要条件
- 環境変数（主なもの）
- セットアップ手順
- 実行方法（使い方）
- 運用・停止方法
- ディレクトリ構成（主要ファイルと説明）
- 補足・注意事項

---

## プロジェクト概要
KabuSys は以下を目的としたモジュール群を提供します：
- ExecutionEngine：ブローカーを通じた注文発行・状態管理・リコンシリエーション
- Monitoring：システム状態・注文状態・リスクの継続監視、LINE 通知、ダッシュボード表示
- Portfolio：候補選定、重み計算、ポジションサイズ算出、セクター制約・レジーム調整
- Research：DuckDB 上の株価/財務テーブルを使ったファクター計算、IC・統計等の分析
- AI：OpenAI（gpt-4o-mini）を用いたニュースセンチメント取得と市場レジーム判定
- Tools：Paper Trading 検証レポート生成スクリプト等

監視ログ等は SQLite（monitoring.db / paper_trading.db 等）に永続化し、DuckDB を分析用に使用します。

---

## 機能一覧
主な機能：
- 実行エンジン起動/停止（run_execution.py）
  - 本番 / Paper Trading の分離（KABUSYS_ENV により切替）
  - BrokerFactory による実ブローカー / モックブローカーの切替
  - リコンシリエーション（起動時の注文・ポジション照合）
- 監視 (run_monitoring.py / MonitoringEngine)
  - CPU/メモリ/ディスク/プロセス存在チェック
  - 注文滞留や約定価格異常の検出
  - ドローダウン・ポジション上限の監視（リスクイベント記録）
  - KillSwitch による停止フラグ生成・通知
  - LINE によるプッシュ通知（AlertManager）
  - Streamlit ダッシュボード表示用のスクリプト
- ポートフォリオ構築
  - 候補選定、等重/スコア重み付け、リスクベースのポジションサイズ算出
  - セクター上限適用およびレジーム乗数
- リサーチ
  - モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB）
  - 将来リターン・IC（スピアマン）・統計サマリ等
- AI（OpenAI）
  - ニュースを銘柄別に集約して LLM でセンチメント評価（ai_scores へ保存）
  - マクロニュース + ETF MA200 乖離で市場レジーム判定（market_regime へ保存）
- ツール
  - Paper Trading の検証レポート生成（tools/paper_verification_report.py）

---

## 必要条件
- Python 3.9+
- 主要依存パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai（OpenAI Python SDK）
  - streamlit（ダッシュボードを使う場合）
- SQLite（標準で Python に同梱）

依存は環境に合わせて requirements.txt を用意するか、手動で pip install してください。

例:
pip install duckdb psutil requests openai streamlit

---

## 環境変数（主なもの）
設定は .env / .env.local / OS 環境変数から読み込まれます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

必須／重要な環境変数（抜粋）：
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）

データパス（デフォルト値）：
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag

Paper Trading 固有：
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

監視間隔：
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。デフォルト: 60）

その他：
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると .env の自動読み込みを無効化します。

.example の .env（抜粋）:
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=xxxxx
OPENAI_API_KEY=sk-xxxxx
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
MONITOR_POLL_INTERVAL=60
LINE_CHANNEL_ACCESS_TOKEN=xxxx
LINE_USER_ID=Uxxxxxxxx

---

## セットアップ手順
1. リポジトリをクローン
   - git clone ...

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -r requirements.txt
   - もし requirements.txt が無ければ:
     pip install duckdb psutil requests openai streamlit

4. data ディレクトリ作成
   - mkdir -p data

5. .env を作成（必要な環境変数を設定）
   - .env.example を参考に作成してください（存在しない場合は README の環境変数セクションを参照）

6. DuckDB / SQLite の初期化は各スクリプトが自動で行います（monitoring DB のテーブル作成等は init_monitoring_db で冪等に実行されます）。

---

## 実行方法（使い方）
以下は主要な起動方法です。パッケージルートから実行してください。

- 監視ループの起動（Monitoring）
  - 簡単起動:
    python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を上書き:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - run_monitoring は常に production の sqlite_path（SQLITE_PATH）を使います（環境に依らず監視 DB は本番 path を使用する設計）。

- 実行エンジンの起動（ExecutionEngine）
  - 開始:
    python -m kabusys.run_execution
  - Paper Trading モード:
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    - このモードでは MockBrokerClient が使用され、paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）へ記録されます（本番 DB と完全分離）。

- Streamlit ダッシュボード（監視ビュー）
  - 起動:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開くため、MonitoringEngine を先に起動してデータを作成しておくことを推奨します。

- Paper Trading 検証レポート生成
  - 単発実行:
    python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 関連（ニューススコア / レジームスコア）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出して利用。
  - OPENAI_API_KEY の設定が必須（関数引数でキーを渡すことも可）。

ログ出力は標準の logging を使用します。必要に応じて LOG_LEVEL を設定してください。

---

## 運用・停止方法
- 停止フラグ:
  - 監視 / 実行はフラグファイルで停止を制御します。
  - data/stop_requested.flag を作成すると run_monitoring と run_execution のループが検知して停止します（run_execution は起動時にこのフラグが既に存在すると起動を行いません）。
  - KillSwitch は data/kill.flag を生成して ExecutionEngine に停止シグナルを送ります（監視ロジックにより自動生成される）。
- PID ファイル:
  - 実行時は data/execution.pid など PID ファイルが使われます。SystemMonitor は PID ファイルを参照してプロセスが存在するか監視します。
- 手動クリア:
  - flag の削除はファイルを削除するだけです（rm data/kill.flag 等）。
- 注意:
  - フラグファイルの存在状態で起動/停止が制御されるため、運用前に data ディレクトリとフラグ状態を確認してください。

---

## ディレクトリ構成（抜粋）
src/kabusys/ の主要なモジュールと簡単な説明：

- __init__.py
  - パッケージ定義（バージョン等）

- config.py
  - 環境変数の読み込み・Settings クラス
  - .env / .env.local 自動読み込み（無効化可能）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
  - MONITOR_POLL_INTERVAL で間隔を指定（デフォルト 60 秒）

- run_execution.py
  - ExecutionEngine 起動スクリプト
  - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB と MockBroker を使用

- monitoring/
  - monitoring_db.py: SQLite 上のテーブル初期化・永続化用クラス（MonitoringDB）
  - system_monitor.py: CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py: 注文滞留・約定異常の監視
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag の書き込みロジック
  - alert_manager.py: LINE Push API 通知
  - monitoring_engine.py: 各 Monitor をまとめて定期実行するエンジン
  - streamlit_dashboard.py: Streamlit による監視ダッシュボード

- execution/
  - execution_engine.py（存在）: 実際のエンジン（起動ロジック）
  - order_manager.py: 発注・状態遷移を管理する OrderManager
  - order_repository.py: 注文レコードの永続化
  - reconciler.py: 起動時の照合・復旧ロジック
  - broker_factory.py 等: ブローカークライアント生成

- portfolio/
  - portfolio_builder.py: 候補選定・等重/スコア重み
  - position_sizing.py: 株数計算・資金配分
  - risk_adjustment.py: セクターキャップ・レジーム乗数

- research/
  - factor_research.py: Momentum/Volatility/Value 等ファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン・IC・統計サマリ等

- ai/
  - news_nlp.py: raw_news から銘柄ごとに記事集約 -> OpenAI でスコア化 -> ai_scores へ保存
  - regime_detector.py: ETF MA200 とマクロニュースを LLM で判定し market_regime に保存

- utils/
  - process_priority.py: プラットフォーム依存を吸収してプロセス優先度 / CPU affinity を設定

- tools/
  - paper_verification_report.py: Paper Trading の検証レポートを生成する CLI

その他:
- data/: デフォルトの DB / PID / flag 等を置くディレクトリ（運用環境で作成してください）
  - data/monitoring.db（デフォルトの monitoring SQLite）
  - data/paper_trading.db（Paper Trading 用 SQLite）
  - data/kabusys.duckdb（DuckDB）
  - data/execution.pid, data/stop_requested.flag, data/kill.flag など

---

## 補足・注意事項
- DB の分離:
  - Monitoring は設定に関わらず SQLITE_PATH（本番 path）を使う設計です。
  - ExecutionEngine は KABUSYS_ENV=paper_trading の時に PAPER_TRADING_SQLITE_PATH を使用し、本番 DB と分離します（Paper Trading の安全性確保）。
- OpenAI 使用:
  - OPENAI_API_KEY の設定が必須です。API 呼び出しは失敗時にフェイルセーフ（ゼロやスキップ）で継続する実装が多いですが、結果の有無を考慮して処理してください。
- 権限:
  - プロセス優先度 / CPU affinity の設定はプラットフォーム依存かつ権限が必要な場合があります。権限不足だと警告が出てスキップされます。
- テスト:
  - 多くの外部呼び出し（OpenAI API, ブローカーAPI, LINE API）はモック可能な設計になっています（テスト時に差し替えてください）。
- データ鮮度:
  - SystemMonitor は DuckDB 上の prices_daily 最終日を参照してデータ鮮度を判定します。DuckDB のテーブルが正しくロードされていることを確認してください。

---

README はここまでです。実際の運用に入る前に .env の設定・data ディレクトリの準備・依存パッケージのインストール・小規模での動作確認（Paper Trading モードでの検証）を必ず行ってください。必要であれば、README に記載したコマンドや .env の例をベースに運用手順書を作成することを推奨します。