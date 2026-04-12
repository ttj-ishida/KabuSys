# KabuSys

KabuSys は日本株向けの自動売買 / 研究 / 監視ツール群です。本リポジトリは注文エンジン、監視モジュール、ポートフォリオ構築、ファクター計算・研究、ニュース NLP（LLM）を用いたセンチメント評価などの機能を提供します。

以下はこのコードベースの概要・セットアップ・使い方・主要ディレクトリ構成の説明です。

---

## プロジェクト概要

- 日本株自動売買システムのコンポーネント群（Execution / Monitoring / Portfolio / Research / AI）。
- DuckDB を用いた時系列ファクター計算、SQLite を用いた監視ログ・注文ログ管理。
- OpenAI（gpt-4o-mini 相当）を用いたニュースセンチメント評価（ai.news_nlp）およびマクロセンチメントを用いた市場レジーム判定（ai.regime_detector）。
- 監視モジュール（MonitoringEngine）はシステム状態、注文異常、ドローダウン等を定期チェックし、LINE 通知や kill.flag による ExecutionEngine 停止シグナル発行が可能。

---

## 主な機能一覧

- Execution（発注関連）
  - 起動時リコンシリエーション（Reconciler）
  - OrderManager による注文作成・送信・同期処理
  - PaperTrading モード（本番 DB と分離、data/paper_trading.db に記録）

- Monitoring（監視）
  - SystemMonitor：CPU/メモリ/ディスク/プロセス稼働・データ鮮度確認
  - TradeMonitor：滞留注文（stale orders）や約定価格の異常検知
  - RiskMonitor：ドローダウン監視、ポジション上限チェック
  - KillSwitch：条件発生時に flag ファイルを書き ExecutionEngine に停止シグナルを送る
  - AlertManager：LINE Push API による一方向アラート（cooldown 機能付き）
  - Streamlit ダッシュボード（監視情報の可視化）

- Portfolio（ポートフォリオ構築）
  - 候補選定（select_candidates）
  - 等配分 / スコア加重配分（calc_equal_weights / calc_score_weights）
  - セクターキャップ適用（apply_sector_cap）
  - ポジションサイズ計算（calc_position_sizes）

- Research（研究）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー等

- AI（LLM 連携）
  - news_nlp.score_news：ニュースをまとめて LLM に投げ、銘柄ごとのスコアを ai_scores テーブルへ書き込む
  - regime_detector.score_regime：ETF ma200 乖離とマクロセンチメントを合成して市場レジームを判定・永続化

- ツール
  - paper_verification_report：Paper Trading DB から検証レポートを生成（稼働率・注文成功率・レイテンシ等）

---

## セットアップ手順（開発環境向け）

前提：Python 3.9+（型ヒント等使用）、git があること。

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトで requirements.txt を用意している場合は pip install -r requirements.txt）

4. 環境変数の準備
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 主要な環境変数（下記参照）を設定してください。

5. データディレクトリを作成
   - mkdir -p data

6. DB 初期化
   - 実行スクリプトが起動時に monitoring DB のスキーマを作成します（init_monitoring_db が呼ばれます）。特段の初期化手順は不要です。

---

## 主な環境変数

（Settings クラス（src/kabusys/config.py）に基づく。デフォルトは括弧内に記載）

- KABUSYS_ENV: 起動環境（development | paper_trading | live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- LINE_CHANNEL_ACCESS_TOKEN: LINE push 用トークン（AlertManager）
- LINE_USER_ID: LINE 宛先ユーザー ID（AlertManager）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite DB（デフォルト: data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が書く flag（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag をクリアするか（"1" で有効）
- PAPER_FILL_MODE: Paper trading の約定挙動（instant | partial | never | reject、デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）

---

## 使い方（主要コマンド例）

プロジェクトをパッケージとしてインポートできる状態（src を PYTHONPATH に含める or パッケージをインストール）で実行することを想定しています。パッケージルートで以下のコマンドを実行してください。

- 監視ループを起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 実行時に process priority を high に設定します（psutil による権限が必要な場合あり）

- ExecutionEngine（注文エンジン）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient が使われ、paper 用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
  - 起動時にプロセス優先度を high に設定します。

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - あるいは上記ファイルを module として実行する場合は引数 `--db` で DB パスを指定

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD : レポート開始日
    - --to YYYY-MM-DD   : レポート終了日
    - --db PATH         : SQLite DB パス（PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- AI（ニューススコアリング）をプログラムから呼ぶ
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=...)  — DuckDB 接続と日付を渡して実行（api_key は省略時に OPENAI_API_KEY を使う）
  - 市場レジーム判定は kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...) を呼べます（module 内の関数）。

備考:
- 起動スクリプトは Settings を用いて環境設定を読み込み、必要な DB スキーマを初期化します（init_monitoring_db が呼ばれます）。
- Execution と Monitoring は PID/kill.flag による連携を行い、KillSwitch により外部から安全に停止できます。

---

## 監視・通知の仕組み（簡易）

- MonitoringEngine は SystemMonitor / TradeMonitor / RiskMonitor を定期実行します。
- 重大な事象（プロセス停止、ドローダウン超過、ポジション上限超過、データ鮮度異常など）は AlertManager 経由で LINE に通知できます（トークン未設定ならログ出力のみ）。
- KillSwitch はドローダウンやポジション上限が閾値を越えると `data/kill.flag` を作成し、ExecutionEngine 側はこれを検出して安全停止できます。

---

## ディレクトリ構成（重要ファイル抜粋）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py
  - monitoring/
    - __init__.py
    - monitoring_db.py      — SQLite スキーマ & DB アクセス層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - ... (ブローカーファクトリ等の実装)
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - utils/
    - process_priority.py

（上記は本リポジトリの主要モジュールのみ抜粋しています。実際の tree はさらに細分化されています。）

---

## 注意事項 / 実運用上のポイント

- 環境依存
  - Settings は .env / .env.local を自動的にプロジェクトルートから読み込みます（但し KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - KABUSYS_ENV が `paper_trading` の場合、本番 DB と分離された paper DB を使用します。live では実際のブローカーが使用されますので注意してください。

- AI (OpenAI) 関連
  - OPENAI_API_KEY が必要です。API 呼び出し時のエラー（429/タイムアウト/5xx）は内部でリトライしますが、完全失敗時はスコアをスキップまたはデフォルト値にフォールバックします（フェイルセーフ設計）。

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等でテーブルを作成します。既存スキーマに新カラム（例: peak_value、latency_ms）がなければ ALTER で追加します。

- 権限
  - プロセス優先度設定や CPU affinity 設定は権限に依存します。psutil の AccessDenied により設定できない環境がありますが、その場合は警告を出してスキップします。

---

## 補足（開発者向け）

- 各モジュールは可能な限り純粋関数 / 副作用最小化で実装されています（例: portfolio.*, research.* は DB を直接変更しない関数群が中心）。
- テスト用に設計された箇所（例: API 呼び出しラッパー）は単体テストでモックしやすく作られています（news_nlp._call_openai_api の patch 等）。
- ログは標準 logging を使用しているため、必要に応じてハンドラを差し替えて監視・集約可能です。

---

README の内容はコードベースの主要点を抜粋したものです。特定の機能や実装について詳しいドキュメント（関数レベルの説明や設計ドキュメント）が必要であれば、どの箇所を深掘りしたいかを教えてください。