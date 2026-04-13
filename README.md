KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買フレームワーク（プロトタイプ実装）です。  
主な目的は「売買ロジック（シグナル生成）」「発注実行」「監視/アラート」「研究/検証」を分離して実装することで、運用・検証・研究を同一コードベースで行えるようにすることです。

本リポジトリに含まれる主なコンポーネント:
- 発注実行エンジン（ExecutionEngine）および Order 管理
- 監視サブシステム（System / Trade / Risk Monitoring）とアラート（LINE Push）
- Paper Trading 用の分離 DB・検証ツール
- ポートフォリオ構築ユーティリティ（候補選定・重み計算・ポジションサイズ算出）
- リサーチ用ファクター計算モジュール（DuckDB を使ったファクター群）
- ニュース NLP / レジーム判定（OpenAI を利用した LLM 処理）
- Streamlit ダッシュボード（監視データ閲覧）

主な特徴（機能一覧）
-------------------
- Execution:
  - Broker 抽象化（実プロバイダ / MockBroker の切り替え）
  - Order 状態管理（作成 → 送信 → 同期 → リコンシリエーション）
  - リスク管理（position 上限、ドローダウン等）
  - 起動時の優先度設定（プロセス優先度 / CPU affinity）
- Monitoring:
  - system_status / trade_logs / risk_logs / positions / dashboard を SQLite に永続化
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態/データ鮮度チェック
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン / ポジション上限の監視と kill.flag の発行
  - AlertManager: LINE による通知（クールダウン管理）
  - Streamlit ダッシュボードで監視情報可視化
- Research / AI:
  - DuckDB を用いたファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン計算 / IC（Information Coefficient）計算
  - ニュースを LLM（OpenAI）でセンチメント化して ai_scores に保存
  - マクロ + MA200 に基づく市場レジーム判定
- Tools:
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率、注文成功率、レイテンシ等）

セットアップ手順
----------------

1. Python 環境（推奨: 3.10+）を用意する
   - 仮想環境作成例:
     - python -m venv .venv
     - source .venv/bin/activate

2. 依存パッケージをインストールする
   - 必要なパッケージ例:
     - duckdb, psutil, requests, openai, streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （本リポジトリに requirements.txt がある場合はそれを利用してください）

3. データディレクトリ作成
   - デフォルトでは data/ 以下に DB や PID/FLAG ファイルが置かれます:
     - data/kabusys.duckdb (DuckDB)
     - data/monitoring.db (SQLite: 監視用)
     - data/paper_trading.db (Paper Trading 用 SQLite)
     - data/execution.pid, data/kill.flag
   - 例: mkdir -p data

4. 環境変数設定
   - .env/.env.local をプロジェクトルートに作成してもよい（config.py が自動ロードを行います）。
   - 主要な環境変数（代表）:
     - KABUSYS_ENV: 実行モード (development | paper_trading | live)。デフォルト: development
       - paper_trading: MockBroker を使用し、paper_sqlite_path に書き込む（production DB とは分離）
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時に必要）
     - DUCKDB_PATH: DuckDB のパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: Monitoring 用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: paper_trading の約定モード (instant|partial|never|reject)（デフォルト: instant）
     - PID_FILE_PATH / KILL_FLAG_PATH（デフォルト: data/execution.pid, data/kill.flag）
     - MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
     - LOG_LEVEL: ログレベル（DEBUG|INFO|...）
   - 自動 env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

5. DB 初期化
   - 監視用 SQLite のテーブルは実行時に自動で init_monitoring_db() により作成されます。明示的な初期化は不要です。

基本的な使い方
--------------

- ExecutionEngine（発注エンジン）の起動
  - 本番 / 開発 / paper_trading の切り替えは KABUSYS_ENV により行う
  - 起動例:
    - KABUSYS_ENV=live python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - paper_trading の場合は MockBrokerClient（ブローカーモック）を使用し、データは PAPER_TRADING_SQLITE_PATH に記録されます。

- Monitoring（監視ループ）の起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（デフォルト 60）
  - 起動例:
    - python -m kabusys.run_monitoring
  - 監視は MonitoringDB（SQLite）へログを永続化します。監視は常に production 用の sqlite_path を参照します（KABUSYS_ENV に依らず）。

- Streamlit ダッシュボード
  - 起動例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only モードで SQLite を開き、dashboard / positions / trade_logs / system_status / risk_logs を表示します。

- Paper Trading 検証レポート
  - ツール: kabusys.tools.paper_verification_report
  - 例:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - --db オプションで DB パスを指定可能（優先度: --db > 環境変数 > デフォルト data/paper_trading.db）

- AI / リサーチ機能（ライブラリ的に利用）
  - ファクター計算:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value
    - 結果はリストの dict（date, code, 各ファクター）
    - 引数: DuckDB 接続と target_date
  - ニュース NLP スコアリング:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=None) — DuckDB 接続と日付を渡す。api_key 未指定時は OPENAI_API_KEY を参照
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

設計上の注意点 / 動作ポリシー
--------------------------
- 環境変数の自動読み込み: config.Settings モジュールはプロジェクトルート（.git または pyproject.toml）から .env / .env.local を読み込みます。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading は production DB と物理的に分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- 起動時にプロセス優先度を上げる処理（set_process_priority("high")）が実行されます。実行環境によっては権限不足でスキップされる場合があります（警告ログのみ）。
- AI（OpenAI）への呼び出しは失敗耐性が組み込まれており、429/ネットワーク/5xx 等はリトライ、パース失敗や非致命的エラーは警告して継続します。API キー未設定の場合は ValueError を返す関数があります。
- Monitoring の polling loop は KeyboardInterrupt で停止します。run_monitoring は監視専用の DB を使用します（環境にかかわらず sqlite_path）。

ディレクトリ構成（主なファイル）
------------------------------
以下は src/kabusys 配下の主要ファイルと役割の概要です。実際にはさらに多くのサブモジュールがあります。

- src/kabusys/
  - __init__.py              — パッケージメタ情報
  - config.py                — 環境変数 / 設定管理（.env 自動読込、Settings クラス）
  - run_execution.py         — ExecutionEngine 起動スクリプト（KABUSYS_ENV により挙動変化）
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 用の検証レポート生成ツール
  - execution/
    - order_manager.py       — Order 管理（作成・送信・同期）
    - reconciler.py          — 起動時のリコンシリエーション（発注・ポジション突合）
    - order_repository.py    — Orders DB (SQLite) アクセス層（※省略されているファイル群あり）
    - broker_factory.py      — Broker クライアント生成
    - ...                    — その他発注関連の実装
  - monitoring/
    - monitoring_db.py       — 監視用 SQLite テーブル定義と永続化 API
    - system_monitor.py      — CPU/プロセス/データ鮮度チェック
    - trade_monitor.py       — 注文滞留・約定異常の検出
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 管理（Execution 停止シグナル）
    - alert_manager.py       — LINE Push 通知
    - monitoring_engine.py   — 複数モニタを束ねるエンジン
    - streamlit_dashboard.py — Streamlit での可視化
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算（等配分・スコア加重）
    - position_sizing.py     — 株数決定（単元丸め・制約適用・スケールダウン）
    - risk_adjustment.py     — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（momentum, volatility, value）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py            — ニュースの LLM センチメント化と ai_scores への書込み
    - regime_detector.py     — マクロ + MA200 によるレジーム判定
  - utils/
    - process_priority.py    — プロセス優先度・CPU affinity 設定ユーティリティ
  - data/ (推奨される作業ディレクトリ)
    - kabusys.duckdb
    - monitoring.db
    - paper_trading.db
    - execution.pid
    - kill.flag

開発 / デバッグのヒント
---------------------
- 設定の自動ロードを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してからテストを実行してください。
- Monitoring の初期テーブルは init_monitoring_db() により冪等に作成されます。既存 DB に対する小さなスキーマ追加（ALTER）もコード内に存在します。
- OpenAI 呼び出し部は _call_openai_api という小さなラッパー関数にまとめられているため、ユニットテストではこれを patch して外部 API をモックできます。
- Streamlit ダッシュボードは SQLite を読み取り専用で開くように実装されています（URI に ?mode=ro を付加）。

ライセンス / 貢献
-----------------
（ここにライセンス情報やコントリビュート方法を記載してください）

お問い合わせ
-----------
実装や使い方に関する質問は README に連絡先や Issue を立てる旨を追記してください。