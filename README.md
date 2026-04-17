# KabuSys

日本株自動売買システムのコンポーネント群（ポートフォリオ構築、実行エンジン、監視、リサーチ、AI ニューススコアリングなど）のコードベースです。本 README はリポジトリの主要機能と起動・利用手順、ディレクトリ構成の概要を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下の機能を持つモジュール群から構成されます。

- Execution（発注・注文管理・リコンシリエーション）
- Monitoring（システム稼働・注文状況・リスク監視、アラート）
- Portfolio（銘柄選定、重み計算、ポジションサイズ決定）
- Research（ファクター計算、特徴量探索）
- AI（ニュースの NLP によるセンチメント評価、レジーム判定）
- Tools（レポート生成、ダッシュボード起動スクリプト等）

設計方針として、DB（SQLite / DuckDB）と純粋関数的な計算ロジックを分離し、テスト容易性と安全性（paper_trading 環境の DB 分離、フェイルセーフ）に配慮した実装になっています。

---

## 主な機能一覧

- 発注フロー管理（OrderManager / ExecutionEngine）
- 再起動時リコンシリエーション（Reconciler）
- リスク管理（RiskManager / RiskMonitor）・ドローダウン・ポジション上限監視
- 監視（SystemMonitor / TradeMonitor / MonitoringEngine）
  - CPU / メモリ / ディスク、Execution プロセス検出、データ鮮度チェック、滞留注文・約定異常検出
- アラート送信（LINE Push 連携 via AlertManager）
- KillSwitch：条件到達時に data/kill.flag を書いて ExecutionEngine を停止させる仕組み
- Paper Trading 向け検証レポート生成ツール（tools/paper_verification_report.py）
- News NLP（OpenAI によるニュースセンチメント評価）と market regime 判定
- Streamlit ベースの監視ダッシュボード（monitoring/streamlit_dashboard.py）
- DuckDB を用いたファクター計算・ファクター評価ユーティリティ（research/*）
- ポートフォリオ構築ロジック（候補選定・重み付け・ポジションサイズ計算・セクター制約など）

---

## 必要環境 / 依存 (例)

- Python 3.10+（typing の | 型などを使用）
- 必須パッケージ（代表例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- これらは pip でインストールしてください（requirements.txt が無い場合の例）:
  - pip install duckdb psutil requests openai streamlit

（実際のプロジェクトでは requirements.txt / poetry / pipenv 等を用意してください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. Python 環境（仮想環境）を作成して有効化
3. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
4. data ディレクトリを作成（SQLite / DuckDB のデフォルトファイル保存先）
   - mkdir -p data
5. 環境変数を設定
   - ルートに .env / .env.local を作成可能（config モジュールが自動で読み込み）
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

重要な環境変数（主要なもの）：
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API 用）
- KABU_API_PASSWORD — 必須（kabu API 用）
- OPENAI_API_KEY — AI モジュール（news_nlp / regime_detector）で使用
- KABUSYS_ENV — 環境指定（development, paper_trading, live）。デフォルト: development
  - paper_trading の場合、実行エンジンは MockBroker を使用し、別ファイルに記録されます
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db（paper_trading 用 DB）
- PAPER_FILL_MODE — paper_trading の注文約定挙動（instant, partial, never, reject）（デフォルト: instant）
- PID_FILE_PATH — デフォルト: data/execution.pid
- KILL_FLAG_PATH — デフォルト: data/kill.flag
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）

.env 読み込みの挙動:
- OS 環境変数 > .env.local > .env の順で適用（.env.local は上書き）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化

---

## 使い方（主要なスクリプト・モジュールの実行方法）

以下はモジュールとして実行する方法の例です（プロジェクトルートで実行）。

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒、デフォルト 60）
  - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用するので注意

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録され、本番 DB と完全分離されます
  - 実行中は data/execution.pid に PID を出力（設定に依存）
  - 停止フラグファイル data/stop_requested.flag が存在すると起動・ループを停止します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションでデータベース指定（デフォルトは PAPER_TRADING_SQLITE_PATH もしくは data/paper_trading.db）

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用モードで SQLite を開く（MonitoringEngine が先に DB を作成している前提）

- AI モジュール（ニューススコアリング / レジーム判定）
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
  - OpenAI API キーは api_key 引数か環境変数 OPENAI_API_KEY を使用

停止・強制停止フロー：
- run_monitoring / run_execution のループはプロジェクト内 data/stop_requested.flag を監視します。停止したい場合はそのファイルを作成してください（運用上の停止用フラグ）。
- KillSwitch（モニタリング側）が条件到達時に data/kill.flag を書き込みます。ExecutionEngine は kill.flag の検出により安全に停止します。起動時に kill_flag_clear_on_start が "1" に設定されていると起動時に kill.flag を自動削除できます。

ログレベル:
- LOG_LEVEL 環境変数（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

---

## 典型的な運用例

1. 開発環境（ローカルで監視と実行を別ターミナルで起動）
   - データフォルダ作成: mkdir -p data
   - .env に必須変数を設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）
   - Terminal A: python -m kabusys.run_monitoring
   - Terminal B: python -m kabusys.run_execution

2. Paper trading（実際の注文 API を叩かず検証する）
   - export KABUSYS_ENV=paper_trading
   - export PAPER_FILL_MODE=instant
   - python -m kabusys.run_execution
   - 検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

3. Streamlit ダッシュボードで監視結果を見る
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

## ディレクトリ構成（主要ファイル / モジュールの概要）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・.env 読み込み / Settings クラス
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading の分離対応）
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）による銘柄別スコア算出
    - regime_detector.py — 市場レジーム判定（ma200 + マクロ NLP）
  - execution/
    - execution_engine.py (実行エンジン本体) —（※ファイルの一部のみ提示）
    - order_manager.py — 外向き API（注文作成・キャンセル等）
    - order_repository.py — SQLite への注文保存 / 取得
    - reconciler.py — 再起動時のリコンシリエーション
    - broker_factory.py / broker_api.py — ブローカークライアント抽象化
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化・読み書きラッパ
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・PID チェック
    - trade_monitor.py — 滞留注文・約定異常のチェック
    - risk_monitor.py — ドローダウン・ポジション上限チェック
    - kill_switch.py — kill.flag 書き込みロジック
    - alert_manager.py — LINE Push API による通知
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算・スケールダウンロジック
    - risk_adjustment.py — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py — モメンタム / ボラ / バリュー等の計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/ （実行時に使用されるディレクトリ、デフォルト DB 等）
    - monitoring.db（デフォルト SQLITE_PATH）
    - kabusys.duckdb（デフォルト DUCKDB_PATH）
    - paper_trading.db（paper_trading 用データベース）
    - execution.pid, stop_requested.flag, kill.flag などのフラグ・PID ファイル

※ 上記は主要なファイルを抜粋したものです。細かい実装は該当ファイルを参照してください。

---

## 運用上の注意 / ヒント

- paper_trading 環境は本番 DB と完全に分離されるよう設計されています。検証時は KABUSYS_ENV=paper_trading を使用してください。
- AI（OpenAI）を使用する機能は API キー（OPENAI_API_KEY）が必須です。API の呼び出しはリトライ・フェイルセーフ実装が入っていますが、無効なキーや通信障害時はスキップされる場面があります。
- 監視ループ・実行エンジンは stop_requested.flag を確認して終了します。運用で止めたい場合は該当フラグファイルを作成してください（あるいはプロセスマネージャで停止）。
- kill.flag は Monitoring 側が条件到達時に書く停止要求ファイルです。起動時に自動で消したい場合は KILL_FLAG_CLEAR_ON_START=1 を設定してください。
- .env のパースはシェルの基本的な記法（export, クォートやコメント）に対応していますが、複雑なケースは避けることを推奨します。

---

## 開発・テスト

- モジュールは可能な限り純粋関数（portfolio, research 等）と副作用を伴う DB / API 層に分離されています。ユニットテストは純粋関数に対して容易に記述できます。
- OpenAI やブローカー API 呼び出し部分は依存注入やパッチで差し替え可能に設計されています（テストではモックを利用）。

---

必要に応じて README に追加したい内容（例: 実際の起動例のログ、より詳細な環境変数一覧や migration 手順、開発用 makefile / docker-compose 例など）があれば指示してください。