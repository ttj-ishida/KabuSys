# KabuSys

KabuSys は日本株の自動売買・リサーチ・監視を想定した軽量ライブラリ群です。本リポジトリは複数のサブモジュール（実行エンジン、監視、ポートフォリオ構築、リサーチ、AI 補助処理など）を含み、SQLite / DuckDB を用いてデータ永続化・分析を行います。

以下はコードベースから抽出した README.md です。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 環境変数（主なもの）
- 起動・使い方
  - 監視ループ起動 (run_monitoring)
  - 実行エンジン起動 (run_execution)
  - Paper Trading 検証レポート生成ツール
  - 監視ダッシュボード (Streamlit)
  - AI モジュール（ニュース NLP / レジーム検出）
- ディレクトリ構成
- 運用メモ / 注意事項

---

プロジェクト概要
- 自動売買に必要なコンポーネント群を提供する Python コードベース。
- 主要機能は「ExecutionEngine（発注管理）」「Monitoring（稼働監視・リスク監視・アラート）」「Portfolio construction（銘柄選定・配分・ポジション決定）」「Research（ファクター計算、特徴量解析）」「AI 補助（ニュースの NLP スコアリング、レジーム判定）」など。
- 永続化は主に SQLite（監視ログ、トレードログ、ポジション等）と DuckDB（時系列価格やファイナンスデータの分析）で行う。

主な機能一覧
- Execution
  - OrderManager / ExecutionEngine（ブローカーとの発注・状態管理、再起動時のリコンシリエーション）
  - ブローカーファクトリ（本番 / Paper Trading の切り替え）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス・データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウン / ポジション上限の監視とイベント記録
  - KillSwitch / AlertManager: 条件に応じた停止フラグ作成や LINE 通知
  - MonitoringEngine: 複数 Monitor を束ねたポーリングループ
  - Streamlit ダッシュボード（read-only 表示）
- Portfolio Construction
  - 銘柄候補選定、重み計算、単元丸め、リスク調整（セクターキャップ・レジーム乗数）
- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）などの統計ユーティリティ
- AI
  - ニュース NLP（OpenAI API を用いた銘柄単位のセンチメントスコア生成）
  - レジーム検出（ETF の MA200 乖離 + マクロニュースセンチメントの合成）
- ツール
  - Paper Trading 検証レポート（kabusys.tools.paper_verification_report）
  - 各種ユーティリティ（プロセス優先度設定など）

セットアップ手順（開発環境想定）
1. Python の仮想環境を作成・有効化
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 本リポジトリに requirements.txt が無い場合、少なくとも以下をインストールしてください：
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

3. 実行方法
   - 開発時はプロジェクトルートから Python モジュールとして実行できます（src 配下がパッケージルートの場合）：
     - PYTHONPATH=src python -m kabusys.run_monitoring
     - PYTHONPATH=src python -m kabusys.run_execution
   - あるいはパッケージを pip install -e . する（pyproject/setup があれば）。

環境変数（主なもの）
- KABUSYS_ENV: 起動環境。development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、実行エンジンは MockBroker を使用して paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を利用します。
- SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定挙動（instant / partial / never / reject、デフォルト: instant）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時に必要）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE通知）で使用
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）。0 以下や不正値は 60 にフォールバック。
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が書き込む停止フラグ path（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を削除するか（"1" でクリア）

.env の自動読み込み
- プロジェクトルートの .env と .env.local が自動で読み込まれます（OS 環境変数が優先）。
- 自動ロードを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方（代表的な起動例）

1) 監視ループ（Monitoring）
- 目的: システムリソースや ExecutionEngine の状態、注文ログを定期的に監視し monitoring DB に記録する。
- 起動:
  - PYTHONPATH=src python -m kabusys.run_monitoring
  - オプション: 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を指定できます（秒）。
- 停止:
  - プロジェクトルート data/stop_requested.flag を作成すると run_monitoring が検知してループを終了します（stop_requested.flag は run_monitoring と run_execution とで使用）。
  - KillSwitch は条件を満たすと data/kill.flag を書き込み、ExecutionEngine の停止を要求します（ExecutionEngine は起動時に kill.flag を検査し、存在すれば起動しません）。

2) 実行エンジン（Execution）
- 目的: ブローカーと連携して発注を行う実行プロセス。
- 起動:
  - PYTHONPATH=src python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading に設定すると paper_trading 用の SQLite（デフォルト data/paper_trading.db）に完全分離して記録します。
- 停止:
  - data/stop_requested.flag を作成すると実行中のエンジンを停止させます。
  - kill.flag（KILL_FLAG_PATH）を監視し、KillSwitch による停止要求が出された場合も停止します。
- PID ファイル: 実行中は data/execution.pid に PID を書き込みます。SystemMonitor はこの PID を確認して Execution の生存監視を行います。

3) Paper Trading 検証レポート
- モジュール: kabusys.tools.paper_verification_report
- 実行例:
  - PYTHONPATH=src python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db data/paper_trading.db
- 出力: 稼働率、注文成功率、送信率、レイテンシ（P95）などの指標と PASS/FAIL 判定（閾値はソース内に定義）。

4) 監視ダッシュボード（Streamlit）
- ファイル: src/kabusys/monitoring/streamlit_dashboard.py
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明: read-only モードで monitoring DB を読み、ダッシュボード表示を行います。DB は読み取り専用で開かれます。

5) AI 関連
- ニュース NLP（kabusys.ai.news_nlp.score_news）
  - raw_news / news_symbols を元に OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出し ai_scores テーブルへ書き込みます。
  - 実行には OPENAI_API_KEY が必要。batch サイズや最大記事数等はソース内の定数で制御。
- レジーム検出（kabusys.ai.regime_detector.score_regime）
  - ETF (1321) の MA200 乖離とマクロニュースの LLM スコアを合成して market_regime テーブルに書き込みます。
  - OpenAI API が必要。API 失敗時は部分的にフォールバックする設計です。

ディレクトリ構成（主要ファイルと説明）
- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動読み込み、Settings クラス）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化・ラップ（MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度の監視
    - trade_monitor.py — 注文滞留・約定異常の監視
    - risk_monitor.py — ドローダウン・ポジション上限の監視
    - kill_switch.py — kill.flag 書き込みロジック
    - alert_manager.py — LINE 通知ラッパ
    - monitoring_engine.py — モニタ群のポーリング制御
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, broker_factory.py, ...（発注・リコン・リスク管理等）
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py — 銘柄選定・配分・ポジション計算
  - research/
    - factor_research.py, feature_exploration.py — ファクター・研究ユーティリティ
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — レジーム判定（OpenAI）
  - data/ (実行時に使用するファイル群: monitoring.db, paper_trading.db, kabusys.duckdb, kill.flag, stop_requested.flag, execution.pid など)

運用メモ / 注意事項
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は idempotent にテーブル・インデックスを作成し、必要に応じて簡易マイグレーション（カラム追加）も行います。
- 権限・OS 差分:
  - process priority / cpu affinity の設定は psutil を使用し、Windows と POSIX 系で処理を分岐します。権限不足時はログに警告が出てスキップされます。
- ルックアヘッドバイアス回避:
  - AI / レジーム判定 / ファクター計算は内部で現在時刻（date.today() 等）を直接参照しない設計に配慮しています。target_date を明示的に渡すこと。
- フェイルセーフ:
  - AI 呼び出し失敗時は（多くの箇所で）明示的にフォールバック値を使用して継続するよう実装されています（例: macro_sentiment=0.0）。
- Paper Trading と本番 DB の分離:
  - KABUSYS_ENV=paper_trading のとき、paper_sqlite_path を使って本番 DB と完全分離されます。
- flag ファイル:
  - stop_requested.flag（run_* スクリプトの外部停止用）と kill.flag（KillSwitch による停止要求）は project_root/data に置かれます。実行前に不要な flag をクリアしてください。

以上がコードベースから作成した README.md の内容です。必要なら「環境変数の全一覧」「より詳しい起動シーケンス（順序図）」「サンプル .env.example」などを追記できます。どの情報を優先して追加しましょうか？