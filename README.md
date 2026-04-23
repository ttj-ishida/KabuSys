# KabuSys

日本株自動売買システム（ライブラリ + 起動スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・注文実行・監視・研究ツールを含む日本株自動売買フレームワークです。DuckDB/SQLite をデータ層に使い、kabuステーション 等のブローカー API と連携して発注を行います。OpenAI を用いたニュース NLP / レジーム判定機能も含みます。

---

主な特徴
- シグナル → ポートフォリオ構築 → 発注 までの ExecutionEngine（本番 / ペーパートレード対応）
- 実行プロセスの監視（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch
- Paper Trading 用の検証レポート生成スクリプト
- DuckDB を用いたファクター計算・リサーチモジュール（ファクター算出 / IC 計算等）
- OpenAI を用いたニュースセンチメント（news_nlp）および市場レジーム判定
- 設定ウィザード（.env 作成）、設定検証 CLI、統一ロギング・プロセス優先度ユーティリティ
- 設計はテストしやすい純粋関数群と軽量な永続化レイヤ（SQLite）で構成

---

必要な依存（代表例）
- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config 検証を行う場合）
- その他（実行環境・用途により追加）

（依存は実際の requirements.txt / poetry 設定に従ってください）

---

セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して依存をインストール
   （pipenv / poetry 等を使っている場合はそちらに合わせてください）
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt   # または個別に duckdb, psutil, openai, pyyaml など
   ```

3. .env の初期作成（対話式ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   - ウィザードが .env を生成します（.env は必ず Git 管理外にしてください）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - そのほか LOG_LEVEL、KABUSYS_ENV（development / paper_trading / live）等を設定します。

4. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告も FAIL 扱いになります。

5. データディレクトリの確認（デフォルト）
   - DuckDB: data/kabusys.duckdb
   - 監視 SQLite: data/monitoring.db
   - ペーパートレード SQLite: data/paper_trading.db
   - ログディレクトリ: logs/
   これらは環境変数（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_DIR 等）で上書き可能です。

---

主要な使い方（起動例）

- 監視プロセスの起動（SystemMonitor のポーリングループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書きできます（デフォルト 60）。
  - 監視は本番用の sqlite_path を常に使用します（環境に依存せず本番 DB を監視する仕様）。

- 実行エンジン（ExecutionEngine）の起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し paper_trading.db に記録します（本番 DB と分離）。
  - プロセスは execution.pid を作成します。停止は data/stop_requested.flag（または kill.flag 等）で制御します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - 環境変数 `PAPER_TRADING_SQLITE_PATH` で DB パスを指定できます。オプション `--db` でも指定可能。

- AI ニューススコア / レジーム判定（ライブラリ呼び出し）
  - プログラムから呼ぶ場合の例（DuckDB 接続を渡す）:
    ```python
    import duckdb
    from kabusys.ai.news_nlp import score_news
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,20), api_key="sk-...")
    score_regime(conn, target_date=date(2026,4,20), api_key="sk-...")
    ```
  - OpenAI API キーは引数で渡すか環境変数 `OPENAI_API_KEY` を設定してください。

---

重要な環境変数（抜粋）

- KABUSYS_ENV: execution 環境 ('development' | 'paper_trading' | 'live')（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）

設定自動ロードについて:
- リポジトリルートの .env/.env.local は自動的に読み込まれます（OS 環境変数が優先）。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時などに便利）。

---

Kill Switch / 停止制御
- KillSwitch はリスク監視 (RiskMonitor) の結果（ドローダウン超過、ポジション上限等）により reason を書き込み、`data/kill.flag` を作成します。ExecutionEngine はこのフラグを検知して安全に停止します。
- 手動で実行を停止したい場合は `data/stop_requested.flag`（run_execution/run_monitoring がチェック）を作成します。

---

ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動ロード）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite ベースの監視 DB 層
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 発注 / 約定監視（省略: 実装あり）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag の管理
    - monitoring_engine.py   — モニタを束ねるエンジン
    - alert_manager.py       — 通知マネージャ（LINE 等への通知機構）
  - execution/
    - execution_engine.py    — 実行エンジンコア（注文ループ等）
    - order_manager.py       — 注文管理
    - risk_manager.py        — 実行時リスク管理
    - broker_factory.py      — ブローカクライアント生成（本番 / モック）
    - order_repository.py    — 発注永続化（SQLite 等）
    - reconciler.py          — 差分修復 / 状態一致化
  - portfolio/
    - portfolio_builder.py   — 候補選定 / 重み計算
    - position_sizing.py     — 発注株数計算
    - risk_adjustment.py     — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（momentum, value, volatility）
    - feature_exploration.py — IC / 統計サマリ等
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — レジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト
  - data/                    — 実行時データ（DB、flag、pid など。リポジトリには含めないでください）

---

開発・運用上の注意
- 本番（KABUSYS_ENV=live）では .env の取り扱い・LINE 通知設定等を慎重に行ってください。validate_config は本番向けガードを含みます。
- Paper Trading は本番 DB と分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI 呼び出しは外部 API 呼び出しであり失敗することがあります。AI モジュールはフェイルセーフ（失敗時にスコア 0 等で継続）を意識して実装されていますが、API キーやレート制限には注意してください。
- 実行スクリプトはプロセス優先度を上げようとします（set_process_priority）。OS 権限により失敗する場合がありますが、その場合は警告を出して続行します。
- ログは logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリの作成に失敗した場合はコンソール出力のみになります。

---

よく使うコマンドまとめ
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

さらに詳しい設計・実装コメントは各モジュールの docstring を参照してください（src/kabusys 以下の各ファイルに詳細なコメントが付いています）。README に記載のない運用フローや内部設計について質問があれば、用途に合わせて追記します。