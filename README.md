README
=====

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的とした Python パッケージ群です。本リポジトリは以下の主要機能を持ちます。

- 注文実行エンジン（ExecutionEngine）と起動・再同期ロジック
- 監視コンポーネント（システム監視 / 注文監視 / リスク監視）とアラート送信
- ポートフォリオ構築（候補選定・配分・ポジションサイズ計算・セクター制限）
- リサーチ用ファクター計算・特徴量探索
- ニュース NLP による銘柄別センチメントスコアリング（OpenAI）
- Paper Trading 検証レポート生成や Streamlit ダッシュボードなどのツール

設計方針の要点：
- DuckDB / SQLite をデータ層に使用し、研究機能と実行機能は分離
- 外部 API 呼び出し（OpenAI, ブローカー等）は明示的に管理し、失敗時はフェイルセーフを優先
- 環境設定は .env / 環境変数で管理（自動ロード機能あり）

主な機能一覧
--------------
- 実行関連
  - 注文作成 / 送信 / 同期（OrderManager, Reconciler）
  - 起動時の自動リコンシリエーション（Reconciler）
  - paper_trading モード（MockBroker + separate SQLite）

- 監視関連
  - SystemMonitor: CPU/メモリ/ディスク/プロセス/データ鮮度
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウン / ポジション上限監視
  - KillSwitch: フラグファイルで ExecutionEngine 停止指示
  - AlertManager: LINE Push による通知
  - MonitoringEngine: 上記 Monitor を束ねるポーリングループ
  - Streamlit ダッシュボード（監視データ表示）

- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 重み計算（等金額 / スコア加重）
  - セクターキャップ適用
  - ポジションサイズ計算（単元株丸め、risk-based 等）

- リサーチ
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- AI（OpenAI）
  - ニュース記事の銘柄別センチメントスコア算出（ai.news_nlp.score_news）
  - 市場レジーム判定（ai.regime_detector.score_regime）

セットアップ手順
----------------
1. Python 環境
   - 推奨: Python 3.10+
   - 仮想環境を作成して有効化することを推奨します。
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - requirements.txt があればそれを使ってください（本例では代表パッケージを示します）:
     - pip install duckdb psutil openai requests streamlit
   - 実際の環境ではプロジェクトに合わせて追加の依存をインストールしてください。

3. 環境変数 / .env
   - プロジェクトルート（.git または pyproject.toml を基準）に .env / .env.local を置くと自動的に読み込まれます（os 環境変数が優先）。
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主要な環境変数（例とデフォルト）:
   - KABUSYS_ENV: 起動環境 — "development" | "paper_trading" | "live"（デフォルト: development）
     - paper_trading: MockBroker を使い data/paper_trading.db に記録（本番 DB と分離）
   - JQUANTS_REFRESH_TOKEN: 必須（J-Quants API 用）
   - KABU_API_PASSWORD: 必須（kabuステーション API 用）
   - OPENAI_API_KEY: OpenAI を使う場合に必須（ai.score_news / score_regime 等）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE通知）に使用（任意）
   - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
   - SQLITE_PATH: data/monitoring.db（デフォルト）
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 時の DB）
   - PID_FILE_PATH: data/execution.pid（デフォルト）
   - KILL_FLAG_PATH: data/kill.flag（デフォルト）
   - MONITOR_POLL_INTERVAL: 監視ループの秒間隔（デフォルト 60、0 以下は無効としてデフォルトにフォールバック）
   - PAPER_FILL_MODE: paper_trading の約定モード（"instant" | "partial" | "never" | "reject"、デフォルト "instant"）

4. データベース初期化
   - Monitoring 用 SQLite スキーマは接続時に init_monitoring_db() により自動作成されます。特別な初期スクリプトは不要です。

使い方（主要なスクリプト）
-------------------------

- 監視ループを起動（MonitoringEngine の単純起動）
  - python -m kabusys.run_monitoring
  - 代替（ソース直実行）: PYTHONPATH=src python src/kabusys/run_monitoring.py
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 備考:
    - 起動時にプロセス優先度を "high" に設定しようとします（権限がなければ警告を出してスキップ）。

- ExecutionEngine を起動（注文実行）
  - python -m kabusys.run_execution
  - paper_trading モード例:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
    - paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは読み取り専用で SQLite DB を開きます（DB がない場合は MonitoringEngine を起動してください）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db PATH を使うか環境変数 PAPER_TRADING_SQLITE_PATH を設定してください（デフォルト data/paper_trading.db）。
  - 出力: 標準出力へサマリと PASS/FAIL 判定（稼働率 / 注文成功率 / 送信率 / P95 レイテンシ 等）

- AI: ニューススコア付与（プログラム呼び出し例）
  - Python から呼び出す例:
    - import duckdb
      from kabusys.ai.news_nlp import score_news
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
  - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を使用します。
  - 注意: API レスポンスは堅牢に検証され、失敗時は部分的にスキップされる設計です。

設定と動作に関する注意点
-----------------------
- .env ロード順: OS 環境変数 > .env.local > .env（ただし OS 環境変数は保護され上書きされません）。
- Settings クラス（kabusys.config.Settings）経由で各種設定を取得します。未設定の必須変数は ValueError を投げます。
- paper_trading モードは本番データベースと分離されるため検証・開発に便利です。
- Monitoring / Execution はプロセス優先度の変更や PID ファイルによる生存確認を行います。起動順序や権限に注意してください。
- OpenAI API 呼び出しはレート制限やネットワーク障害に対してリトライ等の対策を実装していますが、APIキーが未設定だとエラーになります（score_news/score_regime は明示的にチェックします）。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                       — 環境変数 / 設定解決ロジック
- run_monitoring.py                — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py                 — ExecutionEngine 起動スクリプト

- ai/
  - __init__.py
  - news_nlp.py                     — ニュースセンチメントスコア生成（OpenAI）
  - regime_detector.py              — 市場レジーム判定（OpenAI + ETF MA）

- monitoring/
  - __init__.py
  - monitoring_db.py                — SQLite スキーマ / 永続化層
  - system_monitor.py               — システム状態・データ鮮度監視
  - trade_monitor.py                — 注文滞留 / 約定異常検出
  - risk_monitor.py                 — ドローダウン / ポジション上限監視
  - monitoring_engine.py            — Monitor を束ねたポーリング実行
  - kill_switch.py                  — kill.flag による外部停止指示
  - alert_manager.py                — LINE 通知
  - streamlit_dashboard.py          — Streamlit ダッシュボード

- execution/
  - order_manager.py
  - reconciler.py
  - (その他: broker_factory, execution_engine, order_repository 等)

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py

- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py

- tools/
  - __init__.py
  - paper_verification_report.py     — Paper Trading レポート生成ツール

- utils/
  - __init__.py
  - process_priority.py              — cross-platform な優先度 / affinity 設定ユーティリティ

追加情報 / トラブルシューティング
---------------------------------
- SQLite/DuckDB のパスは Settings で決まるため、権限やディレクトリ存在に注意してください（必要に応じて data/ ディレクトリを作成）。
- psutil による優先度変更や CPU affinity の設定は OS と権限に依存します。AccessDenied などが出る場合は権限不足を確認してください。
- OpenAI API 呼び出しは network エラーや rate limit を考慮した実装になっていますが、実稼働では API コスト・レート制限に注意してください。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、必要な環境変数のみ明示的に渡すことを推奨します。

ライセンス・貢献
----------------
- 本リポジトリのライセンス情報・貢献ルールはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

お問い合わせ
------------
- 実装方針や各モジュールの詳細な利用方法については該当モジュールのドキュメント文字列（docstring）を参照してください。README に足りない運用上の質問があればお知らせください。