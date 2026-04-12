# KabuSys

KabuSys は日本株向けの自動売買システムのコードベースです。戦略・ポートフォリオ構築、発注（Execution）、監視（Monitoring）、リサーチ、ニュース NLP（OpenAI を利用したセンチメント評価）などのコンポーネントで構成されています。本 README はプロジェクトの概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュール群から成る自動売買プラットフォームです。

- データリサーチ（DuckDB を用いたファクター計算、将来リターン計算、特徴量探索）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出、リスク調整）
- 発注実行（ブローカー抽象化、注文管理、再同期・リコンシリエーション）
- 監視（システム状態、注文滞留・約定異常、ドローダウン等の監視とアラート）
- AI モジュール（ニュース NLP による銘柄センチメント、マクロセンチメントを用いたレジーム判定）
- 運用ツール（Paper Trading の検証レポート生成、Streamlit ダッシュボード等）

設計上の方針として、外部 API 呼び出しや永続化が必要な箇所は明示され、テストしやすい純粋関数と副作用を伴うモジュールに分離されています。

---

## 主な機能一覧

- Execution（発注）
  - Broker クライアントを抽象化し、Live / Paper（モック）を切り替え可能
  - OrderManager による注文ライフサイクル管理、Duplicate チェック
  - Reconciler による再起動時の自動復旧（OrderSent の突合、ポジション差分確認）
- Monitoring（監視）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス状態、データ鮮度の監視
  - TradeMonitor: 滞留注文（stale orders）、約定異常価格の検出
  - RiskMonitor: ドローダウン、ポジション上限の監視とリスクログ記録
  - KillSwitch: 危険時にフラグファイルを書いて ExecutionEngine を停止可能
  - AlertManager: LINE Messaging API を使った一方向通知（クールダウン有）
  - Streamlit ベースの監視ダッシュボードを用意
- Portfolio（ポートフォリオ構築）
  - 候補選定（スコア降順、tie-breaker）
  - 等金額配分 / スコア加重配分
  - セクター集中制限適用、レジーム乗数（bull/neutral/bear）
  - リスクベース等のポジションサイズ計算（単元株丸め、利用可能キャッシュを考慮）
- Research（リサーチ）
  - Momentum / Volatility / Value ファクター計算（DuckDB を使用）
  - 将来リターン、IC（Spearman）、ファクターサマリー等の統計ユーティリティ
- AI（OpenAI を利用）
  - news_nlp: ニュース記事を集約して LLM に投げ、銘柄ごとのセンチメントを ai_scores テーブルへ書き込み
  - regime_detector: ETF（1321）の MA200 乖離とマクロセンチメントを合成して日次レジーム判定
- ツール
  - paper_verification_report: Paper Trading の検証レポートを標準出力に生成
  - 起動スクリプト: run_monitoring.py、run_execution.py（モードに応じて本番/ペーパー DB を使い分け）

---

## セットアップ手順

以下は一般的なセットアップ手順です。プロジェクト固有の追加手順がある場合は適宜補ってください。

1. リポジトリをクローン
   - git clone <your-repo-url>
   - cd <repo>

2. Python 環境（推奨）
   - Python 3.9+ を想定
   - 仮想環境を作成して有効化
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - 必要なパッケージ例:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例（pip）:
     - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用）

4. データディレクトリの準備
   - デフォルトの DB / ファイルパスは `data/` 配下が想定されています。必要に応じて作成してください。
     - mkdir -p data

5. 環境変数（.env）
   - プロジェクトは .env / .env.local を自動で読み込む仕組みを持ちます（プロジェクトルートが .git または pyproject.toml を含む場合）。
   - 主要な環境変数（例）:
     - KABUSYS_ENV=development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...  （AI モジュール使用時）
     - LINE_CHANNEL_ACCESS_TOKEN=...  （アラート送信時）
     - LINE_USER_ID=...
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant | partial | never | reject
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - MONITOR_POLL_INTERVAL=60  （秒、run_monitoring 用）
   - .env.example を参考に .env を準備してください（もし無ければ上記を参考に作成）。

6. パーミッションと権限
   - process priority 設定（高優先度）を行うため、OS の権限が必要な場合があります。設定に失敗してもログを出してスキップする実装になっています。

---

## 使い方

以下は主要な起動・実行例です。

1. 監視ループ（MonitoringEngine）を起動
   - run_monitoring.py はシステム監視をポーリングで行い、SQLite（monitoring.db）にログを残します。
   - デフォルトのポーリング間隔は 60 秒。環境変数で変更可:
     - export MONITOR_POLL_INTERVAL=30
   - 実行例:
     - python -m kabusys.run_monitoring

   - 補足:
     - Monitoring は KABUSYS_ENV に依らず本番 sqlite_path を使います（監視用は共通 DB を想定）。
     - 起動時に process priority を "high" に設定しようとします。権限が無い場合は警告が出ます。

2. ExecutionEngine（発注エンジン）を起動
   - run_execution.py は ExecutionEngine を組み立てて取引セッションを開始します。
   - Paper Trading の場合（KABUSYS_ENV=paper_trading）は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に完全分離して記録します。
   - 実行例:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
     - KABUSYS_ENV=live python -m kabusys.run_execution

   - 注意:
     - RiskConfig、最大利用率、初期ポートフォリオ値等はコード内で既定値が設定されています。必要に応じて Settings やコードを変更してください。
     - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定しておくと、既存の kill.flag をクリアできます（設定プロパティ参照）。

3. Paper Trading 検証レポートを生成
   - data/paper_trading.db を参照して検証レポートを出力します。
   - 実行例:
     - python -m kabusys.tools.paper_verification_report
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - オプションで DB パス指定:
       - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

4. Streamlit 監視ダッシュボード
   - 起動例:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - read-only で SQLite ファイルへ接続し、Overview / Positions / Orders / System のタブを表示します。

5. AI モジュール（ニュース NLP / レジーム判定）
   - news_nlp.score_news(conn, target_date, api_key=None)
     - DuckDB 接続（prices_daily/raw_news/news_symbols/ai_scores）を渡して実行
     - OpenAI API キーが必要（引数または OPENAI_API_KEY 環境変数）
   - regime_detector.score_regime(conn, target_date, api_key=None)
     - MA200 乖離とマクロ記事センチメントを合成して market_regime テーブルに書き込み
   - 実行時は OpenAI の使用料と API レート制限に注意してください。API の一時エラーはバックオフでリトライされ、最終的にフォールバックやスキップが行われる実装です。

---

## 重要な設定・環境変数（抜粋）

- KABUSYS_ENV: development / paper_trading / live（システム挙動の切り替え）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用
- KABU_API_PASSWORD: kabuステーション API 用
- OPENAI_API_KEY: OpenAI API を使う場合に必須
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート送信に使用
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper トレード用 DB（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: Kill スイッチのフラグファイル（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant | partial | never | reject）

---

## トラブルシューティング / 注意事項

- process priority や CPU affinity の設定は psutil を使って行われます。権限不足やプラットフォーム非対応時は警告を出してスキップします。
- DuckDB / SQLite のパスは Settings で制御できます。複数プロセスから同じファイルに書き込む場合はロックや接続モードに注意してください（monitoring の Streamlit は read-only 接続を推奨）。
- OpenAI API を利用する処理はネットワーク・レートリミット等の失敗を考慮した実装になっています。API キーを漏洩しないように管理してください。
- Paper Trading は production DB から完全に分離する設計です。KABUSYS_ENV=paper_trading 設定を確認してください。
- monitoring の KillSwitch はファイルシステム上のフラグ（kill.flag）を使って ExecutionEngine に停止信号を送る簡便な仕組みです。ファイルの存在/削除で動作するため、誤操作に注意してください。

---

## ディレクトリ構成（抜粋）

以下は主要なファイル / モジュールの一覧と簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings クラス）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 切替対応）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - portfolio/
    - portfolio_builder.py — 候補選定・スコア等
    - position_sizing.py — 発注株数計算、aggregate cap
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — Momentum, Volatility, Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン、IC、統計サマリー等
  - ai/
    - news_nlp.py — ニュース記事を OpenAI で評価して ai_scores に書き込む
    - regime_detector.py — マクロセンチメント + MA200 乖離でレジーム判定
  - monitoring/
    - monitoring_db.py — SQLite ベースの永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常チェック
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — LINE プッシュ通知送信
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit での監視ダッシュボード
  - execution/
    - order_manager.py — 注文管理（Order 作成・送信）
    - reconciler.py — 起動時の注文・ポジション突合作業
    - （その他、broker_api / order_repository 等のモジュールが存在すると想定）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（上記はコードベースの一部抜粋です。実際のリポジトリにはさらに細分化されたモジュールや補助コードが含まれる可能性があります）

---

## 開発上の補足

- 単体テストを書く際は Settings の自動 .env 読み込みを無効にするために環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使用できます。
- OpenAI に依存する関数はテストで外部呼び出しをモックしやすいように分離・ラップされています（_call_openai_api を patch するなど）。
- DuckDB / SQLite の SQL はコメントや設計メモを含む形で実装されており、分析や ETL ジョブの組立てに適しています。

---

必要に応じて README をプロジェクトの実態（requirements.txt、.env.example、CI/CD、起動スクリプトのパラメータ）に合わせてカスタマイズしてください。追加で「インストール用の requirements.txt を作成してほしい」「具体的な起動環境（systemd ユニットや Dockerfile）の例が欲しい」など要望があれば、その内容に合わせて追記します。