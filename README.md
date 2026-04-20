# KabuSys

日本株自動売買システムのコードベース。ポートフォリオ構築・ポジションサイジング、発注実行エンジン（ExecutionEngine）、監視（Monitoring）、リサーチ/ファクター計算、AI（ニュース・レジーム判定）などを含むモジュール群を備えた小規模な自動売買フレームワークです。

バージョン: 0.1.0

---

## 概要

このリポジトリは、以下の機能を組み合わせて日本株の自動売買を行うことを目的としています。

- データ分析用 DuckDB、運用ログ用 SQLite を使ったデータ永続化
- シグナル→ポートフォリオ構築→ポジションサイジング → 発注の ExecutionEngine
- ExecutionEngine の安全性を担保するリスク管理（ドローダウン検知 等）
- 実行系の監視（SystemMonitor / TradeMonitor / RiskMonitor）とアラート、Kill Switch
- Paper Trading（環境分離）対応およびペーパートレード検証レポート生成ツール
- Research 向けファクター計算・特徴量探索モジュール
- OpenAI を利用したニュース NLP による銘柄センチメントや市場レジーム判定

重要な設計方針として、ルックアヘッドバイアス回避（target_date を明示）や本番とペーパートレード DB の分離、安全な DB 書き込み（トランザクション）などに配慮しています。

---

## 機能一覧

- 環境設定ウィザード（.env 作成）: python -m kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml のチェック）: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、data/paper_trading.db に記録
  - プロセス優先度設定、PID ファイル出力、stop flag による安全停止
- 監視プロセス起動スクリプト: python -m kabusys.run_monitoring
  - SystemMonitor をループ実行（MONITOR_POLL_INTERVAL で間隔指定）
  - 停止フラグ（data/stop_requested.flag）でループ終了
- 監視機構
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度チェック
  - TradeMonitor / RiskMonitor: 注文・約定の正常性、ドローダウン監視、ポジション上限監視
  - MonitoringDB: SQLite に監視ログ・トレードログ・ポジション・リスクログ・ダッシュボードを永続化
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止させる
- ポートフォリオ構築
  - 候補選定、等金額/スコア加重、セクター制約、レジーム乗数、ポジションサイズ計算（lot rounding 等）
- Research
  - ファクター計算（momentum / volatility / value など）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI（OpenAI）
  - ニュース NLP による銘柄センチメント（ai_scores テーブル書込）
  - マクロニュース＋ETF MA による市場レジーム判定（market_regime テーブル）
- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

---

## セットアップ手順

前提:
- Python 3.10+（typing 機能などを利用）
- OS 上で psutil, duckdb, openai 等の依存パッケージをインストール

1. リポジトリを取得
   - git clone などで取得してください。

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必要に応じて requirements.txt を用意している場合は pip install -r requirements.txt
   - 主要パッケージ例:
     - pip install duckdb psutil openai

4. .env を作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに `.env` を作成し、以下の必須環境変数を設定:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - そのほかオプション/推奨:
     - KABUSYS_ENV = development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI モジュール利用時）
     - LOG_LEVEL（デフォルト: INFO）
     - KILL_FLAG_CLEAR_ON_START（本番では 0 推奨）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

6. 必要なディレクトリ（data, logs 等）は起動時に自動作成されることが多いですが、権限等に注意してください。

---

## 使い方

基本的な起動 / 実行方法（例）:

- ExecutionEngine を起動（本番/ペーパー共通エントリ）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV によって本番 DB / ペーパートレード DB を切り替えます（paper_trading 時は専用 DB を使用）。
    - 起動前に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中に data/stop_requested.flag を作成するとエンジンが停止します。
    - PID ファイルは data/execution.pid に書かれます（Settings.pid_file_path で上書き可）。

- Monitoring を起動（別プロセスで常駐）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60 秒）。
  - 監視は本番 sqlite_path（Settings.sqlite_path）を使います（環境に依らず本番監視 DB を参照する仕様）。
  - data/stop_requested.flag を作成すると監視ループが終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）。

- AI モジュール（OpenAI）
  - OPENAI_API_KEY を設定して、kabusys.ai.score_news / kabusys.ai.regime_detector を呼び出します。
  - news_nlp は前日 15:00 JST 〜 当日 08:30 JST を対象に記事を集約し LLM に送信します。
  - レート制限や一時エラーにはリトライ実装があります（指数バックオフ）。

環境変数の重要な差分:
- KABUSYS_ENV
  - development: ローカル開発（発注なし）
  - paper_trading: ペーパートレード（MockBrokerClient、data/paper_trading.db に記録）
  - live: 本番（実際に発注）
- PAPER_FILL_MODE（paper_trading 時のモック約定挙動）
  - instant | partial | never | reject
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）

停止・強制停止フラグ:
- data/stop_requested.flag: run_* スクリプトが監視している「プロセス停止要求」フラグ（存在で停止）
- data/kill.flag: KillSwitch が書き込むためのフラグ（ExecutionEngine 側で確認して停止）

ログ:
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一
- デフォルトは stdout と logs/<app_name>.log（日次ローテーション、30日保持）
- LOG_DIR 環境変数でログディレクトリを変更可能

---

## ディレクトリ構成（主要ファイルの説明）

※ 実際のパスはリポジトリのルートにある `src/kabusys` を想定しています。

- src/kabusys/
  - __init__.py
    - パッケージ定義・バージョン
  - config.py
    - 環境変数 / 設定の読み込みロジック（.env 自動ロード、Settings クラス）
  - config_setup.py
    - 対話式 .env 作成ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（プロセス優先度、DB 接続、スレッド起動、停止フラグ確認）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
      - Paper Trading 検証レポート生成ツール
  - portfolio/
    - portfolio_builder.py
      - 候補選定・重み計算
    - position_sizing.py
      - 発注株数計算（risk_based / equal / score）
    - risk_adjustment.py
      - セクター上限適用・レジーム乗数
  - research/
    - factor_research.py
      - momentum / volatility / value 等のファクター計算（DuckDB を使用）
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー
  - ai/
    - news_nlp.py
      - raw_news を集約して OpenAI でセンチメント算出 → ai_scores に書込
    - regime_detector.py
      - ETF MA とマクロニュースの LLM による市場レジーム判定 → market_regime に書込
  - monitoring/
    - monitoring_db.py
      - SQLite のテーブル作成・永続化 API（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
      - CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py
      - （コードベースに含まれるがここでは詳細省略）注文・約定監視
    - risk_monitor.py
      - ドローダウン・ポジション数上限監視
    - kill_switch.py
      - 条件に応じて kill.flag を書き込み ExecutionEngine を停止させる
    - monitoring_engine.py
      - 複数 Monitor を束ねてポーリング・アラート送信
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
      - ExecutionEngine 本体および発注関連（主要な実行ロジックはここにまとまる）
  - utils/
    - logging_setup.py
      - ログ初期化ユーティリティ（stdout + 日次ファイルローテーション）
    - process_priority.py
      - プロセス優先度・CPU affinity 設定ユーティリティ（psutil ベース）
  - research, portfolio, monitoring, ai の各モジュールはそれぞれの責務に分割されています。

---

## 注意点・運用上のヒント

- 本番運用時は KABUSYS_ENV=live とし、.env の値を十分確認してください（validate_config の警告に注意）。
- Kill Switch / kill.flag は本番で非常に重要です。KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に自動で kill.flag を消しますが、本番では 0 を推奨します。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と完全分離するよう設計されています。PAPER_TRADING_SQLITE_PATH を設定して DB を分けてください。
- OpenAI を使う機能は API キーが必須です。API 呼び出しはリトライやクリップなどフェイルセーフ処理が入っていますが、API 料金・レート制限に注意してください。
- DuckDB のスキーマ（prices_daily, raw_financials 等）に依存した処理が多いため、分析データの投入と整合性を確認してください。
- ログディレクトリや data ディレクトリの書き込み権限に注意してください。ログハンドラ作成に失敗するとコンソール出力のみになります。

---

## トラブルシューティング

- run_monitoring / run_execution がすぐ終了する:
  - data/stop_requested.flag が存在していないか確認
  - .env の設定が不足していないか（必須環境変数の有無）を確認 → python -m kabusys.validate_config
- OpenAI 呼び出しで失敗する:
  - OPENAI_API_KEY の設定を確認
  - ネットワーク/プロキシ/レート制限の可能性を確認
- SQLite / DuckDB のファイルが見つからない:
  - 環境変数（SQLITE_PATH / DUCKDB_PATH / PAPER_TRADING_SQLITE_PATH）を確認
  - ディレクトリ権限を確認

---

必要に応じて README にサンプル .env テンプレートや開発向けの起動スクリプト例を追加できます。追加で欲しいセクション（API ドキュメント、設定項目一覧の表、運用手順など）があれば教えてください。