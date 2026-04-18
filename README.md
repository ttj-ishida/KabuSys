# KabuSys

日本株自動売買システムの一部を構成する Python モジュール群です。ポートフォリオ構築、ポジションサイジング、モニタリング、ExecutionEngine 起動用スクリプト、Paper Trading 検証ツール、ニュース NLP / レジーム判定などの機能を提供します。

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュール群で構成されています。

- 実行エンジン（ExecutionEngine）: 発注ロジック・注文管理・リスク管理を組み合わせてトレードを実行。
- 監視 (Monitoring): システム稼働状況、注文ログ、リスク指標の定期ポーリングとアラート発行。
- ポートフォリオ構築: 候補選定・重み計算・ポジションサイズ決定・セクター制約の適用。
- 研究（Research）: DuckDB を使ったファクター計算・特徴量解析。
- AI モジュール: ニュースの NLP によるセンチメントスコアリング、レジーム判定（OpenAI を利用）。
- ユーティリティ: ロギングセットアップ、プロセス優先度設定、設定管理 CLI など。
- ツール: Paper Trading の検証レポート生成スクリプト等。

設計上のポイント:
- DuckDB／SQLite を用いたデータ格納・解析
- 本番/ペーパートレード分離（`KABUSYS_ENV=paper_trading` 時は Paper DB を使用）
- 外部 API（kabu ステーション、J-Quants、OpenAI 等）は設定により切り替え
- ローカルファイル（`data/kill.flag` 等）でプロセス制御

---

## 主な機能一覧

- 環境設定ウィザード（.env 作成）: python -m kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml の検証）: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
  - `KABUSYS_ENV=paper_trading` の時は MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）へ記録
- Monitoring 起動スクリプト: python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒、デフォルト 60）
  - Monitoring は環境に関係なく本番 `SQLITE_PATH` を使用して監視ログを永続化
- Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report
- AI スコアリング:
  - kabusys.ai.score_news: raw_news を LLM で評価して ai_scores に書き込み
  - kabusys.ai.regime_detector.score_regime: レジーム（bull/neutral/bear）判定とテーブル書き込み
- ポートフォリオ関連:
  - 候補選定・重み算出 (等金額 / スコア加重)
  - セクター上限適用、レジーム乗数
  - ポジションサイズ計算（lot 単位、リスクベース・等分配・スコアベース）
- ロギング: 統一的な logging 設定（コンソール stdout + 日次ローテートファイル）
- プロセス管理ユーティリティ: プロセス優先度 / CPU affinity の設定

---

## 前提 / 必要ライブラリ

（プロジェクトの requirements.txt が別にある想定です。最小限の利用ライブラリ例）

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（`validate_config` で YAML 検証を行う場合）
- （sqlite3 は標準ライブラリ）

仮想環境を作成して依存関係をインストールしてください。

例:
- python -m venv .venv
- source .venv/bin/activate
- pip install -r requirements.txt

---

## セットアップ手順（基本）

1. リポジトリをクローンしてワークディレクトリに移動
2. 仮想環境を作成・有効化
3. 依存ライブラリをインストール（duckdb, psutil, openai, pyyaml 等）
4. 環境変数の準備
   - 対話式で .env を作る: python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに `.env` を作成（.env.example を参照）
5. 設定検証: python -m kabusys.validate_config
   - `--strict` を付けると警告も失敗扱い
6. データディレクトリ（デフォルト: data/）やログディレクトリ（デフォルト: logs/）が自動で作成されますが、必要に応じて権限や所有者を確認してください。

自動 `.env` ロードについて:
- デフォルトでプロジェクトルートの `.env` / `.env.local` を自動読み込みします。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 重要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能利用時)
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - paper_trading の場合、ExecutionEngine は PAPER_TRADING_SQLITE_PATH に記録
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定挙動）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- LOG_LEVEL（デフォルト: INFO）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知用、任意）
- MONITOR_POLL_INTERVAL（監視ループのポーリング間隔秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか、開発用）

注意:
- Monitoring（run_monitoring）は環境にかかわらず本番の `SQLITE_PATH` を使って監視ログを書きます（設計上の挙動）。
- ExecutionEngine は paper_trading 環境であれば paper db を使い、本番 DB と完全分離します。

---

## 起動・利用方法

- 設定ウィザード（対話式）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（デーモン化等は各自で管理）:
  - python -m kabusys.run_execution
  - 停止はプロジェクトルートの `data/stop_requested.flag` を作成するとループが検知して停止します。
  - ExecutionEngine には pid ファイル（デフォルト data/execution.pid）が使われます。

- Monitoring を起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 停止は `data/stop_requested.flag` を作成するか Ctrl+C

- Kill Switch（Execution 停止用）:
  - `data/kill.flag` を書き込むと ExecutionEngine に停止シグナルを送れます（KillSwitch が評価して書き込む仕組み）。
  - Execution 起動時に `KILL_FLAG_CLEAR_ON_START=1` が設定されていると起動時に kill.flag を自動クリアする挙動になります（本番では 0 推奨）。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。`--db PATH` や環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。

- AI モジュールの利用（プログラムから呼び出す）:
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key="...") など（DuckDB 接続を渡して呼び出す）
  - regime 判定: kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key="...")

---

## ログ

- ログはデフォルトで stdout（コンソール）とファイル（logs/<app_name>.log）に出力されます。
- 日次ローテーション（30 日分保持）設定済み。
- ログレベルは `LOG_LEVEL` 環境変数または `setup_logging` の引数で調整できます。

---

## 停止・制御フラグ (ファイルベース)

- data/stop_requested.flag
  - run_execution / run_monitoring のループを安全に停止するために監視されるファイル。
  - ファイルが存在すると起動スクリプトは終了します。

- data/kill.flag
  - Kill Switch が作成するファイル。ExecutionEngine に対して停止シグナルを送る用途で用いる。
  - `KILL_FLAG_CLEAR_ON_START` の設定に注意。

---

## ディレクトリ構成（主なファイル・モジュール）

注: 実際は src/kabusys 配下にパッケージが配置されています。簡略ツリー:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理、自動 .env 読み込み
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前チェック CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py       — 共通ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity
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
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — レジーム判定（OpenAI + MA）
    - __init__.py
  - monitoring/
    - monitoring_db.py       — SQLite 監視 DB 層
    - system_monitor.py
    - trade_monitor.py       — （TradeMonitor 実装ファイルが存在）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラート送信用モジュール）
  - portfolio/, research/, ai/ など（上と重複）
  - その他: execution/（ExecutionEngine 関連）、data/（実行時ファイル群）

---

## 注意事項 / 運用上のヒント

- 本番環境（KABUSYS_ENV=live）では `LINE_CHANNEL_ACCESS_TOKEN` や `LINE_USER_ID` を設定してアラート配信を確実にしてください。
- `.env` は機密情報を含むため決して Git にコミットしないでください（config_setup でもその旨注意書きあり）。
- Monitoring は設計上、本番 sqlite_path を使ってログを永続化します。試験的に Monitoring を動かす場合も DB パスに注意してください。
- AI 機能を使う場合は OpenAI API の利用料金やレートリミットに注意してください。モジュールはリトライやバックオフを備えていますが、実運用ではコスト・レート管理が必要です。
- psutil によるプロセス優先度変更や CPU affinity は OS 権限により失敗する場合があります。ログに警告が出ますが、処理自体は継続されます。

---

## 参考コマンドまとめ

- .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定チェック
  - python -m kabusys.validate_config
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば、この README を README.md として保存するための具体的なテンプレート変更や、各モジュールの API 使用例（コードスニペット）を追加で作成します。どの部分を詳しくしたいか教えてください。