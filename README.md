# KabuSys

日本株向け自動売買システムのコアライブラリ群（ライブラリ／起動スクリプト／解析ツール群）。

本 README はこのリポジトリ内の主要スクリプトやモジュールの概要、セットアップ手順、実行方法、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は以下の機能を持つモジュール群で構成されています。

- 市場データからファクターを算出するリサーチ（DuckDB を用いたオフライン解析）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- ExecutionEngine（実口座／ペーパートレード用ブローカラッパー、注文管理、リスク制御）
- 監視（System / Trade / Risk の定期チェック、Kill Switch による停止）
- AI モジュール（OpenAI を使ったニュースセンチメント評価・レジーム判定）
- 運用支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート 等）

設計方針の一部：
- DuckDB を解析用 DB として利用。SQLite は監視・発注ログ等の永続化に使用。
- Paper Trading（`KABUSYS_ENV=paper_trading`）は本番 DB と分離（専用 SQLite）。
- 外部 API（OpenAI 等）は環境変数でキーを指定し、フェイルセーフを考慮した実装。

---

## 主な機能一覧

- 環境設定ウィザード（.env の対話式生成／更新）
  - `python -m kabusys.config_setup`
- 設定検証 CLI（.env と config/*.yaml の妥当性チェック）
  - `python -m kabusys.validate_config [--strict]`
- Execution 起動スクリプト（実取引 / ペーパートレードを分離して起動）
  - `python -m kabusys.run_execution`
  - Paper Trading 時は MockBroker を使用し、デフォルトで `data/paper_trading.db` に記録
- Monitoring 起動スクリプト（SystemMonitor のポーリングループ）
  - `python -m kabusys.run_monitoring`
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）
  - Monitoring は環境にかかわらず本番の `SQLITE_PATH` を使用する（実装上の仕様）
- モニタリング・エンジン（System / Trade / Risk の統合、アラート発行、Kill Switch）
- AI モジュール
  - `kabusys.ai.score_news`：ニュース記事を OpenAI で評価して ai_scores に格納
  - `kabusys.ai.score_regime`：ETF の MA とマクロニュースの LLM 評価を合成して市場レジーム判定
- ツール
  - `python -m kabusys.tools.paper_verification_report`：ペーパートレード実績の検証レポートを生成

---

## セットアップ手順

前提：
- Python 3.10 以上（`X | Y` 型注釈などを使用しているため）
- Git リポジトリのルートがあること（自動 .env ロードに使用）

推奨パッケージ（最低限）：
- duckdb
- psutil
- openai
- sqlalchemy は必須ではない（プロジェクトにより必要な追加依存がある場合があります）
- PyYAML（`validate_config` が YAML パースを行う場合に推奨）

例（pip）:
```
python -m pip install duckdb psutil openai PyYAML
```

.env（環境変数）の準備：
- リポジトリルートに `.env` を配置するか、`.env.local` を作成します。
- 自動ロードはデフォルトで有効。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- 対話式ウィザードで `.env` を生成するには:
  ```
  python -m kabusys.config_setup
  ```

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

よく使う環境変数（主なもの）
- KABUSYS_ENV: execution 環境（development / paper_trading / live）（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必要）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング秒数（run_monitoring 用、デフォルト 60）

ログディレクトリ：
- デフォルトは `logs/`。`LOG_DIR` 環境変数で変更可能。
- ログは日次ローテーションで保持（デフォルト 30 日分）。

必要なデータディレクトリ：
- `data/`：実行時の pid / flag / sqlite ファイル等を格納します（例: data/execution.pid, data/kill.flag, data/monitoring.db）

---

## 使い方（主要コマンド）

1. .env を作成／更新
   ```
   python -m kabusys.config_setup
   ```

2. 設定検証（起動前に実行を推奨）
   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

3. ExecutionEngine を起動
   - 本番（または設定にしたがって）:
     ```
     python -m kabusys.run_execution
     ```
   - 注意:
     - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用して `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に記録します（本番 DB と分離）。
     - 起動時に `data/stop_requested.flag` が存在すると起動をスキップします。
     - Execution は `data/execution.pid` を書きます。

4. Monitoring を起動
   ```
   python -m kabusys.run_monitoring
   ```
   - ポーリング間隔を環境変数で上書き:
     ```
     MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
     ```
   - Monitoring は KABUSYS_ENV にかかわらず `SQLITE_PATH`（監視 DB）を使用します（設計上の仕様）。
   - 停止には `data/stop_requested.flag` を作成するか、CTRL+C。

5. ペーパートレード検証レポート
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   ```
   - デフォルト DB は `data/paper_trading.db`。`--db` または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。

6. AI 機能（ニューススコア／レジーム判定）
   - OpenAI API キーを設定（例: `OPENAI_API_KEY` 環境変数）。
   - プログラム内で呼び出す:
     - ニューススコア: `kabusys.ai.score_news(conn, target_date, api_key=None)`
     - レジーム判定: `kabusys.ai.score_regime(conn, target_date, api_key=None)`

停止／Kill Switch の運用：
- `KillSwitch` は内部ルール（ドローダウン、ポジション上限等）で `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送ります。
- `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

---

## 設定ファイル / データファイル（既定値）

- .env / .env.local（自動ロード対象）
- config/*.yaml（システム設定ファイル群。`validate_config` で存在チェック／パース確認）
  - system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml
- DuckDB: data/kabusys.duckdb（`DUCKDB_PATH`）
- SQLite (monitoring): data/monitoring.db（`SQLITE_PATH`）
- SQLite (paper): data/paper_trading.db（`PAPER_TRADING_SQLITE_PATH`）
- ログ: logs/<app_name>.log（`LOG_DIR`）

---

## ディレクトリ構成（概要）

以下は主要なモジュールと役割の概観（`src/kabusys/` 以下）:

- kabusys/
  - __init__.py
  - config.py
    - Settings クラス、.env 自動読み込みロジック
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前チェック CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（pid / stop flag の扱い）
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト
  - ai/
    - news_nlp.py: ニュースを OpenAI でスコアリングして ai_scores へ書込み
    - regime_detector.py: ETF MA とマクロニュースを使ったレジーム判定
  - monitoring/
    - monitoring_db.py: SQLite のテーブル作成 / CRUD
    - system_monitor.py: CPU/MEM/DISK, データ鮮度, 実行プロセス監視
    - trade_monitor.py: （取引関連の監視、trade_logs 参照）
    - risk_monitor.py: ドローダウン・ポジション上限監視
    - kill_switch.py: kill.flag 管理
    - monitoring_engine.py: 各 monitor を束ねて実行
    - alert_manager.py: アラート発行（LINE 等の実装に依存）
  - execution/
    - execution_engine.py: 実行エンジン本体
    - broker_factory.py: ブローカクライアント生成（Mock/実装分岐）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py 等
  - portfolio/
    - portfolio_builder.py: 候補選定・重み計算
    - position_sizing.py: 発注株数計算・上限調整
    - risk_adjustment.py: セクターキャップ・レジーム乗数
  - research/
    - factor_research.py: モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py: 将来リターン・IC・統計要約
  - data/
    - pipeline.py, stats.py など（DuckDB 利用のデータ操作補助）
  - tools/
    - paper_verification_report.py: ペーパートレード検証レポート

（実際の repo では更に細かいファイル・補助モジュールが存在します）

---

## 運用上の注意とベストプラクティス

- 本番環境で `KABUSYS_ENV=live` を設定すると重大な動作が行われます。`validate_config` を実行して設定を十分に確認してください。
- `.env` は絶対にリポジトリへコミットしないでください（config_setup のヘッダにも注意書きあり）。
- Monitoring は本番監視用の SQLite を使用する仕様になっています（run_monitoring が本番 DB を使う点に注意）。
- Kill Switch / stop flag の運用方法を明確にしておくと安全な停止運用が可能です。
- AI 機能を利用する際は OpenAI の API 使用料に注意してください。呼び出し回数の管理やバッチ処理の実装が行われていますが、実運用前に十分なテストを推奨します。

---

## トラブルシューティング

- .env の自動ロードを無効化したい場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- ログディレクトリ作成に失敗するとコンソール（stdout）出力のみで継続します。`LOG_DIR` を書き込み可能な場所に設定してください。
- `validate_config` で PyYAML 未インストールの警告が出る場合、`pip install PyYAML` してください（YAML 構成ファイルのパースチェックがスキップされます）。
- Execution / Monitoring の強制停止:
  - 正常停止: CTRL+C またはプロセスに SIGINT。
  - 運用的停止: `data/stop_requested.flag` を作成すると run_* スクリプト内のループが検知して終了します。
  - Kill Switch による停止: システムが条件を満たすと `data/kill.flag` が書き込まれ、Execution 側はそれを参照して停止します。

---

この README は主要なポイントをまとめたものです。詳細は各モジュールのドキュメント文字列（docstring）やソースコードのコメントを参照してください。必要であれば、README の英語版や追加の運用手順書（デプロイ手順、systemd 起動ユニット例、監視設定例）を作成します。