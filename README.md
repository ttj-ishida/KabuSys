# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム「KabuSys」のコードベースです。本 README は開発者・運用者向けにプロジェクト概要、主な機能、セットアップ手順、実行方法、ディレクトリ構成などを日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下の機能を備えた自動売買フレームワークです。

- 戦略（ファクター計算 / 特徴量解析）による銘柄選定・ウェイト算出
- ポジションサイズ決定・リスク制御（ドローダウン・ポジション上限など）
- Execution Engine による発注（実アカウント / ペーパートレード分離）
- 監視（System / Trade / Risk のポーリングとアラート・Kill Switch）
- AI モジュール（ニュース NLP による銘柄スコア / レジーム判定）
- 検証・レポート出力（ペーパートレード検証レポートなど）
- 設定ウィザード / 設定検証ツールによる運用準備支援

設計上のポイント：
- DuckDB を分析向け DB、SQLite を監視／履歴用に利用
- 環境変数（.env）主体の設定管理。`.env` を自動ロード（オプションで無効化可）
- 本番・ペーパートレードを明確に分離（KABUSYS_ENV）
- LLM（OpenAI）呼び出しはフェイルセーフ設計（エラー時は安全側で継続）

---

## 機能一覧（主なモジュール）

- `kabusys.config` / `config_setup.py` / `validate_config.py`
  - 環境変数 / .env の読み込み、対話式ウィザード、設定検証 CLI
- `kabusys.execution`
  - ExecutionEngine、ブローカーファクトリ、OrderManager、RiskManager 等（発注ロジック）
  - `run_execution.py`：ExecutionEngine 起動スクリプト
- `kabusys.monitoring`
  - SystemMonitor / TradeMonitor / RiskMonitor、KillSwitch、MonitoringEngine、DB 永続化
  - `run_monitoring.py`：監視ポーリングループ起動スクリプト
- `kabusys.portfolio`
  - 銘柄選定、重み算出、セクター上限、レジーム乗数、株数算出ロジック（純粋関数群）
- `kabusys.research`
  - ファクター計算（モメンタム／バリュー／ボラティリティ）や特徴量解析ユーティリティ
- `kabusys.ai`
  - `news_nlp`：ニュース記事を LLM でスコアリングして ai_scores に書き込む
  - `regime_detector`：マクロニュース＋ETF MA200 乖離で市場レジーム判定
- `kabusys.tools`
  - `paper_verification_report.py`：ペーパートレード検証レポート生成スクリプト
- `kabusys.utils`
  - ログ設定 (`logging_setup`)、プロセス優先度／CPU affinity (`process_priority`) 等ユーティリティ

---

## 環境変数（主なもの）

（詳しくは `kabusys.config.Settings` を参照）

- 必須（運用時）:
  - `JQUANTS_REFRESH_TOKEN`
  - `KABU_API_PASSWORD`

- 運用に影響する主要変数（デフォルト値あり）:
  - `KABUSYS_ENV` : `development` | `paper_trading` | `live`（デフォルト: `development`）
    - `paper_trading` の場合、Execution は MockBroker を使用し、DB は `data/paper_trading.db` に分離
  - `DUCKDB_PATH` : DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
  - `SQLITE_PATH` : 監視用 SQLite（デフォルト: `data/monitoring.db`）
  - `PAPER_TRADING_SQLITE_PATH` : ペーパートレード専用 SQLite（デフォルト: `data/paper_trading.db`）
  - `LOG_LEVEL` : ログレベル（`INFO` 等）
  - `OPENAI_API_KEY` : OpenAI を利用する機能で必須（ai モジュール）
  - `MONITOR_POLL_INTERVAL` : 監視ループのポーリング間隔（秒、`run_monitoring.py` で利用）
  - `KILL_FLAG_CLEAR_ON_START` : 起動時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）
  - `LOG_DIR` : ログ出力ディレクトリ（デフォルト: `logs/`）

- 自動ロード:
  - プロジェクトルート（.git または pyproject.toml）を基準に `.env` / `.env.local` を自動でロードします。
  - 自動ロードを無効にする場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

---

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境を作成して有効化
   - 例: python -m venv .venv && source .venv/bin/activate

2. 依存ライブラリをインストール
   - requirements ファイルがある場合:
     - pip install -r requirements.txt
   - 主要なパッケージ:
     - duckdb
     - psutil
     - openai
     - pyyaml（設定検証で YAML を検証する場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

3. ディレクトリ作成
   - data/ と logs/ を作成（`setup_logging` とデータ保存先）
     - mkdir -p data logs

4. 環境変数設定
   - `python -m kabusys.config_setup` を実行して .env を対話作成することを推奨
   - もしくは `.env` を手動で作成して必要な環境変数を設定する

5. 設定検証（起動前確認）
   - python -m kabusys.validate_config
   - 本番環境では `--strict` を付けて警告も失敗扱いにできます

注: 実運用では KABUSYS_ENV に応じて設定値（特に DB パス、Kill Switch 動作）を確認してください。

---

## 使い方（起動／CLI）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution Engine 起動（発注エンジン）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、ペーパートレード用 DB (`PAPER_TRADING_SQLITE_PATH`) に記録されます
    - 起動時に `data/stop_requested.flag` が存在すると起動せず終了します
    - `data/execution.pid` に PID を書く仕組み（`Settings.pid_file_path`）

- Monitoring 起動（ポーリング監視）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒数で上書きできます（デフォルト 60 秒）
  - 監視は Settings の `sqlite_path` を常に使用（環境に関わらず本番 sqlite_path を参照）

- 停止方法 / Kill Switch
  - `data/stop_requested.flag` を作成すると `run_execution` / `run_monitoring` のループが検知して停止します（運用上の手動停止用）
  - Kill Switch（自動停止判定）は `data/kill.flag` を書き込み、ExecutionEngine に停止信号を送ります（Monitoring が判定して書き込む）
  - Kill Switch を取り扱う場合は `KILL_FLAG_CLEAR_ON_START` の設定に注意（本番では自動クリアを無効化推奨）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD  --to YYYY-MM-DD
    - --db PATH （`PAPER_TRADING_SQLITE_PATH` を上書き）
  - 出力は標準出力に整形レポートを表示（稼働率、成功率、P95 レイテンシなど）

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要: `OPENAI_API_KEY` を設定
  - 関数呼び出し例（内部 API）:
    - `kabusys.ai.score_news(conn, target_date, api_key=None)`
    - `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

---

## 実装上の注意・運用ノウハウ

- Logging:
  - `kabusys.utils.logging_setup.setup_logging(app_name="execution")` 等で一貫したログ設定を行います
  - デフォルトで日次ローテーション（30 日分保持）と stdout 出力を行います

- プロセス優先度:
  - `set_process_priority("high")` を起動直後に呼んでいるスクリプトがあります（管理者権限で失敗する場合は警告でスキップ）

- DB マイグレーション:
  - `init_monitoring_db` は起動時にテーブル作成や簡単なカラム追加（冪等）を行います

- データ鮮度とルックアヘッド防止:
  - AI / 研究モジュールは日付の扱いに注意し、`date.today()` を直接参照しない設計になっています（ルックアヘッドバイアス対策）

- テスト時のヒント:
  - 自動 .env ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
  - AI 呼び出しをモックしたい場合、各モジュール内の API 呼び出しラッパー関数をパッチする設計になっています（テスト用に想定）

---

## ディレクトリ構成（抜粋）

以下は主要ファイル・パッケージの一覧（`src/kabusys` 配下）：

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings
  - config_setup.py               — .env 対話ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py            — SQLite 永続層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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
  - monitoring/ (上記)
  - tools/
    - paper_verification_report.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

プロジェクトルート（リポジトリ直下）には想定される補助ディレクトリ・ファイル:
- data/              — デフォルトの SQLite ファイルや flag, pid ファイルを置く（runtime）
  - stop_requested.flag
  - kill.flag
  - monitoring.db
  - paper_trading.db
  - execution.pid
- logs/              — ログファイル
- config/            — YAML ベースの設定テンプレート（system_config.yaml 等）
- pyproject.toml / setup.py 等

---

## よくある操作例

- .env を作る（対話）
  - python -m kabusys.config_setup

- 設定チェック
  - python -m kabusys.validate_config --strict

- 監視プロセスを起動（標準）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジンを起動（ペーパートレード）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Kill Switch 手動トリガ
  - echo "reason" > data/kill.flag

- 停止フラグ（全プロセス用）
  - touch data/stop_requested.flag
  - 削除: rm data/stop_requested.flag

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 参考・補足

- コードの詳細設計意図は各モジュールの docstring / コメントに記載しています。特に AI 関連・リサーチ・ポートフォリオ構築ロジックは設計ノート（別ドキュメント）に基づいています。
- 本 README はコードベースから抽出した主な使い方と注意点をまとめたものです。運用開始前に `validate_config` を必ず実行し、`.env` の値（特に本番用トークンや kill flag の挙動）を十分にご確認ください。

---

必要であれば、インストール用の requirements.txt のサンプルや systemd / supervisor 用のユニットファイル、運用手順書（SOP）テンプレートも作成できます。どの情報がさらに欲しいか教えてください。