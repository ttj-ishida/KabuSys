# KabuSys

日本株自動売買システムのコアライブラリ（README）。  
この README はリポジトリ内の主要なスクリプト / モジュールの使い方、環境変数、セットアップ手順、ディレクトリ構成をまとめたものです。

注意: 実行ファイルはモジュールとして起動することを想定しています（例: `python -m kabusys.run_monitoring`）。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視のためのライブラリ群です。主な役割は次のとおりです。

- 市場データ（DuckDB）を使ったファクター計算・研究（research）
- ポートフォリオ構築・ポジションサイズ計算（portfolio）
- 発注エンジン（ExecutionEngine）・注文管理（execution）
- システム稼働・注文挙動などの監視（monitoring）
- ニュース NLP によるセンチメント算出（AI モジュール）
- 運用支援ツール（.env 作成ウィザード / 設定検証 / ペーパートレード検証レポート）

設計方針の一部:
- DuckDB を分析用 DB、SQLite を監視・発注（履歴）用 DB として使用
- 実行環境（本番 / ペーパートレード / 開発）を環境変数 `KABUSYS_ENV` で切替
- フェイルセーフを重視（API 失敗時はフォールバックして継続など）

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - 環境変数 / .env の読み込みと Settings クラス（デフォルト値・必須チェック）
- kabusys.config_setup
  - 対話式ウィザードで `.env` を作成/更新
- kabusys.validate_config
  - 起動前チェック（必須環境変数、DB パス、config YAML の存在等）
- kabusys.utils
  - logging の統一設定（ローテーションファイル・stdout）
  - プロセス優先度 / CPU affinity の設定ユーティリティ
- kabusys.monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - kill switch（条件により data/kill.flag を書き込む）
  - 監視データを保存する SQLite 永続化レイヤ（monitoring_db）
  - run_monitoring 起動スクリプト（ポーリング監視）
- kabusys.execution
  - ExecutionEngine 起動スクリプト（run_execution） — 本番 or ペーパートレードで振る舞いを切替
  - ブローカークライアントファクトリ（本番は実ブローカー／paper_trading では Mock）
- kabusys.portfolio
  - 銘柄選定（select_candidates）・重み計算（equal/score）
  - セクターキャップ適用・レジーム乗数（risk_adjustment）
  - ポジションサイズ計算（position_sizing）
- kabusys.research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算・IC 計算など（feature_exploration）
- kabusys.ai
  - news_nlp: OpenAI を使ったニュースセンチメントの集計・ai_scores への書き込み
  - regime_detector: ETF とマクロニュースを組合せた市場レジーム判定
- kabusys.tools
  - paper_verification_report: ペーパートレード DB を集計して PASS/FAIL 判定のレポートを生成

---

## 前提（推奨）依存関係

少なくとも Python 3.10 以上を想定（型注釈の | 演算子等を使用）。主要パッケージ:

- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（`validate_config` の YAML 検証を有効にしたい場合。任意）

インストール例（仮）:
pip install duckdb psutil openai PyYAML

※開発時は requirements ファイルがあればそれに従ってください。

---

## セットアップ手順

1. リポジトリをクローン／チェックアウトし、プロジェクトルートへ移動。

2. Python 仮想環境を作成して依存パッケージをインストール:
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）
   - pip install --upgrade pip
   - pip install duckdb psutil openai PyYAML

3. 環境変数の準備（.env）
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - ウィザードで設定後、設定を検証:
     - python -m kabusys.validate_config
     - 必須環境変数の未設定や config/*.yaml の欠落を検出できます。
   - もしくは直接環境変数を設定しても可。自動ローディングはプロジェクトルートの `.env` / `.env.local` を読み込みます（必要に応じて `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化可能）。

4. データディレクトリ（data）やログディレクトリ（logs）は起動時に自動作成されますが、権限等で失敗することがあるため事前に作成しておくと安心です:
   - mkdir -p data logs

5. OpenAI 機能を使う場合は `OPENAI_API_KEY` を環境変数に設定してください。

---

## 主要な環境変数（抜粋とデフォルト）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG/INFO/…） — デフォルト: INFO
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（監視 DB、デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
- PAPER_FILL_MODE: ペーパートレード時の fill 挙動（instant|partial|never|reject） — デフォルト: instant
- PID_FILE_PATH: data/execution.pid（デフォルト）
- KILL_FLAG_PATH: data/kill.flag（デフォルト）
- KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に kill.flag を自動クリア（本番では 0 推奨）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必要）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）

---

## 使い方（主要スクリプト）

- 監視ループを起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 実行時に `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を変更できます（秒、1以上）。
  - run_monitoring は監視 DB として sqlite_path（Settings.sqlite_path）を使用します：Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を参照します。
  - 停止: プロジェクトルートの `data/stop_requested.flag` が存在するとループを終了します（ファイルの作成で停止を指示）。

- 実行エンジンを起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、専用の paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）に記録されます（本番 DB と完全に分離）。
  - 起動前に `data/stop_requested.flag` が既にある場合は起動しません。
  - 実行中、`data/stop_requested.flag` が作成されるとエンジンは停止します。
  - 実行時にプロセス優先度を "high" に設定します（psutil の権限に依存）。

- .env の作成（ウィザード）
  - python -m kabusys.config_setup
  - 対話式で .env を生成／更新します。生成後は `python -m kabusys.validate_config` でチェックしてください。

- 設定検証
  - python -m kabusys.validate_config [--strict]
  - 必須環境変数や DB パス、config/*.yaml の存在を確認できます。`--strict` を付けると警告も失敗扱い（exit 1）。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB は `data/paper_trading.db`（環境変数 `PAPER_TRADING_SQLITE_PATH` で上書き可）。
  - 出力: 稼働率・注文成功率・レイテンシなどを集計し PASS/FAIL 判定を表示。

- AI / リサーチ関数（ライブラリとして利用）
  - ニューススコア算出:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=...)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=...)
  - ファクター計算:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic 等

---

## 停止 / Kill Switch / フラグについて

- 停止フラグ
  - data/stop_requested.flag
    - run_monitoring / run_execution はこのファイルの存在を監視しています。存在すると安全に終了します。
    - 停止させたい場合は `touch data/stop_requested.flag`（作成）を行います。

- Kill Switch（運用上の自動停止）
  - KillSwitch は監視の結果（例: ドローダウン超過、ポジション上限超過）により `data/kill.flag` を書き込み、ExecutionEngine を停止させるためのシグナルとします。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動的に kill.flag を削除しますが、本番環境では 0 を推奨します。

- PID ファイル
  - run_execution は `data/execution.pid` を PID ファイルとして使用します（Settings.pid_file_path で変更可）。

---

## ロギング

- 共通の logging 設定ユーティリティ: kabusys.utils.logging_setup.setup_logging
  - stdout（StreamHandler）と日次ローテーションのファイルハンドラ（logs/<app_name>.log）を設定します。
  - デフォルトログディレクトリ: logs/
  - ログレベルは `LOG_LEVEL` 環境変数で制御（CLI 引数レベルも可）。

---

## ディレクトリ構成（抜粋）

リポジトリ内の主要ファイル / ディレクトリ（src/kabusys 以下を想定）

- src/kabusys/
  - __init__.py
  - config.py                  — Settings / .env 自動読み込み
  - config_setup.py            — .env 対話ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_monitoring.py          — 監視ポーリングループ起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py         — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py        — システム・データ鮮度チェック
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - trade_monitor.py         — （注文遅延・異常監視: 実装あり）
    - monitoring_engine.py     — 複数モニタの束ね
    - kill_switch.py           — kill.flag 管理
    - alert_manager.py         — 通知管理（LINE 等）
  - execution/
    - execution_engine.py      — 実行エンジン（EngineConfig 等）
    - broker_factory.py        — BrokerClientFactory（本番 / mock 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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

その他:
- data/                       — DB ファイルやフラグファイルを置く想定ディレクトリ（実行時に作成される）
- logs/                       — ログ出力先（自動生成）

---

## 開発・運用の注意点

- 環境切替
  - KABUSYS_ENV によって挙動が変わります（paper_trading で MockBroker を使う等）。本番（live）環境での設定ミスに注意してください（validate_config は警告を出します）。
- データベース
  - DuckDB は分析用に大量データを保持する想定。SQLite は監視・発注履歴を小規模に扱う設計です。
- OpenAI / API 利用
  - OpenAI 呼び出しは API の失敗やレート制限に対してリトライ（指数バックオフ）を行う設計ですが、APIキーは必須です（AI 機能利用時）。
- フェイルセーフ
  - 監視側は「API 失敗時にはフェイルセーフで継続」「部分失敗時に既存データを保護」などの思想が反映されています。
- ログ・ファイルの権限
  - 実行環境（systemd / cron 等）によってはログ・データディレクトリの書き込み権限に注意してください。

---

## よく使うコマンド まとめ

- .env を生成（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループ起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン起動
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または DB を明示: python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- Kill / Stop 制御
  - 停止要求（監視 / 実行に対して）: touch data/stop_requested.flag
  - kill.flag（Kill Switch により書き込まれる）を確認 / 削除:
    - cat data/kill.flag
    - rm data/kill.flag

---

必要であれば、README に以下を追加します:
- 具体的な設定例（.env.example からの記入例）
- systemd / supervisor 用のユニットファイル例
- 詳細な API ドキュメント（各モジュールの関数・返り値仕様）
- テスト手順・CI 設定

どの情報を追加したいか教えてください。