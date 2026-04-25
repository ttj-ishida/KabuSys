# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム「KabuSys」のコアモジュール群を含みます。戦略・ポートフォリオ構築、注文実行・リスク管理、監視・アラート、リサーチおよび AI（ニュース NLP / レジーム判定）を備えた設計になっています。

注意: .env は機密情報（API トークン等）を含みます。絶対にリポジトリへコミットしないでください。

## 主な特徴
- 実行環境を切り替え可能（development / paper_trading / live）
- ペーパートレード用に実際の注文を行わない MockBroker を用意（DB 分離）
- 監視コンポーネント（System / Trade / Risk）と Kill Switch による自動停止
- DuckDB を使ったリサーチ／ファクター計算（prices_daily / raw_financials を参照）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（news_nlp）・市場レジーム判定
- ログはコンソール + 日次ローテートファイルで出力
- 各種ユーティリティ（.env ウィザード / 設定検証 / Paper Trading 検証レポート）

## 機能一覧（抜粋）
- config_setup.py: 対話式 .env 作成ウィザード
- validate_config.py: .env と config/*.yaml の事前検証 CLI
- run_execution.py: ExecutionEngine の起動スクリプト（本番 / paper_trading を切り替え）
- run_monitoring.py: SystemMonitor のポーリング起動スクリプト（MONITOR_POLL_INTERVAL で間隔変更可）
- monitoring/*: 監視系（DB 永続化、監視エンジン、KillSwitch、RiskMonitor 等）
- portfolio/*: 候補選定・重み付け・ポジションサイズ計算・セクター制限
- research/*: ファクター計算（momentum/value/volatility）および特徴量解析
- ai/*: ニュース NLP（score_news）・レジーム判定（score_regime）
- tools/paper_verification_report.py: ペーパートレード結果の検証レポート生成

## 前提・依存関係
主要な外部パッケージ（例）
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能利用時)
- PyYAML（config/*.yaml の検証を行う場合）
- 必要に応じて他ライブラリ（環境による）

推奨: 仮想環境を作成して依存をインストールしてください。
例:
- python -m venv .venv
- source .venv/bin/activate
- pip install duckdb psutil openai pyyaml

（requirements.txt があればそちらを使ってください）

## セットアップ手順

1. リポジトリをチェックアウト
   - git clone ... && cd <repo>

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate

3. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （プロジェクトで提供する requirements.txt があればそれを使用）

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 出来上がった .env は絶対に Git に含めないこと

5. 設定の検証（任意）
   - python -m kabusys.validate_config
   - 警告も厳密に扱いたい場合は --strict を付与

6. データディレクトリの作成（ログや DB のデフォルトパスを利用する場合）
   - mkdir -p data logs

## 重要な環境変数（主要なもの）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading の場合の DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を使う場合）
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（デフォルト: logs）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔、秒; デフォルト: 60）
- PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START（1 にすると起動時に kill flag を自動クリア）

.env 作成時には config_setup のウィザードを使うことを推奨します。

## 使い方（起動例）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution（注文エンジン）起動
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録されます
    - 起動時にプロセス優先度を "high" に設定します
    - 起動を止めたい場合は data/stop_requested.flag を作成するか、実行中プロセスに KeyboardInterrupt を送ります
    - 実行中は data/execution.pid に PID を書きます

- Monitoring（監視ループ）起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL を環境変数で秒数指定できます（デフォルト 60 秒）
    - 監視は設定に関わらず本番 sqlite_path（SQLITE_PATH）を使用して監視ログを記録します
    - 監視は data/stop_requested.flag の存在でループを終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db。--db オプションで指定可能。

- AI 機能（プログラム呼び出し）
  - news センチメントを生成:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=...)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=...)

  （AI 機能を使うには OPENAI_API_KEY が必要です。API 呼び出しはリトライやフォールバックを備えていますが、API キーの管理に注意してください）

## 停止・Kill Switch / フラグファイル
- data/stop_requested.flag
  - run_execution / run_monitoring はこのファイルが存在することを検出すると安全に停止します（起動前に存在する場合 run_execution は起動をキャンセルします）
- Kill Switch（監視経由）
  - KillSwitch は data/kill.flag（設定による）を書き込むことで ExecutionEngine に停止を促します
  - 本番では KILL_FLAG_CLEAR_ON_START=0 を推奨（誤ってクリアしない）

## ログ
- デフォルトで stdout（コンソール）と日次ローテートファイル（logs/<app_name>.log）に出力します
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御できます
- ログ保存先を変更する場合は LOG_DIR を設定

## データベース
- DuckDB: データ分析／prices_daily 等（デフォルト: data/kabusys.duckdb）
- SQLite: 監視・注文ログ（デフォルト: data/monitoring.db）
- ペーパートレード専用 SQLite（paper_trading の場合）: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）

## ディレクトリ構成（主要ファイルの概要）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数読み込み、Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数計算・調整・スケーリング
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — momentum/value/volatility ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）による銘柄別センチメント算出
    - regime_detector.py — ma200 + マクロ NLP による市場レジーム判定
  - monitoring/
    - monitoring_db.py — SQLite のスキーマ初期化・読み書きラッパー
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （注文周りの監視）※コードベースにモジュールあり
    - risk_monitor.py — ドローダウン／ポジション上限監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - monitoring_engine.py — 各モニタを束ねるエンジン
    - alert_manager.py — アラート送信（LINE 等のラッパー想定）
  - execution/
    - execution_engine.py — 発注・セッション管理（起動ロジックは run_execution から）
    - broker_factory.py — ブローカークライアント生成（Mock / 実ブローカー）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 実行系のサブコンポーネント
  - data/ — デフォルトの DB/flag/pid 保存場所（リポジトリ外で作成・運用）
  - utils/
    - logging_setup.py — 共通ログ設定
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

（上記は主要ファイルの抜粋です。詳細は各モジュールの docstring を参照してください）

## 開発時の注意点・運用メモ
- .env は機密情報を含むため Git 管理から除外してください
- KABUSYS_ENV=live での起動は慎重に行ってください（validate_config で本番向けチェックを行えます）
- AI 機能は API 利用料が発生します。API キーと呼び出し頻度に注意してください
- run_monitoring は監視用 DB にアクセスします。監視 DB は本番 sqlite_path を参照する実装です
- プロセス優先度の設定には権限が必要な場合があります（psutil を使用）。設定失敗時は警告が出ますが起動自体は継続します

---

README に書かれている内容で足りない点・補足したい具体的な実行例（systemd service のユニットや Dockerfile など）があれば、目的に合わせて追記例を作成します。