# KabuSys

日本株自動売買システム（ライブラリ & 実行スクリプト群）

このリポジトリは、シグナル生成 → ポートフォリオ構築 → 注文実行（本番 / ペーパートレード）までの自動売買基盤、およびシステム監視・検証ツールを含みます。モジュールはできるだけ純粋関数・DB分離で設計されており、ペーパートレードは本番データと完全に分離されるようになっています。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（起動 / 運用）
- 環境変数一覧（主要）
- ディレクトリ構成（主要ファイルの説明）
- 運用上の注意

---

## プロジェクト概要

- シグナル計算・ファクター研究（DuckDB を用いた価格テーブル参照）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- ExecutionEngine（ブローカークライアント抽象化により本番/ペーパートレードを切替）
- Monitoring（システム状態・注文ログ・リスク監視・Kill Switch）
- AI モジュール（OpenAI を使ったニュースセンチメント評価／市場レジーム判定）
- CLI 補助スクリプト（.env ウィザード、設定検証、ペーパートレード検証レポート）

設計上のポイント:
- ペーパートレード時は MockBrokerClient を使用し、専用 SQLite ファイル（data/paper_trading.db 既定）に記録 → 本番 DB と分離
- .env 自動読み込み（プロジェクトルートの .env / .env.local）を標準で行う（無効化は KABUSYS_DISABLE_AUTO_ENV_LOAD=1）
- ロギングは共通ユーティリティを使用してコンソール＋日次ローテートファイル出力を行う

---

## 機能一覧

- system monitoring
  - CPU/メモリ/ディスク使用率記録
  - 実行プロセスの生死チェック、データ鮮度チェック
- trade monitoring
  - 発注ログ、滞留注文や約定異常の検出（trade_logs / risk_logs）
- risk monitoring
  - ドローダウン監視、ポジション数上限監視、Kill Switch へのトリガ
- ExecutionEngine
  - ブローカー抽象化（実ブローカー / MockBroker）
  - リスク管理（利用率、ポジション上限、サーキットブレーカー等）
- Portfolio construction
  - 候補選定（スコア降順／上位 N）
  - 重み付け（等ウェイト / スコア加重）
  - ポジションサイズ計算（リスクベース / weight ベース、単元丸め、aggregate cap）
  - セクターキャップ、レジーム乗数
- Research / Feature exploration
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（情報係数）計算、統計サマリ
- AI（OpenAI）
  - ニュースの銘柄別センチメント評価（ai_scores テーブルへ書込）
  - マクロニュース + ETF MA を用いた市場レジーム判定（market_regime テーブルへ書込）
- ツール
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repo>

2. Python 環境（推奨: 3.10+）を用意し、仮想環境を作成して有効化

3. 必須ライブラリをインストール
   - 必要パッケージ（主なもの）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config/*.yaml の検証を使う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （このリポジトリに requirements.txt がない場合は上記を参照して必要なパッケージをインストールしてください）

4. 環境設定 (.env) の準備
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成
   - 自動読み込み: デフォルトでプロジェクトルートの .env / .env.local を読み込みます。自動読み込みを無効化するには:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリ作成（初回）
   - data ディレクトリ（既定の DB や PID / フラグファイル格納場所）
   - logs ディレクトリ（ログファイル格納、logging_setup が自動作成可能）

---

## 使い方

主要スクリプトはモジュールとして起動します。すべてのスクリプトはパッケージとして実行することを推奨します。

- 実行エンジン（ExecutionEngine）起動
  - KABUSYS_ENV により挙動が変わります:
    - development: 発注を行わないテスト用
    - paper_trading: MockBroker を使用し data/paper_trading.db に記録
    - live: 本番ブローカーを使用（注意してお使いください）
  - 例:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution

  - 特記事項:
    - 起動前に data/kill.flag が存在するとエンジンは起動しません（安全措置）。
    - PID ファイル: data/execution.pid（デフォルト、Settings.pid_file_path を参照）
    - 停止: data/stop_requested.flag または Kill Switch により停止します（下記参照）

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数で調整可能:
    - MONITOR_POLL_INTERVAL（秒、デフォルト 60）
  - 監視は常に本番 sqlite_path を使用（KABUSYS_ENV に依存せず）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict をつけると警告も失敗扱い（exit 1）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 関連（関数API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB の接続オブジェクトを受け取り、各テーブルを参照して結果を書き込みます。
  - OpenAI API キーは OPENAI_API_KEY 環境変数で指定するか、関数引数で渡してください。

---

## 停止・Kill 機構

- stop_requested.flag
  - run_monitoring.py / run_execution.py は data/stop_requested.flag の存在をチェックし、見つかれば安全にループを抜けて終了します。
  - 外部からプロセスを優雅に止めたい場合はこのファイルを作成してください。

- kill.flag（Kill Switch）
  - Monitoring の判定で深刻なリスク（例: ドローダウン閾値超過、ポジション上限超過）が発生した際に、KillSwitch が data/kill.flag を書き込みます。
  - ExecutionEngine は起動時に kill.flag がある場合は起動を拒否します（本番での誤発注防止）。

- PID ファイル
  - data/execution.pid（デフォルト）に ExecutionEngine の PID を格納する仕組みがある想定です（Settings.pid_file_path）。

---

## 主要環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

運用 / オプション:
- KABUSYS_ENV — 実行環境（development / paper_trading / live） (default: development)
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）ファイルパス（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（default: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレード時の約定シミュレーション（instant / partial / never / reject。default: instant）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL。default: INFO）
- LOG_DIR — ログ出力ディレクトリ（default: logs/）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール利用時に必要）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、default: 60）
- KILL_FLAG_CLEAR_ON_START — 本番での自動 kill.flag クリア（0推奨、1で自動クリア）

自動読み込み:
- .env / .env.local をプロジェクトルートから自動読み込み（無効: KABUSYS_DISABLE_AUTO_ENV_LOAD=1）

---

## ディレクトリ構成（src/kabusys の主要ファイル群）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
  - MONITOR_POLL_INTERVAL で間隔を制御
  - 監視は常に本番 sqlite_path を使う（環境に依存しない）

- run_execution.py
  - ExecutionEngine 起動スクリプト
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い paper DB に記録

- config.py
  - Settings クラス（環境変数のラッパ）
  - .env 自動読み込みロジック、必須チェックヘルパ等

- config_setup.py
  - 対話式 .env 作成ウィザード

- validate_config.py
  - .env / config/*.yaml の検証ツール（--strict オプションあり）

- utils/
  - logging_setup.py — ルートロガー設定（コンソール + 日次ローテーションファイル）
  - process_priority.py — プロセス優先度（Windows / POSIX 対応）と CPU affinity 設定ユーティリティ

- monitoring/
  - monitoring_db.py — SQLite 上の永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — システム状態・データ鮮度の監視
  - trade_monitor.py — （注文ログ監視）※ソース内に実装あり
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — data/kill.flag 書込による停止シグナル管理
  - monitoring_engine.py — 各 Monitor と AlertManager を束ねる実行エンジン

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - Execution / 発注関連ロジックを含む（ブローカー抽象化、リスク制御等）

- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 発注株数計算（単元丸め・aggregate cap）
  - risk_adjustment.py — セクターキャップ、レジーム乗数

- research/
  - factor_research.py — momentum/value/volatility 等のファクター計算（DuckDB を用いた SQL）
  - feature_exploration.py — 将来リターン、IC、統計サマリ

- ai/
  - news_nlp.py — ニュース記事を OpenAI でセンチメント評価し ai_scores テーブルに反映
  - regime_detector.py — ETF MA とマクロニュースを合成して市場レジームを判定

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成（期間指定可）

- __init__.py / version 管理等

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）では十分な確認を行ってください。validate_config は本番向けチェック（LINE トークン未設定等）を警告します。
- kill.flag / stop_requested.flag といったフラグファイルを用いた停止設計になっています。手動で削除すると起動が可能になりますが、本番では意図的な操作に注意してください。
- OpenAI API を使う処理は API 呼び出しに失敗する場合にフォールバック動作を持つ設計ですが、API キー管理・利用制限には注意してください。
- DuckDB / SQLite のファイルパスは Settings で設定可能です。特にペーパートレード用 DB は本番と分離することが重要です（PAPER_TRADING_SQLITE_PATH）。
- ロギングは logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリの作成に失敗した場合は標準出力のみになります。

---

もし README に追記したい内容（例: 実行例や systemd / supervisor 用の起動スクリプトテンプレート、より詳細な設定項目の説明など）があれば指示ください。README をその内容に合わせて拡張します。