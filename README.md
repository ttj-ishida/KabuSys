# KabuSys

日本株向け自動売買システムの一部（ライブラリ／実行スクリプト群）。  
このリポジトリには、実行エンジン・監視・ポートフォリオ構築・リサーチ・AI 補助機能などが含まれます。

注意: README はソースコード（src/kabusys）を元に作成しています。実行には依存パッケージや適切な .env 設定が必要です。

---

## プロジェクト概要

KabuSys は日本株の自動売買を行うためのモジュール群です。主な役割は次のとおりです。

- ExecutionEngine：ブローカーと連携して注文を発行・管理するエンジン
- Monitoring：システム・注文・リスクを監視し、必要に応じて Kill Switch を発動
- Portfolio Construction：銘柄選定・重み付け・株数決定の純粋関数実装
- Research：DuckDB を用いたファクター計算・特徴量解析
- AI 支援機能：ニュースセンチメント解析・市場レジーム判定（OpenAI を利用）
- ユーティリティ：設定読み込み・プロセス優先度設定など

設計方針の一例：
- データベースは DuckDB（分析用）と SQLite（監視／ペーパートレードログ）を併用
- Paper Trading（シミュレーション）と Live（実取引）は DB・ブローカーで分離
- LLM（OpenAI）呼び出しは安全策（リトライ、検証、フェイルオープン）を備える

---

## 機能一覧

- 起動スクリプト
  - python -m kabusys.run_execution : ExecutionEngine を起動（KABUSYS_ENV に応じてペーパートレードと実取引を切替）
  - python -m kabusys.run_monitoring : SystemMonitor のポーリングループを起動
- 設定管理
  - 対話式ウィザード: python -m kabusys.config_setup （.env の初期生成）
  - 設定検証 CLI: python -m kabusys.validate_config（--strict で警告も失敗扱い）
- モニタリング
  - SystemMonitor / TradeMonitor / RiskMonitor を統合する MonitoringEngine
  - kill.flag を用いた Kill Switch（ExecutionEngine 停止）
  - stop_requested.flag / execution.pid を用いたプロセス制御
- ポートフォリオ構築
  - 候補選定（スコア・上位 N）、等ウェイト／スコア加重
  - セクター上限の適用、レジーム乗数、ポジションサイズ計算（lot 単位・キャッシュスケールなど）
- リサーチ
  - モメンタム・ボラティリティ・バリュー計算（DuckDB SQL + Python）
  - 将来リターン計算、IC（情報係数）や統計サマリー
- AI（OpenAI）
  - ニュースのセンチメントスコアリング（ai.news_nlp）
  - マクロニュース + ETF MA200 による市場レジーム判定（ai.regime_detector）
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## セットアップ手順（開発環境向け）

1. Python 環境を用意（推奨: 3.10+）
   - 仮想環境を作る例:
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - 必須の主要パッケージ例:
     - duckdb, psutil, openai
   - オプション:
     - PyYAML（config/*.yaml のパース検証を行う場合）
   - 例:
     - pip install duckdb psutil openai
     - pip install PyYAML  # 任意

3. .env を用意
   - 対話式ウィザードで生成する:
     - python -m kabusys.config_setup
   - もしくは .env ファイルを手動で作成（.env.example を参考にする）
   - 代表的な環境変数（最低限必要なもの）
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - OPENAI_API_KEY=...  （AI 機能を使う場合）

   - 自動ロード:
     - リポジトリルートの .env（および .env.local）は起動時に自動で読み込まれます。
     - テスト等で自動ロードを抑止する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 設定検証
   - python -m kabusys.validate_config
   - 警告も厳格扱いにする場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリの作成
   - デフォルトでは data/ 以下にファイルを作成するため適宜作成してください（多くの起動処理で自動作成されますが念のため）
   - 例: mkdir -p data

---

## 使い方（実行例）

- ExecutionEngine を起動（デフォルトは KABUSYS_ENV 環境に従う）
  - python -m kabusys.run_execution
  - ペーパートレード専用に起動する場合:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録します（本番 DB と完全分離）

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - デフォルトは 60 秒。1 未満または不正値はデフォルトにフォールバックします。

- Paper Trading 検証レポート（SQLite DB を指定可能）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を個別指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- 設定ウィザード（.env の作成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります

停止／Kill 操作について
- ExecutionEngine 停止
  - data/stop_requested.flag（stop_requested.flag）の存在をチェックして終了処理を行います（run_execution/run_monitoring が参照）
  - Kill Switch: KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送る仕組みです
  - 実行中の PID を data/execution.pid に書き出す（run_execution）

AI（OpenAI）利用
- ai.news_nlp と ai.regime_detector は OpenAI API（gpt-4o-mini）を利用します
- 環境変数 OPENAI_API_KEY を設定してください（引数で渡すことも可能）
- API 呼び出しはリトライ・検証・クリップ等の保護ロジックを含みます

ログ・権限
- 実行時にプロセス優先度（High 等）を設定するユーティリティが呼ばれます（psutil を利用）
- 権限不足で設定できない場合は警告でスキップされます

---

## 主要環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）: J-Quants API 用トークン
- KABU_API_PASSWORD（必須）: kabuステーション API パスワード
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring.db）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject、デフォルト instant）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）

---

## ディレクトリ構成（抜粋）

（src/kabusys 以下の主要ファイルとサブパッケージ）

- src/
  - kabusys/
    - __init__.py
    - config.py                 # .env 読込・Settings 定義（自動ロード機構あり）
    - config_setup.py           # 対話式 .env ウィザード
    - validate_config.py        # 設定検証 CLI
    - run_execution.py          # ExecutionEngine 起動スクリプト
    - run_monitoring.py         # Monitoring 起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py            (実装は省略ファイル末尾で継続)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - utils/
      - process_priority.py
      - __init__.py
    - execution/                    (複数の実行関連モジュールが存在)
      - broker_factory.py
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
      - order_record.py
      - ...（その他）
    - data/                         (data フォルダは実行時に使用される）
      - monitoring.db (デフォルト)
      - paper_trading.db (paper_trading 用)
      - execution.pid
      - kill.flag
      - stop_requested.flag

---

## 開発時の注意点 / ヒント

- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB／注文と完全に分離される設計です。テスト時はペーパーモードを推奨します。
- run_monitoring は監視用 DB（SQLITE_PATH）を、環境に関わらず本番 sqlite_path（SQLITE_PATH）を使用します（ソース内コメント参照）。
- OpenAI を使う機能は API キーの管理とコストに注意してください。API 呼び出しは外部依存のためネットワークやレート制限に備えたロジックがありますが、運用時は制御を検討してください。
- .env は絶対に Git にコミットしないでください（config_setup の出力ヘッダにも注意喚起あり）。
- 実行プロセスは data/execution.pid に PID を書き出します。stale PID の自動検出・削除ロジックがあります。

---

## トラブルシュート

- .env が読み込まれない
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定していないか確認
  - プロジェクトルート検出は .git または pyproject.toml を基準に行うため、実行パスを確認してください
- DuckDB / SQLite ファイルのパス警告
  - validate_config が警告を出す場合はパスの親ディレクトリが存在しない可能性があります。起動時に自動作成される場合がありますが、必要に応じて手動で作成してください。
- OpenAI 呼び出し失敗
  - OPENAI_API_KEY が設定されているか、ネットワーク接続、レート制限に達していないかを確認してください

---

必要に応じて README の拡張（詳細な ExecutionEngine の起動フロー、ブローカープラグインの作成方法、DB スキーマの説明など）を作成できます。どの部分を詳しくしたいか教えてください。