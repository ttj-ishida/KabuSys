# KabuSys

日本株自動売買システムの一部コンポーネント群（Execution / Monitoring / Portfolio / Research / AI ユーティリティ等）の実装群です。本リポジトリは本番運用・ペーパー取引・解析用途それぞれに対応するモジュールを含みます。

注意: 本 README はリポジトリ内のソースコードを基に作成しています。実環境での運用には API キーやブローカー設定、各種マスタデータの準備が必要です。OpenAI 等外部 API の利用はコストとレート制限に注意してください。

---

## プロジェクト概要

- Execution（発注エンジン）と Monitoring（監視エンジン）を中心とした自動売買／監視ユーティリティ群。
- DuckDB を用いたパブリック時系列データ（prices_daily / raw_financials / raw_news 等）の解析機能（リサーチ）。
- Portfolio 構築ロジック（候補選定・重み付け・リスク調整・株数決定）を純粋関数で実装。
- AI 補助（ニュースの NLP スコアリング、マクロレジーム判定）を OpenAI API (gpt-4o-mini 想定) で実装。
- 監視用 SQLite DB を持ち、Streamlit ダッシュボードやペーパー取引検証レポート生成ツールを提供。

主要ファイル（抜粋）:
- src/kabusys/run_execution.py — ExecutionEngine 起動スクリプト（KABUSYS_ENV による paper/live 切替）
- src/kabusys/run_monitoring.py — SystemMonitor 単体ポーリング起動スクリプト
- src/kabusys/config.py — 環境変数 / .env 読み込みと Settings
- src/kabusys/monitoring/ — 監視関連（MonitoringDB / SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / AlertManager 等）
- src/kabusys/portfolio/ — ポートフォリオ構築ユーティリティ
- src/kabusys/research/ — ファクター・特徴量・IC 計算
- src/kabusys/ai/ — news_nlp / regime_detector（OpenAI を利用）
- src/kabusys/tools/paper_verification_report.py — Paper Trading 検証レポート生成ツール
- src/kabusys/monitoring/streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード

---

## 機能一覧

- Execution
  - ブローカークライアントの抽象化（実運用 / モックを切替）
  - OrderManager / OrderRepository による注文ライフサイクル管理
  - Reconciler による再起動時の自動復旧（注文・ポジション整合）
  - リスク管理（RiskManager）や注文調停（Reconciler）等（実装参照）

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス存在チェック、データ鮮度チェック
  - TradeMonitor: 滞留注文検出、約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション数監視、ダッシュボード更新
  - KillSwitch: 条件に応じて flag ファイルを書き ExecutionEngine 停止シグナル発行
  - AlertManager: LINE Push によるアラート送信（クールダウンあり）
  - MonitoringEngine: 上記 Monitor を束ねたポーリングループ
  - Streamlit ダッシュボード（read-only で monitoring DB を表示）

- Portfolio
  - 候補選定（select_candidates）
  - 等金額・スコア加重配分（calc_equal_weights / calc_score_weights）
  - リスク調整（セクターキャップ, レジーム乗数）
  - ポジションサイズ計算（単元丸め・aggregate cap・コストバッファ対応）

- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 接続を受ける純粋関数）
  - 将来リターン計算、IC（Spearman）評価、統計サマリ

- AI
  - news_nlp.score_news: raw_news を集約して OpenAI で銘柄ごとのセンチメントを ai_scores に書込
  - regime_detector.score_regime: MA200 乖離とマクロニュースセンチメントを合成して市場レジーム判定

- ツール
  - paper_verification_report: Paper Trading DB から検証レポートを生成（稼働率・成功率・レイテンシ等）

---

## 前提・依存関係

推奨 Python バージョン: 3.10+

主な Python パッケージ（参考）:
- duckdb
- psutil
- requests
- openai
- streamlit

実行前に仮想環境を作成し、必要パッケージをインストールしてください。requirements.txt はリポジトリに含まれていない想定のため、以下は例です：

python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit

（運用ではブローカー SDK 等追加依存が必要になる可能性があります）

---

## 設定 (.env / 環境変数)

設定は環境変数またはプロジェクトルートの .env / .env.local から読み込まれます（src/kabusys/config.py の自動ローダ）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を指定します。

主な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE Push 通知用（任意）
- KABUSYS_ENV — 環境: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、発注は MockBrokerClient を使い、DB は data/paper_trading.db に分離されます
- PAPER_FILL_MODE — paper_trading 時のモック約定モード（instant | partial | never | reject）
- SQLITE_PATH — 監視 DB パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch 用 flag（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）

.env.example を作成して必要な値をセットしてください（コード内で未設定で必須なものは Settings が例外を投げます）。

例 (.env):
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
KABUSYS_ENV=paper_trading
PAPER_FILL_MODE=instant

---

## セットアップ手順

1. レポジトリを取得
   - git clone <repo_url>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

   （必要に応じてブローカー SDK など追加）

4. .env を作成
   - プロジェクトルートに .env または .env.local を配置し、必要な環境変数を設定

5. データディレクトリを用意
   - デフォルトで SQLite / DuckDB は data/ 以下を使用します。適宜作成してください。
   - Monitoring DB は init_monitoring_db() 実行時にスキーマが作られます。

---

## 使い方（主要コマンド）

- ExecutionEngine を起動（Production / Paper 切替は KABUSYS_ENV）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - python -m kabusys.run_execution

  注意: run_execution は Settings を読み取り、paper_trading の場合は専用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。

- SystemMonitor 単体ポーリングを起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - デフォルトは 60 秒間隔。0 以下や不正値は 60 にフォールバックします。

- Streamlit ダッシュボード（監視DB を read-only で表示）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（プログラム的に呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、内部で ai_scores / market_regime へ書き込みます。
  - API キーは引数で渡すか環境変数 OPENAI_API_KEY を利用。

---

## 運用上の注記・ヒント

- PID / Kill Flag
  - ExecutionEngine は PID を Settings.pid_file_path に書きます。SystemMonitor はその PID を参照してプロセス生存チェックを行い、stale PID を検出した場合は削除してアラートを記録します。
  - KillSwitch は Settings.kill_flag_path にファイルを書いて ExecutionEngine に停止シグナルを送ります。起動時にフラグをクリアする挙動は設定で制御可能。

- Paper Trading
  - KABUSYS_ENV=paper_trading を使うと発注は MockBrokerClient に送られ、paper 専用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録されます。本番 DB と完全に分離されるよう設計されています。

- OpenAI 呼び出し
  - rate-limit / ネットワーク断 / 5xx などは適切にリトライ（指数バックオフ）する実装になっていますが、API コストには注意してください。

- .env 自動読み込み
  - config.py はプロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を自動読込します。テストなどで自動読込を無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- データ鮮度
  - SystemMonitor は DuckDB の prices_daily から最終データ日を取得してデータ鮮度を判定します（許容差: 3 日）。本番運用時は prices_daily の定期更新が必要です。

---

## ディレクトリ構成

以下は主要ファイルを抜粋した構成（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - monitoring/
    - __init__.py
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - (order_manager.py, reconciler.py, broker_factory 等 — 発注関連)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - (DuckDB 用パイプライン / stats ユーティリティ 等)
  - utils/
    - __init__.py
    - process_priority.py

ディレクトリ内の各モジュールは、できるだけ副作用を抑えた純粋関数 / クラス設計を心がけています（例: research・portfolio モジュールは DB 参照を限定、monitoring_db は CRUD に特化）。

---

## よくある操作例（まとめ）

- 監視だけを動かす（ローカルで SystemMonitor のみ）
  - python -m kabusys.run_monitoring

- 実際の取引ロジックを起動（注意: ブローカー設定必須）
  - python -m kabusys.run_execution

- ペーパー取引モードで起動
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Streamlit で監視ダッシュボード表示
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading の検証レポートを出力
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

---

## 最後に（セキュリティ / 法的注意）

- ブローカー API キー・OpenAI キー等の機密情報は公開リポジトリに含めないでください。常に環境変数かシークレットマネージャを利用してください。
- 自動売買は金融商品取引に関わる行為です。実運用前に十分な検証とリスク管理、法令遵守を行ってください。

---

必要であれば README に「設定例の .env.example」や「requirements.txt の雛形」「各コンポーネントの詳細な起動オプション」を追加します。どの情報を追記したいか教えてください。