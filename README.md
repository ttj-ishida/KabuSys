# KabuSys

日本株自動売買システム KabuSys のリポジトリ用 README（日本語）。

この README は与えられたコードベースの主要機能・セットアップ・実行方法・ディレクトリ構成をまとめたものです。

重要: この README はコードベースのソースから自動生成されたドキュメントのため、実際の運用環境では環境変数や外部ライブラリ（kabuステーション API、J-Quants、OpenAI 等）の設定や鍵の管理に十分注意してください。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買・リサーチ・監視を行うシステムです。主要コンポーネントは次のとおりです。

- Execution: ブローカーへの発注、オーダー管理、リコンシリエーション（再同期）
- Monitoring: システム稼働状況・注文異常・リスク（ドローダウン等）監視、LINE 通知、ダッシュボード
- Research: DuckDB 上の価格/財務データからファクタ計算や特徴量解析
- Portfolio: 候補選定、配分（等配分 / スコア加重 / リスクベース）、セクター制約、ポジションサイズ決定
- AI: OpenAI を用いたニュースセンチメント（ai スコア）・市場レジーム判定
- Tools: Paper Trading の検証レポート生成などのユーティリティスクリプト
- Utilities: プロセス優先度・CPU affinity 設定、環境変数ロード等

設計上の要点：
- DuckDB / SQLite をデータ層に採用（履歴・監視は SQLite、分析は DuckDB）
- Paper Trading（環境 `paper_trading`）は本番 DB と分離された専用 SQLite を使用
- OpenAI 呼び出しは失敗時にフォールバック（フェイルセーフ）するよう設計
- 自動ロード用の .env サポート（プロジェクトルートの .env / .env.local）

---

## 機能一覧

主要な機能を用途別に列挙します。

- 発注・注文管理
  - OrderManager / OrderRepository によるオーダー生成・永続化
  - ExecutionEngine（run_execution.py 経由）で実行セッション管理
  - Reconciler による再起動時のブローカー照合・ポジション差分検出

- モニタリング・アラート
  - SystemMonitor：CPU / メモリ / ディスク / データ鮮度 / PID 管理
  - TradeMonitor：滞留注文・約定価格異常チェック
  - RiskMonitor：ドローダウン・ポジション数上限の監視、dashboard 更新
  - KillSwitch：閾値に達した際に data/kill.flag を書き込み ExecutionEngine を停止
  - AlertManager：LINE Messaging API へのプッシュ通知（クールダウン管理）
  - Streamlit ダッシュボード（監視可視化）

- ポートフォリオ構築
  - 候補選定（スコア順、上位 N）
  - 重み決定（等金額 / スコア加重）
  - セクター上限適用（セクター集中制限）
  - ポジションサイズ計算（リスクベース / 等分 / スコアベース、単元株丸め、利用可能現金によるスケーリング）

- リサーチ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン・IC（Information Coefficient）計算
  - 統計サマリー

- AI（OpenAI）
  - ニュース NLP（raw_news → ai_scores へ書き込み）
  - 市場レジーム判定（ETF の MA200 とマクロニュースセンチメントの合成）
  - 再試行・JSON 検証・スコアクリッピング等の堅牢な実装

- ツール
  - paper_verification_report：Paper Trading の検証レポート生成（稼働率・成約率・レイテンシ等）

---

## セットアップ手順

前提
- Python 3.10 以上（Union typing, 型ヒントの構文を使用）
- システム依存パッケージ：psutil（プロセス管理・CPU 使用率取得）
- DuckDB、requests、openai、streamlit など

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 必要な依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要パッケージ（例）:
     - pip install duckdb psutil requests openai streamlit

4. 環境変数の設定
   - プロジェクトルートに .env または .env.local を作成して環境変数を設定できます。
   - 自動読み込みはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
     - LOG_LEVEL=INFO
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant|partial|never|reject
     - LINE_CHANNEL_ACCESS_TOKEN=（任意）
     - LINE_USER_ID=（任意）

5. データディレクトリの準備
   - data/ ディレクトリを作成（PID / flag / DB を配置）
     - mkdir -p data

6. DB 初期化
   - 実行スクリプト（run_monitoring/run_execution）内で init_monitoring_db が呼ばれ、必要テーブルが作成されます。明示的に初期化したい場合は小さなスクリプトで init_monitoring_db を呼び出してください。

---

## 使い方（主要スクリプト・コマンド）

以下は主要な実行例です。必要に応じて環境変数を設定してから実行してください。

1. 監視ループを起動（Monitoring）
   - デフォルト：SQLite（monitoring）に記録、ポーリング間隔は MONITOR_POLL_INTERVAL（秒、デフォルト 60）
   - 実行:
     - python -m kabusys.run_monitoring
     - または: python src/kabusys/run_monitoring.py
   - 環境変数例:
     - export MONITOR_POLL_INTERVAL=30
     - export KABUSYS_ENV=development

   停止:
   - data/stop_requested.flag を作成するとループは検出して安全終了します。

2. ExecutionEngine を起動（発注エンジン）
   - run_execution は KABUSYS_ENV に応じて実行モードを切り替えます。
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と分離）。
   - 実行:
     - python -m kabusys.run_execution
     - または: python src/kabusys/run_execution.py
   - 停止:
     - data/stop_requested.flag を作成すると ExecutionEngine は安全に停止します。

3. Streamlit ダッシュボード（監視画面）
   - 起動:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 説明:
     - ダッシュボードは監視 DB を read-only で開いて表示します。monitoring が稼働していない場合は DB が見つからない旨のエラーが表示されます。

4. Paper Trading 検証レポート
   - 実行:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - オプション `--db PATH` で SQLite ファイルを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH を上書き）
   - レポートは稼働率、注文成功率、送信率、レイテンシなどを表示し、PASS/FAIL を判定します。

5. AI 機能（ニューススコア / レジーム判定）
   - プログラム的に呼び出して利用します。例:
     - from kabusys.ai.news_nlp import score_news
     - from kabusys.ai.regime_detector import score_regime
     - score_news(conn, target_date, api_key="...") など
   - 必須: OPENAI_API_KEY を環境変数または api_key 引数で設定してください。
   - 注意: OpenAI API 呼び出しはレートリミット・タイムアウト対策が実装されていますが、実運用では API コスト・レート管理に注意してください。

---

## 重要なファイル・挙動メモ

- 環境分離（Paper Trading）
  - KABUSYS_ENV=paper_trading のとき、run_execution は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離します。
- 監視（Monitoring）は環境にかかわらず本番 sqlite_path を参照して監視ログを記録します（run_monitoring の設計）。
- 停止フラグ / PID
  - data/stop_requested.flag：run_monitoring / run_execution がループ終了 / 停止を検出するためのファイル
  - data/execution.pid：ExecutionEngine の PID 保存ファイル（存在とプロセス存在チェックでプロセスの稼働判定に使用）
  - data/kill.flag：KillSwitch が書き込む停止要請フラグ（ExecutionEngine 停止シグナル）
- プロセス優先度
  - 起動スクリプトは最初に set_process_priority("high") を呼んで可能な限り高優先度に設定します（psutil が必要、権限がない場合は警告が出る）。
- .env 自動ロード
  - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を検出して `.env` / `.env.local` を自動で読み込みます。
  - テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 例 .env（テンプレート）

以下は最小構成の例です（実際の値は各自の環境に合わせて設定してください）。

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABUSYS_ENV=development
LOG_LEVEL=INFO
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PAPER_FILL_MODE=instant
LINE_CHANNEL_ACCESS_TOKEN=your_line_token
LINE_USER_ID=your_line_user_id

---

## ディレクトリ構成

src/kabusys/ 以下の主要ファイル・ディレクトリと役割を示します（抜粋）。

- __init__.py
  - パッケージメタ情報（__version__）

- config.py
  - 環境変数読み込み・Settings クラス（各種設定プロパティ）
  - 自動 .env 読み込みのロジック

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト

- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading モード対応）

- execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine 等
  - ブローカー抽象、オーダー状態管理、再同期ロジック

- monitoring/
  - monitoring_db.py : monitoring 用 SQLite テーブル定義・CRUD
  - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py
  - alert_manager.py : LINE API への通知
  - monitoring_engine.py : 複数 Monitor を束ねる実行ループ
  - streamlit_dashboard.py : Streamlit ダッシュボード
  - __init__.py : public export

- portfolio/
  - portfolio_builder.py : 候補選定・重み付け
  - position_sizing.py : 発注株数計算（単元丸め・スケール調整）
  - risk_adjustment.py : セクター制約・レジーム乗数
  - __init__.py

- research/
  - factor_research.py : ファクター計算（momentum/volatility/value）
  - feature_exploration.py : 将来リターン計算・IC・統計サマリー
  - __init__.py

- ai/
  - news_nlp.py : ニュースの LLM によるセンチメント評価（ai_scores 生成）
  - regime_detector.py : ETF MA とマクロニュースからレジーム判定
  - __init__.py

- tools/
  - paper_verification_report.py : Paper Trading 用検証レポート生成ツール

- utils/
  - process_priority.py : プロセス優先度 / CPU affinity 設定ユーティリティ

- data/
  - （運用時に DB / pid / flag ファイルが配置される想定。リポジトリに含めないこと。）

---

## 運用上の注意

- OpenAI / ブローカー API キーは取り扱いに注意してください。`.env` は Git 管理対象外にしてください。
- Paper Trading 用 DB は本番 DB と分離されていますが、環境設定ミスによる本番 DB への書き込みを避けるため、起動前に環境変数を確認してください。
- process priority / cpu affinity 設定はプラットフォーム依存・権限依存です。権限がない環境では警告を出してスキップします。
- 監視・アラートは二重送信防止のためクールダウン・重複抑止ロジックを内包していますが、LINE トークンが未設定の場合は送信はスキップされ、ログのみ行われます。
- DuckDB / SQLite のバージョン互換性に注意（executemany の空リスト等の制約に備えたコードがあります）。

---

README はここまでです。追加で以下が必要であれば教えてください：
- 実際の要件に合わせた requirements.txt のサンプル
- デプロイ / systemd / Supervisor 用のサービスファイル例
- 詳細な API キー管理手順やテスト手順