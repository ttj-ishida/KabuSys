# KabuSys

バージョン: 0.1.0

KabuSys は日本株自動売買システムのコードベースです。取引エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI を用いたニュース解析などのコンポーネントを含みます。本 README はローカル開発 / デプロイのための概要、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

注意: この README はソースコードから抽出した情報に基づいており、実行前に必ず `python -m kabusys.validate_config` で設定検証を行ってください。

---

## プロジェクト概要

- 日本株自動売買プラットフォームの構成要素（発注エンジン、監視、リスク管理、ポートフォリオ構築、リサーチ、AI ニュース解析）を含むライブラリ兼実行スクリプト群。
- DuckDB を分析用途に、SQLite を監視・発注ログ等の永続化に使用。
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント解析 / マクロセンチメント解析の機能を持つ（APIキー必須）。
- 開発 / ペーパートレード / 本番（live）モードを環境変数 `KABUSYS_ENV` で切り替え可能。paper_trading モードでは MockBroker を用い、本番 DB とは分離された専用 SQLite（デフォルト: `data/paper_trading.db`）へ記録される。

---

## 主な機能一覧

- Execution（実行エンジン）
  - ブローカークライアント（実口座 or Mock）による発注管理
  - OrderManager / RiskManager / Reconciler を組み合わせた ExecutionEngine
  - PID / stop フラグで安全停止

- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/Disk、プロセス状態、データ鮮度検査
  - TradeMonitor / RiskMonitor: 注文滞留、約定異常、ドローダウン・ポジション上限監視
  - KillSwitch: 条件に応じて `data/kill.flag` を書き込み ExecutionEngine に停止指示
  - MonitoringEngine: 各モニタを束ねたポーリングループ
  - 永続化: SQLite 上の監視テーブル（`monitoring_db.init_monitoring_db`）

- ポートフォリオ構築（純粋関数群）
  - 候補選定、等重/スコア重みの計算、リスク調整（セクターキャップ）、株数決定（単元丸め・aggregate cap）

- リサーチ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）等の統計解析ユーティリティ

- AI（ニュース NLP / レジーム検出）
  - raw_news を LLM でセンチメント化して `ai_scores` に書き込み（score_news）
  - ETF 1321 の MA とマクロニュースを合成して市場レジーム判定（score_regime）
  - API 呼び出しはリトライやフェイルオープンの設計が施されています

- ツール
  - Paper Trading の検証レポート生成スクリプト（期間指定可）

- ユーティリティ
  - ロギングセットアップ（コンソール + 日次ローテーション）
  - プロセス優先度 / CPU アフィニティ設定
  - .env 対話式ウィザードと設定検証 CLI

---

## 前提 / 必要要件

- Python 3.10+
- 標準モジュール: sqlite3, threading, logging, pathlib, datetime 等
- 外部ライブラリ（最低限推奨）
  - duckdb
  - psutil
  - openai （AI 機能を使う場合）
  - PyYAML（設定検証で config/*.yaml を検証したい場合。必須ではない）
- （任意）仮想環境の使用を推奨

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil openai pyyaml
```

※ requirements.txt は付属していないため、上記パッケージを必要に応じてインストールしてください。

---

## 環境変数（主なもの）

- 基本
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

- API キー / 認証
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - OPENAI_API_KEY（AI 機能利用時）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知）

- データベース / パス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 専用 DB。デフォルト: data/paper_trading.db）

- 監視関連
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
  - MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト 60）

その他は `.env.example` を参照し `.env` を作成してください。

---

## セットアップ手順（推奨ワークフロー）

1. リポジトリをクローン、仮想環境を作成して依存をインストール。
2. 対話式で `.env` を作成:
   ```bash
   python -m kabusys.config_setup
   ```
   - ウィザードで必要な値を入力します（シークレットはマスクされます）。
3. 設定検証:
   ```bash
   python -m kabusys.validate_config
   # 警告も厳密に扱う場合:
   python -m kabusys.validate_config --strict
   ```
   - 必須環境変数が揃っているか、DB パスの親ディレクトリ存在、config/*.yaml のパース（PyYAML があれば）などを確認します。
4. データディレクトリ作成、権限確認:
   - デフォルトは `data/`（SQLite、PID、flag）と `logs/`（ログ）を使用します。実行前にこれらが作成されるか、ログセットアップ時に自動作成されます。

---

## 使い方（主な実行コマンド）

- 実行エンジン起動（ExecutionEngine）
  - paper_trading の場合は MockBroker を使い、paper_trading 用 DB に記録される。
  - コマンド:
    ```bash
    python -m kabusys.run_execution
    ```
  - 停止は `data/stop_requested.flag` を作成することでスレッドに停止指示されます（stop flag）。

- 監視ループ起動（SystemMonitor のポーリング）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - コマンド:
    ```bash
    # 例: 30 秒間隔
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視は本番 sqlite_path を使用（環境にかかわらず `SQLITE_PATH` を参照）。

- 設定ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成:
  ```bash
  # 全期間（DB の全期間）
  python -m kabusys.tools.paper_verification_report
  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # 別 DB 指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 機能（ライブラリ呼び出し例、スクリプトは公開関数を提供）
  - ニューススコアリング（コード内関数を直接呼ぶ場合）:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OpenAI API キーが必要（引数または OPENAI_API_KEY 環境変数）。

---

## 運用上の注意点

- stop フラグ / kill フラグ
  - 実行停止用のフラグ: `data/stop_requested.flag`（run_execution / run_monitoring で監視）
  - Kill Switch（監視が発動すると `data/kill.flag` を書き込む）: ExecutionEngine 起動時に `KILL_FLAG_CLEAR_ON_START=1` が設定されていると自動クリアされる（本番では 0 を推奨）。

- データ分離
  - paper_trading モードでは本番 SQLite を用いず `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）を使用するため、データは分離されます。

- ログ
  - デフォルトログディレクトリ: `logs/`
  - ログファイル名例: `logs/execution.log`, `logs/monitoring.log`
  - 日次ローテーション（30 日保持）

- 権限
  - プロセス優先度設定 / CPU affinity はプラットフォーム制約や権限により失敗する可能性があります。多くの関数は失敗時に警告ログでスキップします。

- OpenAI API
  - レスポンスの検証・トリミング・リトライロジックが含まれますが、API 使用に伴うコストやレート制限に注意してください。

---

## ディレクトリ構成（主要ファイル / モジュールと簡単な説明）

（以下は `src/kabusys` 配下の主要ファイル/パッケージの概要）

- kabusys/
  - __init__.py
    - __version__ 定義
  - config.py
    - 環境変数・設定読み込みロジック（.env 自動ロード、Settings クラス）
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（KABUSYS_ENV による切替）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 可変）
  - utils/
    - logging_setup.py: ログ設定ユーティリティ（stdout + 日次ファイル）
    - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
    - 発注ロジック、リスク管理、ブローカークライアント生成等（実装ファイル群）
  - monitoring/
    - monitoring_db.py: SQLite 上の監視テーブル作成・読み書き
    - system_monitor.py: システム状態・データ鮮度監視
    - trade_monitor.py: （注文ログ監視。参照あり）
    - risk_monitor.py: ドローダウン・ポジション上限監視
    - kill_switch.py: kill.flag 管理
    - monitoring_engine.py: 各モニタを束ねるループロジック
    - alert_manager.py: （アラート送信ロジック。参照あり）
  - portfolio/
    - portfolio_builder.py: 候補選定・重み計算
    - position_sizing.py: 株数計算・aggregate cap・単元丸め
    - risk_adjustment.py: セクターキャップ・レジーム乗数
  - research/
    - factor_research.py: Momentum / Volatility / Value ファクター計算（DuckDB）
    - feature_exploration.py: 将来リターン計算・IC・統計サマリー等
  - ai/
    - news_nlp.py: ニュースを LLM に送って銘柄ごとにセンチメントを算出・書き込み
    - regime_detector.py: MA200 とマクロニュースを合成して市場レジーム判定
  - tools/
    - paper_verification_report.py: Paper Trading の検証レポート生成
  - data/ (実行時に作成する想定)
    - *.db, pid/flag ファイルなど

---

## 開発・拡張のヒント

- DuckDB に入っているテーブル（prices_daily / raw_financials / raw_news / ai_scores / market_regime 等）を整備すると、研究・AI 機能が利用できるようになります。
- AI コールは単体テストしやすいように内部呼び出し関数を patch/モックする設計になっています（例: news_nlp._call_openai_api の差し替え）。
- `monitoring_db.init_monitoring_db` は冪等でテーブル・マイグレーションを担います。既存 DB に新しいカラムがない場合は自動追加処理があります。

---

以上です。まずは .env を作成して `python -m kabusys.validate_config` で問題ないことを確認してから、`python -m kabusys.run_execution` / `python -m kabusys.run_monitoring` を順に試してください。必要があれば README を補足しますので、特に載せてほしいコマンドや運用シナリオがあれば教えてください。