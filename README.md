# KabuSys

日本株向けの自動売買システム（ライブラリ＆ランタイムコンポーネント群）。  
本リポジトリには、取引エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築・ポジションサイズ計算、研究用ファクター計算、ニュースのLLM解析などの主要コンポーネントが含まれます。

- 状態: v0.1.0（src/kabusys/__init__.py の __version__）

---

## プロジェクト概要

KabuSys は次のような責務を持つモジュール群で構成されています。

- Execution: シグナル受け取り→発注→注文状態管理→再起動時のリコンシリエーション
- Monitoring: システム状態、注文滞留、リスク（ドローダウン・ポジション数）監視、LINE通知、ダッシュボード
- Portfolio: 候補選定、配分（等配分 / スコア加重）、ポジションサイズ算出、セクターキャップ適用、レジーム乗数
- Research: DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー）、特徴量探索、IC計算
- AI: OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（news_nlp）と市場レジーム判定（regime_detector）
- Tools: Paper Trading 検証レポート生成、Streamlit 監視ダッシュボード起動スクリプト等
- Utils: プロセス優先度・CPU affinity 設定ユーティリティ、設定(.env)読み込みロジック 等

設計上の特徴：
- DuckDB / SQLite をデータ層として利用（研究用と監視用等で分離）
- Paper Trading 環境を想定した完全分離（PAPER_TRADING_SQLITE_PATH）
- 環境変数 / .env による設定（自動ロード機能有り、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
- OpenAI 呼び出しは堅牢化（リトライ / バリデーション / スコアクリップ）

---

## 主な機能一覧

- Execution
  - Broker 抽象化（実ブローカー / モックの切替）
  - Order 管理、状態遷移、再起動時の同期（Reconciler）
  - RiskManager（発注前リスクチェック、サーキットブレーカー等）※設定あり

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス存否、データ鮮度監視
  - TradeMonitor: 注文滞留・約定価格異常検出
  - RiskMonitor: ドローダウン通知、ポジション上限監視
  - KillSwitch: 条件に応じて data/kill.flag を書き込み Execution を停止
  - AlertManager: LINE Push による通知（クールダウン実装）
  - Streamlit ダッシュボード（data/monitoring.db を参照）

- Portfolio
  - 候補選定、等配分 / スコア加重、リスクベースの株数計算
  - セクター上限適用、レジーム乗数計算

- Research
  - モメンタム / ボラティリティ / バリューのバッチ計算（DuckDB を使用）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー

- AI
  - news_nlp.score_news: ニュースを銘柄別に集約し LLM でセンチメント評価 → ai_scores へ書込
  - regime_detector.score_regime: ETF ma200 乖離とマクロセンチメントを合成して market_regime に書込

- Tools
  - paper_verification_report: Paper Trading DB を読み取り検証レポート出力
  - streamlit_dashboard: Streamlit による監視表示

---

## 要件（推奨）

- Python 3.10+
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード使用時)
- SQLite（標準ライブラリで利用可能）
- ネットワーク接続（OpenAI / LINE API 利用時）

パッケージは requirements.txt があればそれを使うか、必要に応じて以下をインストールしてください:

pip install duckdb psutil requests openai streamlit

---

## セットアップ手順

1. リポジトリをクローン / 配置
2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt  （requirements.txt がない場合は上記パッケージ群）
4. .env を用意（プロジェクトルートに配置）
   - サンプル: .env.example を参照してください（本リポジトリに例が無い場合は下記に主要キー例を記載）
5. data ディレクトリを作成（DB や flag 用）
   - mkdir -p data
6. 環境変数の自動ロード
   - デフォルトで config.py がプロジェクトルートの .env / .env.local を自動で読み込みます。
   - 自動読み込みを無効にするには: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（例）
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須な箇所があれば）
- KABU_API_PASSWORD: kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 使用時）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用監視 DB（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒。default=60）
- PAPER_FILL_MODE: paper_trading の注文約定モード（instant|partial|never|reject）
- PID_FILE_PATH / KILL_FLAG_PATH など（config.Settings 参照）

---

## 使い方

注意: スクリプトはモジュール形式で実行することを推奨します（パッケージとしての import を想定）。

1) 監視ループの起動（SystemMonitor 単体実行）
- 実行:
  - python -m kabusys.run_monitoring
- 説明:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒、デフォルト 60）
  - 実行中は SQLite（settings.sqlite_path）に system_status 等のログを書きます
  - data/stop_requested.flag が存在するとループを終了します
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存せず）

2) ExecutionEngine（発注エンジン）の起動
- 実行:
  - python -m kabusys.run_execution
- 説明:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db を利用（本番 DB と分離）
  - 起動時に data/stop_requested.flag があれば起動せず終了
  - 実行中に data/stop_requested.flag が作成されるとエンジンを停止
  - 実行中は pid ファイル（data/execution.pid）を書きます

3) Streamlit 監視ダッシュボード
- 実行:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - read-only で監視 DB を開き、Overview / Positions / Orders / System タブを表示します

4) Paper Trading 検証レポート生成
- 実行:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプションで --db PATH を指定して別 DB を使えます
- 説明:
  - 指定期間の稼働率、注文成功率、送信率、レイテンシ等を集計して PASS/FAIL 判定を出力します

5) AI 関連（ニューススコアリング / レジーム判定）
- OpenAI API キーが必要（OPENAI_API_KEY）
- ニューススコアリング:
  - Python から呼ぶ例:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="sk-...")
- レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="sk-...")

6) ライブラリとしての利用（研究・ポートフォリオ構築）
- 研究モジュール呼び出し例:
    from kabusys.research import calc_momentum, calc_volatility, calc_value
    records = calc_momentum(duckdb_conn, date(2026,4,10))
- ポートフォリオ:
    from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes

---

## フラグファイル・PID の扱い

- data/stop_requested.flag: run_monitoring/run_execution が監視している停止フラグ
- data/kill.flag: KillSwitch が書き込む停止通告（ExecutionEngine 停止用）
- data/execution.pid: ExecutionEngine の PID（SystemMonitor が存在確認に利用）
- これらのファイルは data ディレクトリに置かれます。運用時に外部から作成・削除してプロセス制御が可能です。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数/.env 読み込みと Settings 定義
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — システム監視（CPU/メモリ/ディスク・データ鮮度・プロセス）
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - alert_manager.py — LINE 通知
    - monitoring_engine.py — 各 Monitor を束ねるループ
    - streamlit_dashboard.py — Streamlit ダッシュボード（起動スクリプト）
  - execution/
    - order_manager.py — 注文作成・状態管理 API
    - reconciler.py — 起動時のリコンシリエーション（注文・ポジション同期）
    - （broker_factory, execution_engine, order_repository 等が存在する想定）
  - portfolio/
    - portfolio_builder.py — 候補選定・等配分/スコア配分
    - position_sizing.py — 発注株数・リスク制限
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム/ボラティリティ/バリュー計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py — ニュースセンチメント取得（OpenAI）
    - regime_detector.py — マクロ＋MA200 合成でレジーム判定（OpenAI）
  - tools/
    - paper_verification_report.py — Paper Trading の評価レポート生成

その他:
- data/ — DBファイル・flag・pid を置く想定のディレクトリ（リポジトリ直下）
- pyproject.toml / .git / README.md 等（プロジェクトルート判定に使用）

---

## 注意事項 / 運用上のヒント

- 環境変数は .env / .env.local から自動で読み込まれますが、OS環境変数は上書きされません（.env.local は上書き可）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- Paper Trading は本番 DB と完全分離されるよう実装されています。KABUSYS_ENV=paper_trading を利用して安全に検証してください。
- OpenAI 呼び出しは外部依存かつコストが発生します。API キーは厳重に管理してください。
- LINE 通知は channel token / user id を設定しない場合は送信されずログに出力されます。
- DuckDB / SQLite のスキーマは monitoring_db.init_monitoring_db() により自動作成・マイグレーションされます。
- process priority / cpu affinity の設定は OS に依存し、権限がない場合は警告が出てスキップされます。

---

必要であれば README に以下を追加できます：
- 具体的な .env.example のテンプレート
- requirements.txt の完全リスト
- 各コンポーネント（ExecutionEngine / Broker API）のより詳細な運用手順
- 開発者向けテスト実行手順（単体テスト・モックの差し替え方法）

ご希望があれば上記の追記・修正を行います。