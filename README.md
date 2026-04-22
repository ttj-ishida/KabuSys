# KabuSys

日本株向け自動売買システムの実験実装 / ライブラリ群です。  
（パッケージ内にある各種モジュールを組み合わせて戦略の研究・ポートフォリオ構築・発注・監視・レポート生成を行います）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要機能を備えたモジュール群です。

- データアクセス: DuckDB / SQLite を用いた時系列・財務データの集計・読取
- リサーチ: モメンタム・ボラティリティ・バリューなどのファクター計算、特徴量探索、IC 計算
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ算出、セクター制約・レジーム調整
- 実行エンジン: ブローカー抽象化（paper_trading 用の Mock を含む）、注文管理、リスク管理、和解（reconciliation）
- 監視: システム稼働・データ鮮度・注文状況・リスクを定期チェックし、kill flag を発動可能
- AI 支援: OpenAI を用いたニュースセンチメント（news_nlp）・市場レジーム判定（regime_detector）
- ツール: ペーパートレード検証レポート生成などのユーティリティスクリプト
- 設定管理: .env ウィザード（config_setup）・起動前検証 CLI（validate_config）
- ロギング・プロセス優先度制御などのユーティリティ

本 README はコードベース内の公開モジュールをもとに、セットアップと主要な使い方をまとめたものです。

---

## 主な機能一覧

- 設定管理
  - .env を対話式で生成/更新する `python -m kabusys.config_setup`
  - 設定ファイル・環境変数の整合性チェック `python -m kabusys.validate_config`
- 実行・発注
  - ExecutionEngine 起動スクリプト `python -m kabusys.run_execution`
    - KABUSYS_ENV=paper_trading では MockBrokerClient を使い `data/paper_trading.db` に記録
- 監視
  - SystemMonitor のループ起動 `python -m kabusys.run_monitoring`
  - MonitoringEngine: System / Trade / Risk の定期チェック、アラート発行、KillSwitch 評価
- ポートフォリオ
  - 候補選定、等重/スコア重み、ポジションサイズ計算、セクターキャップ、レジーム乗数
- リサーチ
  - ファクター計算（momentum, volatility, value）
  - 将来リターン・IC・統計サマリ等
- AI（OpenAI）
  - ニュースから銘柄単位のセンチメントを算出し ai_scores テーブルへ書き込み
  - マクロニュース + ETF MA を組合せた市場レジーム判定
- ツール
  - Paper Trading の性能検証レポート生成 `python -m kabusys.tools.paper_verification_report`

---

## セットアップ手順

以下はローカルで動かすための最低限の手順の例です。

1. リポジトリをクローン / ソースを用意
   - ここではソースルートが `src/` を含んでいる状態を想定します。

2. Python 仮想環境作成
   - python >= 3.10 を想定
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - 必須（最低限）:
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
   - 例:
     - pip install duckdb psutil openai
   - validate_config の YAML チェックを有効にする場合:
     - pip install PyYAML

   （プロジェクトには requirements.txt が含まれていないため、必要なパッケージを適宜インストールしてください）

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは `.env.example` を参考に手動で `.env` を作成
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict をつけると警告があると exit 1 になります

6. ディレクトリ/ファイルの確認
   - デフォルトで使用するローカルファイル:
     - data/monitoring.db (SQLite 監視 DB)
     - data/paper_trading.db (Paper Trading 用 DB)
     - data/kabusys.duckdb (DuckDB)
     - logs/ (ログファイルを保存)
   - 必要に応じて .env でパスを上書きできます（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH など）。

---

## 環境変数（主要なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード

- 実行動作に影響する主要な環境変数
  - KABUSYS_ENV: 実行環境（development / paper_trading / live） デフォルト: development
    - paper_trading にすると MockBrokerClient を使用し、paper 専用 DB に記録されます
  - LOG_LEVEL: ログレベル（DEBUG, INFO, ...） デフォルト: INFO
  - LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH: ExecutionEngine の pid-file（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: KillSwitch が書き込むフラグ（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
  - PAPER_FILL_MODE: Paper Trading の約定挙動（instant, partial, never, reject） デフォルト: instant
  - OPENAI_API_KEY: OpenAI 用 API キー（AI 機能使用時に必要）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

---

## 使い方（主要スクリプト）

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env ファイルを対話式に作成・更新します

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります

- 実行エンジン起動（発注系）
  - python -m kabusys.run_execution
  - 構成:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper DB に記録
    - 起動時に data/stop_requested.flag が存在すると起動せず終了
    - 起動中は data/execution.pid に PID を書きます
    - 停止は data/stop_requested.flag を作成するか kill flag (data/kill.flag) により停止判定されます

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 監視は常に本番 sqlite_path （KABUSYS_ENV に依らず）を使用します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD で期間指定
    - --db PATH で DB を指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（モジュールレベルの呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらをスクリプトや定期ジョブから呼び出して ai_scores / market_regime を更新します

- ロギング
  - 全スクリプト共通で `kabusys.utils.logging_setup.setup_logging(app_name=...)` を使用しており、logs/<app_name>.log に日次ローテーションで出力されます。LOG_DIR 環境変数で変更可能。

---

## 監視・停止関連

- Kill Switch
  - kabusys.monitoring.kill_switch.KillSwitch が条件（ドローダウンやポジション上限等）を評価し、必要なら `data/kill.flag` を書き込みます
  - ExecutionEngine はこの kill.flag を見て安全に停止できます

- stop_requested.flag
  - `data/stop_requested.flag` を作成すると run_execution / run_monitoring 側のループが検知して終了します（運用上の一時停止用）

---

## ディレクトリ構成（主要ファイルの説明）

（パッケージルート: src/kabusys 以下。代表的なファイル/モジュールのみ抜粋）

- kabusys/
  - __init__.py
    - パッケージ情報（__version__ 等）
  - config.py
    - .env 自動ロード、Settings クラス（すべての設定を環境変数から取得）
  - config_setup.py
    - .env を対話式で作成するウィザード
  - validate_config.py
    - .env / config/*.yaml の起動前チェック CLI
  - run_execution.py
    - ExecutionEngine を起動するエントリスクリプト（スレッドで session 実行）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
      - Paper Trading 用の検証レポート生成
  - ai/
    - news_nlp.py
      - raw_news を LLM で評価し ai_scores に書込むロジック
    - regime_detector.py
      - ETF + マクロニュースから市場レジーム判定を行う
  - research/
    - factor_research.py
      - momentum / volatility / value などのファクター計算
    - feature_exploration.py
      - 将来リターン計算・IC・統計サマリ等
  - portfolio/
    - portfolio_builder.py
      - 候補抽出・重み計算（等重／スコア重み）
    - position_sizing.py
      - 各銘柄の発注株数決定（lot 単位の丸め・aggregate cap 等）
    - risk_adjustment.py
      - セクター上限適用・レジーム乗数
  - monitoring/
    - monitoring_db.py
      - SQLite 用の永続化レイヤ（テーブル作成・CRUD）
    - system_monitor.py
      - システム状態・データ鮮度監視
    - trade_monitor.py
      - 注文／約定関連の監視（ログ参照・異常検出）
    - risk_monitor.py
      - ドローダウン・ポジション上限の監視
    - kill_switch.py
      - フラグファイルによる停止判定
    - monitoring_engine.py
      - 各 Monitor を束ねるポーリング実行ロジック
  - execution/
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
      - 発注・注文管理・リスク管理・和解の実装群（抽象化されたブローカークライアント経由）
  - utils/
    - logging_setup.py
      - 標準的なロギング設定（stdout + 日次ローテーション）
    - process_priority.py
      - プロセス優先度・CPU affinity 設定ユーティリティ

---

## 開発上の注意点 / 運用メモ

- .env は絶対にリポジトリにコミットしないこと（config_setup でもヘッダで明記しています）
- KABUSYS_ENV を `live` にすると本番向けのチェックや警告が強化されます。`live` 設定は慎重に
- monitoring はデフォルトで本番用の sqlite_path を使用します（run_monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使う実装になっています）
- Paper Trading は本番 DB と分離するよう設計されています（PAPER_TRADING_SQLITE_PATH）
- OpenAI など API 呼び出しは失敗時にフェイルセーフ（0.0 や無効扱い）で継続する実装が多く、運用側での監視・ログ確認を推奨します
- ログは logs/<app_name>.log に日次ローテーションで保存されます。LOG_DIR で変更可

---

## よく使うコマンド例

- .env 作成
  - python -m kabusys.config_setup

- 設定確認
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（Paper Trading で起動する例）
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

- 監視起動（ポーリングを 30 秒間隔にしたい場合）
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring

- Paper Trading レポート（2026-04-01 から 2026-04-11）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば README に「依存パッケージ一覧（pip install 例）」「より詳細なディレクトリツリー」「各モジュールの API ドキュメント（関数一覧）」なども追加できます。どの情報を優先的に追記しますか？