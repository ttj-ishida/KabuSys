# KabuSys

KabuSys は日本株向けの自動売買 / 監視フレームワークです。本リポジトリはアルゴリズム、発注管理、監視、AI によるニュースセンチメント、研究用ファクター計算などを含むモジュール群を提供します。

以下はこのコードベースの概要、機能、セットアップ手順、使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

- 日本株自動売買システムのコアライブラリ。
- ExecutionEngine（発注エンジン）・Monitoring（監視）・Portfolio Construction・Research（ファクター計算）・AI（ニュースのセンチメント評価）を含む。
- 実稼働（live）・ペーパートレード（paper_trading）・開発（development）の環境切替に対応。
- SQLite（監視ログ等）と DuckDB（時系列価格・財務データ等）をデータストアとして使用。
- OpenAI（gpt-4o-mini）を使ったニュース NLP / レジーム判定の統合（任意）。

---

## 主な機能一覧

- Execution（発注）周り
  - OrderManager / OrderRepository による注文生成・管理
  - Reconciler による再起動時の自動復旧（ブローカーと突合）
  - Paper Trading モード（本番 DB とは完全に分離された専用 SQLite を使用）
- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク・プロセス・データ鮮度の監視
  - TradeMonitor: 注文滞留・約定異常監視
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: リスク条件に応じた停止フラグ（data/kill.flag）書き込み
  - AlertManager: LINE Messaging API への通知（クールダウン付き）
  - Streamlit ダッシュボード（監視 UI）
- Portfolio construction
  - 候補選定・重み計算（等分・スコア加重）
  - セクター上限適用、レジーム乗数
  - 株数決定・単元丸め、投下資金スケーリング
- Research
  - momentum/value/volatility 等のファクター計算（DuckDB ベース）
  - 将来リターン・IC（情報係数）計算、統計サマリ
- AI
  - news_nlp: raw_news を LLM でセンチメント化して ai_scores に保存
  - regime_detector: MA200 とマクロニュースで日次レジーム判定
- ユーティリティ
  - process_priority（プロセス優先度 / CPU affinity 設定）
  - .env 自動ロード（プロジェクトルート検出）

---

## セットアップ手順

前提:
- Python 3.10 以上（typing の | 演算子等を使用）
- OS に応じた SQLite / DuckDB の利用可能環境

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai requests streamlit
   - （必要に応じて他の依存パッケージを追加）

4. data ディレクトリを作成（いくつかのスクリプトが自動で作成しますが事前に用意しておくと安全）
   - mkdir -p data

5. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数が優先されます）。
   - 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

例: .env（最小）
- KABUSYS_ENV=development            # development | paper_trading | live
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- OPENAI_API_KEY=...                 # AI 機能を使う場合に必要
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- LINE_CHANNEL_ACCESS_TOKEN=...
- LINE_USER_ID=...
- LOG_LEVEL=INFO

注意:
- Paper Trading 実行時は KABUSYS_ENV=paper_trading にすると MockBrokerClient（実装による）を利用し、paper_trading 専用 DB に記録します。本番 DB と完全分離されます。

---

## 使い方

基本的な実行例と各スクリプトの役割を示します。

1. 監視（Monitoring）プロセス起動
   - python -m kabusys.run_monitoring
   - 説明: SystemMonitor をポーリングして system_status / risk_logs / trade_logs / dashboard を更新します。
   - 環境変数:
     - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）。1 未満・不正値は無視されデフォルトにフォールバック。
     - run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を監視 DB として使います。
   - 停止:
     - プロセスを Ctrl+C（KeyboardInterrupt）するか、プロジェクト内の data/stop_requested.flag を作成するとループが終了します。

2. Execution（発注エンジン）起動
   - python -m kabusys.run_execution
   - 説明: ExecutionEngine を起動します。KABUSYS_ENV=paper_trading のときは paper_trading 用 DB を使います。
   - 実行フロー:
     - PID ファイル（data/execution.pid）を作成・監視。
     - data/stop_requested.flag が存在すると起動を避けたり、起動中に検出すると停止します。
   - 停止:
     - data/stop_requested.flag を作成するか、プロセスに SIGINT を送る。

3. Streamlit ダッシュボード
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 説明: 監視用 UI。読み取り専用で SQLite を開く（存在しない場合はエラーを表示）。

4. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - オプション:
     - --db PATH: ペーパートレード SQLite ファイルを明示的に指定（PAPER_TRADING_SQLITE_PATH 環境変数の代替）
     - --from / --to: YYYY-MM-DD 形式で期間指定

5. AI 機能（ニューススコア / レジーム判定）
   - kabusys.ai.score_news と kabusys.ai.regime_detector.score_regime は OpenAI API キー（OPENAI_API_KEY）を必要とします。
   - 呼び出し例（Python API 内から）:
     - from kabusys.ai.news_nlp import score_news
     - score_news(conn, date(2026,4,1), api_key="...")  # api_key を引数で渡すか環境変数を利用
   - 注意: API 呼び出しに失敗した場合はフェイルセーフ（部分スコア化、0.0 フォールバック等）の挙動を取ります。

6. 環境切替
   - KABUSYS_ENV の有効値: development / paper_trading / live
   - Settings クラスで環境に応じた挙動（is_paper など）を提供します。

---

## 主要ファイル / 生成されるデータファイル

デフォルトで使用されるファイル（プロジェクトルートの data/ 内）:
- data/monitoring.db          — 監視ログ SQLite（Settings.sqlite_path）
- data/paper_trading.db       — ペーパートレード専用 SQLite（PAPER_TRADING_SQLITE_PATH）
- data/kabusys.duckdb         — DuckDB（価格・財務データ等）
- data/execution.pid          — ExecutionEngine の PID ファイル
- data/kill.flag              — KillSwitch が停止シグナルを書き込むファイル
- data/stop_requested.flag    — 外部からプロセス停止を指示するフラグファイル

---

## ディレクトリ構成

リポジトリの主要なソース構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / .env の読み込みと Settings
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py                  — ニュースを LLM で評価して ai_scores に保存
    - regime_detector.py           — レジーム判定（MA200 + マクロニュース）
  - monitoring/
    - monitoring_db.py             — SQLite 永続化層（monitoring 用）
    - system_monitor.py            — システム・データ鮮度監視
    - trade_monitor.py             — 注文滞留 / 約定異常監視
    - risk_monitor.py              — ドローダウン / ポジション上限監視
    - kill_switch.py               — kill.flag 書き込みロジック
    - alert_manager.py             — LINE push 通知ラッパ
    - monitoring_engine.py         — 各モニタを束ねるエンジン
    - streamlit_dashboard.py       — Streamlit ダッシュボード
  - execution/
    - order_manager.py             — 注文ステートマシンの外向 API
    - reconciler.py                — 再起動時の同期・ポジションリコン
    - (その他: broker_factory, execution_engine, order_repository 等)
  - portfolio/
    - portfolio_builder.py         — 候補選定・重み計算
    - position_sizing.py           — 株数決定・スケール処理
    - risk_adjustment.py           — セクター上限・レジーム乗数
  - research/
    - factor_research.py           — Momentum/Value/Volatility 等の計算
    - feature_exploration.py       — 将来リターン・IC・統計サマリ
  - data/                          — （実行時に使われる/生成される）DB・フラグ等
  - utils/
    - process_priority.py          — プロセス優先度 / CPU affinity のユーティリティ

---

## 注意事項 / 運用上のポイント

- .env の自動読み込み
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）にある `.env` / `.env.local` を自動で読み込みます。
  - OS 環境変数は上書きされません（.env.local は override=True でロードするが protected set により OS 変数は保護されます）。
  - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- DB マイグレーション
  - init_monitoring_db() は安全に複数回呼べる（冪等）ように実装されています。既存の DB にカラムがない場合は簡易な ALTER を行います。

- Paper Trading
  - KABUSYS_ENV=paper_trading の場合、paper_trading 用の SQLite に書き込まれ、本番 DB とは分離されます。PAPER_FILL_MODE（instant/partial/never/reject）で約定挙動を制御できます。

- OpenAI API
  - OPENAI_API_KEY が未設定だと AI 機能は動作しません。API 呼び出しはリトライやフェイルセーフ（部分失敗でスキップ等）を備えていますが、API 利用料が発生します。

- プロセス優先度
  - run_monitoring / run_execution は起動時にプロセス優先度を "high" に設定しようと試みます。権限がない環境では警告を出しますが実行は継続されます。

---

README は以上です。実運用・拡張にあたっては以下を確認してください:
- 実際のブローカークライアント実装（API 認証・線形化等）
- orders / reconciler の詳細なデータ永続化とエラーハンドリング方針
- 本番稼働時の監視・アラート閾値と LINE 通知の設定

必要であれば、README に含めるサンプル .env のテンプレートや、運用手順（デプロイ・サービス化、systemd ユニット例）も作成します。どの情報が欲しいか教えてください。