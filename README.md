# KabuSys

日本株向け自動売買システムの一部を実装したコードベースの README です。  
このドキュメントはローカル開発・ペーパートレード・本番運用での起動・設定手順や主要機能、ディレクトリ構成を簡潔にまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動発注を想定したシステム群です。  
主な責務はデータ収集（DuckDB）、ファクター / 特徴量生成、シグナル生成、ポートフォリオ構築、発注実行（kabuステーション 連携またはモック）、および運用監視やレポート生成です。  
本リポジトリは以下の要素を含みます（抜粋）:

- 実行エンジン（ExecutionEngine）起動スクリプト
- 監視ループ（SystemMonitor）起動スクリプト
- Pre-Market / Night-Batch レポート生成ロジック
- ポートフォリオ構築・リスク調整・ポジションサイジング等の純関数群
- AI（OpenAI）を使ったニュース NLP / レジーム判定の実装（OpenAI API 必須）
- ユーティリティ（ログ設定・プロセス優先度設定・設定読み込み／ウィザード等）

---

## 主な機能一覧

- 実行（execution）
  - ExecutionEngine を起動して注文フローを管理（実発注 or モック）
  - ペーパートレード用 DB 分離（KABUSYS_ENV=paper_trading の場合）
  - リスク管理（risk_config.yaml を読み込み検証）
- 監視（monitoring）
  - SystemMonitor による定期ポーリング（デフォルト 60 秒）
  - 監視 DB（SQLite）への記録
  - 停止フラグ（data/stop_requested.flag）による安全停止
- レポート / 検証
  - Pre-Market レポート（起床時の運用可否判定）
  - Night Batch レポート（夜間バッチの総括）
  - Paper Trading 検証レポート（過去期間の稼働／注文指標）
- ポートフォリオ構築
  - 候補選定（スコア順、上位 N 件）
  - 重み計算（等金額、スコア加重）
  - セクター制約適用、レジーム乗数
  - 株数算出（単元丸め、リスクベース / 等配分）
- 研究・解析
  - ファクター計算（Momentum, Volatility, Value 等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI 統合（任意）
  - ニュースを LLM（OpenAI）でスコア化し ai_scores に保存
  - レジーム判定（ETF MA + マクロ NLP を合成）
- 設定管理
  - .env ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - 自動 .env ロード（プロジェクトルートが見つかれば .env/.env.local を読み込み）

---

## セットアップ手順（ローカル開発向け）

下記は一般的なセットアップ手順です。実際の依存関係（requirements.txt 等）がある場合はそれに従ってください。

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - requirements.txt が存在しない場合は、少なくとも下記パッケージが必要な可能性があります:
     - duckdb, pyyaml, psutil, openai

4. 環境変数（.env）の準備
   - 対話式ウィザードで初期 .env を生成:
     - python -m kabusys.config_setup
   - あるいはテンプレート（.env.example）があれば手動で作成
   - 重要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - JQUANTS_BULK_API_KEY（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合必須）
     - KABUSYS_ENV ("development" | "paper_trading" | "live") — デフォルト "development"
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（デフォルト: INFO）

   - 自動ロード抑制: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化

5. 設定検証
   - python -m kabusys.validate_config
   - --strict をつけると警告もエラー扱い（戻りコード 1）

6. ディレクトリ作成（必要に応じて）
   - data/ や logs/ は多くのモジュールで期待されます。通常は自動作成されますが権限などで失敗することがあるため事前作成を推奨します:
     - mkdir -p data logs artifacts

---

## 使い方（主要スクリプト）

- 実行エンジン（Execution）
  - 起動:
    - python -m kabusys.run_execution
  - 備考:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します（本番 DB と完全分離）。
    - 起動時に停止フラグ（data/stop_requested.flag）が存在すると起動せず終了します。
    - 実行中に停止フラグが作成されるとエンジンは安全に停止します。
    - リスク設定は config/risk_config.yaml を参照します（必要に応じて編集）。

- 監視（Monitoring）
  - 起動:
    - python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60）。
  - 備考:
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視 DB は共通で運用される想定）。
    - 停止フラグ: data/stop_requested.flag を検出してループ終了。

- Pre-Market レポート（起動前チェック）
  - python -m kabusys.run_pre_market_report
  - オプション:
    - --save : artifacts/pre_market/{date}/ に保存
    - --json : JSON 形式で出力（保存時は stderr に保存先を出力）
  - 戻り値:
    - レポートが BLOCKED の場合は非ゼロ終了コード（1）を返す

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗として扱う

- .env ウィザード（対話式）
  - python -m kabusys.config_setup

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定:
    - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH が優先されます）

- ログ設定
  - 各起動スクリプトは内部で kabusys.utils.logging_setup.setup_logging を呼び出します
  - デフォルトログディレクトリ: logs/
  - ログファイル: logs/<app_name>.log（日次ローテーション・30日保持）
  - LOG_LEVEL により出力レベルを制御

---

## 重要なファイル・フラグ

- data/stop_requested.flag
  - 存在すると起動済の監視 / 実行エンジンが停止を検知して安全に終了します
- data/execution.pid（PID ファイル）
  - 実行エンジンの PID を記録する場所（設定で変更可）
- config/risk_config.yaml
  - リスクマネージャーのパラメータ（必須）
- .env / .env.local
  - 環境変数設定ファイル（自動ロード順: OS 環境変数 > .env.local > .env）
- DuckDB / SQLite DB
  - デフォルト:
    - DUCKDB_PATH: data/kabusys.duckdb
    - SQLITE_PATH: data/monitoring.db
    - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading 時)

---

## よく使う環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN, JQUANTS_BULK_API_KEY — J-Quants API 用
- KABU_API_PASSWORD, KABU_API_BASE_URL, KABU_TRADE_PASSWORD — kabuステーション API 用
- OPENAI_API_KEY — OpenAI を使う機能（news_nlp, regime_detector 等）
- KABUSYS_ENV — "development" | "paper_trading" | "live"
- MONITOR_POLL_INTERVAL — 監視のポーリング間隔（秒）
- LOG_LEVEL — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START — 本番での自動クリア抑止等のフラグ

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み・自動 .env ロード・Settings クラス
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前設定チェック CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（発注処理）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - run_pre_market_report.py
    - Pre-Market レポート生成エントリポイント
  - execution/
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py（発注関連）
  - monitoring/
    - monitoring_db.py, system_monitor.py（監視関連）
  - operations/
    - pre_market_collector.py, pre_market_report.py, night_batch_report.py（レポート / 収集）
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py（ポートフォリオ構成ロジック）
  - research/
    - factor_research.py, feature_exploration.py（ファクター・研究用ロジック）
  - ai/
    - news_nlp.py, regime_detector.py（LLM 統合）
  - utils/
    - logging_setup.py（ログ設定）
    - process_priority.py（プロセス優先度）
  - tools/
    - paper_verification_report.py（ペーパートレード検証レポート）
  - artifacts/（実行時に使われる保存領域、例: pre_market, night_batch）
  - data/（SQLite / DuckDB / flag / pid 等）

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）は注意して運用してください。validate_config.py は本番向けのチェック（LINE 通知設定や kill flag の扱い）を行います。
- .env は秘密情報を含むため絶対に Git にコミットしないでください（config_setup のヘッダーにも同様の注意書きがあります）。
- AI API（OpenAI）利用部分は API キー・コスト・レート制限に注意してください。news_nlp.py はエラー時にリトライや保護機構を持っていますが、実運用では使用制限等の検討が必要です。
- 監視（monitoring）は本番 evironment に依らず本番監視 DB を使う設計になっています。監視の記録先やポーリング間隔を運用要件に合わせて調整してください。
- ペーパートレードは production DB とは分離されますが、DB パスの確認を必ず行ってください。

---

## トラブルシューティング

- .env が読み込まれない／別の値で読み込みたい:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを抑止できます
- ログファイルが生成されない:
  - logs/ ディレクトリの作成権限を確認。logging_setup では作成に失敗した場合コンソール出力のみで継続します
- Execution 起動時に即終了してしまう:
  - data/stop_requested.flag が存在している可能性があります（削除して再起動）
- risk_config.yaml のエラー:
  - run_execution は config/risk_config.yaml を必須で読み込みます。ファイルが無い・キーが不足・値の範囲外の場合は例外になります

---

この README はコードベースの主要な使い方と設計方針を簡潔にまとめたものです。各モジュール内の docstring（ソース）に詳細な仕様・設計意図が書かれていますので、必要に応じて参照してください。質問や特定機能のドキュメントの追記が必要であれば教えてください。