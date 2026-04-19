# KabuSys

日本株向け自動売買システムのコアライブラリ（コードベースの抜粋）。  
この README はリポジトリ内の主要なスクリプト／モジュールを説明し、ローカルでのセットアップと起動方法、主要機能、ディレクトリ構成を日本語でまとめたものです。

なお、実際の運用では `.env` に機密情報（API トークン等）を保存し、Git にコミットしないでください。

---

## プロジェクト概要

KabuSys は以下のような機能を持つモジュール群から構成される自動売買システムのコアです。

- 実行エンジン（ExecutionEngine）用スクリプトと依存コンポーネント（ブローカークライアント、オーダー管理、リスク管理など）
- 監視（Monitoring）コンポーネント（SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、AlertManager 等）
- ポートフォリオ構築ロジック（候補選定・重み計算・ポジションサイジング・セクター制約）
- リサーチ／ファクター計算（DuckDB を用いたファクター計算・特徴量解析）
- AI（OpenAI）を使ったニュースの NLP スコアリングや市場レジーム判定
- 設定ウィザード・設定検証ツール・ペーパートレード検証レポートなどの CLI ツール

設計上のポイント：
- paper_trading（ペーパートレード）と live（本番）は DB を分離しているため、ペーパー環境は本番 DB に影響しない。
- .env ベースの設定管理。自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（無効化可）。
- DuckDB を分析用 DB、SQLite を監視・オーダー履歴などの永続化に使用。
- OpenAI を使う機能は API キーが必要。失敗時は安全にフォールバックする設計。

---

## 主な機能一覧

- 実行エンジン起動（run_execution.py）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - MockBroker を用いたペーパートレード（データは data/paper_trading.db）
  - リスク管理（max_position_pct, max_utilization, circuit breaker 等）
- 監視（run_monitoring.py / MonitoringEngine）
  - システムリソース監視（CPU / メモリ / ディスク）
  - データ鮮度チェック、実行プロセスの検出
  - リスク監視（ドローダウン、ポジション上限）
  - Kill Switch（条件発生時に data/kill.flag を書き込み ExecutionEngine を停止）
- ポートフォリオ構築
  - 候補選定（score/order_rank ベース）
  - 重み計算（等金額 / スコア加重）
  - ポジションサイジング（risk_based / equal / score）
  - セクター上限適用、レジーム乗数（bull/neutral/bear）
- リサーチ
  - momentum / volatility / value 等のファクター計算（DuckDB）
  - 将来リターンの計算、IC（情報係数）計算、統計要約
- AI（OpenAI）
  - ニュース記事を LLM（gpt-4o-mini）でセンチメント化して ai_scores に保存
  - マクロニュース＋ETF MA200 乖離から市場レジームを判定して market_regime に書き込み
  - API 呼び出しはリトライ・バックオフを実装し、失敗時はフェイルセーフで継続
- ユーティリティ
  - .env 対話ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ペーパートレード検証レポート（tools/paper_verification_report.py）
  - ログ設定ユーティリティ（utils/logging_setup.py）
  - プロセス優先度設定（utils/process_priority.py）

---

## 必要環境 / 依存パッケージ（例）

推奨 Python バージョン: 3.9+

主な依存ライブラリ:
- duckdb
- psutil
- openai
- PyYAML（config 検証時に YAML 内容チェックを行いたい場合に必要）

インストール例:
```
pip install duckdb psutil openai PyYAML
```

（プロジェクトに requirements.txt があればそれを使ってください）

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. Python 環境を用意（仮想環境推奨）
3. 必要パッケージをインストール（上記参照）
4. .env を作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - または手動で `.env` を作成（例は config_setup.py の出力フォーマット参照）
5. 設定検証:
   ```
   python -m kabusys.validate_config
   ```
   `--strict` を付けると警告もエラー扱いになります。
6. ログディレクトリはデフォルトで `logs/` に作成されます（必要に応じて `LOG_DIR` 環境変数で変更）。

重要な環境変数（主なもの）:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- OPENAI_API_KEY — AI 機能を使う場合に必要
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- LOG_DIR — ログ保存先（デフォルト: logs/）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）

自動 .env 読み込みを無効化する（テスト等）:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 使い方（起動と CLI）

- Execution Engine を起動（本番 or paper_trading は KABUSYS_ENV に依存）:
  ```
  python -m kabusys.run_execution
  ```
  起動時に `data/stop_requested.flag` が存在すると起動をスキップします。実行中は `data/execution.pid` に PID を書きます。

- Monitoring を起動:
  ```
  python -m kabusys.run_monitoring
  ```
  デフォルトで SQLite の監視 DB（Settings.sqlite_path）を使用してポーリングします。`MONITOR_POLL_INTERVAL` で秒数を変更可能（例: 30 秒）。

- 設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポートを生成:
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（例: ニューススコア付け）:
  - OpenAI API キーが必要です（環境変数 OPENAI_API_KEY または引数渡し）。
  - モジュール関数を呼ぶ例（スクリプトから）:
    ```py
    from kabusys.ai.news_nlp import score_news
    # duckdb_conn は duckdb.connect(...)
    score_news(duckdb_conn, target_date, api_key="sk-...")
    ```

- ログ:
  - デフォルト: console（stdout）と日次ローテートで `logs/<app_name>.log`（30日分保持）
  - ログ設定は `kabusys.utils.logging_setup.setup_logging()` を各起動スクリプトで呼んでいます。

---

## 注意点・運用上のヒント

- KABUSYS_ENV が `paper_trading` の場合、Execution は専用の PAPER_TRADING_SQLITE_PATH に記録され本番 DB とは分離されます。安全な開発に有用です。
- Monitoring はコード上「環境にかかわらず本番 sqlite_path を使用」する箇所があるため（run_monitoring.py のコメント）、運用設計時に注意してください。
- Kill Switch: RiskMonitor 等が条件を満たすと `data/kill.flag` を書き込みます。ExecutionEngine は起動時にこれを検出し、また Monitoring からの通知で停止できます。`KILL_FLAG_CLEAR_ON_START` が `1` のときは起動時に自動クリアされますが、本番では `0` を推奨します（validate_config でも警告）。
- OpenAI 呼び出しはエラー・レート制限を考慮してリトライとバックオフを実装していますが、API 利用料に注意してください。
- config/ 以下の YAML ファイルは設定ファイルの雛形・参照に使います。`validate_config` は PyYAML が無いと内容チェックをスキップしますが、存在チェックは行います。
- プロセス優先度設定（utils/process_priority.py）は psutil を利用します。環境によってはアクセス権限で失敗することがあります（警告ログのみ）。

---

## ディレクトリ構成（抜粋）

リポジトリ内の主要ファイル・ディレクトリ構成の例（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定読み込み・Settings クラス
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py        — （コード抜粋では省略）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        — （アラート送信ロジック：LINE など）
  - execution/
    - execution_engine.py     — ExecutionEngine（本体は抜粋外）
    - broker_factory.py       — ブローカークライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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
  - monitoring/                — 監視関連（上記）
  - tools/
    - paper_verification_report.py
  - data/                      — 実行時生成の DB / flag / pid（デフォルト）
  - logs/                      — デフォルトログ出力先（実行時に作成）

（実際のリポジトリにはさらに modules や data pipeline、strategy 等の実装が含まれます）

---

## トラブルシューティング

- 「環境変数が未設定です」エラー:
  - 必須の `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD` などが `.env` に設定されているか確認してください。
  - `python -m kabusys.config_setup` で .env を作成できます。
- PyYAML が無い:
  - `validate_config` 実行時に YAML パースチェックを行えません。`pip install PyYAML` をして再度実行してください。
- OpenAI API 呼び出しで失敗（RateLimit 等）:
  - rate limit・ネットワーク障害はコード内でリトライしますが、API キー、ネットワーク、使用制限（料金）の確認をしてください。
- ログファイルが作れない:
  - `LOG_DIR` の書き込み権限を確認、または `setup_logging(..., log_dir=Path("some/dir"))` で明示的に指定してください。

---

README は以上です。必要であれば以下の追記を行います：
- より詳細なコマンド例（systemd / cron での起動）、  
- 各設定ファイル（config/*.yaml）の項目説明、  
- テストの実行方法（ユニットテスト・モックの方針）など。必要であれば教えてください。