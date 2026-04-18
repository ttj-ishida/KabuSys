KabuSys — 日本株自動売買システム
=================================

このリポジトリは、日本株の自動売買・研究・モニタリング機能を含む小規模なトレーディングフレームワークです。  
ここに含まれるモジュールは、取引エンジン（ExecutionEngine）、監視（Monitoring）、ファクター計算やポートフォリオ構築、AI ベースのニュース解析などで構成されています。

主な機能
--------
- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - ブローカークライアント抽象化（MockBrokerClient を用いたペーパー時の完全分離）
  - 注文管理・リスク管理・照合ロジック
- Monitoring（監視）
  - システムリソース・プロセス監視（CPU / メモリ / ディスク）
  - 注文ログ・ポジション・リスクログの永続化（SQLite）
  - Kill Switch（閾値超過で execution 停止フラグを書き込み）
  - アラート送信フック（LINE 等）
- 研究（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB を使用）
  - 将来リターン・IC 計算、特徴量サマリ
- ポートフォリオ構築（portfolio）
  - 候補選定・重み付け・セクター制約・ポジションサイズ計算（純粋関数）
- AI モジュール（ai）
  - ニュース NLP によるセンチメントスコア付与（OpenAI）
  - 市場レジーム判定（ma200 + マクロニュースセンチメント合成）
- ユーティリティ
  - ロギング設定、プロセス優先度設定、環境変数ロード等
- ツール
  - .env 対話ウィザード（config_setup）
  - 起動前設定検証（validate_config）
  - ペーパートレード検証レポート生成スクリプト

セットアップ手順
----------------
1. Python 環境を用意（推奨: 3.10+）
2. 必要パッケージをインストール（例）
   - duckdb
   - psutil
   - openai
   - PyYAML（任意だが validate_config の YAML 検証で使う）
   インストール例:
   ```
   pip install duckdb psutil openai PyYAML
   ```
   （プロジェクトに requirements.txt がある場合はそれを使ってください）
3. リポジトリをチェックアウトし、パッケージとしてインストール（任意）
   ```
   pip install -e .
   ```
4. .env の作成（対話式ウィザードを推奨）
   ```
   python -m kabusys.config_setup
   ```
   あるいは .env.example を参考に .env を作成して環境変数を設定します。

必須環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: execution モード（development / paper_trading / live）、デフォルトは development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード時の SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: AI 機能を使う場合に必要

起動前チェック
--------------
設定を検証するには:
```
python -m kabusys.validate_config
# 警告を FAIL 扱いにする:
python -m kabusys.validate_config --strict
```

使い方（実行例）
----------------

- 実行エンジン（ExecutionEngine）を起動
  ```
  # 通常（KABUSYS_ENVに応じて本番またはペーパーが選択される）
  python -m kabusys.run_execution
  ```
  - 実行時、data/execution.pid に PID を書き込みます。
  - 停止させたい場合はプロジェクトルートの data/stop_requested.flag を作成するとエンジンが停止します。
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、発注履歴は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。

- 監視ループ（Monitoring）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト 60 秒。
  - 監視 DB は Settings.sqlite_path（デフォルト data/monitoring.db）を使用（Monitoring は常に本番 sqlite_path を参照）。
  - 停止: data/stop_requested.flag を作成すると監視ループが終了します。

- .env 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- Paper Trading 検証レポート生成
  ```
  # 全期間（DB 内）
  python -m kabusys.tools.paper_verification_report

  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # --db で DB パスを指定することも可能
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

重要な挙動メモ
--------------
- Kill Switch / 停止フラグ
  - KillSwitch はリスク条件を満たすと data/kill.flag を書き込み、ExecutionEngine 側で停止処理を促します。
  - ExecutionEngine の起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると起動時に kill.flag を自動クリアします（本番では 0 を推奨）。
  - run_execution / run_monitoring は stop_requested.flag（data/stop_requested.flag）をチェックして graceful shutdown を行います。

- ログ
  - ログは kabusys.utils.logging_setup.setup_logging を通じて統一的に設定されます。
  - デフォルトログディレクトリ: logs/、ファイル名はアプリ名（execution.log / monitoring.log 等）
  - LOG_LEVEL 環境変数でログレベルを変更可能。

- DB 初期化 / マイグレーション
  - monitoring_db.init_monitoring_db() が必要なテーブルを冪等に作成します（起動時に自動保証）。
  - DuckDB は research / ai モジュールで分析用に使用されます（DUCKDB_PATH）。

ディレクトリ構成（主要ファイル）
-------------------------------
（リポジトリの src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理 (Settings)
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト

  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）によるスコアリング
    - regime_detector.py     — 市場レジーム判定
    - __init__.py

  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status/trade_logs/...）
    - system_monitor.py      — システム監視（CPU/メモリ/データ鮮度）
    - trade_monitor.py       — 注文系監視（stale orders 等） ※（コード参照）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 管理
    - monitoring_engine.py   — 複数 Monitor を束ねるループ
    - alert_manager.py       — アラート送信（LINE 等） ※（コード参照）

  - execution/
    - execution_engine.py    — ExecutionEngine 本体（run_session 等）
    - broker_factory.py      — ブローカークライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - ...（その他発注周り）

  - portfolio/
    - portfolio_builder.py   — 候補選定・重み算出
    - position_sizing.py     — 発注株数計算・スケーリング
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py     — モメンタム/ボラティリティ/バリュー計算（DuckDB）
    - feature_exploration.py — 将来リターン/IC/統計サマリ
    - __init__.py

  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
    - __init__.py

  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度・CPU affinity 設定
    - __init__.py

補足 / 運用上の注意
-------------------
- KABUSYS_ENV を live にして運用する際は、LINE の通知設定や kill flag の挙動（KILL_FLAG_CLEAR_ON_START）などを十分確認してください。
- OpenAI 等の外部 API を利用する箇所は API キーやコスト・レート制限に注意してください。AI モジュールはリトライやフォールバックを備えていますが、運用時の監視は必須です。
- DuckDB のテーブルスキーマ（prices_daily / raw_financials / raw_news 等）は外部で用意しておく必要があります。research / ai モジュールはこれらのデータを参照して計算を行います。

貢献 / 開発
-----------
- 小さなモジュール単位でユニットテストを書き、例えば portfolio.* や research.* は外部 IO を伴わない純粋関数が多くテストが容易です。
- .env の自動ロードはプロジェクトルート検出に依存します（.git または pyproject.toml を探索）。CI / テストで自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"（ソース参照）

---

この README はリポジトリ内のコードをもとに作成しました。追加で README に載せたいコマンド例や運用手順（systemd/cron でのデーモン化、Docker イメージ化等）があれば教えてください。必要に応じてサンプルの systemd ユニットや docker-compose.yml のテンプレートも作成します。