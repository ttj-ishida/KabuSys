# KabuSys

日本株自動売買システムの参考実装。ポートフォリオ構築、注文実行、監視、Research/AI 補助（ニュース NLP / レジーム判定）、および Paper Trading 検証ツールを備えます。

注意: このリポジトリはシステム全体のコード断片を含みます。実運用化には追加の安全対策・テストが必要です。

---

## 概要

KabuSys は以下の機能を組み合わせたモジュール群です。

- 戦略に基づく銘柄選定と配分（portfolio）
- 注文作成・管理・再同期（execution）
- 実行エンジンの監視とアラート（monitoring）
- DuckDB を用いたファクター計算・研究ユーティリティ（research）
- OpenAI を使ったニュースセンチメント評価 / 市場レジーム判定（ai）
- Paper Trading 用検証ツール（tools）
- プロセス優先度や CPU affinity 操作などのユーティリティ（utils）

設定は主に環境変数（.env / .env.local）で行います。自動で .env を読み込む仕組みが組み込まれています（無効化可能）。

---

## 主な機能一覧

- Execution
  - Broker クライアントを抽象化し、live / paper_trading を切り替え可能
  - OrderManager / OrderRepository / Reconciler による注文ライフサイクル管理と再同期
  - 起動時に PID ファイルを使ったプロセス管理と停止フラグ対応
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、実行プロセスの死活確認
  - TradeMonitor: 滞留注文や約定価格異常の検知
  - RiskMonitor: ドローダウン・ポジション上限の監視、ダッシュボード永続化
  - KillSwitch: 条件に応じた停止フラグ（data/kill.flag）書き込み
  - AlertManager: LINE Messaging API によるプッシュ通知（クールダウン管理）
  - Streamlit ダッシュボード（read-only で監視 DB を表示）
- Research / Portfolio
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC 計算、特徴量探索 utilities
  - 銘柄選定、等金額/スコア重み、ポジションサイズ計算、セクターキャップ、レジーム乗数
- AI
  - news_nlp.score_news: raw_news を OpenAI に投げて銘柄ごとのスコアを ai_scores に書き込み
  - regime_detector.score_regime: 200 日 MA とマクロニュースの LLM センチメントを合成して market_regime に書き込み
  - 両方とも OpenAI API キーが必要。リトライ・バックオフなどの堅牢化あり
- Tools
  - paper_verification_report: Paper Trading DB から稼働率・注文成功率・レイテンシなどを集計してレポート出力

---

## 要件 / 依存パッケージ（抜粋）

- Python 3.10+
- duckdb
- psutil
- openai
- requests
- streamlit
- （標準ライブラリ）sqlite3, threading, logging など

インストール例（仮の requirements.txt を使う場合）:
```
pip install duckdb psutil openai requests streamlit
```

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. Python 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux/Mac
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install duckdb psutil openai requests streamlit
   ```
4. .env を準備
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動読み込みされます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必要な環境変数（例）
     ```
     KABUSYS_ENV=development           # development | paper_trading | live
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     LINE_CHANNEL_ACCESS_TOKEN=...
     LINE_USER_ID=...
     PAPER_FILL_MODE=instant          # instant | partial | never | reject
     LOG_LEVEL=INFO
     ```
   - .env ファイルのパースは shell 風の形式（コメント、export 付き行、引用符、インラインコメントをある程度サポート）に対応しています。

5. 初回 DB 作成
   - 実行や監視を始めると自動的に monitoring DB のテーブルが作成されます（init_monitoring_db）。DuckDB ファイルは自分で prices_daily / raw_financials 等のテーブルを準備する必要がある機能群があります。

---

## 使い方（主要コマンド）

プロジェクトルートの `src` をパッケージソースとして扱うか、パッケージとしてインストールして利用できます。簡易的な実行方法を示します。

- ExecutionEngine を起動（本番/テスト切替は KABUSYS_ENV）
  - 直接実行:
    ```
    python src/kabusys/run_execution.py
    ```
  - またはパッケージとして（パスが通っている場合）:
    ```
    python -m kabusys.run_execution
    ```
  - Note:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い `data/paper_trading.db` に記録します（本番 DB と分離）。
    - Execution は起動前に `data/stop_requested.flag` が存在すると起動しません。
    - Execution の PID は `data/execution.pid` に書き込まれます（プロセス生存チェックに使用）。

- Monitoring を起動（SystemMonitor のポーリング）
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 実行:
    ```
    python src/kabusys/run_monitoring.py
    ```
  - または:
    ```
    python -m kabusys.run_monitoring
    ```
  - Monitoring は常に production 用の sqlite_path（Settings.sqlite_path）を使用して監視ログを残します。
  - 停止は `data/stop_requested.flag` を作成するか、KeyboardInterrupt (Ctrl+C)。

- Streamlit ダッシュボード（監視の可視化）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - 監視 DB を読み取り専用で開き、ポジション、注文履歴、最新のシステム状態、リスクログを表示します。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```
  - 引数 `--db` を指定しない場合は環境変数 `PAPER_TRADING_SQLITE_PATH` またはデフォルト `data/paper_trading.db` を使用。
  - 出力は標準出力にレポート形式で表示されます。

- AI 機能（ニューススコア / レジーム判定）
  - news_nlp.score_news / regime_detector.score_regime は Python API として呼び出すか、スクリプト化して実行してください。
  - 例（対話的 / スクリプト内呼び出し）:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026, 4, 15), api_key="sk-...")
    ```
  - OpenAI API キーが必要です（引数または環境変数 OPENAI_API_KEY）。API 呼び出しはリトライ/バックオフを伴いますが、APIキー未設定時は ValueError を投げます。
  - 使用モデルはコード内で `gpt-4o-mini` に設定されています（将来変更可能）。

---

## 重要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（Settings.env）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading の模擬約定挙動（instant | partial | never | reject）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知設定
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

---

## 停止 / 制御ファイル

- data/stop_requested.flag
  - run_monitoring / run_execution のループがこのファイルの存在を検知すると安全に停止します。
- data/kill.flag
  - KillSwitch によって書き込まれる停止シグナル（ExecutionEngine に対する停止要求として運用側で利用）。
- data/execution.pid
  - Execution エンジンの PID を記載するファイル。SystemMonitor はこの PID を見てプロセス生存を判定します。

---

## ディレクトリ構成（抜粋）

以下はパッケージ内部の主要なファイル/モジュール構成です（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings クラス、自動 .env ロード
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
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
  - monitoring/
    - monitoring_db.py
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
    - （その他 OrderRepository / broker などの実装を想定）

注: 実際のリポジトリでは `kabusys.data` 等のモジュール参照があります（DuckDB の prices_daily 等）。これらはデータ準備や ETL パイプラインとして別途用意されることを想定しています。

---

## 追加の設計ノート / 安全考慮

- .env の自動ロード
  - プロジェクトルートは `.git` または `pyproject.toml` を基準に自動検出します。テスト等で自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
- Paper Trading
  - `KABUSYS_ENV=paper_trading` にすると Execution は Mock ブローカーを使い、`data/paper_trading.db` に記録します（本番 DB と完全分離）。
- OpenAI の利用
  - LLM 呼び出しは外部 API 呼び出しのため課金・レート制限のリスクがあります。API キー管理と呼び出し頻度の設計に注意してください。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は既存 DB に対する簡易マイグレーション（カラム追加等）を含んでいますが、本格的なマイグレーション戦略は必要です。
- 権限・実行優先度
  - set_process_priority は OS 権限に依存します（権限不足時は警告を出してスキップ）。

---

## 開発 / 貢献

- 新しい機能追加や修正はブランチを切って PR を作成してください。
- テストや型チェック（mypy）を追加すると品質向上に貢献します。
- 実運用へ移す場合は、より厳密なエラーハンドリング、セキュリティ（API キーの管理）・監査ログ・自動テストを整備してください。

---

以上です。必要ならば README にサンプル .env.example のテンプレートや、より詳しいコマンド例（systemd / supervisor による起動、Dockerfile、CI 設定など）を追加できます。どの情報がさらに欲しいか教えてください。