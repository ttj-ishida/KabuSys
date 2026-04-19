# KabuSys

日本株自動売買システム（KabuSys）のコードベース説明書です。  
この README はリポジトリに含まれる主要モジュールの使い方、セットアップ手順、環境変数、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムの骨組みを提供する Python モジュール群です。以下の機能群を含みます。

- 実行エンジン（ExecutionEngine）による発注処理（本番 / ペーパートレード対応）
- 監視（Monitoring）: システム状態・注文状態・リスク監視、Kill Switch
- ポートフォリオ構築（候補選定・重み付け・建玉サイズ計算）
- リサーチ（ファクター計算、特徴量探索）
- AI 補助（ニュースの NLP スコアリング、レジーム判定：OpenAI を利用）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード・検証）

この README は src/kabusys 以下の主要スクリプト／モジュールに基づいています。

---

## 機能一覧

- run_execution.py
  - ExecutionEngine を起動
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、paper_trading DB に記録（本番 DB と分離）
  - PID ファイル・停止フラグを扱う

- run_monitoring.py
  - SystemMonitor をポーリング（デフォルト 60 秒）
  - MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能
  - 監視結果は SQLite（monitoring DB）へ永続化

- config_setup.py
  - .env の初期作成 / 更新を対話式で支援するウィザード

- validate_config.py
  - .env と config/*.yaml の事前検証ツール（--strict オプション有）

- tools/paper_verification_report.py
  - ペーパートレード DB を解析して検証レポートを生成

- ai/news_nlp.py / ai/regime_detector.py
  - OpenAI を用いたニュースセンチメント評価・市場レジーム判定
  - DuckDB の prices_daily / raw_news 等を参照して結果を ai_scores / market_regime へ保存

- portfolio/*
  - 銘柄選定、重み計算、セクター制限、ポジションサイズ計算（純粋関数群）

- monitoring/*
  - MonitoringDB（SQLite ベースの永続化）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - KillSwitch（条件を満たせば data/kill.flag を書き込み Execution を停止させる）

- utils/*
  - ロギング設定（ログ回転、コンソール出力）
  - プロセス優先度／CPU affinity 設定ユーティリティ

---

## 前提条件 / 推奨環境

- Python 3.10+
- 必要なパッケージ（代表例）
  - duckdb
  - psutil
  - openai (AI 機能利用時)
  - PyYAML (config 検証で YAML をチェックする場合)
- SQLite（標準ライブラリで可）

インストール例（代表的なパッケージ）:
```
pip install duckdb psutil openai PyYAML
```

※ 実際の requirements.txt がある場合はそれを使用してください。

---

## セットアップ手順

1. リポジトリをクローン / 配置
2. Python 仮想環境を作成してパッケージをインストール
3. 初期 .env を作成（対話式）
   ```
   python -m kabusys.config_setup
   ```
   - J-Quants トークン、kabu API パスワード等を入力します。
   - .env は絶対に Git にコミットしないでください。

4. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   - --strict を付けると警告も失敗扱いになります。

5. （AI 機能利用時）OpenAI API キーを .env または環境変数 OPENAI_API_KEY に設定

6. DB ディレクトリ / data ディレクトリ等が自動作成されますが、必要に応じて手動で作成してください。

---

## 使い方

基本的にモジュールはモジュール経由で起動できます。以下は代表的なコマンド例です。

- ExecutionEngine を起動（実運用 or ペーパートレード）
  ```
  # 本番（KABUSYS_ENV=live 等は .env で設定）
  python -m kabusys.run_execution

  # ペーパートレードで起動したい場合（環境変数で上書き）
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
  - paper_trading の場合は settings.paper_sqlite_path（デフォルト data/paper_trading.db）に記録されます。
  - ExecutionEngine は data/execution.pid を PID ファイルとして使います。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。

- Monitoring を起動
  ```
  # MONITOR_POLL_INTERVAL は秒（デフォルト 60）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - 監視結果は SQLite（settings.sqlite_path、デフォルト data/monitoring.db）に保存されます。
  - 監視は常に本番 sqlite_path を使用します（環境に依らず）。

- .env の作成 / 更新（対話式）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```
  - 環境変数 PAPER_TRADING_SQLITE_PATH でデフォルト DB を指定可能（デフォルト: data/paper_trading.db）。

- AI 関連（プログラム呼び出し）
  - ニュース NLP スコアリング:
    ```py
    from kabusys.ai.news_nlp import score_news
    # duckdb_conn: duckdb.connect(...)
    score_news(duckdb_conn, target_date, api_key="...")  # returns 書き込んだ銘柄数
    ```
  - レジーム判定:
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")
    ```
  - CLI 用のラッパーは組み込まれていませんが、上記をスクリプト経由で呼び出すか Python -c / 小さなエントリポイントを作って使用してください。

---

## 主な環境変数

（重要なもののみ抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 実行環境・ログ等
  - KABUSYS_ENV — 実行環境（development | paper_trading | live）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
  - LOG_DIR — ログ保存ディレクトリ（デフォルト logs/）

- DB パス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト data/paper_trading.db）

- AI
  - OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）

- Monitoring / Execution 制御
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）
  - KILL_FLAG_PATH — kill.flag のパス（デフォルト data/kill.flag）

- Paper Trading のモード
  - PAPER_FILL_MODE — MockBrokerClient の約定振る舞い（instant|partial|never|reject）

- その他
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動で .env を読み込まない

設定は .env / .env.local を通じて行います。Settings モジュールはプロジェクトルート（.git または pyproject.toml）を基準に .env を自動ロードします。

---

## ログ / フラグファイル / DB

- ログ
  - デフォルト出力先: stdout とファイル logs/<app_name>.log（TimedRotatingFileHandler、日次ローテーション、30 日保存）
  - ログ設定は kabusys.utils.logging_setup.setup_logging() を通じて統一されます

- フラグ / PID / DB
  - data/stop_requested.flag — 外部からプロセスを優雅に停止するための停止フラグ（run_* 系が参照）
  - data/kill.flag — KillSwitch による緊急停止シグナル（ExecutionEngine 停止）
  - data/execution.pid — ExecutionEngine の PID ファイル（デフォルト）
  - SQLite / DuckDB のパスは Settings で指定（デフォルト data/*.db）

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys の主要なファイル・ディレクトリ構成（抜粋）です:

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py       — SystemMonitor 起動スクリプト
    - utils/
      - logging_setup.py       — ログ設定ユーティリティ
      - process_priority.py    — プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py       — SQLite 永続化レイヤ
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py       (存在する想定)
    - execution/               — ExecutionEngine 周り（OrderManager 等）
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

（実際のリポジトリではさらにファイル／ディレクトリが存在します）

---

## 実行時の注意点 / 運用メモ

- KABUSYS_ENV が `live` の場合は本番運用となるため、LINE や kill_flag 等の設定を慎重に行ってください。validate_config の live ガードも確認してください。
- Monitoring は本番 sqlite_path を常に使用します。監視 DB と実際のペーパートレード DB は分離されています。
- PID ファイル / stop flag / kill flag を使って外部から安全にプロセスを停止できます。停止フラグは起動前に既に存在する場合、run_execution は起動しません。
- OpenAI を利用する機能は API レート制限・エラーに対してリトライ処理を実装していますが、APIキーの管理およびコストに注意してください。
- ログディレクトリが作成できない場合、ファイル出力は無効化され、コンソール出力のみになります（警告が出ます）。

---

## 参考コマンドまとめ

- .env を作る（対話式）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- 実行エンジン起動
  ```
  python -m kabusys.run_execution
  ```

- 監視起動
  ```
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

もし README に追記して欲しい箇所（追加の CLI ラッパー、具体的な設定例、サンプル .env、テスト手順 など）があれば教えてください。必要に応じてサンプル .env や運用手順書を作成します。