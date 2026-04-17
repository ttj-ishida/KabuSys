# KabuSys

日本株向けの自動売買 / 研究プラットフォーム（モジュール群）。
このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・研究ユーティリティ・AI ベースのニュース NLP 等を含む実装例を提供します。

> 注: この README は src/kabusys 以下のコードを基に作成しています。

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群です。

- 株価データ（DuckDB）を利用したファクター計算・研究
- シグナルからの銘柄選定・ウェイト計算・発注株数計算（ポートフォリオ構築）
- 発注エンジン（ExecutionEngine）と注文管理（OrderManager / OrderRepository）
- 監視（System / Trade / Risk）とアラート送信（LINE）
- Paper Trading 用の分離された DB と検証レポート生成
- OpenAI を利用したニュースセンチメント（ai/news_nlp）と市場レジーム判定（ai/regime_detector）
- 環境設定ウィザード・設定検証 CLI

設計の特徴として、DB（DuckDB / SQLite）や環境変数に基づく設定、フェイルセーフ（API失敗時のフォールバック）、およびルックアヘッドバイアス防止を意識した実装が含まれます。

## 主な機能一覧

- 環境設定ウィザード（.env の対話式生成）: kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml のチェック）: kabusys.validate_config
- ExecutionEngine 起動スクリプト（本番 / paper_trading 切替）: run_execution.py
  - paper_trading 環境では MockBroker を利用し、data/paper_trading.db に記録して本番 DB と分離
- Monitoring（System / Trade / Risk）のポーリングループ起動: run_monitoring.py
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
- 監視ログ永続化（SQLite）と API（MonitoringDB）
- Kill Switch（条件に応じて data/kill.flag を書き込み ExecutionEngine を停止）
- LINE によるアラート通知（AlertManager）
- ポートフォリオ構築ユーティリティ
  - 候補選定、等金額／スコア重み、ポジションサイズ計算、セクターキャップ、レジーム乗数
- 研究モジュール（DuckDB を使ったファクター計算）
  - モメンタム / ボラティリティ / バリュー等
  - 将来リターン計算、IC 計算、統計サマリー
- AI モジュール
  - ニュースセンチメント: kabusys.ai.news_nlp （OpenAI を使用）
  - 市場レジーム判定: kabusys.ai.regime_detector（OpenAI を使用）
- Paper Trading 検証レポート生成ツール: kabusys.tools.paper_verification_report

## 必要条件（推奨）

- Python 3.10+
- SQLite3（標準ライブラリ）
- 推奨 Python パッケージ:
  - duckdb
  - psutil
  - openai
  - requests
  - PyYAML（config YAML の内容検証を行いたい場合）
- その他：インターネット接続（OpenAI / LINE を利用する場合）

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb psutil openai requests pyyaml
```

## セットアップ手順

1. リポジトリをクローンし、仮想環境を用意して依存パッケージをインストールします（上記参照）。

2. .env の作成（対話式ウィザード推奨）:

   - 自動で .env を読み込む仕組みがあります（プロジェクトルートに .env / .env.local があれば読み込み）。
   - ウィザードを使うと対話形式で .env を生成できます:

   ```bash
   python -m kabusys.config_setup
   ```

   対話ウィザードは以下の主要項目を扱います（一部）:

   - KABUSYS_ENV: execution 環境 — development / paper_trading / live
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
   - OPENAI_API_KEY（ai モジュールを使う場合）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信）

3. 設定検証:

```bash
python -m kabusys.validate_config        # 注意点を表示
python -m kabusys.validate_config --strict  # 警告もエラー扱い
```

4. 必要であれば config/*.yaml を生成・編集（スクリプトやテンプレートが別途ある想定）。

5. データディレクトリ:

- デフォルトでは data/ 配下に DB やフラグファイルを置きます（例: data/kabusys.duckdb, data/monitoring.db）。
- run_execution や run_monitoring は data/ 内の PID / stop/kill フラグを参照します。

## 使い方

以下は一般的な起動 / 実行コマンド例です。

- 環境設定ウィザード（.env 作成）:

```bash
python -m kabusys.config_setup
```

- 設定検証（起動前チェック）:

```bash
python -m kabusys.validate_config
```

- ExecutionEngine を起動（実行エンジン）:

```bash
python -m kabusys.run_execution
```

- Monitoring を起動（ポーリング）:

```bash
# ポーリング間隔を環境変数で上書き（秒）
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

- Paper Trading 検証レポート（既存の paper_trading DB に対し）:

```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を明示する例:
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

- AI モジュール（ニュースセンチメント / レジーム判定）
  - 関数はプログラム内 API（kabusys.ai.score_news / score_regime）として呼び出します。OpenAI API キーが必要です（OPENAI_API_KEY 環境変数または引数で渡す）。

注意事項:

- run_execution は KABUSYS_ENV が `paper_trading` の場合、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離します。
- run_monitoring は KABUSYS_ENV にかかわらず「本番 sqlite_path」を使用します（監視 DB は共通の monitoring.db を想定）。
- stop フラグ: data/stop_requested.flag（存在するとループが終了）
- Kill Switch: Settings.kill_flag_path（デフォルト data/kill.flag）により ExecutionEngine 停止を誘発

## 主要 CLI / モジュール一覧（抜粋）

- run_execution.py — 発注エンジン起動スクリプト
- run_monitoring.py — 監視ポーリング起動スクリプト
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証ツール
- tools/paper_verification_report.py — Paper Trading 用検証レポート
- monitoring/ — SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch / AlertManager / monitoring_db
- portfolio/ — portfolio_builder / position_sizing / risk_adjustment
- research/ — factor_research / feature_exploration
- ai/ — news_nlp / regime_detector
- utils/ — process_priority（プロセス優先度・CPU affinity 設定ユーティリティ）
- data pipeline / execution / strategy 等の実装ファイルが想定される（本コードベースには関連ファイル参照あり）

## 環境変数（主なもの）

必須:

- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要（推奨設定）:

- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- OPENAI_API_KEY: OpenAI API キー（ai モジュールを使用する場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE アラート用
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

その他:

- PAPER_FILL_MODE: paper_trading の MockBroker の fill モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動でクリアする（1=有効。production では 0 推奨）

## ディレクトリ構成（src/kabusys 配下の主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / Settings 管理（.env の自動読み込みロジック含む）
  - config_setup.py        — .env 対話式ウィザード
  - validate_config.py     — 設定検証 CLI
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - utils/
    - process_priority.py

その他、execution/*、data/*、strategy/* などのサブパッケージが参照されます（本 README のコードスニペットで使用）。

## 運用上の注意点 / FAQ

- 開発時は KABUSYS_ENV=development を使い、実際の発注は行わない設計です。ペーパートレードは paper_trading を利用してください。
- run_monitoring は監視専用 DB（SQLITE_PATH）を用います。監視は本番 DB を参照するため、監視ログが別に欲しい場合はパスの設定に注意してください。
- OpenAI 呼び出しは外部 API に依存し、レート制限や一時エラーに対してリトライ戦略が実装されていますが、API キー漏洩には十分注意してください。
- kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は本番では危険です。デフォルトは 0（クリアしない）を推奨します。
- process_priority.set_process_priority は OS による制限（権限等）で失敗する可能性があり、安全に警告を出してスキップします。

---

この README はコード内の docstring と挙動を要約したものです。詳細実装や追加機能については各モジュール（src/kabusys 以下）の docstring を参照してください。必要であれば、README に追記するサンプル設定ファイル（.env.example）や運用手順（デプロイ / systemd / supervisor 用）も作成できます。必要でしたら教えてください。