KabuSys — 日本株自動売買システム
===============================

このリポジトリは、シンプルな日本株自動売買プラットフォームのコア部分（実行エンジン、監視、ポートフォリオ構成、リサーチ、AI を使ったニュース判定など）を含みます。本 README はコードベースの概要、機能、セットアップと実行方法、ディレクトリ構成を日本語でまとめたものです。

注意: 本 README はソース内の注釈や docstring を基に作成しています。実運用時は .env.example を参照して必要な環境変数を設定してください。

プロジェクト概要
----------------
KabuSys は以下の主要コンポーネントを持つ自動売買基盤です。

- ExecutionEngine（発注・注文管理・リスク管理・リコンシリエーション）
- Monitoring（システム状態、注文挙動、リスクの定期監視とアラート）
- Portfolio construction（候補選定・重み計算・株数決定）
- Research（ファクター計算・将来リターン・IC 計算など）
- AI モジュール（ニュースのセンチメントスコアリング、マクロレジーム判定）
- Tools（paper trading の検証レポート生成、Streamlit ダッシュボード）

主な設計方針:
- DuckDB や SQLite を用いたローカル DB によるデータ管理
- 本番 / paper_trading を環境変数 KABUSYS_ENV で切替可能（paper_trading は発注 DB を分離）
- AI 系（OpenAI）呼び出しは API キーで制御し、フェイルセーフ（API 失敗時は安全側フォールバック）を重視
- 自動監視から異常時に kill.flag を書くことで ExecutionEngine を安全停止させる仕組み

機能一覧
--------
- 発注管理（OrderManager / OrderRepository）
- 起動時リコンシリエーション（Reconciler）による安全な再開
- リスク管理（RiskManager）による注文拒否など（設定で閾値指定）
- 監視（SystemMonitor, TradeMonitor, RiskMonitor）：
  - CPU / メモリ / ディスク監視、Execution プロセス生存確認
  - 注文滞留検出、約定価格異常検出
  - ドローダウン・ポジション上限検出と kill flag の発動
- アラート送信（AlertManager）: LINE Messaging API 経由の一方向通知（クールダウン管理）
- Streamlit による監視ダッシュボード（読み取り専用）
- Paper Trading 向け検証レポート生成ツール（tools/paper_verification_report.py）
- ポートフォリオ構築ユーティリティ（候補選定、等重 / スコア重み、リスク調整、株数決定）
- リサーチ: ファクター計算（momentum / volatility / value）・特徴量探索（IC, 統計サマリ）
- AI: ニュース NLP による銘柄センチメント、マクロニュースを使った市場レジーム判定

セットアップ手順
----------------

1. Python 環境
   - 推奨: Python 3.10 以上（ソースで型 | 演算子が使用されています）
   - 仮想環境を作成して有効化してください。
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージ（代表例）
   - duckdb, psutil, openai, requests, streamlit
   - 実際の requirements.txt は本リポジトリに含まれていないため、環境に合わせてインストールしてください。
     例:
       pip install duckdb psutil openai requests streamlit

3. 環境変数
   - ルートに .env / .env.local を置くと自動的にロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主な必須／重要な変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
     - KABU_API_PASSWORD — kabuステーション API（必須）
     - OPENAI_API_KEY — OpenAI 呼び出し（AI コンポーネント使用時）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知（任意）
     - KABUSYS_ENV — 動作モード: development / paper_trading / live （デフォルト: development）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
     - PAPER_FILL_MODE — paper_trading の注文約定挙動（instant|partial|never|reject、デフォルト instant）
     - PID_FILE_PATH, KILL_FLAG_PATH — 各種ファイルパス（デフォルト data/...）
     - MONITOR_POLL_INTERVAL — 監視ループの秒間隔（デフォルト 60）

   - .env の書式はシェル互換（export 付き行、シングル/ダブルクォート、コメント対応）です。

4. データディレクトリ
   - デフォルトで data/ に DB やフラグファイルが置かれます。必要に応じて作成・権限設定をしてください。

使い方（主要スクリプト）
-----------------------

- 監視ループを起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - オプション: 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（整数、1以上）。無効値は 60 秒にフォールバック。
  - 注意: monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（デフォルト data/monitoring.db）を使用して監視ログを永続化します。
  - 停止: プロジェクトルート data/stop_requested.flag ファイルが検知されるとループを抜けます。

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合:
    - MockBrokerClient を使い、Paper Trading 専用 DB（デフォルト data/paper_trading.db）に記録します（本番 DB と分離）。
  - 停止制御:
    - 起動中に data/stop_requested.flag を作成するとエンジン停止処理が働きます。
    - 実行の PID は data/execution.pid に書き出されます。

- Streamlit ダッシュボード（監視用）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で監視 DB の状態（ダッシュボード、ポジション、最近の注文、システム状態、リスクログ）を表示します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
  - 出力: 稼働率、注文成功率、送信率、レイテンシ（P95）などの集計と PASS/FAIL 判定を標準出力に出す。

- AI 関連（ニュース / レジーム判定）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で指定してください。API 失敗時は安全側のフォールバック（0 や中立）を行う設計です。

停止・強制停止フラグ
-------------------
- data/stop_requested.flag — run_monitoring / run_execution が監視する「停止リクエスト」ファイル。存在すると安全にループを終了します。
- data/kill.flag — KillSwitch が生成するファイル。重大なリスク（ドローダウン等）で ExecutionEngine の停止を誘発する目的で作成されます。KillSwitch は冪等に書き込みを行います。
- KillSwitch を手動でクリアするにはファイルを削除してください（KillSwitch.clear() ロジックは flag を unlink します）。

主要な設定・振る舞いの補足
-----------------------
- Settings クラス（kabusys.config.Settings）でアプリケーション全体の環境変数アクセスを管理しています。自動で .env / .env.local を読み込みます（プロジェクトルートが特定できる場合）。
- PAPER_FILL_MODE（paper_trading） の有効値: instant | partial | never | reject。無効値は例外を投げます。
- Monitoring DB の初期化は init_monitoring_db() が行い、必要なテーブルや単純なマイグレーション（列追加）を行います。
- set_process_priority("high") が起動時に呼ばれてプロセス優先度を上げようとしますが、権限不足や未サポート OS の場合は警告を出してスキップします。
- AlertManager（LINE 通知）はトークン・ユーザ ID が未設定の場合は送信をスキップします。通知にはレベル・カテゴリ単位のクールダウンが適用されます。

トラブルシューティング（よくある注意点）
------------------------------------
- psutil で優先度や CPU affinity の設定が失敗することがあります（権限不足）。ログの警告を確認してください。
- DuckDB / SQLite のファイルパスは Settings が expanduser() を適用します（~ の展開対応）。
- Streamlit で DB を読み取り専用で開く際、URI +/- mode=ro が使われます。DB が存在しない場合はエラー表示されます。
- OpenAI 呼び出しで Rate Limit や 5xx が出た場合、内部で指数バックオフしてリトライします。繰り返し失敗する場合は API キーやネットワーク状態を確認してください。

ディレクトリ構成（主なファイルと説明）
-------------------------------------
src/kabusys/
- __init__.py — パッケージ定義（__version__ 等）
- config.py — 環境変数 / 設定読み込みロジック（Settings）
- utils/
  - process_priority.py — プロセス優先度 & CPU affinity ユーティリティ
- execution/
  - order_manager.py — 発注 API 外向けロジック（OrderManager）
  - order_repository.py — SQLite ベースの注文永続化（存在）
  - reconciler.py — 起動時のリコンシリエーション（注文・ポジション整合）
  - execution_engine.py — 実際のエンジン（起動 / セッション管理）（存在）
  - broker_factory.py, broker_api.py — ブローカークライアントの抽象 / Factory（存在）
  - order_record.py — 注文レコードの状態列挙（存在）
- monitoring/
  - monitoring_db.py — SQLite を用いた監視ログ層（テーブル定義・CRUD）
  - system_monitor.py — CPU / メモリ / ディスク / データ鮮度 / PID チェック
  - trade_monitor.py — 注文滞留・約定異常チェック
  - risk_monitor.py — ドローダウン・ポジション上限チェック
  - kill_switch.py — kill.flag 書き込みロジック
  - alert_manager.py — LINE 通知（push）
  - monitoring_engine.py — 各 Monitor を束ねるポーリング実行
  - streamlit_dashboard.py — Streamlit ベースのダッシュボード
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け（等重・スコア重み）
  - position_sizing.py — 株数決定・資金・ロット丸め・scale down ロジック
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — momentum/volatility/value ファクター算出
  - feature_exploration.py — 将来リターン・IC・統計サマリ等
- ai/
  - news_nlp.py — ニュースを OpenAI でセンチメント化して ai_scores に書き込む
  - regime_detector.py — ETF MA とマクロ記事の LLM によるレジーム判定、market_regime 書き込み
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート出力（CLI）
- run_monitoring.py — SystemMonitor ポーリングループ起動用スクリプト
- run_execution.py — ExecutionEngine 起動用スクリプト

補足（開発者向け）
----------------
- 自動で .env を読み込む処理は config._find_project_root() を使って .git や pyproject.toml を探索し、CWD に依存しない読み込みを行います。
- DB マイグレーションは軽微な列追加レベルで monitoring_db.init_monitoring_db() に実装済みです。
- AI 系のテストは外部 API 呼び出し部分（_call_openai_api など）をモックできるよう設計されています。

ライセンス・貢献
----------------
- この README にはライセンス情報を含めていません。実プロジェクトに組み込む場合は適切な LICENSE ファイルを追加してください。

問い合わせ
----------
- 実装に関する質問や追加ドキュメントが必要であれば、どの部分を深掘りしたいか教えてください（例: ExecutionEngine の起動フロー、OrderRepository スキーマ、AI プロンプト設計など）。