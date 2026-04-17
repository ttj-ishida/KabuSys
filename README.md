# KabuSys

KabuSys は日本株向けの自動売買フレームワーク（プロトタイプ）です。戦略の構築・ポートフォリオ組成・発注実行・監視・検証ツールを備え、Paper Trading（検証）と Live 運用を切り替えて利用できます。

主な設計方針：
- モジュール分割（execution, monitoring, portfolio, research, ai 等）
- DuckDB / SQLite によるデータ永続化（価格データは DuckDB、監視ログは SQLite）
- Paper Trading と Live を明確に分離（Paper は専用 DB を使用）
- 外部サービス呼び出しを抽象化（BrokerClientFactory / OpenAI 呼び出し等）
- フェイルセーフ（API 失敗時はフォールバック／ログを残して継続）

---

## 機能一覧
- Execution（発注エンジン）
  - Broker 抽象化（Paper 用 MockBroker を含む）
  - OrderManager / Reconciler による起動時リコンシリエーション
  - RiskManager（発注制限・サーキットブレーカー等）
- Monitoring（監視）
  - SystemMonitor：プロセス・CPU/メモリ/ディスク・データ鮮度の監視
  - TradeMonitor：滞留注文・約定異常価格の検出
  - RiskMonitor：ドローダウン・ポジション上限の監視
  - AlertManager：LINE Push による通知（任意設定）
  - KillSwitch：条件に応じて ExecutionEngine 停止フラグを書き込み
  - Streamlit ダッシュボード
- Portfolio（組成）
  - 候補選定・等配分 / スコア配分
  - セクター上限適用、レジーム乗数
  - 発注株数計算（単元丸め・aggregate cap）
- Research（研究用）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（情報係数）、統計サマリ
- AI（自然言語処理）
  - ニュースセンチメントによる銘柄スコアリング（OpenAI 使用）
  - 市場レジーム判定（MA200 とマクロニュースの合成）
- ツール
  - Paper Trading 検証レポート生成スクリプト（期間指定可能）

---

## 動作要件（推奨）
- Python 3.10+
- 必須パッケージ（代表例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボードを使う場合)
- SQLite（Python 標準モジュール sqlite3 を使用）
- ネットワーク接続（Live 実行時のブローカー API / OpenAI 等）

requirements.txt はこのリポジトリに含まれていない想定のため、上記パッケージを適宜インストールしてください。

例:
pip install duckdb psutil requests openai streamlit

---

## セットアップ手順（ローカル）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
4. data ディレクトリを作成（必要に応じて）
   - mkdir -p data
5. 環境変数設定
   - プロジェクトルートの `.env` または環境変数で設定します。
   - 自動ロード機能が有効（Settings モジュール）なら `.env` / `.env.local` を置くだけで読み込まれます。

推奨の最小環境変数（例）:
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- OPENAI_API_KEY=...         (AI 機能を使う場合)
- KABUSYS_ENV=development|paper_trading|live
- LINE_CHANNEL_ACCESS_TOKEN=... (通知を使う場合)
- LINE_USER_ID=...                (通知を使う場合)

主要な設定（Settings により取得可能）:
- KABUSYS_ENV: operation mode（development / paper_trading / live）
  - paper_trading 時は MockBrokerClient が使われ、専用 DB（data/paper_trading.db）に記録されます
- SQLITE_PATH: 監視用 SQLite DB（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant|partial|never|reject（Paper の約定挙動）

---

## 使い方（主要スクリプト・コマンド）

- ExecutionEngine（発注エンジン）起動
  - 環境に応じて KABUSYS_ENV を設定
    - Paper Trading（検証用）:
      - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - Live 実行:
      - KABUSYS_ENV=live python -m kabusys.run_execution
  - 実行前に data/execution.pid や data/kill.flag の扱いに注意してください。
  - 起動時に stop フラグ（data/stop_requested.flag）や kill.flag が存在すると起動・継続を制御します。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）。
  - 監視は常に本番の sqlite_path を参照する設計です（KABUSYS_ENV に関わらず）。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、ポートフォリオ / 注文 / システム状態を可視化します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH を上書き）
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- AI 関連（スクリプトから呼び出す API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OpenAI API キー（OPENAI_API_KEY）を必要とします。CLI のエントリは用意されていないため、スクリプトやジョブから呼び出してください。

- 停止 / 再開制御
  - Graceful 停止用フラグファイル:
    - data/stop_requested.flag — run_monitoring / run_execution のループを検知して停止
    - data/kill.flag — KillSwitch が書き込むことで ExecutionEngine 停止を指示
  - KillSwitch.clear() を使うか、ファイルを削除して再起動します。

---

## .env 例（テンプレート）
以下は .env の一例です（プロジェクトルートに置く）:

JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PAPER_FILL_MODE=instant
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

注意: 実運用では秘密情報の管理に注意してください（.env をバージョン管理しない等）。

---

## ディレクトリ構成（主なファイル）
（項目は src/kabusys 以下を想定）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理（Settings）
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート CLI
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP（OpenAI）による銘柄スコアリング
    - regime_detector.py            — 市場レジーム判定（MA200 + マクロニュース）
  - monitoring/
    - __init__.py
    - monitoring_db.py              — SQLite 監視ログ層（テーブル初期化・CRUD）
    - system_monitor.py             — システム／データ鮮度監視
    - trade_monitor.py              — 注文滞留・約定異常監視
    - risk_monitor.py               — ドローダウン・ポジション監視
    - kill_switch.py                — 停止フラグ管理
    - alert_manager.py              — LINE 通知
    - monitoring_engine.py          — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py        — Streamlit ダッシュボード
  - execution/
    - (OrderManager, ExecutionEngine, Reconciler, OrderRepository 等の実装ファイル)
    - order_manager.py
    - reconciler.py
    - order_repository.py
    - order_record.py
    - broker_factory.py
    - execution_engine.py
    - risk_manager.py
    - order_repository.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py          — 候補選定 / 重み計算
    - position_sizing.py            — 株数計算（単元丸め、aggregate cap）
    - risk_adjustment.py            — セクター制限・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py            — モメンタム／ボラ／バリュー計算
    - feature_exploration.py        — 将来リターン / IC / 統計
  - data/                           — デフォルトの DB ファイルやフラグファイルを配置（git 管理外推奨）
    - monitoring.db
    - paper_trading.db
    - kabusys.duckdb
    - execution.pid
    - kill.flag
    - stop_requested.flag
  - utils/
    - __init__.py
    - process_priority.py           — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 注意事項 / 運用メモ
- Paper Trading は本番 DB と明確に分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- Settings はプロジェクトルートの .env（または .env.local）を自動読み込みします。OS 環境変数が優先されます。
- Monitoring の初期化（init_monitoring_db）は冪等設計。初回起動時にテーブルを作成します。
- OpenAI 呼び出しはレートリミット・一時エラーを考慮したリトライを実装していますが、APIキーや料金の管理は利用者側で行ってください。
- streamlit ダッシュボードは読み取り専用で DB を開きます。監視データがないと表示が空になることがあります。
- process priority / cpu affinity の設定には OS 権限が必要な場合があります（psutil を使用）。アクセス拒否時はログに警告が出ますが処理は継続します。
- ログレベルは LOG_LEVEL 環境変数（Settings.log_level）で制御できます。

---

この README はコードベースの主要ポイントをまとめたものです。個々のモジュール（ExecutionEngine や RiskManager、AI モジュール等）の詳細はソースコードの docstring を参照してください。運用にあたっては .env の管理、DB バックアップ、テスト環境と本番環境の切り分けを徹底してください。