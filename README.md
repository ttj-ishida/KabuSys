# KabuSys

日本株向け自動売買システムのコアライブラリ群（リサーチ／ポートフォリオ構築／発注／監視／ユーティリティ）。  
このリポジトリは、実行スクリプト・監視エンジン・ペーパートレード分離・AI を用いたニュース評価などを含む、運用に耐える設計を意識したモジュール群で構成されています。

## 概要
- DuckDB を用いた時系列データ分析（prices_daily / raw_financials 等）
- SQLite を用いた監視・発注ログ（monitoring.db / paper_trading.db）
- ExecutionEngine（発注ロジック）と MonitoringEngine（監視・Kill Switch）
- Paper Trading と Live を明確に分離（Paper 用 DB と MockBroker）
- OpenAI（gpt-4o-mini）を使ったニュース NLP（センチメント評価）／レジーム判定モジュール
- 各種 CLI：.env ウィザード、設定検証、ペーパートレード検証レポート生成 等

## 主な機能一覧
- 環境設定ウィザード（kabusys.config_setup）
  - .env の初期作成・更新を対話式で支援
- 設定検証 CLI（kabusys.validate_config）
  - 必須環境変数／config/*.yaml／DBパス等の事前チェック
- Execution 起動スクリプト（kabusys.run_execution）
  - KABUSYS_ENV に応じて本番または paper_trading モードで起動
  - paper_trading は data/paper_trading.db に記録（本番 DB と完全分離）
- Monitoring 起動スクリプト（kabusys.run_monitoring）
  - 定期ポーリングで SystemMonitor 等を実行（MONITOR_POLL_INTERVAL で制御）
  - 停止フラグ（data/stop_requested.flag）でループを終了
- 監視サブシステム（kabusys.monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager（通知は実装次第）
  - monitoring DB のスキーマ初期化・永続化（monitoring_db）
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定・重み計算・ポジションサイズ計算・セクター制約適用
- リサーチ（kabusys.research）
  - モメンタム／ボラティリティ／バリュー等のファクター計算
  - 将来リターン・IC 計算・特徴量サマリ等
- AI モジュール（kabusys.ai）
  - ニュースのセンチメントスコア化（OpenAI） → ai_scores に書き込み
  - 市場レジーム判定（ma200 + マクロセンチメント合成）
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

## セットアップ手順（ローカル / 開発）
前提: Python 3.10+ を推奨（| 型等を利用しているため）。適宜仮想環境を作成してください。

1. リポジトリをクローン
   - git clone で取得

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 代表的な依存:
     - duckdb
     - psutil
     - openai
     - （任意）PyYAML（config/*.yaml 内容検証に使用）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. .env を作成
   - 設定ウィザードを使うと簡単:
     - python -m kabusys.config_setup
   - もしくは手動で `.env` を作成（.env.example を参考にしてください）
   - 自動ロード:
     - 起動時、プロジェクトルート（.git または pyproject.toml がある場所）を基に `.env` と `.env.local` を自動読み込みします。
     - 自動ロードを無効にする場合: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

5. 設定検証（必須項目や YAML 構文をチェック）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにするには `--strict` を付与

6. ログディレクトリ
   - デフォルトは `logs/`。存在しない場合は自動作成されます。作成できない場合はコンソール出力のみになります。

## 使い方（主要コマンド例）

- 環境設定ウィザード（.env を作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution エンジン起動
  - python -m kabusys.run_execution
  - 動作モードは `KABUSYS_ENV` に依存:
    - development: 発注抑止（ローカル用）
    - paper_trading: MockBroker を用い paper_db に記録（PAPER_TRADING_SQLITE_PATH で上書き可）
    - live: 実際に発注（注意：本番設定を正しく行ってから）

- Monitoring 起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定（デフォルト 60）
  - python -m kabusys.run_monitoring

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH を使用

- AI 系（ニュース評価 / レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY）
  - ニューススコアリング関数（ライブラリ API 呼び出し）:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

## 主要環境変数（抜粋）
- KABUSYS_ENV: execution モード（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: monitoring DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、default 60）
- OPENAI_API_KEY: OpenAI を使う機能の API キー
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に Kill Flag を自動クリアするか（0/1、本番では 0 推奨）

## 実行時の振る舞い（重要な注意点）
- run_execution.py:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading.db に記録します。実運用の DB と分離されます。
  - 起動時に data/stop_requested.flag がある場合は起動しません。
  - 実行中は data/execution.pid を作成します（PID ファイル）。
- run_monitoring.py:
  - 監視は常に本番用の sqlite_path を使用（KABUSYS_ENV に依らず）。
  - data/stop_requested.flag が作成されるとループを終了します。
- Kill Switch:
  - RiskMonitor 等が条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
  - 本番環境では `KILL_FLAG_CLEAR_ON_START=0` にしておくことを推奨します。
- ログ:
  - logs/<app_name>.log に日次ローテーションで保存（30日分保持）。コンソールは stdout に出力。

## 依存関係（代表）
- duckdb
- psutil
- openai
- PyYAML（任意：config/*.yaml の検証用）
- （利用するブローカークライアント等に応じて追加）

インストール例:
- pip install duckdb psutil openai PyYAML

## ディレクトリ構成
（src/kabusys 以下の主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス・自動 .env ロードロジック
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
      - Paper Trading 検証レポート生成 CLI
  - ai/
    - news_nlp.py
      - ニュースセンチメント API ラッパー（OpenAI）
    - regime_detector.py
      - マーケットレジーム判定（ma200 + LLM）
  - monitoring/
    - monitoring_db.py
      - monitoring DB スキーマ初期化・永続化層
    - system_monitor.py
    - trade_monitor.py (実装ファイルが存在します)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (通知管理：実装に応じて接続)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ （実行時に使用されるデフォルトパス）
    - monitoring.db (デフォルトの SQLite)
    - paper_trading.db (paper_trading 用 DB)
    - kabusys.duckdb (デフォルト DuckDB)
    - stop_requested.flag / kill.flag / execution.pid 等

（注）上記はコードベースの主要モジュール概観です。細部は各ファイルの docstring を参照してください。

## 開発メモ / 注意事項
- DB のスキーマ更新は monitoring_db.init_monitoring_db に記述（既存 DB のマイグレーション処理あり）。
- AI モジュールは API 呼び出しに失敗してもフェイルセーフ（デフォルト値で継続）する設計です。ただし本番での運用では API レートや料金を考慮してください。
- プロセス優先度（set_process_priority）を起動時に設定しますが、権限不足で失敗する場合は警告のみ出ます。
- DuckDB への書き込みは executemany の空リストに対する互換性に注意（コード側で回避実装あり）。

---

README に書かれていない細かい使い方やコンフィグ項目は各モジュールの docstring を参照してください。必要であれば、導入手順や運用ガイド（デプロイ、監視ルール、バックアップ手順等）を別途作成できます。どの情報を追加したいか教えてください。