# KabuSys

日本株自動売買システム（ライブラリ & 実行スクリプト群）

このリポジトリは、銘柄選定・ポートフォリオ構築、注文管理、監視・アラート、Paper Trading 検証、ニュース NLP を含む自動売買関連のコンポーネント群を収めています。モジュールはできるだけ純粋関数／軽量な I/O 層で分離されており、ローカル開発・ペーパートレード・本番（live）を切り替えて運用できます。

以下は本コードベースに対する README（日本語）です。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要スクリプト／CLI）
- 環境変数（主要）
- 注意点 / 動作仕様
- ディレクトリ構成（ファイル一覧と簡単説明）
- トラブルシューティング

---

## プロジェクト概要

KabuSys は日本株向けの自動売買／研究パイプラインを想定したコード群です。主な特徴は以下です。

- ファクター計算・特徴量探索（DuckDB を用いたローカル分析）
- ポートフォリオ構築（候補選定・重み算出・株数算出）
- ExecutionEngine（発注フロー、保有管理、リスク制御） — 実装のあるファイル群を用意
- Monitoring（システム健全性、滞留注文、ドローダウン検出、Kill Switch）
- Paper Trading 用DB分離（ペーパートレード時は production DB と完全分離）
- ニュース NLP（OpenAI を利用した銘柄センチメント評価）および市場レジーム判定
- 各種 CLI（.env ウィザード、設定検証、レポート生成 等）

---

## 主な機能一覧

- portfolio:
  - 銘柄候補選定（select_candidates）
  - 等金額・スコア基準の重み算出（calc_equal_weights, calc_score_weights）
  - ポジションサイズ算出（calc_position_sizes）
  - セクター上限適用、レジーム乗数（apply_sector_cap, calc_regime_multiplier）
- research:
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）評価、統計サマリ
- execution:
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - 注文管理／リポジトリ／リコンシリエーション（コード内に実装）
- monitoring:
  - SystemMonitor（プロセス生存・CPU/メモリ/Disk・データ鮮度）
  - TradeMonitor（滞留注文、約定異常）
  - RiskMonitor（ドローダウン、ポジション上限）
  - KillSwitch（フラグファイルで ExecutionEngine を停止）
  - AlertManager（LINE push を利用した通知）
  - MonitoringEngine（これらを束ねるポーリングエンジン）
- tools:
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）
- ai:
  - news_nlp（OpenAI を利用したニュースセンチメント集計 → ai_scores に書込）
  - regime_detector（ETF の MA と LLM によるレジーム判定）
- utils:
  - process_priority（プロセス優先度 / CPU affinity 設定）

---

## セットアップ手順

前提
- Python 3.10+（コード内で | 型ヒント等を使用）
- システムに duckdb、psutil、openai、requests 等がインストールされていること（後述）

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) / .venv\Scripts\activate (Windows)

3. 依存パッケージをインストール
   - 最低限の想定パッケージ:
     - duckdb
     - psutil
     - openai
     - requests
     - PyYAML（config ファイルの構文チェック用、任意）
   - 例:
     - pip install duckdb psutil openai requests PyYAML

   （プロジェクトに requirements.txt がある場合はそれを使ってください）

4. 環境変数設定（.env）
   - ルートに `.env` を作成するか、下記の `python -m kabusys.config_setup` で対話式ウィザードを実行します。
   - 自動ロード: config.py はプロジェクトルート（.git または pyproject.toml を検出）を起点に .env を自動読み込みします。テストや特殊用途で無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. DB 初期化
   - 実際の起動スクリプト（run_monitoring/run_execution）が起動時に必要テーブルを生成します（init_monitoring_db）。
   - DuckDB ファイル（分析用）は config（DUCKDB_PATH）で指定できます（デフォルト: data/kabusys.duckdb）。
   - Paper Trading 用 SQLite（ペーパートレード時に用いる DB）は `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）。

---

## 使い方

主要な CLI / 実行スクリプトの使い方を示します。プロジェクトルートで実行してください（.env がある場合は自動読み込みされます）。

1. .env 対話式ウィザード（初期設定）
   - python -m kabusys.config_setup
   - 指示に従って J-Quants トークン、Kabu API パスワード等を入力し .env を生成します。

2. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いで終了コード 1 を返します。

3. ExecutionEngine を起動（発注エンジン）
   - python -m kabusys.run_execution
   - 注意:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用して `data/paper_trading.db` を利用（本番 DB と完全分離）。
     - 実行中は pid ファイル（data/execution.pid のデフォルト）を書き込み、stop フラグ（data/stop_requested.flag）で停止できます。
     - 起動直後に `data/stop_requested.flag` が存在すると起動せず終了します。

4. Monitoring を起動（監視ループ）
   - python -m kabusys.run_monitoring
   - 環境変数でポーリング間隔を指定可能:
     - MONITOR_POLL_INTERVAL（秒、デフォルト 60）
   - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを残します。
   - 停止は `data/stop_requested.flag` を作成すると検知してループを抜けます。

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - 省略時は DB パスは環境変数 PAPER_TRADING_SQLITE_PATH またはデフォルト（data/paper_trading.db）。

6. ニュース NLP / レジーム判定（プログラム API）
   - ai.score_news と ai.regime_detector.score_regime を Python API から呼び出して利用します。
   - 実行には OPENAI_API_KEY が必要（引数経由でも渡せます）。

---

## 主要な環境変数（サマリ）

必須
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意／デフォルトあり（主なもの）
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY — OpenAI API キー（ai モジュールで使用）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（0/1）

注意: .env ファイルは決して VCS にコミットしないでください。

---

## 注意点 / 動作仕様（重要）

- Python バージョン:
  - 型ヒント等の記法から Python 3.10 以上を想定しています。
- DB の分離:
  - run_execution は KABUSYS_ENV=paper_trading 時に paper_sqlite_path を使い、本番 sqlite_path と完全に分離します。
  - run_monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（監視 DB）を使用します。
- Kill / Stop の仕組み:
  - 実行停止指示: data/stop_requested.flag（run_execution と run_monitoring が参照）
  - Kill Switch（重大停止）: data/kill.flag（KillSwitch が書き込む。ExecutionEngine はこのファイルを検知して停止）
  - PID 管理: data/execution.pid（ExecutionEngine が書き込む）
- Process priority / CPU affinity:
  - 起動時に set_process_priority("high") を呼び出しますが、権限不足や非対応 OS の場合は警告でスキップされます。
- OpenAI 呼び出し:
  - news_nlp と regime_detector は LLM を利用します。API エラー・タイムアウトはリトライ／フォールバックを実装していますが、API キーがないと実行できません。
- 自動 .env 読み込み:
  - config.py はプロジェクトルートを .git または pyproject.toml で検出し、`.env` と `.env.local` を自動で読み込みます。テスト等で無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主なファイルと説明）

以下は src/kabusys 配下の主要ファイルです（抜粋）：

- src/kabusys/__init__.py
  - パッケージ定義（__version__ 等）

- src/kabusys/config.py
  - 環境変数読み込み・Settings クラス（.env 自動読み込みロジック含む）

- src/kabusys/config_setup.py
  - .env を対話式に作成/更新する CLI ウィザード

- src/kabusys/validate_config.py
  - 起動前の設定検証 CLI（必須環境変数・パス・YAML の存在チェック等）

- src/kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 時は MockBrokerClient を利用）

- src/kabusys/run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）

- src/kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - 銘柄選定・重み・株数算出・セクター制約・レジーム乗数

- src/kabusys/research/
  - factor_research.py, feature_exploration.py
  - ファクター計算、将来リターン、IC、統計サマリ

- src/kabusys/ai/
  - news_nlp.py（記事の LLM スコアリング）
  - regime_detector.py（市場レジーム判定）

- src/kabusys/monitoring/
  - monitoring_db.py（SQLite テーブル初期化 / 永続化 API）
  - system_monitor.py, trade_monitor.py, risk_monitor.py
  - monitoring_engine.py（モニタ群を束ねる）
  - alert_manager.py（LINE Push 通知）
  - kill_switch.py（フラグ書込による停止）

- src/kabusys/tools/
  - paper_verification_report.py（Paper Trading 検証レポート生成）

- src/kabusys/utils/
  - process_priority.py（優先度 / CPU affinity ユーティリティ）

---

## トラブルシューティング

- 必須環境変数未設定エラー:
  - validate_config を実行して未設定を確認、または config_setup で .env を作成してください。
- DuckDB / SQLite ファイルが無い:
  - 分析用 DuckDB（DUCKDB_PATH）や monitoring SQLite（SQLITE_PATH）は起動時に親ディレクトリが存在しない場合に警告が出ます。必要に応じてディレクトリを作成してください（run_* が自動でファイルを作ることもあります）。
- OpenAI 関連:
  - OPENAI_API_KEY が未設定だと ai スクリプトは ValueError を投げます。モジュール API を直接使う際はキーを渡すか環境変数を設定してください。
- psutil の権限関連:
  - set_process_priority や set_cpu_affinity は管理者権限が必要な場合があります。権限不足のときはログに警告が出て処理はスキップされます。
- run_execution / run_monitoring がすぐ終了する:
  - data/stop_requested.flag が残っていると起動せず終了します。不要な場合は削除してください。
- YAML の検証がスキップされる:
  - PyYAML がインストールされていない場合、validate_config は YAML チェックをスキップします（警告）。

---

必要に応じて README にサンプル .env のテンプレートや systemd サービスの例、Dockerfile の追加なども作成できます。ほかに README に追加したい情報（例: CI/CD、ユニットテスト、デプロイ手順、systemd の unit サンプル）があれば教えてください。