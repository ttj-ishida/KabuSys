# KabuSys

日本株向けの自動売買システム（プロトタイプ）。  
戦略・ポートフォリオ構築、発注実行、監視・アラート、研究用ファクター計算、ニュースNLP/レジーム判定などのコンポーネントを含みます。

---

## 概要

KabuSys は以下の機能を備えたモジュール群で構成されたプロジェクトです。

- 発注・実行エンジン（ExecutionEngine、OrderManager、Broker クライアント抽象化）
- 取引監視・システム監視（MonitoringEngine、SystemMonitor、TradeMonitor、RiskMonitor）
- 監視ログ永続化（SQLite ベースの monitoring DB）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- 研究用モジュール（DuckDB を使ったファクター計算、IC 計算など）
- AI モジュール（ニュースの NLP スコアリング、マクロレジーム判定） — OpenAI API を使用
- 運用ツール（Paper Trading 検証レポート生成、Streamlit ダッシュボード）
- ユーティリティ（環境設定読み込み、プロセス優先度設定、CPU affinity）

設計上の特徴：
- DuckDB / SQLite を用いたローカル解析・監視データ管理
- 本番 / Paper Trading の DB 分離（paper_trading 環境では data/paper_trading.db を使用）
- 環境変数（.env / .env.local）読み込みを自動化。テスト時は無効化可能
- 外部 API（OpenAI、LINE、kabuステーション 等）は抽象化・フェイルセーフ実装

---

## 機能一覧

- Execution
  - 発注作成・送信・状態同期（Reconciler による再起動時の復旧）
  - RiskManager（レート制限・ポジション上限・ドローダウン等のリスク制御）
- Monitoring
  - システムリソース監視（CPU/メモリ/ディスク）
  - データ鮮度チェック（DuckDB の prices_daily を参照）
  - 注文滞留・約定異常検出
  - リスクイベントの記録・通知（LINE）
  - kill.flag による ExecutionEngine 停止シグナル
  - Streamlit ダッシュボード表示
- Portfolio
  - 候補選定（スコア降順）
  - 重み計算（等分・スコア重み）
  - セクター集中制限適用
  - ポジションサイズ計算（単元丸め・aggregate cap・スケールダウン）
- Research
  - モメンタム / ボラティリティ / バリュー系ファクターの DuckDB ベース計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
- AI
  - ニュース記事を LLM（OpenAI）で集約評価し ai_scores に書込み
  - ETF + マクロニュースで日次レジーム判定（bull/neutral/bear）
- Tools
  - paper_trading の検証レポート出力（paper_verification_report）
  - streamlit ダッシュボード

---

## 必要要件

- Python 3.10 以上（型ヒントの構文等を使用）
- SQLite（標準ライブラリ）
- 推奨パッケージ（pip でインストール）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit (ダッシュボード使用時)

例:
pip install duckdb psutil openai requests streamlit

（実行環境に応じて追加パッケージが必要になる場合があります）

---

## セットアップ手順

1. リポジトリをクローン / コピー
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate
3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil openai requests streamlit
4. data ディレクトリ作成
   - mkdir -p data
5. 環境変数 / .env の準備
   - プロジェクトルートに `.env` または `.env.local` を作成して必要な環境変数を設定します。
   - 自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主な環境変数（抜粋）：
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須: 使用箇所次第）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須: 実運用）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール使用時）
- KABUSYS_ENV — 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH — 監視 DB パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_FILL_MODE — paper_trading 時のモック約定挙動 ("instant"|"partial"|"never"|"reject")
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...)

注意:
- paper_trading 環境では発注はモック実装（MockBrokerClient）を使用し、DBは paper_trading.db に分離されます。

---

## 使い方

基本的な実行コマンド例。

- ExecutionEngine（発注実行）を起動
  - 開発（デフォルト）:
    - python -m kabusys.run_execution
  - Paper Trading:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行時にプロセス優先度を high に設定します（psutil を用いるため権限が必要な場合あり）。

- Monitoring（監視ポーリング）を起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60）
  - python -m kabusys.run_monitoring
  - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI モジュール（プログラムから呼び出す）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key="...")  # DuckDB 接続を渡す
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")

- 設定関連
  - 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索して行います。
  - テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

運用上の注意:
- run_monitoring は MonitoringDB（SQLite）へ常にアクセスします。監視は本番 sqlite_path を使用する仕様です（KABUSYS_ENV に依らず）。
- kill.flag（Settings.kill_flag_path）を監視で書き込むことで ExecutionEngine を安全に停止できます。
- PID ファイル（Settings.pid_file_path）を使ってプロセス生存チェックを行い、stale PID を検出すると削除します。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数/.env 読み込みと Settings
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

src/kabusys/execution/
- broker_api.py*, broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, order_record.py, ...  
(発注・ブローカ抽象化・再同期関連)

src/kabusys/monitoring/
- monitoring_db.py — SQLite スキーマ初期化＆読み書き
- system_monitor.py, trade_monitor.py, risk_monitor.py
- monitoring_engine.py — 各 Monitor を統合してポーリング
- alert_manager.py — LINE 通知
- kill_switch.py — kill.flag 書込みロジック
- streamlit_dashboard.py — Dash 用 UI

src/kabusys/portfolio/
- portfolio_builder.py — 候補選定・重み付け
- position_sizing.py — 株数決定ロジック
- risk_adjustment.py — セクター制限・レジーム乗数

src/kabusys/research/
- factor_research.py — モメンタム/ボラティリティ/バリュー計算
- feature_exploration.py — 将来リターン・IC・統計サマリ

src/kabusys/ai/
- news_nlp.py — ニュース記事を OpenAI で評価して ai_scores に書込
- regime_detector.py — ETF + マクロニュースでレジーム判定

src/kabusys/tools/
- paper_verification_report.py — Paper Trading 検証レポート生成

src/kabusys/utils/
- process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（*はここに示していないが関連ファイルあり）

---

## データベース / スキーマ（監視用の概要）

- monitoring_db.init_monitoring_db(conn) が監視用の SQLite テーブルを初期化します（冪等）。
  - system_status (cpu, memory, disk, process_ok, recorded_at)
  - trade_logs (order events, latency_ms 列を含む)
  - positions (currently held positions)
  - risk_logs (リスクイベント)
  - dashboard (集計: portfolio_value, cash, drawdown_pct, peak_value 等)

実行スクリプト（run_execution/run_monitoring）が必要に応じて init を呼びます。

---

## 運用上の注意点

- Paper Trading と本番 DB は分離されています。KABUSYS_ENV=paper_trading のときは paper_sqlite_path が使われます。
- MONITOR_POLL_INTERVAL は環境変数で監視のポーリング間隔を秒単位で上書きできます（デフォルト 60）。1 未満の値は無効と判定されデフォルトにフォールバックします。
- process priority の設定はプラットフォーム差（Windows/Linux/macOS）を吸収しますが、権限不足や未対応 OS では警告が出ます。
- OpenAI を使う機能（news_nlp, regime_detector）は API キーが必須です。API 呼び出しはリトライ・フェイルセーフ実装で、失敗時はスコアにフォールバックまたはスキップします。
- LINE 通知は channel token / user id が未設定の場合はログに留めて送信しません。
- duckdb のクエリはルックアヘッドを避ける設計（target_date を扱う際の排他条件など）になっています。

---

## 開発・テストのヒント

- 自動 .env ロードを無効化（テスト時）:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出し部分は _call_openai_api を patch してユニットテスト可能（モック化しやすい構造）。
- MonitoringEngine.run_once() を使うと 1 回だけ各 Monitor を呼ぶユニットテストが容易です。

---

必要であれば、README に具体的な環境変数のテンプレート（.env.example）や docker / systemd ユニット例、さらに詳しい API 仕様（OrderRequest など）を追記できます。どの情報を優先して追加しますか？