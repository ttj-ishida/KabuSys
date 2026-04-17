# KabuSys

日本株向けの自動売買システム（リサーチ / ポートフォリオ構築 / 発注エンジン / 監視）です。  
このリポジトリは、戦略・ポートフォリオ構築ロジック、発注実行コンポーネント、監視/アラート、AI を用いたニュースセンチメント評価などを含みます。

---

## 概要

主な目的は「自動売買のエンジン化」と「運用監視」です。  
設計上のポイント：

- 環境変数（.env）で設定を管理
- Paper Trading（モックブローカー）モードと本番モードを分離（DB も分離）
- DuckDB を使ったリサーチ（ファクター計算等）、SQLite を使った監視・注文ログ保存
- OpenAI を用いたニュース NLP（センチメント評価）・レジーム判定（オプション）
- 監視コンポーネントは LINE 通知や kill flag による自動停止機構を備える

---

## 主な機能一覧

- Execution（発注）
  - ExecutionEngine（起動・セッション管理）
  - OrderManager（注文作成・同期）
  - Reconciler（起動時の再同期・ポジション差分検出）
  - Paper Trading モード（MockBrokerClient、データは data/paper_trading.db に保存）
  - リスク管理（RiskManager）による発注制限

- Monitoring（監視）
  - SystemMonitor：CPU/MEM/Disk、プロセス生存、データ鮮度を監視
  - TradeMonitor：滞留注文・約定異常を検出
  - RiskMonitor：ドローダウン・ポジション上限などを監視
  - MonitoringEngine：上記を束ねるポーリングループ
  - AlertManager：LINE Push によるアラート（クールダウンあり）
  - KillSwitch：条件達成で data/kill.flag を書いて Execution を停止

- Portfolio（ポートフォリオ構築）
  - 候補選定、等重/スコア重み付け、ポジションサイズ計算、セクター制限、レジーム乗数等

- Research（リサーチ）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC 計算、統計サマリー

- AI（オプション）
  - news_nlp: OpenAI を用いたニュースの銘柄別センチメントスコア生成（ai_scores テーブルへ）
  - regime_detector: ETF とマクロニュースを使った市場レジーム判定

- Tools
  - paper_verification_report: Paper Trading の検証レポート生成ツール（稼働率・成功率・レイテンシ等）

---

## 要件（推奨）

- Python >= 3.10
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit (ダッシュボード起動時)
- SQLite は標準ライブラリで利用可能

インストール例:
```
pip install duckdb psutil openai requests streamlit
```

（実際の運用では requirements.txt を用意して pip install -r で管理することを推奨します。）

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 仮想環境を作成・有効化（推奨）
3. 必要パッケージをインストール（上記参照）
4. .env を作成（プロジェクトルートに置く）
   - 参考: .env.example（存在する場合）
   - 自動読み込み: デフォルトで .env と .env.local がロードされます（環境変数が優先）
   - 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

主要な環境変数（代表例）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須な機能がある場合）
- KABU_API_PASSWORD: kabuステーション API パスワード（本番接続時）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定振る舞い）
- PID_FILE_PATH: Execution の PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager での通知に使用

例（.env の一部）:
```
KABUSYS_ENV=paper_trading
OPENAI_API_KEY=sk-...
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
MONITOR_POLL_INTERVAL=30
LOG_LEVEL=INFO
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
```

---

## 使い方

- 実行エンジン（Execution）
  - 本番・Paper モードに応じて動作します（KABUSYS_ENV に依存）。
  - 起動:
    ```
    python -m kabusys.run_execution
    ```
  - Paper Trading 時は MockBrokerClient を使用し、データは data/paper_trading.db に保存されます。
  - 停止方法:
    - 管理者が停止フラグを立てる: data/stop_requested.flag を作成すると終了処理が行われます。
    - KillSwitch（監視ロジック）がトリガーした場合は data/kill.flag が書かれ、Execution 側で停止処理に反映できます。

- 監視ループ（Monitoring）
  - 起動:
    ```
    python -m kabusys.run_monitoring
    ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60）。
  - 監視は常に本番用 sqlite_path を使用します（環境に関わらず監視データは一元的に保管）。
  - 停止方法:
    - data/stop_requested.flag を作成すると監視ループは終了します。
    - KillSwitch が条件を満たすと data/kill.flag が生成され Execution を停止するトリガーになります。

- 監視ダッシュボード（Streamlit）
  - 起動:
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - 読み取り専用で監視 DB を表示します。MonitoringEngine が起動していないとエラーになります。

- Paper Trading 検証レポート
  - 実行例:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
    ```
  - 出力: 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを表示し PASS/FAIL を判定します。

- AI 機能
  - ニューススコアリング（news_nlp.score_news）
    - DuckDB 接続と target_date を与えてスコアを生成し ai_scores テーブルに書き込みます。
    - OpenAI API キー（OPENAI_API_KEY）が必要です。
  - レジーム判定（ai.regime_detector.score_regime）
    - DuckDB と target_date、OpenAI API キーで実行します。MA とマクロセンチメントを合成して market_regime に書き込みます。

---

## 主要モジュール（簡易説明）

- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出）
  - Settings クラスで環境変数アクセスをラップ

- kabusys.execution
  - 発注関連ロジック（OrderManager、ExecutionEngine、Reconciler、RiskManager 等）

- kabusys.monitoring
  - 監視関連（SystemMonitor、TradeMonitor、RiskMonitor、AlertManager、KillSwitch、MonitoringEngine）
  - monitoring_db: SQLite のテーブル初期化／永続化 API（init_monitoring_db, MonitoringDB）

- kabusys.portfolio
  - ポートフォリオ候補選定・重み付け・ポジションサイズ計算・リスク調整

- kabusys.research
  - DuckDB を使ったファクター計算・特徴量探索（calc_momentum 等）

- kabusys.ai
  - news_nlp: ニュースセンチメント評価（OpenAI）
  - regime_detector: 市場レジーム判定（OpenAI + ETF）

- kabusys.tools
  - paper_verification_report: Paper Trading の結果検証

- kabusys.utils
  - process_priority: プラットフォーム依存のプロセス優先度設定（psutil 使用）

---

## ディレクトリ構成

（主要ファイル抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py
  - execution/
    - order_manager.py
    - order_repository.py
    - execution_engine.py
    - reconciler.py
    - broker_factory.py
    - ...（発注関連の実装）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
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
  - tools/
    - paper_verification_report.py

- data/
  - monitoring.db (デフォルトの監視 SQLite)
  - kabusys.duckdb (デフォルトの DuckDB)
  - paper_trading.db (Paper Trading 用 DB)
  - execution.pid, stop_requested.flag, kill.flag などの制御ファイル

---

## 運用上の注意・トラブルシューティング

- .env の自動読み込みはプロジェクトルート（.git / pyproject.toml）を起点に行われます。CI / テストで自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI API を使う機能は API キーが必須です。未設定だと ValueError が発生します。
- process_priority や cpu_affinity の設定はプラットフォーム依存であり、権限不足（非 root）や未対応 OS では警告を出してスキップします。
- Monitoring／Execution は stop_requested.flag（data/stop_requested.flag）で優雅に停止できます。KillSwitch による停止は data/kill.flag に理由が書き込まれます。
- DuckDB / SQLite のパスは Settings で上書き可能です（環境変数 DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）。
- DB スキーマのマイグレーション処理は init_monitoring_db で一部（カラム追加等）を自動化していますが、本格的な運用では適切なマイグレーション管理を推奨します。

---

## 貢献・拡張案

- Broker クライアントの追加（実ブローカー連携）
- 単元株サイズの銘柄別対応（lot_size を銘柄マスタで管理）
- 更に詳細な監視ルール・アラート条件の追加
- DuckDB の ETL パイプライン改善（データ取り込みの自動化）
- テストカバレッジの拡充（ユニット / 統合テスト）

---

README の内容はコードベースの主要機能と運用フローを簡潔にまとめたものです。実際の導入・運用では .env 設定、アクセス権、外部 API の利用規約等を確認してください。質問や追加で欲しいドキュメント（例: API 仕様、設計ドキュメント抜粋、運用手順書 等）があれば教えてください。