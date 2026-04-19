# KabuSys

日本株向けの自動売買／リサーチ基盤の実装サンプル。  
主に以下を含みます：戦略のためのファクター計算・特徴量探索、ポートフォリオ構築（候補選定・重み・発注株数算出）、実行エンジン起動スクリプト、監視（Monitoring）機能、AI（ニュースセンチメント／レジーム判定）統合、ペーパートレード検証ツール、各種ユーティリティ。

バージョン: 0.1.0

---

## 主要機能（一部）

- Execution（発注）エンジン起動スクリプト（run_execution）
  - KABUSYS_ENV により paper_trading / live / development を切替
  - paper_trading 時は MockBrokerClient を利用、paper_trading.db に記録して本番 DB と分離
  - 停止フラグ（data/stop_requested.flag）/ PID ファイル管理（data/execution.pid）
  - リスク管理（RiskManager、Reconciler、OrderManager 等の組立て）

- Monitoring（監視）
  - run_monitoring によるポーリングループ
  - システム状態（CPU/メモリ/ディスク）、Execution プロセス生存確認、データ鮮度確認など
  - RiskMonitor（ドローダウン／ポジション数監視）、KillSwitch による停止判定
  - 監視ログは SQLite（monitoring.db）へ永続化

- ポートフォリオ構築（pure functions）
  - 候補選定（select_candidates）
  - 等分配 / スコア加重（calc_equal_weights, calc_score_weights）
  - ポジションサイジング（calc_position_sizes） — 単元株丸め、利用可能現金によるスケーリング等
  - セクター制約・レジーム乗数（apply_sector_cap, calc_regime_multiplier）

- 研究（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（情報係数）計算、統計サマリー（外部ライブラリに依存しない実装、DuckDB 経由）

- AI 統合
  - ニュースを OpenAI（gpt-4o-mini 等）で評価して ai_scores を生成（news_nlp）
  - マクロニュース + ETF MA200 乖離を使った市場レジーム推定（regime_detector）
  - OpenAI API の呼び出しは堅牢化（バックオフ、バリデーション、部分失敗の保護）

- ツール
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）
  - .env 作成ウィザード（config_setup）・設定検証 CLI（validate_config）

- ユーティリティ
  - 統一的ログ設定（utils.logging_setup）
  - プロセス優先度 / CPU affinity 設定（utils.process_priority）
  - 環境変数読み込み・管理（config）

---

## 動作要件

- Python 3.10 以上（型注釈の | 演算子を使用しているため）
- 主な外部依存（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で YAML ファイル検査を行う場合）
- SQLite（標準ライブラリで利用）
- ネットワークアクセス（kabuステーション API / OpenAI API を利用する場合）

※ requirements.txt は本リポジトリに含まれていない想定です。上記パッケージを pip でインストールしてください。

---

## セットアップ手順（開発環境例）

1. リポジトリをクローン
   - git clone <repo>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

4. データ / ログ ディレクトリ（任意）
   - data/ と logs/ は自動作成されることが多いですが、必要に応じて作成してください：
     - mkdir -p data logs

5. .env の作成（ウィザード）
   - python -m kabusys.config_setup
   - ウィザードが対話的に .env を生成します（デフォルト: プロジェクトルート/.env）

6. 設定検証
   - python -m kabusys.validate_config
   - 警告を厳密に扱う場合は --strict を付与して実行（警告があると exit(1)）

---

## 環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 実行環境 / 動作制御
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
  - LOG_DIR — ログ保存先ディレクトリ（デフォルト: logs/）

- DB パス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 用）

- AI
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）

- Paper Trading 設定
  - PAPER_FILL_MODE — instant / partial / never / reject（デフォルト: instant）

- Monitoring
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1）

（ウィザード実行で主要キーを設定できます）

---

## 使い方

### .env 作成・検証（推奨フロー）

1. 対話式ウィザードで .env 作成
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - 警告も致命としたい場合:
     - python -m kabusys.validate_config --strict

### 実行エンジン（Execution）の起動

- 通常起動（設定に従って paper_trading/live を切り替え）
  - python -m kabusys.run_execution

- 挙動
  - プロセス優先度を高く設定して開始
  - PID ファイル（data/execution.pid）を管理
  - data/stop_requested.flag が存在すると起動を中止 / 実行中に検出すると停止する
  - paper_trading 環境では paper_trading 用 SQLite に記録して本番 DB と分離

### 監視（Monitoring）起動

- python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒）
  - 監視ログは Settings.sqlite_path（通常 data/monitoring.db）へ書き込まれる
  - 実行中に data/stop_requested.flag が存在するとループを終了

### Paper Trading 検証レポート

- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを直接指定可能（優先度: --db > env PAPER_TRADING_SQLITE_PATH > デフォルト）

### AI モジュールの利用（関数呼び出し例）

- news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡し、target_date のニュースウィンドウをスコアリングして ai_scores へ書込む
  - api_key が None の場合は環境変数 OPENAI_API_KEY を使用

- regime_detector.score_regime(conn, target_date, api_key=None)
  - market_regime テーブルに結果を書き込む

※ これらはライブラリ API なのでスクリプト/ジョブから呼び出して利用します。

### 停止・Kill Switch

- Execution の安全停止（Kill Switch）
  - RiskMonitor / KillSwitch の判定により data/kill.flag が書き込まれると ExecutionEngine に停止シグナルを送る（Settings.kill_flag_path の既定は data/kill.flag）
  - KillSwitch は冪等（既に存在する場合は上書きしない）
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動で kill.flag を消去する（本番での自動クリアは危険）

- 一時的に全ループを停止したい場合
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループが検出して終了する

---

## ログ

- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（30日分保持）。
- コンソール出力（stdout）にも同内容が出ます。
- ログ設定は kabusys.utils.logging_setup.setup_logging から統一的に行われます。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数読み込み・Settings
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI 統合）
    - regime_detector.py — 市場レジーム判定（LLM + MA200）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算
    - risk_adjustment.py — セクター制約・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — 将来リターン・IC・統計
  - monitoring/
    - monitoring_db.py — 監視用 SQLite 永続化層（テーブル作成 / マイグレーション含む）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 発注系監視（ログ参照）←（ファイル内の実装がある想定）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書込みユーティリティ
    - monitoring_engine.py — 各 Monitor 統合ランナー
  - execution/  — Execution 系の実装（OrderManager, ExecutionEngine 等）
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity
  - data/ （実行時に作成される想定）
  - logs/ （ログ出力先、実行時に作成）

---

## 開発者向けメモ / 注意事項

- 時刻／日付の扱いはルックアヘッドバイアス防止のため注意深く実装されています（多くの関数が date / target_date 引数を受ける）。
- DuckDB 接続は研究モジュールの SQL クエリで多用されます。テーブルスキーマ（prices_daily / raw_financials / raw_news 等）に依存します。
- OpenAI 呼び出し部分は失敗許容に実装されていますが、API キーの管理・レート制御には注意してください。
- 本番（KABUSYS_ENV=live）では kill.flag や KILL_FLAG_CLEAR_ON_START の値に十分注意すること。
- テスト時は環境変数自動ロード（config モジュールの自動 .env 読込）を無効化できます：
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

README はプロジェクトの概要と主要な使い方をまとめたものです。実装の詳細や追加のスクリプトは各モジュールの docstring を参照してください。必要であれば、README にインストール用の requirements.txt や実行例（systemd / container 用の設定例）を追記できます。