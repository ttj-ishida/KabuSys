# KabuSys

日本株向け自動売買システムのリポジトリ（開発中）。  
この README はリポジトリ内の主要スクリプト・モジュールに基づき、導入・起動方法、主要機能、ディレクトリ構成を日本語でまとめたものです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したシステムです。  
主な目的は以下：

- トレード実行エンジン（実運用 / ペーパートレード）  
- システム監視（プロセス監視、データ鮮度、ログ・アラート）  
- ポートフォリオ構築（銘柄選定・配分・ポジションサイズ計算）  
- 研究用ファクター計算・特徴量解析（DuckDB を利用）  
- ニュース NLP（OpenAI を用いたセンチメント評価）  
- 各種運用ツール（ペーパートレード検証レポート等）

設計方針として「テストしやすい純粋関数」「ルックアヘッドバイアス防止」「フェイルセーフ（API失敗時に停止しない）」が意識されています。

---

## 機能一覧（主な機能）

- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV による切り替え（development / paper_trading / live）
  - paper_trading 時は MockBrokerClient を使用し、専用 SQLite（data/paper_trading.db）へ記録
  - プロセス優先度設定、PID ファイル管理、停止フラグ対応

- Monitoring（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期ポーリング
  - kill.flag による ExecutionEngine 停止トリガ（Kill Switch）
  - ロギング、監視 DB（SQLite）への記録

- ポートフォリオ構築（kabusys.portfolio）
  - 銘柄候補選定、等配分／スコア加重、位置サイズ計算、セクターキャップ、レジーム乗数

- リサーチ（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 利用）
  - 将来リターン計算、IC（Information Coefficient）等の統計解析

- AI サービス（kabusys.ai）
  - news_nlp: OpenAI を使ったニュースセンチメント評価（ai_scores テーブルへ書込）
  - regime_detector: ETF MA とマクロニュースを組み合わせた市場レジーム判定

- ツール
  - 環境設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

- ユーティリティ
  - 統一的なロギング設定（kabusys.utils.logging_setup）
  - プロセス優先度 / CPU affinity 設定（kabusys.utils.process_priority）
  - 監視 DB 永続化レイヤ（kabusys.monitoring.monitoring_db）

---

## 前提条件

- Python 3.10+（ソースは型注釈やモダンな文法を使用）
- 必要な外部ライブラリ（インストール手順は下記）
  - duckdb
  - psutil
  - openai（AI 機能利用時）
  - pyyaml（設定 YAML の検証を行う場合）
- （任意）OpenAI を使う場合は有効な OPENAI_API_KEY が必要

※ requirements.txt はリポジトリに含まれていない想定のため、プロジェクトに合わせて pip install してください。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <this-repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell/CMD)
   ```

3. 依存ライブラリをインストール（例）
   ```
   pip install duckdb psutil openai pyyaml
   ```
   実運用で必要なライブラリはプロジェクト方針に合わせて追加してください。

4. .env を作成（対話ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは必要な環境変数（J-Quants トークン、kabu API パスワード等）を対話形式で作成します。
   ウィザード実行後、`.env` がプロジェクトルートに保存されます。

5. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   --strict を付けると警告も失敗扱いになります:
   ```
   python -m kabusys.validate_config --strict
   ```

6. ログディレクトリ / data ディレクトリ作成（通常自動作成されますが権限やパスを確認）
   - デフォルト DB / ファイル:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading DB: data/paper_trading.db
     - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag
   - ログ: logs/<app>.log（logs ディレクトリ）

---

## 環境変数（主要なもの）

（.env に記載する項目は config_setup で案内されます）

- 必須（実行に必要）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 運用関連
  - KABUSYS_ENV: execution 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
  - LOG_LEVEL: ログレベル（"DEBUG"/"INFO"/...）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB、デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE（paper_trading 時の約定モード: "instant"|"partial"|"never"|"reject"、デフォルト "instant"）
  - KILL_FLAG_CLEAR_ON_START（Execution 起動時に kill.flag を自動クリアするか。0/1、デフォルト 0）
  - OPENAI_API_KEY（AI 機能を使う場合）

- モニタリング特有
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

---

## 使い方（起動・運用）

基本的には各モジュールを Python モジュール実行します（プロジェクトのルートから）。

- ExecutionEngine（トレード実行エンジン）起動
  - 通常:
    ```
    python -m kabusys.run_execution
    ```
  - KABUSYS_ENV によって実行モードが変わります:
    - development: 発注無し（開発）
    - paper_trading: MockBroker を使用し paper_trading 用 DB に記録（data/paper_trading.db）
    - live: 実取引（kabuステーション API を使用）

  注意:
  - 起動時に data/stop_requested.flag や data/kill.flag の有無を確認します。停止フラグがある場合は起動や継続処理に影響します。
  - 起動直後にプロセス優先度を "high" に設定しようとします（権限が必要な場合は警告になることがあります）。

- Monitoring（監視プロセス）起動
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に関わらず本番 DB を参照）します。
  - 監視は SystemMonitor / TradeMonitor / RiskMonitor を定期実行し、必要に応じて kill.flag を書き込みます。

- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  ```

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB は data/paper_trading.db。`--db` オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で変更可。

- AI 機能（Python API から呼ぶ）
  - ニュースセンチメント評価:
    ```py
    from kabusys.ai import score_news
    score_news(duckdb_conn, target_date, api_key="...")
    ```
  - レジーム判定:
    ```py
    from kabusys.ai import score_regime  # 実装では kabusys.ai.regime_detector.score_regime
    # score_regime(conn, target_date, api_key=...)
    ```
  - いずれも OPENAI_API_KEY（または引数の api_key）が必要。

---

## 運用上の注意点 / トラブルシューティング

- kill.flag / stop_requested.flag
  - kill.flag (デフォルト: data/kill.flag) は Kill Switch。Monitoring が条件を満たすと書き込まれ、ExecutionEngine はこれを検知して停止します。
  - stop_requested.flag (data/stop_requested.flag) は run_monitoring / run_execution の外部停止フラグとして用いられます（存在すればループを抜けます）。

- process priority（優先度）設定は psutil を使います。権限が足りない環境では警告が出ますが処理は続行します。

- DuckDB / SQLite の初期化は起動時に自動で行われます（必要なテーブル・マイグレーションを実行）。ただしファイルの書き込み権限やパスを事前に確認してください。

- OpenAI / API 呼び出し
  - レート制限や一時的なエラーに対して指数バックオフでリトライする実装ですが、API キーが未設定の場合は例外になります。
  - AI 機能は外部 API を使うため、コストとレイテンシに注意してください。

- ログ
  - ログはデフォルトで stdout（コンソール）と logs/<app>.log（日次ローテーション）に出力されます。ログディレクトリが作れない場合はファイル出力をスキップしてコンソールのみになります。

---

## ディレクトリ構成（抜粋）

以下は主要ファイル・モジュールの構成（`src/kabusys` 配下を抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings 管理、.env 自動ロード
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring 起動スクリプト

  - ai/
    - news_nlp.py              — ニュース NLP（OpenAI）によるスコアリング
    - regime_detector.py       — 市場レジーム判定

  - monitoring/
    - monitoring_db.py         — SQLite 監視 DB 永続化層
    - system_monitor.py        — システム状態 / データ鮮度監視
    - risk_monitor.py          — ドローダウン / ポジション監視
    - trade_monitor.py         — （trade関連監視 — 実装ファイル参照）
    - monitoring_engine.py     — モニター集約、アラート連携
    - kill_switch.py           — Kill Switch ロジック
    - alert_manager.py         — （アラート送信管理 — 実装ファイル参照）

  - execution/                  — Execution 関連（Engine, OrderManager, BrokerFactory 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - tools/
    - paper_verification_report.py

  - utils/
    - logging_setup.py         — ログセットアップ
    - process_priority.py      — 優先度 / CPU affinity ユーティリティ

---

## 追加情報 / 開発メモ

- DuckDB を分析・研究用途に用いているため、prices_daily / raw_financials / raw_news 等のテーブルが前提です。データ準備は別途行ってください。
- 設計メモ（ソース内ドキュメント）を参照すると、各モジュールの想定振る舞いや注意点（例: レジーム判定のスケール、PAPER_FILL_MODE の有効値等）が詳述されています。
- テスト・CI は別途整備を推奨します（現在 README にテスト手順は含まれていません）。

---

必要であれば、この README を英語翻訳したり、起動スクリプトごとのより詳細な運用手順（systemd / supervisor 用のユニットファイル例や Docker 化手順）を追加できます。どの情報を優先して追記しますか？