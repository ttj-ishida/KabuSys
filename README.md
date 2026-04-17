# KabuSys

日本株向けの自動売買・リサーチ基盤（KabuSys）のコードベース用 README。  
このリポジトリは、取引実行エンジン、監視（Monitoring）、リサーチ（ファクター計算・特徴量探索）、AI 補助（ニュースの NLP スコアリング / レジーム判定）などを含むモジュール群で構成されています。

注意: 本 README はソースツリー内の docstring / 実装から主な使い方と設定をまとめたものです。

## 概要

- 自動売買 ExecutionEngine（発注、オーダー管理、リスク管理、照合）
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor、kill switch、LINE 通知）
- リサーチ機能（DuckDB を使ったファクター計算・将来リターン・IC 計算等）
- Portfolio Construction（候補選定、重み計算、ポジションサイズ算出、セクターキャップ・レジーム調整）
- AI コンポーネント（OpenAI を使ったニュースセンチメントと市場レジーム判定）
- ペーパートレード用の分離された DB サポートと検証レポート生成ツール

設計上のポイント:
- 環境変数 / .env による設定管理（`.env` を自動ロード、wizard で作成可能）
- Paper Trading は本番 DB と分離（`data/paper_trading.db` 等）
- DuckDB を分析用途に利用、SQLite を監視ログ / オーダー履歴に使用
- OpenAI 等外部 API 呼び出しは明示的に API キー必須、エラー時はフェイルセーフにフォールバック

## 主な機能一覧

- ExecutionEngine:
  - 発注・約定管理、リスク制御、オーダー再照合
  - Paper Trading モード（MockBrokerClient）により本番と完全分離
- Monitoring:
  - CPU / メモリ / ディスク / 実行プロセス監視
  - データ鮮度チェック（prices_daily の最終日）
  - 注文滞留・約定異常検知
  - ドローダウン・ポジション上限アラートと kill switch（停止フラグ書き込み）
  - LINE へのプッシュ通知（AlertManager）
- Research:
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターンの算出、IC（Spearman）計算、統計要約
- Portfolio:
  - 候補選定、等ウェイト・スコア加重、リスクベース配分
  - セクター上限適用、レジーム乗数
  - ポジションサイズ計算（単元丸め、aggregate cap のスケーリング）
- AI:
  - ニュース記事を LLM（OpenAI）でスコア化し ai_scores に書き込み
  - マクロニュース + ETF MA200 乖離から市場レジーム（bull/neutral/bear）を判定
- ツール:
  - Paper Trading 検証レポート生成（期間指定可）

## 前提 / 必要環境

- Python 3.10+（型アノテーションで `X | Y` を使用）
- 推奨パッケージ（requirements.txt があればそれを使用）:
  - duckdb
  - psutil
  - openai（AI 機能を使用する場合）
  - requests (LINE 通知)
  - PyYAML（config 検証で YAML を検査する場合に推奨）
- SQLite（標準ライブラリで利用）
- 実行権限や OS によってはプロセス優先度 / CPU affinity の設定が失敗することがあります（警告でスキップ）。

## セットアップ手順

1. リポジトリをクローン / 展開
   - 例: git clone <repo-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil requests
   - AI 機能を使う場合: pip install openai
   - コンフィグ YAML 検証を使う場合: pip install pyyaml

4. 環境変数設定 (.env)
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - 主要な必須環境変数（少なくとも以下は設定してください）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - その他の主要設定例:
     - KABUSYS_ENV = development | paper_trading | live
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB)
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（AlertManager を使う場合）
   - .env を編集後、検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります

5. データディレクトリの準備
   - 多くの動作は自動で `data/` を作成しますが、必要に応じて事前にディレクトリを作っておいてください。

## 使い方 / コマンド

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 失敗時は exit code 1 を返します（--strict で警告も FAIL）

- 監視プロセス起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き（デフォルト: 60）
  - 監視は常に「本番の sqlite_path（Settings.sqlite_path）」を使用します（環境に依らず）

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合:
    - MockBrokerClient を使用し、Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）に記録します（本番 DB と完全分離）。
  - 実行中は PID を data/execution.pid に書きます。
  - プロセス停止は data/stop_requested.flag の作成で検知します（stop フラグを立てることで安全停止）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能（ニューススコア / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）を設定
  - ニューススコア: kabusys.ai.score_news（プログラムから呼び出し可能）
  - レジーム判定: kabusys.ai.regime_detector.score_regime
  - コマンドラインラッパーはありませんが、モジュールを import して利用できます。

- 停止 / Kill Switch
  - KillSwitch は `data/kill.flag`（default）に理由を書き込むことで ExecutionEngine に対して停止シグナルを送ります（Settings.kill_flag_path で上書き可能）。
  - run_monitoring/run_execution は `data/stop_requested.flag` を見て安全にループを抜けます（コード中にて stop flag path が定義されています）。

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (default: development)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper trading 用 DB, default: data/paper_trading.db)
- LOG_LEVEL (default: INFO)
- OPENAI_API_KEY（AI 機能で必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（AlertManager 用）
- MONITOR_POLL_INTERVAL（run_monitoring 用。秒。default: 60）
- KILL_FLAG_CLEAR_ON_START（live 環境での自動クリアは危険。0 推奨）

詳細は code 中の kabusys.config.Settings のプロパティや validate_config の定義を参照してください。

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化 / MonitoringDB ラッパ
    - monitoring_engine.py   — 各モニタを束ねるエンジン
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - execution/                — 発注エンジン関連（order_manager, risk_manager 等）※実装は別ファイル群
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
    - news_nlp.py             — ニュース NLP -> ai_scores
    - regime_detector.py      — レジーム判定
    - __init__.py
  - tools/
    - paper_verification_report.py

（上記はこの README 作成時点での主要ファイル群の抜粋です。実際のリポジトリではさらに細かなモジュールが存在します。）

## 運用上の注意

- 本番（KABUSYS_ENV=live）では kill flag / PID / DB パス等を慎重に設定してください。validate_config は live 時に追加警告を出します。
- Paper Trading モードは本番 DB と完全に分離される設計です。テストや検証は paper_trading 環境で行ってください。
- OpenAI や LINE API を利用する機能は外部料金が発生する場合があるため注意してください。
- プロセス優先度設定（set_process_priority）は psutil を使用し、権限不足や未対応 OS の場合は警告でスキップされます。
- run_monitoring は監視ログを本番 sqlite_path に書き込みます。監視を分離したい場合は環境変数でパスを調整してください。

## 例: よくある開始手順（ローカル検証向け）

1. 仮想環境作成 & パッケージインストール
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install duckdb psutil requests openai pyyaml

2. .env を生成
   - python -m kabusys.config_setup

3. 設定検証
   - python -m kabusys.validate_config

4. DuckDB/SQLite の初期化（特に DuckDB は prices_daily 等のテーブルをロードする処理が別途必要）
   - （データロードスクリプトを用意して DuckDB にマーケットデータを投入）

5. ペーパートレードで実行エンジン起動（安全）
   - export KABUSYS_ENV=paper_trading
   - python -m kabusys.run_execution

6. 監視プロセス起動
   - python -m kabusys.run_monitoring

7. 検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

## 開発 / テスト

- モジュールは可能な限り純粋関数（副作用少）で実装されており、ユニットテストが書きやすい構造になっています（たとえば research / portfolio の関数群は DuckDB 参照または純粋計算）。
- 外部 API 呼び出し部はラップされているため、unittest.mock などでモック可能です（news_nlp._call_openai_api 等）。

---

この README はソース内の docstring をベースに要点をまとめたものです。さらに詳しい実装仕様や運用ドキュメントは個別のモジュール docstring（例: portfolio/、research/、monitoring/ 内）およびプロジェクトの設計ドキュメント（存在する場合）を参照してください。必要であれば README に追加したい具体的なセクション（例: systemd でのサービス化手順、Dockerfile、CI 設定例 等）を教えてください。