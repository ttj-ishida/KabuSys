# KabuSys

日本株向け自動売買システムのコードベース（簡易ドキュメント）。  
この README はプロジェクトの概要、主要機能、セットアップと実行方法、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関するコンポーネント群を含む小規模なシステムです。主な役割は次の通りです。

- 注文の生成・管理・ブローカー連携（Execution）
- 監視（Monitoring）：システム状態、注文件数、約定の異常などを定期的に記録／通知
- ポートフォリオ構築（Portfolio）：シグナルに基づく候補選定、重み付け、株数算出
- リサーチ（Research）：ファクター計算、特徴量探索
- AI 補助機能（AI）：ニュースセンチメント / 市場レジーム判定（OpenAI API を利用）
- 開発ツール：Paper Trading 検証レポート生成、Streamlit ダッシュボード等

設計上の特徴：
- DuckDB / SQLite を用いたローカルデータ処理・永続化
- モジュールは「ビジネスロジック」「IO（DB・API）」を分離
- Paper Trading と本番を DB レベルで分離可能
- 外部 API（OpenAI 等）はオプション、フェイルセーフ実装あり

---

## 主な機能一覧

- Execution
  - OrderManager / ExecutionEngine / Reconciler による注文作成・送信・再同期
  - Paper Trading モード（KABUSYS_ENV=paper_trading）で MockBroker を使用し、paper_trading 専用 DB に記録
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス存在、株価データ鮮度を監視
  - TradeMonitor: 注文滞留（stale orders）、約定価格の異常を検出
  - RiskMonitor: ドローダウン・ポジション上限を監視し、リスクログに永続化
  - KillSwitch: 条件を満たしたらフラグファイル（data/kill.flag）を書き込み Execution を停止
  - AlertManager: LINE Messaging API 経由でアラート送信（オプション）
  - Streamlit ダッシュボード（監視データの可視化）
- Portfolio
  - 候補選定、等配分／スコア配分、リスク調整、株数算出（単元・投下キャップ考慮）
- Research
  - ファクター計算（Momentum, Volatility, Value 等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI
  - news_nlp: ニュースを LLM でセンチメント評価し ai_scores に書き込み
  - regime_detector: ETF MA とマクロセンチメントを合成して市場レジーム判定
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
  - Streamlit ベースの監視ダッシュボード

---

## セットアップ手順

前提:
- Python 3.9+（コード上は型注釈に対応したバージョンが想定されています）
- Git clone でリポジトリを取得

推奨仮想環境作成例:
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
```

必要パッケージの一例（環境により調整してください）:
```bash
pip install duckdb psutil requests openai streamlit
```

必須／推奨環境変数（Settings クラス参照）:
- 必須（実際に該当機能を使う場合）
  - JQUANTS_REFRESH_TOKEN: J-Quants API（ファクター等で使用）
  - KABU_API_PASSWORD: kabuステーション API パスワード（ブローカー連携）
- OpenAI 関連（AI 機能を使う場合）
  - OPENAI_API_KEY
- DB パス等（デフォルト値あり）
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- 動作モード
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- その他（オプション）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（AlertManager の通知）
  - PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject）
  - LOG_LEVEL（INFO 等）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを抑止

.env 自動読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます（OS 環境変数が優先されます）。
- テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

初期ディレクトリ準備:
```bash
mkdir -p data
# 必要なら空の DB を作るか、Monitoring 起動時に init_monitoring_db() が実行されテーブル作成されます
```

---

## 使い方（主要な起動方法）

- 監視ループを起動（Monitoring）
  - スクリプト: src/kabusys/run_monitoring.py
  - 起動方法:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - 説明:
    - Settings.sqlite_path（デフォルト data/monitoring.db）へ接続し監視ログを記録します。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可（デフォルト 60）。
    - 監視は常に production 用 sqlite_path を使用（KABUSYS_ENV に依らず）。
    - 停止: プロジェクトルートの data/stop_requested.flag を作成するとループが検出して終了します。

- Execution エンジンを起動（注文実行）
  - スクリプト: src/kabusys/run_execution.py
  - 起動方法:
    ```bash
    python -m kabusys.run_execution
    ```
  - 説明:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録して本番 DB と分離します。
    - 起動時に data/execution.pid に PID を書きます（内部処理）。
    - 停止: data/stop_requested.flag を作成すると停止処理がトリガーされます。
    - KillSwitch が発動すると data/kill.flag が書き込まれ、Execution 側が検出して停止する設計です。

- Paper Trading 検証レポート生成
  - スクリプト: src/kabusys/tools/paper_verification_report.py
  - 実行例:
    ```bash
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
    ```
  - 説明:
    - デフォルト DB は data/paper_trading.db。環境変数 PAPER_TRADING_SQLITE_PATH で上書き可。
    - 指標（稼働率、注文成功率、レイテンシ等）に対して PASS/FAIL を判定して標準出力にレポートします。

- Streamlit 監視ダッシュボード
  - ファイル: src/kabusys/monitoring/streamlit_dashboard.py
  - 起動方法:
    ```bash
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - 説明:
    - 読み取り専用で SQLite DB を開き、Positions / Orders / System / Overview を表示します。
    - MonitoringEngine が DB にデータを出力していることが前提です。

- AI 機能（ニュースセンチメント / レジーム判定）
  - 関数:
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーを渡すか環境変数 OPENAI_API_KEY を設定してください。API 呼び出しは外部サービスに依存します。失敗時はフェイルセーフ（多くの場合デフォルト値で継続）を取る設計です。

補助ファイル（停止・通知など）
- 監視が停止を検出するファイル
  - data/stop_requested.flag — run_* スクリプトがループを終了するためにチェック
- Execution 停止用フラグ
  - data/kill.flag — KillSwitch が書き込み、ExecutionEngine に停止を促す（冪等）
- PID ファイル
  - data/execution.pid — Execution 起動時に作成

---

## よく使う環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須: ファクター等で使用)
- KABU_API_PASSWORD (必須: kabu API)
- OPENAI_API_KEY (AI 機能利用時必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- SQLITE_PATH (監視 DB、default: data/monitoring.db)
- DUCKDB_PATH (DuckDB ファイル、default: data/kabusys.duckdb)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、default: data/paper_trading.db)
- MONITOR_POLL_INTERVAL (run_monitoring でポーリング秒数を上書き)
- PAPER_FILL_MODE (paper_trading の約定動作: instant|partial|never|reject)

---

## 開発者向けメモ

- .env のパースは独自実装されており、'.env' / '.env.local' を自動で読み込みます（OS 環境変数優先）。
- Settings クラスは環境変数の検証とデフォルト値を提供します。無効な値は ValueError を投げます。
- init_monitoring_db(sqlite_conn) は監視用 DB のテーブル作成と簡単なマイグレーションを行います（冪等）。
- プロセス優先度は psutil を利用して設定されます（set_process_priority）。権限やプラットフォームによってはスキップされます。
- OpenAI API 呼び出しはリトライ・バックオフ・レスポンス検証を実装しているため、直接呼ぶ場合は api_key を渡すか環境変数を設定してください。
- duckdb を使ったリサーチ機能は SQL と Python を組み合わせて効率的に計算する設計です。

---

## ディレクトリ構成（主要部分）

以下はソースツリーの要約（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / 設定管理
  - run_monitoring.py           — SystemMonitor のポーリング起動スクリプト
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py
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
    - (OrderManager, Reconciler, ExecutionEngine 周りの実装)
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - ...
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/                        — デフォルトデータベース / フラグファイル置き場（実行時に使用）
  - その他（data ファイルや DB は実行時に生成／利用）

※ 実際の完全なツリーはリポジトリを参照してください。

---

## トラブルシューティング / ヒント

- DB が見つからない / ロックエラー:
  - monitoring 用 DB は run_monitoring 実行で init が走ります。streamlit などから読み取り専用で開く場合は URI に ?mode=ro を付けて開いています。
- KABUSYS_ENV=paper_trading を忘れると本番 DB に書き込まれる可能性があるため注意してください（paper_trading 用 DB が指定可能）。
- OpenAI の API レート制限やネットワークエラーはリトライ実装がありますが、大量実行時は API コスト・制限に注意してください。
- kill.flag / stop_requested.flag / execution.pid はファイルベースの単純な同期手段です。手動で削除・作成して動作を制御できます（KillSwitch.clear() も利用可能）。

---

この README はコードベースの主要な使い方と構成を簡潔にまとめたものです。詳細な設計仕様（PortfolioConstruction.md や StrategyModel.md 等）や API ドキュメントが別途ある場合はそちらも参照してください。必要であれば追加の使い方説明（例: ExecutionEngine の詳細構成、OrderRepository のスキーマ等）を追記します。