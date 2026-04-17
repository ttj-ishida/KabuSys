# KabuSys

KabuSys は日本株の自動売買／リサーチ／監視を目的とした小規模な Python パッケージです。本リポジトリには、実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）および AI を使ったニューススコアリング等のコンポーネントが含まれます。

以下はコードベース（src/kabusys）に基づく README です。

---

目次
- プロジェクト概要
- 主な機能
- 必要条件
- セットアップ手順
- 使い方
  - 実行エンジン（ExecutionEngine）
  - 監視ループ（Monitoring）
  - Streamlit 監視ダッシュボード
  - Paper Trading 検証レポート
  - AI モジュール（ニュース NLP / レジーム判定）
- 環境変数（主なもの）
- 停止 / キルフロー
- ディレクトリ構成（抜粋）

---

プロジェクト概要
- 日本株自動売買システムのコア機能（発注管理、再接続／リコンシリエーション、リスク監視、監視ダッシュボード、ポートフォリオ構築、ファクター計算、ニュース NLP スコアリング）を含むライブラリ群です。
- 実行用スクリプト（run_execution.py, run_monitoring.py）および運用補助ツール（Streamlit ダッシュボード、paper_verification_report）を同梱しています。
- ローカル SQLite（監視ログ等）と DuckDB（時系列価格・ファイナンスデータの分析）をデータ層として利用します。

主な機能
- ExecutionEngine 起動・発注管理（OrderManager, OrderRepository）
- 再起動時の自動同期（Reconciler）
- リスク管理（RiskManager、RiskMonitor）と KillSwitch（閾値超過で停止シグナル）
- システム監視（CPU/メモリ/ディスク、Execution プロセス生存、データ鮮度）
- 注文滞留・約定異常検出（TradeMonitor）
- 監視ログ永続化（SQLite 用の MonitoringDB）
- Streamlit による監視ダッシュボード
- ポートフォリオ構築・位置決め（等配分・スコア加重・リスクベース等）
- リサーチ用ファクター計算（momentum / volatility / value）
- ニュースを LLM（OpenAI）でスコアリングする AI モジュール（news_nlp）、および市場レジーム判定（regime_detector）
- Paper Trading 向けの検証レポート生成ツール

必要条件
- Python 3.10+
- 利用する主な外部パッケージ（例）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit (ダッシュボード利用時)
- SQLite（組み込み）を使用
- （Optional）LINE 通知のために LINE Messaging API のアクセストークン

セットアップ手順（ローカル開発環境想定）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai requests streamlit
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）
4. 環境変数の設定
   - ルートに .env/.env.local を置くと自動で読み込まれます（詳細は下記参照）
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（実運用時）
   - OpenAI を使う場合: OPENAI_API_KEY
5. データディレクトリ
   - デフォルト DB パスは project_root/data/*.db です。必要に応じて事前に data ディレクトリを作成してください。
   - 例: mkdir -p data

主なファイル／スクリプトの使い方

1) 実行エンジン（ExecutionEngine）起動
- 概要: 発注ロジックを担う ExecutionEngine を別スレッドで起動します。KABUSYS_ENV に応じて本番 / Paper Trading が切り替わります。
- 起動:
  - 本番（default: development/live）:
    - python -m kabusys.run_execution
  - Paper Trading（ブローカーは MockBrokerClient を使用し、DB を data/paper_trading.db に記録）
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
- 備考:
  - プロセス優先度を High に設定します（psutil 経由、権限不足なら警告）。
  - 起動時に data/stop_requested.flag があれば起動せず終了します。
  - 実行中に data/stop_requested.flag を作成すると安全に停止します（touch data/stop_requested.flag）。

2) 監視ループ（Monitoring）起動
- 概要: SystemMonitor を定期ポーリングして system_status / risk_logs / trade_logs 等を記録します。
- 起動:
  - python -m kabusys.run_monitoring
- オプション／環境変数:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）。1 未満や不正値は無視され 60 秒にフォールバック。
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用します。
- 停止:
  - data/stop_requested.flag を作成することでループを抜けます。

3) Streamlit 監視ダッシュボード
- 起動例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 機能:
  - ダッシュボード（ポートフォリオ、ポジション一覧、注文ログ、最新のシステムステータス、リスクログ）
- 注意:
  - SQLite を read-only URI で開くため、MonitoringEngine が DB を作成していないと警告表示になります。

4) Paper Trading 検証レポート（tools）
- スクリプト: src/kabusys/tools/paper_verification_report.py
- 実行例:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で PAPER_TRADING_SQLITE_PATH を上書きできます。
- 出力: 稼働率、注文成功率、送信率、レイテンシ（P95）等の集計と PASS/FAIL 判定（閾値はスクリプト内定義）。

5) AI モジュール（ニュース NLP / レジーム判定）
- news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡して、raw_news / news_symbols から記事を集約し OpenAI API（gpt-4o-mini）で銘柄ごとのセンチメントを ai_scores テーブルへ書き込みます。
- regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の MA200 乖離とマクロ記事の LLM センチメントを合成して market_regime テーブルへ書き込みます。
- 必要: OPENAI_API_KEY 環境変数、または api_key を明示的に渡す。
- 注意: API 呼び出しの失敗時は安全側のフォールバック（スコア 0.0 等）を行う設計ですが、API 利用はコストが発生します。

環境変数（主なもの）
- KABUSYS_ENV: 起動環境。development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須：関連機能使用時）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須：実取引時）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- PAPER_FILL_MODE: Paper Trading 時の約定挙動（instant | partial | never | reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE 通知）用
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化

自動 .env 読み込みの挙動
- ルート（.git または pyproject.toml があるディレクトリ）を基準に .env と .env.local を自動で読み込みます。
- OS 環境変数が優先され、.env.local が .env を上書きします。
- テスト等で自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

停止 / キルフロー
- 優雅な停止（run_monitoring / run_execution が監視しているループを止める）
  - touch data/stop_requested.flag をプロジェクトルートに作成すると、ループが検知して終了します。
- KillSwitch（監視側）:
  - 閾値を超えた場合、KillSwitch が data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります（ExecutionEngine は kill.flag を検出して停止する設計）。
  - kill.flag を削除してクリアするには rm data/kill.flag してください。
- PID ファイル:
  - 実行時に execution.pid（デフォルト data/execution.pid）を作成します。stale PID が検出されると監視が削除・アラートします。

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py            — パッケージ定義、バージョン
  - config.py              — Settings クラス（環境変数管理、.env ローダー）
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポートジェネレータ
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py (省略)
    - execution_engine.py (省略)
    - broker_factory.py (省略)
    - ...                  — 発注周りの実装
  - monitoring/
    - monitoring_db.py     — SQLite テーブル定義・CRUD（MonitoringDB）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py — 各 Monitor を束ねる
    - alert_manager.py     — LINE への通知
    - kill_switch.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/                  — 既定の DB ファイル置き場（git 管理外を想定）
  - utils/
    - process_priority.py   — プロセス優先度 / CPU affinity 設定ユーティリティ

設計上の注意点 / 補足
- DuckDB を分析（prices_daily / raw_financials / raw_news など）に使います。DuckDB の接続を関数に渡して純粋に SQL で集計する設計です。
- 監視周り（MonitoringDB）は SQLite を想定し、init_monitoring_db() が必要テーブルを冪等に作成します。最初の接続時に自動的にスキーマが作られます。
- AI（OpenAI）呼び出しはリトライ・バックオフ・レスポンスバリデーション等のフェイルセーフが組み込まれていますが、API キーの管理とコストに注意してください。
- Paper Trading は本番 DB と完全分離する設計（settings.is_paper により sqlite の切替あり）。

ライセンス / コントリビュート
- （ここにライセンス情報と貢献方法を記載してください。リポジトリ側の LICENSE を参照してください。）

問題報告・改善提案
- バグや改善は Issue を立ててください。PR も歓迎します。

---

以上がこのコードベースに対する README の簡易版です。必要であれば以下の内容を追加で出力します：
- 具体的な .env.example（推奨キー一覧）
- 代表的な起動/運用手順（systemd / supervisor 用 unit ファイル例）
- テスト実行例（ユニットテストの実行方法）