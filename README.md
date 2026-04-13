# KabuSys

日本株自動売買システムの一部（モニタリング、ポートフォリオ構築、リサーチ、AI モジュール、実行エンジンなど）の実装コードベース。  
この README はコードベース（src/kabusys 以下）に含まれる主要モジュールの説明、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株自動売買システムのコンポーネント群を提供します。主な責務は次のとおりです。

- ExecutionEngine：ブローカーとの発注・注文管理・リスク制御・再同期（reconciliation）
- Monitoring：プロセス稼働状況、注文状態、リスク指標の監視とアラート（LINE 連携）および監視データの永続化（SQLite）
- Portfolio：銘柄選定、重み計算、ポジションサイジング、セクター制限などポートフォリオ構築ロジック
- Research：DuckDB を使ったファクター計算・特徴量解析
- AI（news_nlp, regime_detector）：OpenAI を用いたニュースセンチメント集約や市場レジーム判定
- Tools：Paper Trading の検証レポート生成や Streamlit ダッシュボードなどのユーティリティ

設計方針として「ルックアヘッドバイアスを避ける」「外部 API 呼び出しは明示的に」「DB マイグレーションは冪等」などが盛り込まれています。

---

## 主な機能一覧

- 監視（Monitoring）
  - SystemMonitor：CPU/メモリ/ディスク使用率、Execution プロセス PID、データ鮮度チェック
  - TradeMonitor：滞留注文（stale orders）・約定価格の異常検知
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新、リスクログ記録
  - AlertManager：LINE Messaging API に対する通知（クールダウン管理）
  - KillSwitch：フラグファイル（data/kill.flag）を書いて ExecutionEngine 停止を指示
  - MonitoringEngine：上記 Monitor を束ねて定期ポーリング
  - Streamlit ダッシュボード（監視データ可視化）

- 実行（Execution）
  - OrderManager / OrderRepository：注文状態管理と永続化
  - Reconciler：再起動時の発注状態・ポジション突合せ
  - BrokerClientFactory：環境に応じて実ブローカー or モックブローカーを生成（paper_trading を分離）

- ポートフォリオ（Portfolio）
  - 候補選定、等重・スコア重み計算、セクター制限、ポジションサイズ計算（単元株丸め等）

- リサーチ（Research）
  - ファクター計算（Momentum, Volatility, Value など）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（OpenAI）
  - ニュースの銘柄別センチメントスコア生成（ai_scores へ書き込み）
  - マクロニュース + ETF（1321）MA200乖離を使った市場レジーム判定（market_regime へ書き込み）
  - OpenAI API 呼び出しは堅牢なリトライやレスポンス検証を実装

- ツール
  - Paper Trading 検証レポート生成スクリプト（期間指定が可能）
  - Streamlit ベースの監視ダッシュボード

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の型注釈や | 型等を使用）
- git, pip など

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール（一例）
   - pip install duckdb psutil requests streamlit openai

   ※ 必要に応じて requirements.txt を作成して管理してください。

4. データディレクトリ作成
   - mkdir -p data

5. 環境変数 / .env 設定
   - プロジェクトルートに .env または .env.local を配置すると自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   代表的な環境変数（最低限の例）
   - KABUSYS_ENV=development|paper_trading|live
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...
   - LINE_CHANNEL_ACCESS_TOKEN=...
   - LINE_USER_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - MONITOR_POLL_INTERVAL=60

   サンプル .env（機密情報は実際の値に置き換えてください）:
   ```
   KABUSYS_ENV=development
   OPENAI_API_KEY=sk-...
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=secret
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   PID_FILE_PATH=data/execution.pid
   KILL_FLAG_PATH=data/kill.flag
   ```

---

## 使い方

以下は開発 / 運用でよく使う実行例です。

- 監視ループを起動（polling）
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能。デフォルトは 60 秒。
    - 監視は KABUSYS_ENV にかかわらず sqlite_path（SQLITE_PATH）を使用して永続化します。

- ExecutionEngine を起動（注文実行）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ完全に分離して記録します。
    - 起動時にプロセス優先度を High に設定し、pid ファイルを利用します。

- Paper Trading 検証レポートを生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例：
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db。別パス使用時は --db を指定するか PAPER_TRADING_SQLITE_PATH を設定。

- Streamlit ダッシュボード（監視データの可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を read-only URI で開きます。MonitoringEngine が先に起動してデータを作っていることを確認してください。

- AI 関連（ニューススコア / レジーム判定）
  - kabusys.ai.score_news（プログラム経由で呼び出す）や kabusys.ai.regime_detector.score_regime を利用。利用時は OPENAI_API_KEY の設定が必須です。

注意点
- Monitoring は監視用の sqlite DB の初期化（テーブル作成・既存 DB に対するマイグレーション）を自動で行います（init_monitoring_db）。
- run_monitoring は Monitoring の DB を本番 sqlite_path に対して操作します（KABUSYS_ENV に依らず）。
- run_execution は KABUSYS_ENV=paper_trading の場合 DB を分離します（paper_sqlite_path）。
- KillSwitch は data/kill.flag の存在で ExecutionEngine に停止指示を送ります（KillSwitch.clear() を ExecutionEngine 起動時に行う設定があります）。

---

## 環境変数（主なもの）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時に必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知に必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PID_FILE_PATH: 実行プロセスの PID ファイル path（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag path（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）

設定不足や不正値がある場合、Settings クラスが ValueError を投げます。例: PAPER_FILL_MODE の値チェック、KABUSYS_ENV の許容値チェック等。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル・モジュールのツリー（今回のコードベース抜粋分）です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_monitoring.py
    - run_execution.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他の execution 関連モジュールが存在する想定)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - utils/
      - __init__.py
      - process_priority.py
    - (data/ モジュール等、他のサブパッケージ参照あり)

各モジュールは単一責務を意識して分割されています。monitoring_db.py はテーブル作成や永続化を担当し、上位の Monitor クラスはビジネスルールを実装します。

---

## 開発・運用上の補足

- Python の型注釈やモダンな機能を使っているため Python 3.10 以上を推奨します。
- OpenAI を利用する機能は API 呼び出しに対してリトライやレスポンス検証を入れており、失敗時にはフェイルセーフ（0.0 でフォールバック、部分書き込み保護等）を行いますが、本番では API キー管理やコストに注意してください。
- Monitoring の poll 設定やアラート設定（LINE）は環境変数で調整できます。アラートは同一 (level, category) に対して内部クールダウンを持ちます。
- run_monitoring / run_execution は起動時にプロセス優先度を可能な範囲で上げます（psutil を使用）。権限により失敗する可能性があるため警告でスキップされます。
- DB マイグレーションは簡易な形で init_monitoring_db が実行時に追加カラムなどを検査して ALTER を行います（冪等）。

---

## よくあるコマンドまとめ

- 監視開始:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- 実行開始（通常／paper_trading 切替）:
  - KABUSYS_ENV=development python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

必要に応じて README に追記できます（例: requirements.txt、CI 設定、詳細な API ドキュメント、テスト実行方法など）。追加したい項目があれば教えてください。