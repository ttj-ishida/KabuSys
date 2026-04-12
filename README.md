# KabuSys

バージョン: 0.1.0

日本株向けの自動売買・リサーチ・監視フレームワークです。Signal -> Execution の実行基盤、監視コンポーネント、ファクター計算・研究ユーティリティ、AI を使ったニュースセンチメントやレジーム判定などの機能を含みます。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群を含む Python パッケージです。

- 注文の生成・送信・状態管理（Execution Engine / OrderManager / Reconciler）
- Paper Trading モード（本番 DB と分離して mock ブローカーを使用）
- モニタリング（CPU / メモリ / ディスク / データ鮮度 / 注文滞留 / ドローダウン監視）
- アラート（LINE Push）
- Streamlit ベースの監視ダッシュボード
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算、セクター制約、レジーム乗数）
- リサーチ（ファクター計算、将来リターン、IC 計算、統計サマリー）
- AI モジュール（ニュースの NLP スコアリング、マクロニュースを用いた市場レジーム判定）
- 各種ツール（Paper Trading 検証レポート生成など）

設計思想としては「外部サービ ス（ブローカー等）へのアクセスを分離」「DB・永続化の限定」「ルックアヘッドバイアス防止」「フェイルセーフ／冪等性」を重視しています。

---

## 主な機能一覧

- Execution
  - OrderManager: 注文ライフサイクル管理（作成、送信、同期）
  - Reconciler: 再起動時の注文・ポジション照合
  - RiskManager（設定に基づくリスク制御）
- Monitoring
  - SystemMonitor: プロセス稼働・リソース・データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: フラグファイルによる Execution 停止シグナル
  - AlertManager: LINE による通知（クールダウン管理あり）
  - MonitoringEngine: 上記モニタの統合ポーリング
  - Streamlit ダッシュボード（監視データの可視化）
- Portfolio
  - 候補選定、等重・スコア重み、リスク調整、ポジションサイズ計算（単元考慮・aggregate cap）
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB 上での SQL 実装）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- AI
  - news_nlp: OpenAI を用いたニュースの銘柄別センチメント計算・ai_scores への保存
  - regime_detector: ETF MA とマクロニュースの LLM センチメント合成によるレジーム判定
- Tools
  - paper_verification_report: Paper Trading DB を解析して検証レポートを生成

---

## セットアップ手順

前提:
- Python 3.9+（パッケージ記述に合わせる。プロジェクトの要件に応じて調整してください）
- SQLite は標準で利用可能
- DuckDB, psutil, requests, openai, streamlit 等の外部依存あり

手順例:

1. リポジトリをクローン / 配布パッケージを展開
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate
3. 必要なパッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit
   実際の requirements.txt がある場合はそれを使用してください。

4. データディレクトリ作成
   - mkdir -p data

5. 環境変数の設定
   - プロジェクトルートに .env や .env.local を置けば自動読み込みされます（デフォルト）。
   - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主要な環境変数（代表例、デフォルト値 / 有効値は code を参照）:
- KABUSYS_ENV (development | paper_trading | live) — default: development
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API 使用時）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- OPENAI_API_KEY — AI モジュール実行時に必要
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — AlertManager（LINE）使用時
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db (Monitoring 用)
- PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db (paper_trading 用)
- PAPER_FILL_MODE — instant | partial | never | reject (paper_trading の約定挙動)
- PID_FILE_PATH — default: data/execution.pid
- KILL_FLAG_PATH — default: data/kill.flag
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）

注: .env 読み込みはプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を自動検出して行います。

---

## 使い方（起動 & ツール）

主要なエントリポイントはモジュール実行形式です。プロジェクトルートで仮想環境を有効にして実行してください。

- 監視ループを起動（Monitoring — 常駐）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔(秒)を上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は Settings の sqlite_path（本番 DB）を使用して monitoring テーブル等を初期化します

- 実行エンジンを起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）と MockBroker を使用し、本番 DB と分離されます
  - 起動時に ExecutionEngine が PID ファイルを書きます（Settings.pid_file_path）

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を read-only モードで開き、ダッシュボードを表示します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - デフォルト DB は data/paper_trading.db。--db オプションでパスを指定可能

- AI 関連（プログラム内 API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)  — raw_news を集約して ai_scores に保存
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — market_regime テーブルへ書き込み
  - どちらも OPENAI_API_KEY が必要（api_key 引数で直接渡すことも可能）

運用上の注意:
- Execution 起動時に KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に既存の kill.flag を削除できます（Settings.kill_flag_clear_on_start を参照）。
- KillSwitch は RiskMonitor の評価により data/kill.flag を作成します。Execution 側でこのファイルの存在を検出して安全に停止する仕組みが期待されます。
- paper_trading は本番 DB と完全分離されるよう設計されています（データ損壊リスク軽減）。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル/ディレクトリ構成（本リポジトリに含まれるファイルの一部）です。

- src/kabusys/
  - __init__.py                — パッケージ定義（version 等）
  - config.py                  — 環境変数 / 設定読み込みロジック
  - run_monitoring.py          — SystemMonitor のポーリング起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - monitoring/
    - __init__.py
    - monitoring_db.py         — SQLite を用いた監視ログ層（テーブル作成・CRUD）
    - system_monitor.py        — システム状態・データ鮮度監視
    - trade_monitor.py         — 注文滞留・約定異常監視
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — kill.flag 管理
    - alert_manager.py         — LINE 通知（クールダウン）
    - monitoring_engine.py     — 全 Monitor を束ねるポーリングエンジン
    - streamlit_dashboard.py   — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - (その他 Execution 関連モジュール)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py              — ニュースセンチメント取得（OpenAI）
    - regime_detector.py       — レジーム判定（ETF MA + マクロセンチメント）
    - __init__.py
  - utils/
    - process_priority.py      — プロセス優先度・CPU affinity 設定ユーティリティ
    - __init__.py

データファイル（推奨場所）
- data/kabusys.duckdb        — DuckDB（価格・ファイナンス等の履歴テーブル）
- data/monitoring.db         — SQLite（監視ログ）
- data/paper_trading.db      — SQLite（Paper Trading 用、KABUSYS_ENV=paper_trading 時に使用）
- data/execution.pid         — ExecutionEngine の PID ファイル
- data/kill.flag             — KillSwitch が書き込む停止フラグ

---

## 設定 / 環境変数一覧（主なもの）

- KABUSYS_ENV
  - 値: development | paper_trading | live
  - 役割: 実行モード（paper_trading の場合、Paper DB と MockBroker を使用）

- JQUANTS_REFRESH_TOKEN
  - J-Quants API 用（必須: 使用コンポーネントがある場合）

- KABU_API_PASSWORD
  - kabuステーション API パスワード（必須: 本番ブローカー使用時）

- OPENAI_API_KEY
  - OpenAI API を使う AI モジュールで必須

- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID
  - AlertManager（LINE 通知）用

- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PAPER_FILL_MODE (instant | partial | never | reject; default: instant)

- PID_FILE_PATH, KILL_FLAG_PATH
- KILL_FLAG_CLEAR_ON_START (1 で実行時に kill.flag を削除)
- MONITOR_POLL_INTERVAL (秒; run_monitoring のポーリング間隔を上書き)

- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)

---

## 運用上の注意 / ベストプラクティス

- Paper Trading を本番データベースと混同しないこと。KABUSYS_ENV=paper_trading を明示的に設定してください。
- OpenAI の API 呼び出しはレート制限・一時エラーに対してリトライロジックを実装していますが、API キー・利用量を適切に管理してください。
- Monitoring は監視 DB に記録します。運用時は外部から DB を参照（ダッシュボード）してシステム状態を確認してください。
- pid/kill.flag による停止制御を組み合わせることで、安全に Execution を停止できます。kill.flag が存在する場合は Execution 側で適切に停止処理を行ってください。
- .env/.env.local を用いた設定管理が可能です。OS 環境変数を保護するための挙動が実装されています（auto-load の振る舞いは kabusys.config を参照）。

---

## 開発者向けメモ

- settings = kabusys.config.settings を使って設定を取得できます。
- DuckDB ベースのリサーチ関数は SQL と Python の混合で高効率にファクター計算を行います。
- 各モジュールは可能な限り副作用を避け、純粋関数を多用する設計です（portfolio / research 等）。
- テストを書く際は .env 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を使うか、環境を整えてください。
- 外部 API 呼び出しはモジュール内で分離されており、テスト時は patch / mock で差し替え可能です（例: news_nlp._call_openai_api のモック化）。

---

何か追加で README に含めたい内容（例: 実際の起動例、より詳細な環境変数ドキュメント、依存関係の固定バージョン、CI/CD の設定）や、特定ファイルの説明を掘り下げたい場合は教えてください。README を用途に合わせて拡張します。