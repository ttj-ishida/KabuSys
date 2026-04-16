# KabuSys

KabuSys は日本株向けの自動売買システムのコア実装群です。戦略の研究・ファクター計算、ポートフォリオ構築、注文実行エンジン、監視・アラート、Paper Trading 検証ツール、LLM を使ったニュースセンチメント評価などのコンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

主な目的は、日本株向けの自動売買ワークフローを安全に運用できるようにすることです。以下の領域をカバーします。

- 戦略研究、ファクター計算（DuckDB を用いた時系列計算）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・セクターキャップ）
- 注文管理 / 実行エンジン（ブローカー抽象化、リコンシリエーション）
- 監視（システム状態、注文滞留、リスク監視、アラート送信）
- Paper Trading 用分離 DB とモックブローカー
- ニュース NLP（OpenAI を用いたセンチメント評価）及び市場レジーム判定
- 可視化: Streamlit ベースの監視ダッシュボード
- 運用補助ツール: Paper Trading 検証レポート生成

設計上の特徴：
- DuckDB（時系列・分析用）、SQLite（監視・注文ログ）を併用
- .env / 環境変数で挙動を制御（自動ロード機能あり）
- Paper Trading と本番は DB を分離して安全に検証可能
- フェイルセーフ（API 失敗時のフォールバック等）

---

## 機能一覧

- research
  - ファクター計算（モメンタム、バリュー、ボラティリティ）
  - 将来リターン、IC（Information Coefficient）算出、統計サマリ
- portfolio
  - 候補選定（スコア順・上位 N）
  - 重み計算（等金額・スコア重み）
  - リスク調整（セクター上限の適用、レジーム乗数）
  - ポジションサイズ計算（単元株丸め、aggregate cap）
- execution
  - 注文状態管理（OrderManager）
  - Reconciler（再起動後の同期待ち合わせ、ポジション差分検出）
  - Broker 抽象化（本番 / モック対応）
- monitoring
  - SystemMonitor：CPU / メモリ / ディスク / プロセス生存 / データ鮮度
  - TradeMonitor：滞留注文・約定異常価格検出
  - RiskMonitor：ドローダウン監視・ポジション上限監視
  - KillSwitch：条件に応じた停止フラグ書き込み（kill.flag）
  - AlertManager：LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード
- ai
  - news_nlp：ニュースを OpenAI に送り銘柄別センチメントを ai_scores に書込
  - regime_detector：ETF MA とマクロニュースの LLM 評価を合成し市場レジーム判定
- tools
  - paper_verification_report：Paper Trading DB から運用検証レポート生成

---

## セットアップ手順

前提
- Python 3.10+（型アノテーションで `X | Y` を使用）
- システムにより root 権限なしではプロセス優先度の設定が制限される場合があります

1. リポジトリをクローン
   - git clone ... （省略）

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) または .venv\Scripts\activate (Windows)

3. 依存パッケージをインストール
   - 必要な主なライブラリ:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボード用)
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （※ 本リポジトリに requirements.txt が無い場合は上記を目安にしてください。）

4. 環境変数 / .env
   - プロジェクトルートに .env/.env.local を置くと自動読み込みされます（OS 環境変数 > .env.local > .env の優先順）。
   - 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
   - 必須環境変数（実行内容により必要）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 運用に便利な変数（省略可能、デフォルトあり）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / regime_detector 用）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート送信用
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading 注文の約定挙動）
     - MONITOR_POLL_INTERVAL: 監視ループ間隔（秒、デフォルト 60）
     - PID_FILE_PATH / KILL_FLAG_PATH 等も環境変数で上書き可

5. データディレクトリ作成
   - data ディレクトリを作る:
     - mkdir -p data

---

## 使い方

### ExecutionEngine（発注エンジン）を起動
- 本番 / 開発 / Paper Trading の env に応じて挙動が変わります。

例：Paper Trading で起動
- KABUSYS_ENV=paper_trading を設定すると MockBrokerClient が使われ、paper_sqlite_path（デフォルト: data/paper_trading.db）に記録されます。

起動
- python -m kabusys.run_execution

起動中の停止方法
- data/stop_requested.flag を作成すると実行エンジンは検知して安全に停止します。
- また KillSwitch が条件を満たした場合は data/kill.flag を書き込み、上位からの手動停止トリガーとなります。

PID ファイル
- 実行時に data/execution.pid（設定により異なる）を書きます。SystemMonitor はこの PID を見てプロセス生存を判定します。

### Monitoring（監視ループ）を起動
- 監視は sqlite（monitoring.db）にログを永続化します。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。

起動
- python -m kabusys.run_monitoring

ポーリング間隔の上書き
- 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を変更可能。1 未満や不正な値はデフォルト 60 秒にフォールバック。

停止
- run_monitoring はプロジェクトルート/data/stop_requested.flag を監視して停止します。KeyboardInterrupt（Ctrl+C）でも終了します。

### Streamlit ダッシュボード
- 監視 DB を読み取り専用で表示するダッシュボード。

起動例
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

（引数 --db にパスを渡せます）

### Paper Trading 検証レポート
- Paper Trading の DB から検証指標（稼働率、注文成功率、レイテンシ等）を出力します。

例
- python -m kabusys.tools.paper_verification_report
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- オプション: --db PATH で DB を指定（PAPER_TRADING_SQLITE_PATH 環境変数も使用可能）

### AI モジュール
- news_nlp.score_news(conn, target_date, api_key=None)
  - raw_news と news_symbols を集約して OpenAI API に投げ、ai_scores テーブルへ書き込みます。
  - api_key を引数で渡すか環境変数 OPENAI_API_KEY を設定してください。

- regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の MA 乖離とマクロニュース LLM 評価を合成して market_regime に書き込みます。

注意: OpenAI 呼び出しは API 失敗時にフェイルセーフでフォールバックしますが、API キーが未設定だと例外になります。

---

## 重要なファイル・フラグ（運用メモ）

- data/stop_requested.flag
  - run_execution.py / run_monitoring.py が存在をチェックし、検出するとループを終了します（手動停止用）。
- data/kill.flag
  - KillSwitch がリスク条件（例: ドローダウン超過）を満たした場合に書き込む停止・通知用フラグ。
- data/execution.pid（既定）
  - ExecutionEngine の PID を書くファイル。SystemMonitor はこの PID を見てプロセス生存を判定します。
- DB ファイル
  - data/monitoring.db（監視ログ、デフォルト）
  - data/paper_trading.db（Paper Trading 用）
  - data/kabusys.duckdb（分析・ファクターテーブル）

---

## ディレクトリ構成（主要ファイル）

以下はソースツリーの主要モジュールと説明です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数/.env のロードと Settings
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - ai/
    - news_nlp.py           — ニュースセンチメント（OpenAI 呼び出し）
    - regime_detector.py    — レジーム判定（MA + LLM）
  - research/
    - factor_research.py    — ファクター計算（momentum/value/volatility）
    - feature_exploration.py— IC / forward returns / 統計
  - portfolio/
    - portfolio_builder.py  — 候補選定、重み計算
    - position_sizing.py    — 株数計算、スケーリング、単元丸め
    - risk_adjustment.py    — セクターキャップ、レジーム乗数
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他ブローカー抽象等)
  - monitoring/
    - monitoring_db.py      — SQLite テーブル初期化・読み書きラッパ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py      — LINE Push 通知
    - kill_switch.py
    - streamlit_dashboard.py
  - utils/
    - process_priority.py   — psutil を使った優先度 / CPU affinity 設定
  - research/ / data/ 等の補助モジュール

---

## 運用上の注意

- データ分離: Paper Trading は settings.is_paper を見て専用の SQLite を利用します（本番 DB と完全分離）。
- プロセス優先度設定: set_process_priority("high") を使いますが、権限不足で失敗することがあります（ログに WARNING を出力してスキップします）。
- .env パース: config._parse_env_line はシェル風の export やクォート処理をある程度サポートしますが、複雑な .env は注意してください。
- DB マイグレーション: init_monitoring_db は冪等的にテーブルを作成し、既存カラムがない場合は追加する簡易マイグレーションを行います。
- OpenAI 呼び出し: レート制限や一時障害に対して指数バックオフでリトライする実装が入っていますが、API 使用量には注意してください。
- セキュリティ: API キーやパスワードは .env に入れる場合、アクセス管理に注意してください。

---

## 例: 最小限の起動手順（開発用）

1. 仮想環境を有効化し依存をインストール
   - pip install duckdb psutil requests openai streamlit

2. .env を作成（最小）
   - KABUSYS_ENV=development
   - KABU_API_PASSWORD=your_password
   - JQUANTS_REFRESH_TOKEN=...
   - OPENAI_API_KEY=...  # AI 機能を使う場合

3. データディレクトリ作成
   - mkdir -p data

4. 監視を起動（別ターミナル）
   - python -m kabusys.run_monitoring

5. Execution（開発）を起動
   - python -m kabusys.run_execution

6. Streamlit ダッシュボード
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

必要に応じて README に含めるコマンド例や環境変数のより詳細なテンプレート（.env.example）を作成できます。追加で記載したい内容（例: requirements.txt、CI 手順、デプロイ方法、DB スキーマの詳細など）があれば教えてください。