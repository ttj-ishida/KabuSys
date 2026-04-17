# KabuSys

日本株向け自動売買システムの一部コンポーネント群（設定管理、監視、実行エンジン起動スクリプト、ポートフォリオ構築、リサーチ、AI ニュース処理 等）。

以下はこのリポジトリに含まれる主要スクリプト／モジュールの使い方とセットアップ手順をまとめた README です。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能を提供するモジュール群を含みます。

- 環境変数 / .env ベースの設定管理（対話式ウィザード・検証ツールあり）
- ExecutionEngine 起動スクリプト（本番 / ペーパートレード分離）
- Monitoring（システム状態・注文滞留・リスク監視）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限など）
- リサーチ用ファクター計算・特徴量探索（DuckDB を用いた分析）
- AI モジュール（ニュースの NLP スコアリング、レジーム判定。OpenAI API 利用）
- 各種ユーティリティ（プロセス優先度設定、Paper Trading 検証レポート生成 等）

設計上のポイント:
- DuckDB と SQLite を併用（DuckDB は分析用、SQLite は監視・発注履歴用）
- ペーパートレード時は発注 DB を完全に分離（data/paper_trading.db）
- ルックアヘッドバイアスを避ける設計（日時参照に注意）
- OpenAI 連携は明示的に API キーを渡すか環境変数で指定

---

## 機能一覧（抜粋）

- 設定関連
  - .env 対話式作成 wizard: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config

- 実行 / 監視
  - 実行エンジン起動: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、data/paper_trading.db を使用
  - 監視ループ起動: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視は本番 sqlite_path を使用（環境に関わらず）

- モニタリング
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセス検出
  - TradeMonitor: 注文滞留、約定価格の異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件で data/kill.flag を書き込み ExecutionEngine に停止シグナル送信
  - MonitoringDB: SQLite に監視ログを永続化（system_status / trade_logs / risk_logs / positions / dashboard）

- ポートフォリオ
  - 候補選定（スコア順）
  - 等金額・スコア加重の重み計算
  - セクター集中制限の適用
  - ポジションサイズ計算（単元株丸め・リスクベース配分・スケールダウンロジック）

- リサーチ / AI
  - ファクター計算（Momentum, Volatility, Value 等） — DuckDB 上の prices_daily / raw_financials を参照
  - 特徴量探索、IC（Information Coefficient）計算、統計サマリー
  - ニュース NLP（OpenAI）による銘柄ごとのセンチメントスコア生成（ai_scores 更新）
  - レジーム判定（ma200 とマクロニュースセンチメントの合成）

- ユーティリティ
  - process_priority: プロセス優先度 / CPU affinity 設定（psutil 使用）
  - tools/paper_verification_report: ペーパートレード検証レポート生成

---

## 依存ライブラリ（代表）

主に下記を使用します。実行する機能によって必要なライブラリは増減します。

- Python 3.9+
- duckdb
- psutil
- openai (OpenAI Python SDK)
- PyYAML（設定ファイル検証時のみ必要）
- その他標準ライブラリ（sqlite3, logging, threading 等）

インストール例:
```
pip install duckdb psutil openai PyYAML
```

※ 本プロジェクトの配布パッケージに requirements.txt や poetry/pyproject があればそちらを使ってください。

---

## 環境変数（主要）

重要な環境変数とデフォルト値（.env 作成時に対話ウィザードで設定）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI モジュールを使う場合)
- LINE_CHANNEL_ACCESS_TOKEN (任意、アラート用)
- LINE_USER_ID (任意、アラート用)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db) — Monitoring 用（run_monitoring は常に本番 sqlite_path を使用）
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — paper_trading 用
- LOG_LEVEL (DEBUG/INFO/WARNING/...)
- KILL_FLAG_CLEAR_ON_START (0/1) — 本番では 0 推奨
- PAPER_FILL_MODE (paper_trading の MockBrokerClient の挙動: instant|partial|never|reject)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔（秒）; デフォルト 60)
- PID_FILE_PATH / KILL_FLAG_PATH (デフォルト: data/execution.pid / data/kill.flag)

注意:
- .env の自動読み込みはプロジェクトルート (.git または pyproject.toml が存在するディレクトリ) を基準に行われます。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト用）。

---

## セットアップ手順（ローカル）

1. リポジトリをクローン／展開
2. 仮想環境作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix
   .venv\Scripts\activate     # Windows
   ```
3. 依存ライブラリをインストール
   ```
   pip install duckdb psutil openai PyYAML
   ```
4. .env の初期作成（対話式ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   - ウィザード後は `.env` が作成されます。Git 等には絶対コミットしないでください。
5. 設定検証（推奨）
   ```
   python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告も失敗扱いになります。

6. データディレクトリを作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（主要コマンド）

- 実行エンジン（ExecutionEngine）の起動
  - 本番 / 開発 / paper_trading は KABUSYS_ENV によって切り替わります。
  - ペーパートレード時は MockBrokerClient を使用し、データベースは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録されます（本番 DB とは分離）。
  ```
  python -m kabusys.run_execution
  ```

  停止（外部から）:
  - プロセスを直接 kill するか、監視・手動で data/stop_requested.flag を作成すると run_execution のループは停止します（スクリプト内では stop flag を監視しています）。

- 監視ループの起動
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定可能（例: `MONITOR_POLL_INTERVAL=30`）。
  - 監視は Settings で定義した sqlite_path を使用（環境にかかわらず本番 sqlite_path を使用する仕様）。
  - 監視が KillSwitch 条件に合致すると Settings.kill_flag_path（デフォルト data/kill.flag）へ理由を書き込みます。

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```
  - DB パスは `--db` OR 環境変数 `PAPER_TRADING_SQLITE_PATH` OR デフォルト `data/paper_trading.db` の順で決定されます。

- AI モジュール（ニュース NLP / レジーム判定）
  - ai.news_nlp.score_news や ai.regime_detector.score_regime はプログラム的に呼び出す想定（OpenAI API キーが必要）。
  - 例（モジュールを使う場合のサンプル呼び出し）:
    ```python
    from kabusys.ai.news_nlp import score_news
    import duckdb, datetime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=datetime.date(2026, 4, 10), api_key="sk-...")
    ```

- 設定ファイルの自動ロードについて
  - プロジェクトルートに `.env` / `.env.local` があると自動で環境変数へロードされます（ただし OS 環境変数は上書きされません）。
  - 自動ロードを無効化したい場合:
    ```
    export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    ```

---

## 停止フラグ・PID・その他ファイル

- data/stop_requested.flag
  - run_monitoring / run_execution で監視される「一時停止」フラグ（存在を検出するとループを終了）。
- data/kill.flag
  - KillSwitch が発動した際に作成されるファイル。ExecutionEngine は設定によりこのファイルの存在をチェックして停止します。
- data/execution.pid（デフォルト）
  - ExecutionEngine が PID を書き込むファイル（SystemMonitor はこのファイルを見てプロセス存在チェックを行う）。
- これらファイルのパスは Settings で上書き可能（PID_FILE_PATH, KILL_FLAG_PATH 等）。

---

## ディレクトリ構成（主なファイル）

リポジトリの src/kabusys 配下の主要構成:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境設定 / .env 自動ロードロジック / Settings クラス
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 起動前チェック CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py                 — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py          — 市場レジーム判定
  - monitoring/
    - monitoring_db.py            — SQLite 永続化層（初期化含む）
    - system_monitor.py           — システム状態監視
    - trade_monitor.py            — 注文滞留・約定異常監視
    - risk_monitor.py             — ドローダウン・ポジション上限監視
    - kill_switch.py              — Kill Switch ロジック（kill.flag 書き込み等）
    - monitoring_engine.py        — 各 Monitor を束ねるエンジン
    - alert_manager.py            — （未表示：アラート送信用ロジック）
  - execution/                     — 発注関連（order_manager, repo, engine 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (DB schema やログ関連)
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py         — psutil を使った優先度設定 / CPU affinity

（上記は抜粋。詳細は各モジュールの docstring を参照してください）

---

## 運用上の注意・ベストプラクティス

- 本番実行（KABUSYS_ENV=live）の前に必ず `python -m kabusys.validate_config` で設定を確認してください。
- .env は絶対に Git 管理下へコミットしないでください。
- run_monitoring は監視 DB（sqlite）のパスを本番用の sqlite_path に固定してアクセスします。ペーパートレード DB は run_execution の方で分離されます。
- OpenAI API を使う処理は API 失敗時に失敗を吸収して継続するよう設計されていますが、API キーと使用量に注意してください。
- process_priority と CPU affinity は可能な場合にのみ適用されます（権限不足や未対応 OS ではスキップされます）。
- kill.flag / stop_requested.flag / execution.pid の扱いに注意。KILL_FLAG_CLEAR_ON_START=1 を本番で設定すると Kill Switch が無効化される恐れがあるため本番では 0 推奨。

---

## 開発 / テストヒント

- モジュールの多くは純粋関数や DB 接続を引数に取る設計なので、ユニットテストでモックや一時 DB を渡して検証がしやすいです。
- OpenAI 呼び出しは内部で _call_openai_api を使っているため、ユニットテストではパッチしてネットワークに依存しないようにできます。
- DuckDB を使ったリサーチ関数は、サンプル prices_daily / raw_financials テーブルを作成してテストできます。

---

もし特定のモジュールの使い方（例: ExecutionEngine の設定項目、OrderRepository の API、AI モジュールの詳細なテスト手順など）についてドキュメント化を希望される場合は、対象を指定していただければ詳しい README セクションやサンプルコードを追加します。