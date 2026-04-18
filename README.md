# KabuSys

日本株向け自動売買システム（KabuSys）のリポジトリ向け README。  
このドキュメントはリポジトリ内の主要コンポーネントの概要、セットアップ手順、実行方法、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python ベースのシステムです。  
主な機能は次の通りです。

- 市場データを用いたファクター計算（モメンタム、バリュー、ボラティリティなど）
- ポートフォリオ構築（候補選定、重み算出、ポジションサイズ決定、セクター上限適用）
- Paper Trading（モックブローカー）と Live（実口座）を切り替え可能な実行エンジン
- システム稼働監視・トレード監視・リスク監視と Kill Switch（停止フラグ）
- ニュースの NLP（OpenAI） を用いたセンチメント評価とレジーム判定
- Paper Trading の検証レポート生成ツール
- 設定ウィザード（.env 生成）・設定検証ツール

設計方針として、DB（DuckDB / SQLite）や OpenAI の呼び出しは明示的に分離され、ルックアヘッドバイアスを避ける実装を重視しています。

---

## 主な機能一覧

- 設定管理:
  - .env 自動読み込み（プロジェクトルートに基づく）
  - config_setup による対話式 .env 作成
  - validate_config による起動前チェック（--strict オプションあり）
- 実行エンジン:
  - run_execution.py：ExecutionEngine 起動。KABUSYS_ENV=paper_trading 時は MockBroker を使用し paper_trading DB に分離。
- 監視:
  - run_monitoring.py：SystemMonitor を定期ポーリング。MONITOR_POLL_INTERVAL で間隔変更可能（デフォルト 60 秒）。
  - MonitoringEngine による複数モニタの統合運用、Kill Switch 評価、アラート発行
- リサーチ:
  - factor_research: モメンタム / ボラティリティ / バリュー計算（DuckDB 上の prices_daily など参照）
  - feature_exploration: 将来リターン・IC・統計サマリー
- ポートフォリオ構築:
  - portfolio_builder: 候補選定・重み計算
  - position_sizing: 発注株数計算（単元丸め・リスク/キャッシュ制約考慮）
  - risk_adjustment: セクター制限・レジーム乗数
- AI 関連:
  - ai.news_nlp: raw_news を OpenAI でスコア化し ai_scores に書き込み
  - ai.regime_detector: ETF の MA 乖離 + マクロニュースでレジーム判定を行い market_regime に書込
- ツール:
  - tools.paper_verification_report: Paper Trading の検証レポート生成

---

## 必要条件（概略）

- Python 3.10 以上を推奨（typing の記法等に依存）
- 必須パッケージ（一例）
  - duckdb
  - psutil
  - openai
  - その他：標準ライブラリ（sqlite3 等）
- 任意（YAML 検証を行う場合）
  - PyYAML

（プロジェクトの pyproject.toml / requirements があればそちらを優先してください）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作る（例）
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

2. 依存ライブラリをインストール
   - 例（必要なライブラリをまとめてインストールする場合）:
     ```bash
     pip install duckdb psutil openai
     # YAML 検証をしたい場合
     pip install pyyaml
     ```
   - 実際の依存はプロジェクトの管理ファイルで確認してください。

3. .env を用意する
   - 対話式ウィザードで生成:
     ```bash
     python -m kabusys.config_setup
     ```
   - 手動で作成する場合は `.env.example` を参照して `.env` を作成してください。
   - 自動読み込みはデフォルトで有効です。自動読み込みを無効にするには:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. 設定検証（起動前チェック）
   ```bash
   python -m kabusys.validate_config
   # --strict を付けると警告も失敗扱いになります
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ / ログディレクトリの確認
   - デフォルトの DB / ログパスは環境変数で上書き可能です（例: DUCKDB_PATH, SQLITE_PATH, LOG_DIR）。
   - ログはデフォルトで `logs/` に日次ローテートで出力されます。

---

## 環境変数（主なもの）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用切替:
  - KABUSYS_ENV: development | paper_trading | live
- DB / ファイル:
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用、デフォルト: data/paper_trading.db）
  - PID_FILE_PATH, KILL_FLAG_PATH
- ログ:
  - LOG_LEVEL（DEBUG/INFO/...）
  - LOG_DIR
- OpenAI:
  - OPENAI_API_KEY
- その他:
  - PAPER_FILL_MODE（paper_trading の約定モード: instant | partial | never | reject）
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒））
  - KILL_FLAG_CLEAR_ON_START（本番環境で Kill Flag を自動クリアするか。0 推奨）

詳しくは `kabusys.config.Settings` のプロパティの説明を参照してください。

---

## 使い方（主要エントリポイント）

- 設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（ExecutionEngine）
  - Paper Trading（例）
    ```bash
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
    - paper_trading 時は MockBroker を使い、デフォルトで `data/paper_trading.db` に記録されます（本番 DB と分離）。
  - Live（実発注）
    ```bash
    export KABUSYS_ENV=live
    python -m kabusys.run_execution
    ```

  - run_execution は起動時に `data/stop_requested.flag` の存在を確認し、存在する場合は起動をスキップします。停止はフラグファイルの作成により行います。

- 監視プロセス起動（SystemMonitor）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を指定できます（デフォルト 60 秒）。
  - 監視は常に本番 sqlite_path を参照（環境にかかわらず monitoring は production DB を使用する設計）。

- Paper Trading 検証レポート生成
  ```bash
  # デフォルト DB path は data/paper_trading.db
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 関連（プログラムから呼び出す場合）
  - ニューススコアリング:
    ```python
    from kabusys.ai import score_news
    # duckdb_conn: duckdb connection, target_date: datetime.date
    n = score_news(duckdb_conn, target_date, api_key="xxx")
    ```
  - レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="xxx")
    ```

---

## 運用上の注意

- Kill Switch / Stop フラグ:
  - `data/kill.flag` は ExecutionEngine に対する致命停止シグナル（kill）として用いられます。KillSwitch は risk 条件を満たすとこのファイルを書き込みます。
  - `data/stop_requested.flag` は起動スクリプト（run_execution / run_monitoring）がループを終了するために監視するファイルです。
- PID ファイル:
  - ExecutionEngine は起動時に PID ファイルを書き込みます（設定によりパス変更可）。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は必要なテーブルとカラムを冪等に作成・マイグレーションします。
- OpenAI API:
  - OpenAI の呼び出しはリトライ・バックオフ・レスポンス検証を備えていますが、API キーは `.env` または引数で確実に設定してください。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主要ファイル・ディレクトリです（省略あり）。実際のリポジトリではさらにファイルが存在する可能性があります。

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / 設定管理（Settings）
  - config_setup.py             — .env 対話式ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading レポート生成
  - ai/
    - __init__.py
    - news_nlp.py               — ニュース NLP（OpenAI）による ai_scores 書込
    - regime_detector.py        — 市場レジーム判定
  - monitoring/
    - monitoring_db.py          — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - monitoring_engine.py      — 各モニタを束ねる実行ループ
    - system_monitor.py         — システム状態 & データ鮮度監視
    - trade_monitor.py          — （省略: トレード監視ロジック）
    - risk_monitor.py           — ドローダウン・ポジション上限監視
    - kill_switch.py            — kill.flag 管理
    - alert_manager.py          — （省略: アラート送信ロジック）
  - execution/
    - execution_engine.py       — ExecutionEngine 実装（起動 / セッション管理）
    - order_manager.py          — 発注管理
    - order_repository.py       — 注文永続化（SQLite）
    - broker_factory.py         — BrokerClient の生成（Mock/実クライアント）
    - reconciler.py             — 注文状態整合処理
    - risk_manager.py           — リスク制御ロジック
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/
    - pipeline.py               — データパイプライン（prices_daily など） ※参照あり
    - stats.py                  — zscore 正規化などユーティリティ
  - utils/
    - logging_setup.py          — 統一ログ設定
    - process_priority.py       — プロセス優先度 / CPU affinity
    - __init__.py

---

## 最低限の .env（例）

以下は最小構成の例（実際には必須トークンは秘匿してください）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=your_openai_api_key
```

`.env` は決してリポジトリにコミットしないでください。

---

## トラブルシューティング（よくある事項）

- .env が読み込まれない:
  - プロジェクトルートが検出されない（.git / pyproject.toml がない）場合、自動ロードはスキップされます。`KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロードを無効化できます。
- OpenAI 呼び出しで失敗する:
  - API キー設定を確認。ネットワーク / レート制限は内部でリトライ処理がありますが、繰り返す場合はエラーログを確認してください。
- 実行時に DB 関連エラー:
  - パスの親ディレクトリが存在しないと警告が出ます。`data/` ディレクトリ等を作成してください。`validate_config` や logging_setup が警告を出します。
- 監視と実行が同じ SQLite を参照しているか確認:
  - run_monitoring は「監視 DB（sqlite_path）」を常に使用します。paper_trading 時の Execution は `paper_sqlite_path` を使用して本番 DB から分離されます。

---

## 貢献 / 開発メモ

- 新しい機能や修正はローカルでユニットテスト／手動テストを行い、設定検証ツールで問題がないことを確認してください。
- ロギングは共通で設定されます（kabusys.utils.logging_setup.setup_logging）。起動スクリプトは必ず最初に呼び出してください。
- プロセス優先度設定はプラットフォーム差分を吸収しており、psutil が必要です（kabusys.utils.process_priority）。

---

この README はソース中のドキュメンテーション文字列とモジュール構成に基づいて作成しました。実運用の前に必ず `python -m kabusys.validate_config` で設定を検証し、必要に応じて `.env` を `python -m kabusys.config_setup` で生成してください。質問や追加のドキュメント要望があれば教えてください。