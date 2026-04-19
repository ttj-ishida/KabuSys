# KabuSys

日本株向け自動売買システムのモジュール群と運用ユーティリティ群をまとめたリポジトリの README（日本語）。

この README はコードベース（src/kabusys 以下）の主要コンポーネント、導入・起動手順、使い方、ディレクトリ構成などを簡潔にまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関する以下の要素を含むモジュール群です。

- 注文実行エンジン（ExecutionEngine：実ブローカー / ペーパートレード切替対応）
- 監視（Monitoring）：システム状態監視・リスク監視・Kill Switch、アラート連携
- ポートフォリオ構築（候補選定・重み算出・ポジションサイジング・セクター制約）
- 研究（ファクター計算・特徴量探索・IC 等）
- AI 支援（ニュース NLP によるセンチメント評価、市場レジーム判定）
- 運用用スクリプト（起動スクリプト、設定ウィザード、設定検証、レポート生成）
- ユーティリティ（ロギング設定、プロセス優先度／CPU affinity 設定 等）

設計方針の一部：
- 本番 DB / ペーパートレード DB を分離可能
- DuckDB を用いたオフライン解析・ファクター計算
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価（外部 API 呼び出し部分にリトライや堅牢性処理を実装）
- 起動スクリプトはプロセス優先度を高く設定し、PID / Flag ファイルで制御

---

## 機能一覧

主な機能（モジュール／スクリプトごと）

- 実行・運用
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録。
  - run_monitoring.py: SystemMonitor ポーリングループ起動。MONITOR_POLL_INTERVAL で間隔を変更可能。

- 設定
  - config_setup.py: .env の対話式ウィザードで初期作成・更新。
  - validate_config.py: .env と config/*.yaml の事前検証。--strict で警告も失敗扱い。

- 監視（monitoring）
  - monitoring_db.py: SQLite ベースの永続層（system_status / trade_logs / positions / risk_logs / dashboard）。
  - system_monitor.py: CPU・メモリ・ディスク・プロセス生存・データ鮮度の監視。
  - risk_monitor.py: ドローダウン・保有数上限の監視と警告記録。
  - kill_switch.py: 条件を満たすと data/kill.flag を書き込み ExecutionEngine を停止させる。
  - monitoring_engine.py: 上記モニタ群を束ねてポーリングし、アラート送出等を行う。

- ポートフォリオ（portfolio）
  - portfolio_builder.py: 候補選定・等重・スコア重み。
  - position_sizing.py: 株数算出（risk_based/equal/score）、集約上限のスケーリング、単元丸め。
  - risk_adjustment.py: セクターキャップ適用、レジーム乗数。

- 研究（research）
  - factor_research.py: Momentum / Volatility / Value 等のファクター計算（DuckDB 接続を使用）。
  - feature_exploration.py: 将来リターン計算、IC（Spearman）や統計サマリー。

- AI（ai）
  - news_nlp.py: raw_news を集約して OpenAI に送信、銘柄ごとのセンチメントを ai_scores に書き込み。
  - regime_detector.py: ETF（1321）MA200 とマクロニュースの LLM スコアを合成して市場レジームを判定し market_regime に書き込み。

- ツール
  - tools/paper_verification_report.py: ペーパートレード DB を解析してシステム稼働率や注文成功率などの検証レポートを生成。

- ユーティリティ
  - utils/logging_setup.py: StreamHandler + TimedRotatingFileHandler による統一ログ設定。
  - utils/process_priority.py: Windows/Linux の差分を吸収してプロセス優先度・CPU affinity を設定。

---

## セットアップ手順（開発 / ローカル運用向け）

1. リポジトリをクローンし、仮想環境を作成・有効化：
   - python 3.10+ を推奨
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（必要に応じて requirements.txt を用意してください）：
   - 主な外部依存例:
     - duckdb
     - psutil
     - openai
     - pyyaml (config 検証で任意)
   - 例:
     - pip install duckdb psutil openai pyyaml

3. データディレクトリとログディレクトリを作成（スクリプトが自動作成する場合もありますが事前準備推奨）：
   - mkdir -p data logs

4. .env を作成：
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参考に（リポジトリに例ファイルがあれば参照）。

5. 設定の検証（必須環境変数やパスのチェック）：
   - python -m kabusys.validate_config
   - 厳密モード（警告も失敗扱い）:
     - python -m kabusys.validate_config --strict

6. DuckDB / SQLite の初期テーブルは起動スクリプトが必要に応じて作成します（monitoring 用の init は run_* スクリプト内で呼ばれます）。

注意:
- 本番運用時は KABUSYS_ENV を適切に設定します（development / paper_trading / live）。
- OpenAI を利用する機能を使う場合は OPENAI_API_KEY を設定してください。

---

## 環境変数（主なもの・デフォルト）

以下は Settings クラス・config_setup の定義をもとに抜粋した主要な環境変数です。

- 必須（必ず設定する）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境関連
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

- DB / ファイルパス
  - DUCKDB_PATH: 分析用 DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH: 実行エンジン PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: Kill Switch フラグ（デフォルト: data/kill.flag）

- ペーパートレード
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

- MONITOR 関連
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" で有効。デフォルト: 0）

- OpenAI
  - OPENAI_API_KEY: news_nlp / regime_detector が使用する API キー

- ログ
  - LOG_DIR: ログの保存ディレクトリ（デフォルト: logs/）

---

## 使い方（起動例・主要スクリプト）

- 環境準備（.env を作成）
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- 実行エンジン起動（本番 / ペーパートレード）
  - 本番（KABUSYS_ENV=live を .env で設定してから）:
    - python -m kabusys.run_execution
  - ペーパートレード（環境変数を一時的に上書きして起動）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - このモードでは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH にデータを記録します。

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（例: MONITOR_POLL_INTERVAL=30）

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict を付けると警告があると exit(1) になる。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

- ライブラリとしての利用（Python import）
  - 研究用関数:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value
    - これらは duckdb 接続と target_date を受け取り、結果リストを返します。
  - AI 関連:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=None)  # api_key を None にすると環境変数 OPENAI_API_KEY を使用
  - ポートフォリオ関連:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes

注意点:
- run_execution/run_monitoring は起動時にプロセス優先度を高に設定します（utils.process_priority）。
- Kill Switch / stop flag 機構はファイルベースです（data/kill.flag / data/stop_requested.flag）。運用時は取り扱いに注意してください。
- OpenAI 呼び出しを行う機能は API 失敗時にリトライやフォールバックを行う設計ですが、API キー設定やコストに注意してください。

---

## ディレクトリ構成

主要なディレクトリと代表ファイル（src/kabusys 以下）

- src/kabusys/
  - __init__.py
  - config.py                — 設定読み込み・Settings クラス（.env 自動読み込みロジック含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py            — ニュースを LLM でスコアリングして ai_scores に書込
    - regime_detector.py     — マクロ + MA200 を合成して市場レジーム判定

  - monitoring/
    - monitoring_db.py       — SQLite 永続層（テーブル作成・CRUD ユーティリティ）
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度/プロセスチェック
    - risk_monitor.py        — ドローダウン・ポジション数監視
    - kill_switch.py         — Kill Switch（flag ファイル）
    - monitoring_engine.py   — 各モニタを束ねるエンジン
    - alert_manager.py       —（アラート送信ロジック、コードベースに存在）

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py

  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py

  - tools/
    - __init__.py
    - paper_verification_report.py

  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — 優先度 / CPU affinity
    - __init__.py

- data/                      — デフォルトの DB / PID / flag 等（リポジトリルートに存在する想定）
  - monitoring.db (SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - execution.pid
  - kill.flag
  - stop_requested.flag

- logs/                      — ログファイル保存先（LOG_DIR またはデフォルト logs/）

---

## 運用上の注意・ベストプラクティス

- KABUSYS_ENV は慎重に設定してください。`live` は本番モードで実際の注文が出ます。
- 本番では KILL_FLAG_CLEAR_ON_START を 0 にして、Kill Switch の誤動作を避けてください。
- OpenAI を使用する処理は API コストが発生します。利用頻度を制御してください。
- .env は絶対に Git にコミットしないでください（config_setup はヘッダにその旨を記載しています）。
- run_monitoring/run_execution は stop flag / kill.flag により外部から安全に停止できます。デバッグや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動 .env 読み込みを無効化できます。

---

もし README に追加したい具体的なコマンド例（systemd ユニット、docker-compose、CI 設定）や、各モジュールの API ドキュメント（引数や戻り値の詳細）などがあれば教えてください。要望に合わせてセクションを追加します。