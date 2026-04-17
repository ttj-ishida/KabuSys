# KabuSys

バージョン: 0.1.0

日本株向けの自動売買 / 研究プラットフォームの一部を実装した Python パッケージです。取引実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、LLM を使ったニュース・レジーム判定などのモジュール群を含みます。

## 概要

KabuSys は以下を目的としたモジュール群を提供します。

- 実際の発注を行う ExecutionEngine（本番／ペーパートレード対応）
- システム稼働状態・注文状況・リスク監視と Kill Switch（フラグファイルでエンジン停止）
- ポートフォリオ構築（候補選定、重み算出、ポジションサイズ算出、セクター制限）
- DuckDB を使ったファクター計算・研究用集計
- OpenAI を使ったニュースセンチメント / レジーム判定（オプション）
- ペーパートレード結果の検証レポート生成ツール
- 環境変数のウィザード & 設定検証ツール

設計方針として、ルックアヘッドバイアス回避やフェイルセーフ（API失敗時のフォールバック）に配慮しています。

## 主な機能一覧

- run_execution: ExecutionEngine の起動（KABUSYS_ENV に応じて本番 or ペーパートレード）
  - paper_trading 環境では MockBrokerClient を使用し、専用 SQLite（data/paper_trading.db）へ記録
  - PID ファイル管理、停止フラグ検知（data/stop_requested.flag）
- run_monitoring: SystemMonitor のポーリングループ起動
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
  - システム状態・データ鮮度のチェック、監視ログは monitoring DB に永続化
- MonitoringEngine: System / Trade / Risk monitor を束ねてアラート送信や Kill Switch 評価
- MonitoringDB: SQLite による永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
- RiskMonitor / TradeMonitor / SystemMonitor: 各種監視ロジック（ドローダウン、滞留注文、異常約定等）
- portfolio: 銘柄候補選定、重み付け、ポジションサイズ計算、セクターキャップ、レジーム乗数
- research: DuckDB を用いたファクター計算（モメンタム / ボラティリティ / バリュー）と特徴量解析
- ai:
  - news_nlp: raw_news を集約し OpenAI に投げて銘柄別センチメントを ai_scores に格納
  - regime_detector: ETF（1321）MA + マクロニュースで市場レジームを判定して書き込み
- tools:
  - paper_verification_report: ペーパートレード結果（SQLite）から検証レポートを生成
- 開発支援:
  - config_setup: .env の対話的生成・更新ウィザード
  - validate_config: 起動前に環境変数・設定ファイルの妥当性チェック

## 必須・推奨要件

最低限の依存（抜粋）:
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config/*.yaml の構文チェックは任意だがインストール推奨）

実行前にプロジェクトルートに requirements.txt があれば次のようにインストールしてください:

```bash
pip install -r requirements.txt
```

あるいは最低限:

```bash
pip install duckdb psutil openai PyYAML
```

（環境に合わせて仮想環境の利用を推奨）

## セットアップ手順

1. リポジトリをクローン／展開してプロジェクトルートへ移動
2. 依存ライブラリをインストール（上記参照）
3. 環境変数設定
   - .env を作成（推奨: ウィザードを使用）
   - 対話式ウィザード:

     ```bash
     python -m kabusys.config_setup
     ```

   - 最低必須環境変数（validate_config でもチェックされます）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD

   - 主要な環境変数（抜粋）:
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: デフォルト data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト data/paper_trading.db）
     - OPENAI_API_KEY: OpenAI を使う場合に必須
     - MONITOR_POLL_INTERVAL: 監視ループの秒間隔（run_monitoring 用）
     - PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject）
     - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリア（開発用。1=自動クリア）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env 自動ロードを無効化
4. 設定検証（任意だが推奨）:

```bash
python -m kabusys.validate_config
# 警告を fail 扱いにする場合:
python -m kabusys.validate_config --strict
```

5. DB の初期化
   - 実行スクリプト（run_execution / run_monitoring）が初回接続時に必要テーブルを作成します（SQLite の init_monitoring_db）。DuckDB のテーブルはデータ取得パイプラインで作成される想定です。

## 使い方（主要コマンド）

- ExecutionEngine を起動（バックグラウンドは各自管理）:

```bash
python -m kabusys.run_execution
```

- Monitoring を起動（実行中は監視ログを SQLite に追記）:

```bash
python -m kabusys.run_monitoring
# ポーリング間隔を環境変数で変更:
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

- 設定ウィザード（.env 生成・更新）:

```bash
python -m kabusys.config_setup
```

- 設定検証:

```bash
python -m kabusys.validate_config
python -m kabusys.validate_config --strict
```

- ペーパートレード検証レポート:

```bash
python -m kabusys.tools.paper_verification_report
# 期間や DB パス指定:
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db /path/to/paper_trading.db
```

- AI モジュール（スクリプト化されていれば呼び出し例）:
  - news_nlp.score_news(conn, target_date, api_key)
  - regime_detector.score_regime(conn, target_date, api_key)
  - これらは DuckDB 接続（duckdb.connect(...)）を渡して利用します。OPENAI_API_KEY は環境変数または引数で指定してください。

注意:
- KABUSYS_ENV=paper_trading のときは MockBrokerClient と paper_trading 用 SQLite を使用し、本番 DB（monitoring.db）とは分離されます。
- run_execution は停止フラグ data/stop_requested.flag を監視し、存在すれば停止します。kill.flag は ExecutionEngine 側停止の別手段です（KillSwitch により作成される）。

## 環境変数の主な一覧（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV (development | paper_trading | live) — default development
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- OPENAI_API_KEY (AI 機能を使う場合)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (アラート通知に使用)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- KILL_FLAG_CLEAR_ON_START (0|1)
- MONITOR_POLL_INTERVAL (秒, run_monitoring 用)
- PAPER_FILL_MODE (instant|partial|never|reject)

## 実行上の注意点

- process priority の設定（psutil）を試みます。権限不足や未対応 OS の場合は警告ログが出て処理は継続します。
- OpenAI API 呼び出しはレートリミットやネットワークエラーに対してリトライロジックを持ちますが、API キーが未設定だと例外になります（score_news / score_regime は ValueError を出します）。
- monitoring は常に本番の sqlite_path（monitoring.db）を使用します（run_monitoring の実装）。paper_trading の監視データを分離したい場合は run_monitoring の DB を差し替えて運用してください。
- .env の自動ロードはプロジェクトルートの検出に基づきます（.git または pyproject.toml を探索）。テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

## ディレクトリ構成（主要ファイル）

プロジェクトの Python パッケージは src/kabusys 配下にあります。主要構成:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読み込みと Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py            — ニュースの LLM スコアリング
    - regime_detector.py     — 市場レジーム判定（MA + マクロニュース）
  - monitoring/
    - monitoring_db.py       — monitoring 用 SQLite 永続化層
    - monitoring_engine.py   — 各 Monitor を束ねるランナー
    - system_monitor.py      — システム稼働・データ鮮度監視
    - trade_monitor.py       — 注文滞留・約定異常監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 操作
    - alert_manager.py       — （アラート送信ロジック: 実装ファイル参照）
  - execution/
    - execution_engine.py    — ExecutionEngine（起動／セッション実行）
    - order_manager.py
    - order_repository.py
    - order_record.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/
    - pipeline.py (想定)   — DuckDB/データ取得 pipeline（利用箇所参照）
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ
  - (その他モジュール)

（実際のファイルツリーはリポジトリ内の src/kabusys を参照してください）

## 開発・拡張メモ

- DuckDB を使った分析・ファクター計算は conn（duckdb.connect(...) が返す接続）を渡す設計。研究用途ではローカル DuckDB ファイルを用意してください。
- AI 周り（news_nlp / regime_detector）は OpenAI の JSON mode を想定したレスポンス処理を行っています。API スキーマや SDK の将来的変更に対して適宜修正が必要です。
- position sizing / risk modules は将来的に銘柄別単元株数や手数料モデルを取り込む余地があります（TODO コメント参照）。
- monitoring_db.init_monitoring_db はスキーママイグレーションの簡易対応を含みます。既存の SQLite に対して安全に実行できます。

## ライセンス / 貢献

リポジトリの LICENSE を参照してください。貢献や issue は Pull Request / Issue を通じて歓迎します。

---

この README はコードベースの主要機能・使い方のサマリです。具体的な実装や細かいパラメータについては各モジュールの docstring を参照してください。