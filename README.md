README
======

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的とした Python パッケージ群です。本リポジトリは以下の主要機能を含みます。

- 実行エンジン (ExecutionEngine) — 発注・注文管理・リスク制御（本番 / ペーパートレード切替）
- 監視コンポーネント — システム状態・注文ログ・リスク監視、Kill Switch の発動
- ポートフォリオ構築モジュール — 候補選定・重み計算・株数決定・セクター制限
- リサーチ機能 — ファクター計算、特徴量探索、IC 計測
- AI 補助機能 — ニュースを LLM でスコアリング（OpenAI API 使用）
- ユーティリティ — .env 対話ウィザード、設定検証、ログ設定など
- ツール — Paper Trading の検証レポート出力等

主な機能一覧
-------------
- 環境設定ウィザード（kabusys.config_setup）で .env を対話生成
- 設定検証 CLI（kabusys.validate_config）で起動前チェック
- ExecutionEngine（kabusys.run_execution）:
  - KABUSYS_ENV による動作モード切替（development / paper_trading / live）
  - paper_trading モードでは MockBroker を利用し、paper_trading 用 DB に記録
  - stop / kill フラグによる安全停止機構、PID ファイル管理
- Monitoring（kabusys.run_monitoring）:
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングし DB に記録
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視は環境に依らず本番の sqlite_path を参照（監視ログの一元化）
- AI 周り:
  - news_nlp.score_news: raw_news を LLM（gpt-4o-mini 等）でスコアリングして ai_scores に書き込み
  - regime_detector.score_regime: ETF MA とマクロニュースを合成して市場レジーム判定
- ポートフォリオ:
  - 候補選定、等重/スコア重み、リスクベースのポジションサイズ計算、セクター制限
- ツール:
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポートを生成

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成・有効化してください。
   - python 3.10+ を推奨します。

2. 必要ライブラリをインストール（例）:
   - 必須: duckdb, psutil, openai
   - 推奨 / オプション: PyYAML（config 検証のため）
   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```
   ※ requirements.txt がある場合はそれを利用してください（本リポジトリに同梱がなければ上記を個別に入れてください）。

3. データ・ログディレクトリの準備（通常は自動作成されますが事前に用意しておくと権限問題を避けられます）:
   ```
   mkdir -p data logs
   ```

4. 環境変数 (.env) の作成:
   - 対話式ウィザードで .env を生成:
     ```
     python -m kabusys.config_setup
     ```
   - ウィザードで作成された .env は Git にコミットしないでください（シークレット含む）。

5. 設定の検証:
   ```
   python -m kabusys.validate_config
   # 警告をエラー扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```

主要な環境変数（代表）
-----------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- OPENAI_API_KEY（AI 機能利用時に必要）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔秒数、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか、デフォルト 0）

使い方
------
- .env 作成（初回）:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- ExecutionEngine を起動:
  - 本番相当（KABUSYS_ENV=live）や開発（development）などは .env の KABUSYS_ENV を設定してください。
  - ペーパートレード:
    ```
    export KABUSYS_ENV=paper_trading
    # 必要に応じて PAPER_TRADING_SQLITE_PATH を設定
    python -m kabusys.run_execution
    ```
  - ノート:
    - ペーパートレード時は MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）に記録されます。
    - 起動時に data/stop_requested.flag が存在するとエンジンは起動せず終了します。
    - 実行中は data/execution.pid に PID が書かれます。

- Monitoring を起動:
  ```
  # ポーリング間隔を 30 秒に変更する例
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - 監視サービスは監視用 sqlite（Settings.sqlite_path）を使用します（環境に依存せず本番パスを参照）。
  - 停止は data/stop_requested.flag を作成することで可能です。

- Paper Trading 検証レポートを生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # デフォルト DB を使わない場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 機能（ニューススコア / レジーム判定）:
  - OPENAI_API_KEY を環境変数に設定してください。
  - ライブラリ呼び出し例（コード内関数を直接呼ぶ想定）:
    - news_nlp.score_news(conn, target_date, api_key=None)
    - regime_detector.score_regime(conn, target_date, api_key=None)
  - エラー時はフェイルセーフ（スコア 0 やスキップ）にフォールバックする設計です。

ログと出力
-----------
- ログ出力先:
  - デフォルトで logs/<app_name>.log（日次ローテーション、30 日保持）と stdout に出力します。
  - app_name は各起動スクリプトで "execution" や "monitoring" として設定されます。
- DB:
  - DuckDB: data/kabusys.duckdb（分析用）
  - SQLite（監視）: data/monitoring.db
  - SQLite（paper_trading）: data/paper_trading.db（ペーパートレード時に使用）

停止 / Kill Switch
------------------
- Kill Switch（自動停止）は risk_monitor と kill_switch により判定され、条件を満たすと data/kill.flag を書き込みます。
- 手動で ExecutionEngine を停止したい場合は data/stop_requested.flag を作成してください（実行ループが検知して安全に停止します）。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 をセットすると kill.flag を自動クリアします（本番では 0 を推奨）。

依存関係（主なもの）
-------------------
- Python 標準ライブラリ: sqlite3 等
- サードパーティ:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証・optional）
  - その他、環境に応じた HTTP クライアント等

ディレクトリ構成（主要ファイル）
------------------------------
以下はパッケージ内の主要ファイル・モジュールの一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env 自動読み込み / Settings
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度・CPU affinity 設定
  - monitoring/
    - monitoring_db.py        — 監視用 SQLite 永続化層
    - system_monitor.py       — システム状態監視
    - risk_monitor.py         — ドローダウン・ポジション監視
    - kill_switch.py          — kill.flag 管理
    - monitoring_engine.py    — 複数 monitor を束ねるエンジン
    - (その他: trade_monitor, alert_manager 等)
  - execution/
    - (ExecutionEngine, order_manager, broker_factory, risk_manager 等)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（MA + マクロセンチメント）

開発メモ / 注意点
-----------------
- .env の自動読み込み:
  - config.py はプロジェクトルート（.git または pyproject.toml を探索）を検出できれば .env/.env.local を自動読み込みします。
  - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 監視モジュールは監視 DB（sqlite_path）を使用します。監視は本番 DB を参照する設計のため、監視用途で別 DB を使いたい場合は設定を調整してください。
- AI 機能を利用する際は OpenAI 利用制限やコスト管理に注意してください。API 呼び出しにはレート制限・リトライロジックを備えていますが、運用時の設計を検討してください。
- 本リポジトリは実運用の注文系ロジックを含むため、本番環境で使用する場合は各種設定（KABUSYS_ENV、LINE 通知、KILL_FLAG 等）を慎重に確認してください。

ライセンス
----------
（このリポジトリにライセンスファイルがある場合はそちらを参照してください。無い場合は組織ポリシーに従ってください。）

おわりに
--------
まずは .env を作成 → validate_config でチェック → 監視・実行を順に立ち上げる流れを推奨します。運用中は logs と data ディレクトリのバックアップ・監視、および kill.flag / stop_requested.flag の管理に注意してください。質問や追加のドキュメントが必要であれば教えてください。