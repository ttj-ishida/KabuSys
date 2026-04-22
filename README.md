# KabuSys — README

日本株自動売買システムの一部（ライブラリ・ランナースクリプト・ツール群）。  
このリポジトリには、実運用/ペーパートレード用の Execution 起動スクリプト、監視（Monitoring）周り、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント／レジーム判定）などのモジュールが含まれます。

以下はこのコードベースの概要、主要機能、セットアップ手順、使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要
- 目的：日本株の自動売買システム（Execution エンジン）とそれを支援するモジュール群（監視、リスク管理、ポートフォリオ構築、リサーチ、AI ニュース解析など）。
- 設計方針：
  - 本番用 / ペーパートレード用を環境変数 `KABUSYS_ENV` で切り替え可能（development / paper_trading / live）。
  - 設定は .env ファイルまたは環境変数で与える（自動ロード機能あり）。.env を生成するウィザードあり。
  - DuckDB を分析・リサーチ用に、SQLite を監視・発注ログ用に使用。
  - OpenAI を利用する AI モジュールは API キーが必須（環境変数 `OPENAI_API_KEY`）。

---

## 主な機能一覧
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（`KABUSYS_ENV=paper_trading` では MockBroker を利用して専用 DB に記録）
  - run_monitoring.py: SystemMonitor をポーリングして監視ログを記録
- 設定管理
  - config_setup.py: 対話式 .env ウィザード（初期設定）
  - validate_config.py: 起動前の設定検証ツール（YAML ファイル存在確認や環境変数検査）
- 監視（monitoring）
  - monitoring_db.py: SQLite ベースの永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - monitoring_engine.py / system_monitor.py / risk_monitor.py / trade_monitor.py / kill_switch.py / alert_manager（監視ループおよびアラート/Kill Switch）
- Execution 周辺（概要）
  - ExecutionEngine 起動、注文管理、リスク管理、リコンシリエーション（実装は execution モジュール参照）
- ポートフォリオ構築（純粋関数）
  - 選定・重み付け: select_candidates, calc_equal_weights, calc_score_weights
  - リスク調整: apply_sector_cap, calc_regime_multiplier
  - 目標株数計算: calc_position_sizes
- リサーチ
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB を使用）
  - feature_exploration: 将来リターン、IC、統計サマリー等
- AI
  - news_nlp: raw_news を OpenAI に投げてセンチメントスコアを ai_scores テーブルへ書き込み
  - regime_detector: ETF + マクロニュースから日次レジーム（bull/neutral/bear）判定・登録
- ツール
  - tools/paper_verification_report.py: ペーパートレードの検証レポート生成（稼働率、成功率、レイテンシ等）

---

## セットアップ手順（開発/ローカル向け）
1. リポジトリをクローンして作業ディレクトリに移動:
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成・アクティベート:
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要なパッケージをインストール（最低限の推奨パッケージ）:
   ```
   pip install duckdb psutil openai
   ```
   - 追加（オプション）:
     - PyYAML（`validate_config` が YAML を検証する際に必要）:
       ```
       pip install PyYAML
       ```

4. 初期設定（対話式ウィザード）:
   ```
   python -m kabusys.config_setup
   ```
   - `.env` が生成されます（デフォルト: プロジェクトルートの `.env`）。
   - 注意: `.env` は機密情報を含むため絶対に Git にコミットしないでください。

5. 設定の検証:
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict   # 警告も失敗扱いにする
   ```

6. データディレクトリ / ログディレクトリ作成は自動的に行われますが、手動で作る場合:
   ```
   mkdir -p data logs
   ```

---

## 主要な環境変数（よく使うもの）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時必須）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（"1" でクリア、デフォルト "0"。本番では 0 推奨）

自動で .env をロードする機能が有効（デフォルト）。自動ロードを無効化するには:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 使い方（基本コマンド）
- ExecutionEngine を起動（バックグラウンドやプロダクションでの使用を想定）:
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合は専用ペーパートレード DB（PAPER_TRADING_SQLITE_PATH）を使用します。
  - 起動時に `data/stop_requested.flag` が存在すると起動せず終了します。
  - 実行中は pid ファイル（デフォルト: data/execution.pid）が生成されます。

- Monitoring を起動（SystemMonitor のポーリング）:
  ```
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（秒、デフォルト 60）。
  - 監視用 DB は環境に関わらず本番の sqlite_path を使用します（monitoring 用に別 DB を使いたい場合は .env 等でパスを切り替えてください）。
  - 停止: プロセスを KeyboardInterrupt で終了、もしくは `data/stop_requested.flag` を書くことでループを終了させます。

- 設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: `data/paper_trading.db`、`--db` で指定可能。
  - 出力は標準出力（コンソール）。

- AI モジュール（例: ニューススコア付与） — プログラムから使用:
  - OpenAI API キーが必要です（環境変数 `OPENAI_API_KEY` を設定）。
  - 例（Python スクリプト内）:
    ```
    from kabusys.ai.news_nlp import score_news
    import duckdb
    conn = duckdb.connect('data/kabusys.duckdb')
    score_news(conn, target_date=date(2026,4,10), api_key=None)  # api_key=None なら env 参照
    ```

---

## ログ
- デフォルト保存先: logs/
- 各アプリケーションでログファイル名は app_name（例: execution.log, monitoring.log）になります。
- ログローテート: 日次ローテーション、30日保持（TimedRotatingFileHandler）。

ログ設定は共通ユーティリティ `kabusys.utils.logging_setup.setup_logging` で行われます。

---

## 停止・Kill Switch
- ExecutionEngine の強制停止は kill flag（デフォルト `data/kill.flag`）や stop flag (`data/stop_requested.flag`) を用いる運用が想定されています。
- KillSwitch（monitoring 側）はリスク判定（ドローダウンやポジション数上限）により kill.flag を作成し、Execution 側がそれを検知して停止する仕組みです。
- 注意: 本番環境で `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag が自動クリアされ、誤って本番が再起動される危険があるため、本番ではデフォルト 0 を推奨します。

---

## 依存関係（主なライブラリ）
- duckdb
- psutil
- openai
- PyYAML（オプション、config 検証用）
- 標準ライブラリ: sqlite3, logging, threading, datetime, pathlib, json, time, math など

必要なパッケージは適宜 pip でインストールしてください。

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py       — （コードベースに存在、監視ロジック）
    - kill_switch.py
    - alert_manager.py       — （アラート送信管理）
  - execution/                — Execution エンジン関連（BrokerFactory 等）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - risk_manager.py
    - reconciler.py
    - broker_factory.py
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
  - utils/
    - logging_setup.py
    - process_priority.py

その他、config/*.yaml（設定テンプレート）や data/、logs/ などがプロジェクトルートに存在する想定です。

---

## 運用上の注意
- 本番での誤動作を避けるため、`validate_config` で必須環境変数の確認を行ってください。
- .env ファイルは機密情報（API トークン・パスワード）を含むため絶対にコミットしないでください。
- OpenAI や外部 API 呼び出し時のエラーはリトライやフォールバックロジックが実装されていますが、API コスト・レート制限に注意してください。
- データベースパスはデフォルトで `data/` 以下を使用します。永続ストレージやバックアップ方針を検討してください。
- `KABUSYS_ENV=live` の場合は特に慎重に設定を確認してください（LINE 通知設定など）。

---

もし README に追加したい例（デフォルト .env のテンプレート、systemd / Supervisor 用の実行例、さらに詳細な API 使用例など）があれば指示をください。