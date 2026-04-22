# KabuSys

日本株自動売買システム（KabuSys）のドキュメント README（日本語）

概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムの骨格（エンジン、監視、ポートフォリオ構築、リサーチ、AI 補助）です。主要コンポーネントは以下の通りです。

- ExecutionEngine：発注・注文管理・リスク管理を担うエンジン（本番 / ペーパートレード両対応）
- Monitoring：システム状態、注文・リスク監視、Kill Switch を含む監視フレームワーク
- Portfolio：銘柄選定、重み計算、ポジションサイズ決定、セクター上限等の純粋関数群
- Research：ファクター計算、将来リターン、IC 評価などの研究用ユーティリティ（DuckDB を使用）
- AI：ニュース NLP によるセンチメント（OpenAI）や市場レジーム判定（LLM を利用可能）
- Tools：ペーパートレード検証レポートなどのユーティリティスクリプト
- utils：ログ設定・プロセス優先度設定など共通ユーティリティ
- 設定管理：.env 対話ウィザード（config_setup）と起動前検証（validate_config）

設計上の注意点：
- 設定は .env ファイルまたは環境変数で管理されます（自動ロード機能あり）。
- DuckDB は分析用 DB、SQLite は監視 / 発注ログ用に使用します。ペーパートレードは本番 DB から完全に分離された専用 SQLite を使用します。
- OpenAI（ニュース NLP / レジーム判定）を利用する機能は API キーが必要です（環境変数 OPENAI_API_KEY）。

---

## 機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
- 起動前設定検証ツール（python -m kabusys.validate_config）
- ExecutionEngine（本番 / ペーパートレード切替）
  - BrokerFactory によるブローカークライアント生成（paper_trading 時は Mock）
  - OrderManager / OrderRepository / RiskManager / Reconciler を組み合わせた実行処理
  - PID ファイル管理・stop フラグの監視
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、プロセス生存確認
  - TradeMonitor: 注文滞留や約定異常の検出（trade_logs を参照）
  - RiskMonitor: ドローダウン・ポジション上限の監視とリスクログ記録
  - KillSwitch: 条件に応じて data/kill.flag を書き込む（ExecutionEngine 停止トリガ）
  - AlertManager（LINE など）と組み合わせて通知可能（LINE トークン利用）
- Portfolio（純粋関数）
  - 銘柄候補選定、等金額/スコア加重重み、ポジションサイズ算出、セクター上限、レジーム乗数
- Research
  - momentum / volatility / value 等のファクター計算（DuckDB）
  - 将来リターン、IC（Spearman）計算、ファクター統計サマリ
- AI
  - news_nlp: raw_news から銘柄ごとに LLM でセンチメントを算出し ai_scores に書き込み
  - regime_detector: ETF の MA とマクロニュースの LLM 判定を合成して market_regime に記録
- Tools
  - paper_verification_report: ペーパートレード結果の検証・レポート生成

---

## セットアップ手順（開発 / ローカル向け）

前提
- Python 3.10 以上（型注釈や union 演算子 `|` を使用）
- Git（推奨）

1. リポジトリをクローン／チェックアウト
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   ※ プロジェクトに requirements.txt がない場合、主要依存は下記をインストールしてください。
   ```
   pip install duckdb psutil openai pyyaml
   ```
   - duckdb: リサーチ / AI 関連の DB 操作
   - psutil: プロセス / システム情報取得（monitoring, process_priority）
   - openai: LLM 呼び出し（news_nlp, regime_detector）
   - pyyaml: config/*.yaml の検証（optional）

4. .env の初期作成
   対話式ウィザードで .env を作成・更新できます：
   ```
   python -m kabusys.config_setup
   ```
   - 必須環境変数（最低限設定するもの）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - ペーパートレード / 本番の選択は KABUSYS_ENV（development / paper_trading / live）

5. 設定検証
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict   # 警告を FAIL として扱う
   ```

6. データディレクトリ（logs や data）は起動時に自動作成されますが、手動で作ることもできます：
   ```
   mkdir -p data logs
   ```

注意:
- OpenAI を利用する機能を実行する場合は環境変数 OPENAI_API_KEY を設定してください。
- ペーパートレード時は PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に書かれます（本番 DB と分離）。

---

## 使い方（主要コマンド）

- ExecutionEngine を起動する
  - 実行（モジュールとして）
    ```
    python -m kabusys.run_execution
    ```
  - KABUSYS_ENV によって動作が変わります：
    - paper_trading: MockBrokerClient を利用し、data/paper_trading.db に記録
    - live: 本番ブローカーを利用（要 kabu API 設定）
  - 停止方法：プロセスに SIGINT（Ctrl+C）を送るか、data/stop_requested.flag を作成します（run_execution はこのフラグを監視して終了）。

- Monitoring を起動する
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視テーブルを記録します。
  - 停止方法：Ctrl+C または data/stop_requested.flag の作成。

- 環境設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルトの DB パスは環境変数 PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）

- AI 機能（コードレベル呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらを CLI から直接呼ぶラッパーは含まれていません（将来的に追加可能）。

ログ:
- ログはデフォルトで stdout とファイル（logs/<app_name>.log）に出力されます。
- LOG_DIR / LOG_LEVEL 環境変数で変更可能。

停止フラグ / Kill Switch:
- data/kill.flag: KillSwitch が書き込むと ExecutionEngine に停止シグナル（手動クリア推奨）
- data/stop_requested.flag: run_* スクリプトがポーリングループで参照する停止フラグ（外部から安全に停止可能）

---

## 重要な環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV (development | paper_trading | live)  — デフォルト: development

- DB パス
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — 監視 DB（monitoring.db）デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 DB（paper_trading.db）

- ログ / デバッグ
  - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
  - LOG_DIR — ログ保存先（デフォルト logs/）

- AI
  - OPENAI_API_KEY — OpenAI API キー（news_nlp, regime_detector 利用時）

- Monitoring 関連
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
  - PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト data/execution.pid）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0。production では 0 推奨）

- Paper trading 動作
  - PAPER_FILL_MODE — instant | partial | never | reject（デフォルト instant）

---

## ディレクトリ構成

（リポジトリのルートに `pyproject.toml` / `.git` 等を想定）

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / Settings クラス、自動 .env ロード
    - config_setup.py           — .env 対話ウィザード
    - validate_config.py        — 起動前設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — Monitoring 起動スクリプト
    - utils/
      - logging_setup.py        — 統一的なログ設定（stdout + 日次ローテートファイル）
      - process_priority.py     — プロセス優先度・CPU affinity 設定
    - execution/                — 実行エンジン関連（Engine, OrderManager, RiskManager 等）
      - __init__.py
      - broker_factory.py
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - monitoring/
      - monitoring_db.py        — SQLite スキーマ・永続化ヘルパ
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
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
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - data/                     — 実行時に作成される（data/*.db / flags / pid 等）
    - logs/                     — ログファイル（デフォルト）
    - tools/
      - paper_verification_report.py
      - __init__.py
- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  (一部ファイルは自動生成スクリプトやテンプレートを利用)

---

## 開発メモ / 注意点

- ペーパートレードは本番データベースと完全に分離されています（paper_sqlite_path を使用）。安全に動作確認が行えます。
- OpenAI 連携は API コストとレイテンシに留意してください。news_nlp / regime_detector はバックオフ・リトライやフェイルセーフ（失敗時はスコア 0 など）を組み込んでいますが、運用設計が必要です。
- monitoring は監視ログ・リスクイベントを SQLite に永続化します。監視のアラートは AlertManager 経由で LINE などに通知できます（トークン未設定の場合は通知されません）。
- ローカル開発時でも .env を絶対に Git にコミットしないでください（config_setup のファイルヘッダに注意書きあり）。
- DuckDB / SQLite のスキーマ変更や列追加のためのマイグレーション処理が monitoring_db に組み込まれています（簡易マイグレーション）。

---

## よくある操作例

- .env を対話式で作る
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（問題がある場合はメッセージが出ます）
  ```
  python -m kabusys.validate_config
  ```

- ペーパートレード実行（先に .env で KABUSYS_ENV=paper_trading を設定）
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- 監視プロセス起動（デフォルト 60 秒毎）
  ```
  python -m kabusys.run_monitoring
  ```

- ペーパートレード検証レポート作成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば、README に以下を追加できます：
- 実際の .env.example（テンプレート）のサンプル
- systemd / Supervisor / Docker Compose 用の起動例
- 各モジュール（ExecutionEngine, RiskManager, TradeMonitor 等）の詳細設計ドキュメントリンク

追加で欲しい内容や書き換え希望（例: systemd ユニットのサンプル、Dockerfile 例、より詳細な API キー管理方針）があれば教えてください。