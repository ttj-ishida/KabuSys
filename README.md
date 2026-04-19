# KabuSys — 日本株自動売買システム（README）

このドキュメントはリポジトリ内のコードベースを元に作成した README です。ローカル開発・ペーパートレード・本番実行に必要な概要、セットアップ、使い方、ディレクトリ構成をまとめています。

補足：
- コードは Python モジュール `kabusys` を想定しています（エントリポイントは `python -m kabusys.<module>`）。
- 実行時の振る舞いは主に環境変数（.env）で制御します。デフォルトのパスは `data/`、ログは `logs/` に出力されます。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したシステムです。主な機能は次の通りです。

- 戦略（ファクター計算・ポートフォリオ構築）やポジションサイジングのロジック（research / portfolio）
- 発注・実行のための ExecutionEngine（実口座・ペーパートレード双方に対応）
- システム監視・リスク監視・アラート（monitoring）
- ニュース・LLM を用いた AI モジュール（ニュースセンチメント、レジーム判定）
- ペーパートレード検証レポート生成ツール（tools）
- 設定ウィザード・設定検証コマンド（config_setup / validate_config）

設計方針：
- DuckDB を分析向けデータ格納に使用、SQLite を監視・発注履歴用に使用
- Paper Trading は本番 DB と完全に分離（別 SQLite ファイル）
- OpenAI API を使った処理は API キー必須だが、失敗時はフォールバックやフェイルセーフを用意

---

## 機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証ツール（python -m kabusys.validate_config）
- ExecutionEngine 起動（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、ペーパートレード DB（data/paper_trading.db 等）へ記録
  - 停止制御: `data/stop_requested.flag` を作成すると安全に終了
  - Kill Switch: `data/kill.flag` を書くとエンジンを強制停止させる仕組みあり
- Monitoring（python -m kabusys.run_monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期実行、監視ログを SQLite に保存
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
- AI 機能
  - ニュース NLP（kabusys.ai.news_nlp）: OpenAI を用いて銘柄ごとのセンチメントを計算し ai_scores テーブルへ格納
  - レジーム判定（kabusys.ai.regime_detector）: ETF MA とマクロセンチメントを組合せ日次で regime を判定
- 研究・分析機能（kabusys.research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）計算等
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選択、重み付け、ポジションサイズ計算、セクターキャップ適用など
- ペーパートレード検証レポート（kabusys.tools.paper_verification_report）

---

## 必要条件（依存関係）

最小限のパッケージ例（プロジェクトで管理されている requirements.txt があればそれを使用してください）：

- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- pyyaml（設定ファイル検証を行う場合）
- その他プロジェクト固有の依存（requests 等）があれば requirements.txt を参照

例:
pip install -r requirements.txt

必須環境変数（主要）:
- JQUANTS_REFRESH_TOKEN（J-Quants API）
- KABU_API_PASSWORD（kabuステーション API）
- OPENAI_API_KEY（AI 機能を使う場合）
- KABUSYS_ENV（development / paper_trading / live） — デフォルト: development

ストレージパス（デフォルト）:
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_DIR: logs/
- PID/フラグ: data/execution.pid, data/stop_requested.flag, data/kill.flag

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ...

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - requirements.txt がない場合は最低限 duckdb, psutil, openai, pyyaml をインストール

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - ウィザードで各種環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABUSYS_ENV など）を設定できます。
   - もしくは .env を手動で作成（.env は Git にコミットしないこと）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）になります。

6. DB 初期化
   - 実行スクリプト（run_monitoring / run_execution）が起動時に必要なテーブルを自動作成します。手動作成は不要です。

---

## 使い方（主要コマンド）

- 設定ウィザード
  - python -m kabusys.config_setup
    - .env を対話式で生成・更新します。

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は別 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し MockBroker に記録します。
    - 起動時に `data/stop_requested.flag` が存在する場合は起動せず終了します。
    - 実行中に `data/stop_requested.flag` を作成すると安全に停止します（監視プロセスからも止められる）。

- 監視プロセス起動
  - python -m kabusys.run_monitoring
    - 環境変数 MONITOR_POLL_INTERVAL（秒）で監視間隔を指定できます（デフォルト 60 秒）。
    - 監視は run_monitoring 内で Settings の sqlite_path を参照して監視用 DB に書き込みます（環境にかかわらず本番 sqlite_path を使用）。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- AI / レジーム判定・ニューススコアリング
  - AI 機能は OpenAI API キーが必要です（OPENAI_API_KEY 環境変数 または関数引数を指定）。
  - 例: kabusys.ai.score_news を呼ぶスクリプト経由で利用します。

- ログ
  - デフォルトで logs/<app_name>.log に日次ローテーションで保存されます（30日分保持）。
  - app_name は起動スクリプトが指定（"execution" / "monitoring" 等）。

停止とフラグファイルについて:
- data/stop_requested.flag: 実行スクリプト（monitoring / execution）のループを安全に終了させるためのフラグ。手動で作成するとプロセスが検出して終了します。
- data/kill.flag: Kill Switch により作成されることがあり、ExecutionEngine を強制停止するトリガーとして運用されます。KillSwitch クラスが理由テキストを書き込みます。
- data/execution.pid: ExecutionEngine が PID を保管するファイル。プロセス優先度や監視で使用されます。

プロセス優先度:
- 起動スクリプトは set_process_priority("high") を呼び出します。psutil を利用してプラットフォームに合わせて優先度を設定します。権限不足時は警告が出ますが動作は継続します。

---

## よくある運用例

1. 開発環境での試行
   - KABUSYS_ENV=development（デフォルト）
   - python -m kabusys.config_setup
   - python -m kabusys.validate_config
   - python -m kabusys.run_monitoring（監視を確認）
   - python -m kabusys.run_execution（Engine の挙動を確認）

2. ペーパートレード（単独で試験）
   - .env で KABUSYS_ENV=paper_trading を指定
   - python -m kabusys.run_execution（mock ブローカーで data/paper_trading.db に書き込み）
   - 終了後、python -m kabusys.tools.paper_verification_report --from ... --to ... で評価

3. 本番デプロイ（注意事項）
   - KABUSYS_ENV=live に設定する前に validate_config の警告・設定を十分に確認
   - LINE 通知 (LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID) を設定するとアラートを受け取れる
   - KILL_FLAG_CLEAR_ON_START を本番で 1 にするのは危険（デフォルト 0 を推奨）

システムデーモン化の例（systemd）— 単純例:
- /etc/systemd/system/kabusys-execution.service (簡略)
  - ExecStart=/path/to/venv/bin/python -m kabusys.run_execution
  - Restart=on-failure
  - EnvironmentFile=/path/to/.env（あるいは .env を読み込む仕組み）

---

## ディレクトリ構成（主要ファイル・モジュール）

リポジトリの主要構成（src/kabusys 以下を抜粋）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数/.env 自動読み込み・Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py            — ニュースを LLM でスコアリング
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py       — SQLite 用永続層（テーブル初期化・読み書き）
    - system_monitor.py      — システム / データ鮮度監視
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag の管理
    - monitoring_engine.py   — 各モニタの束ね役
    - (他: trade_monitor.py, alert_manager.py 等が想定)
  - execution/
    - execution_engine.py    — 実行エンジン本体（EngineConfig など）
    - broker_factory.py      — ブローカークライアント生成（Mock / Live 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - research/
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — IC, 統計サマリ等
  - portfolio/
    - portfolio_builder.py   — 候補選定、重み計算
    - position_sizing.py     — 発注株数決定
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - data/                    — （実行時に使用される）data ディレクトリ（DB / pid / flag）
  - logs/                    — デフォルトログディレクトリ（run 時に作成される）

補足:
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

---

## 注意点・運用上の留意事項

- .env は絶対にリポジトリにコミットしないこと（機密情報を含むため）。
- 本番環境で KABUSYS_ENV=live を設定する場合は、LINE 通知・Kill Switch 設定・KILL_FLAG_CLEAR_ON_START の値などを十分に確認してください。
- OpenAI を使用する処理は API キーと利用料金が発生します。レート制限・失敗時のハンドリングは実装されていますが、利用ルールを遵守してください。
- DuckDB/SQLite は軽量 DB ですが、運用中のファイルバックアップやディスク容量に注意してください（monitoring はディスク使用率を監視します）。
- process priority や CPU affinity の設定時に権限不足で失敗することがあります（警告が出ますが、処理自体は続行されます）。

---

## 参考コマンドまとめ

- .env ウィザード:
  - python -m kabusys.config_setup
- 設定チェック:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- ペーパートレード検証:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はリポジトリ内のコード（モジュール docstring・実装）に基づいて記述しています。追加のユーティリティ、設定ファイル（config/*.yaml）、外部スクリプト等がある場合はそれらも合わせて参照してください。質問や README に追記してほしい内容があれば教えてください。