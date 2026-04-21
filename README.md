# KabuSys — README (日本語)

日本株自動売買システム用ライブラリ（モジュール群）の README です。本リポジトリは、データ処理・リサーチ・ポートフォリオ構築・発注エンジン・監視・AI を組み合わせた自動売買基盤を構成するモジュール群を収めています。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要コマンド／ワークフロー）
- ディレクトリ構成
- よくある注意点 / トラブルシューティング

---

## プロジェクト概要

KabuSys は日本株の自動売買基盤のコンポーネント群です。主な役割は以下の通りです。

- 戦略リサーチ（DuckDB を使ったファクター計算・特徴量解析）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- Execution エンジン（ブローカーへの発注、リスク管理、リコンシリエーション）
- 監視（システム稼働・注文状況・リスクの継続監視、Kill Switch）
- AI 補助（ニュースの NLP による銘柄スコアリング、レジーム判定）
- 開発運用用ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

設計上、監視ログは SQLite、分析データは DuckDB に格納する想定です。Paper Trading 用に本番 DB と分離した DB を利用するモードもあります。

---

## 主な機能一覧

- 環境設定管理
  - .env 自動読み込み／対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
- 実行系
  - ExecutionEngine 起動スクリプト（run_execution）:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し data/paper_trading.db に記録（本番 DB と分離）
    - プロセス優先度調整、PID ファイル管理、停止フラグ監視など
- 監視系
  - MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor
  - KillSwitch（data/kill.flag による ExecutionEngine 停止）
  - run_monitoring 起動スクリプト（ポーリングループ、MONITOR_POLL_INTERVAL で間隔変更可）
- ポートフォリオ構築
  - 候補選定、等加重・スコア重み、ポジションサイジング（単元丸め・aggregate cap）
  - セクター制限、レジーム乗数
- リサーチ
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI（LLM）連携
  - ニュース NLP による銘柄スコアリング（OpenAI Chat API を使用）
  - レジーム判定（ETF の MA 乖離とマクロ記事の LLM 評価を合成）
  - 再試行やレスポンスバリデーションなどの堅牢化実装あり
- ツール
  - Paper Trading の検証レポート生成スクリプト（paper_verification_report）

---

## セットアップ手順

前提
- Python 3.10 以上（コードでタイプヒントの `|` を使用しているため）
- SQLite（Python 標準ライブラリで利用可）
- DuckDB（Python パッケージ）
- psutil（プロセス優先度や CPU affinity）
- OpenAI SDK（AI 機能を使う場合）
- PyYAML（config/*.yaml の検証を行いたい場合、任意）

推奨例（venv を使う場合）:

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil openai pyyaml

   （AI を使わない場合は openai は不要、YAML 検証をしないなら pyyaml は任意）

4. 初期設定ファイル（.env）を作成
   - python -m kabusys.config_setup
     - 対話式に .env を生成・更新できます
   - 生成後、必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を設定してください

5. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合は --strict を付与

デフォルトのファイル/ディレクトリ
- DuckDB: data/kabusys.duckdb
- SQLite (monitoring): data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db
- PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag
- ログ: logs/<app_name>.log（TimedRotatingFileHandler で日次ローテーション）

環境変数の例（一部）
- KABUSYS_ENV: development | paper_trading | live
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で使用）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB パス（必要に応じて）
- LOG_LEVEL, LOG_DIR, DUCKDB_PATH, SQLITE_PATH など

---

## 使い方

基本的なワークフロー例:

1. .env を作成
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば .env を修正して再検証

3. 監視プロセスを起動
   - python -m kabusys.run_monitoring
   - 補足:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
     - monitoring は環境にかかわらず本番 sqlite_path を使って監視テーブルを初期化する

4. Execution エンジンを起動
   - python -m kabusys.run_execution
   - 補足:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用する（data/paper_trading.db に記録）
     - 起動時に data/stop_requested.flag が存在する場合は起動を中止
     - Execution 側もプロセス優先度を High に設定し、PID ファイル（data/execution.pid）を扱います

5. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db オプションで SQLite パスを明示可能。環境変数 PAPER_TRADING_SQLITE_PATH でも指定できます。

6. AI 関連（プログラム的に呼ぶ例）
   - news_nlp.score_news(conn, target_date, api_key=...)
     - DuckDB 接続を渡してニューススコアを ai_scores テーブルに書き込みます
   - regime_detector.score_regime(conn, target_date, api_key=...)
     - market_regime テーブルへレジームを書き込みます

停止／停止フラグ
- Execution の強制停止には data/kill.flag を書き込む仕組み（KillSwitch）があります。
- 監視プロセスや実行プロセスは data/stop_requested.flag の存在を見て安全に終了します。

ログ
- setup_logging が提供され、コンソール出力と logs/<app_name>.log に日次ローテーションで出力されます。
- ログディレクトリ書き込みに失敗した場合は標準出力のみの動作にフォールバックします。

---

## ディレクトリ構成（要点）

以下は src/kabusys 以下の主なファイルとディレクトリ（抜粋）です。各ファイルは該当の責務に沿った実装を持っています。

- src/kabusys/
  - __init__.py (バージョン定義等)
  - config.py
    - .env 自動ロード、Settings クラス（環境変数アクセス用）
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py (共通ロギング初期化)
    - process_priority.py (プロセス優先度 / CPU affinity)
  - monitoring/
    - monitoring_db.py (SQLite スキーマ初期化 / DB ラッパー)
    - system_monitor.py (システム状態・データ鮮度監視)
    - trade_monitor.py (滞留注文や約定異常の検知) — （実装ファイルあり）
    - risk_monitor.py (ドローダウン監視・ポジション上限)
    - kill_switch.py (kill.flag 管理)
    - monitoring_engine.py (各モニタ統合)
    - alert_manager.py (通知管理: LINE 等の仕組みを呼べる想定)
  - execution/
    - （ExecutionEngine / BrokerFactory / OrderManager / Reconciler / RiskManager 等）
  - portfolio/
    - portfolio_builder.py (候補選定、重み)
    - position_sizing.py (株数計算、aggregate scaling)
    - risk_adjustment.py (セクター上限、レジーム乗数)
  - research/
    - factor_research.py (momentum / value / volatility 計算)
    - feature_exploration.py (forward returns, IC, factor summary)
  - ai/
    - news_nlp.py (ニュース NLP スコアリング、OpenAI 連携)
    - regime_detector.py (レジーム判定)
  - tools/
    - paper_verification_report.py (Paper Trading 検証レポート生成)

（上記は抜粋です。個別の実装ファイルにさらに細分化されたモジュールが存在します。）

---

## よくある注意点 / トラブルシューティング

- Python バージョン
  - 本プロジェクトは Python 3.10 以上を想定しています（型ヒントの union 演算子 `|` を使用）。

- パッケージ依存
  - DuckDB、psutil、openai、PyYAML（任意）などをインストールしてください。
  - psutil によるプロセス優先度設定は権限が必要な場合があります（Linux の nice 値や Windows の優先度変更で AccessDenied が発生することがあります）。その場合は警告を出してスキップします。

- ログ／ディレクトリ権限
  - logs ディレクトリや data ディレクトリに書き込み権限が必要です。作成に失敗した場合、ファイルハンドラは無効化されコンソールのみになります。

- OpenAI API
  - AI 機能を利用する際は OPENAI_API_KEY を環境変数または関数引数で指定してください。リトライや 5xx 対策は実装済みですが、API コストに注意してください。

- DB 分離（Paper Trading）
  - KABUSYS_ENV=paper_trading にすると発注系は paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。監視系は（設計上）環境にかかわらず本番 sqlite_path を使用する箇所があるため注意してください（run_monitoring の挙動参照）。

- 停止フラグ
  - data/stop_requested.flag や data/kill.flag はファイル存在で状態制御するため、不要なフラグファイルが残っていると起動や継続処理が停止します。起動前に不要なフラグは削除してください。

---

必要に応じて、この README の補遺として各モジュールの API リファレンスや実行時のログ例、systemd / supervisor 用のサービス定義テンプレートなどを追加できます。追加してほしいセクションがあれば教えてください。