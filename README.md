# KabuSys

日本株自動売買システム用ライブラリ / 実行スクリプト群

このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・リサーチ・AI補助モジュールを含む日本株向け自動売買基盤の一部です。軽量なローカル DB（SQLite / DuckDB）を用い、ペーパートレードと本番（live）を切り替え可能な構成になっています。

## 主な特徴
- 実行コンポーネント
  - ExecutionEngine 起動スクリプト（run_execution.py）
    - KABUSYS_ENV による paper_trading と live 切替
    - ペーパートレード時は MockBrokerClient を使用し DB を分離
- 監視・運用
  - System / Trade / Risk を統合する MonitoringEngine（run_monitoring.py）
  - kill.flag による外部からの停止指示（Kill Switch）
  - 停止フラグ / PID / ログ管理の仕組み
- ポートフォリオ構築（純粋関数）
  - 候補選定、重み計算、ポジションサイズ計算、セクター制限など
- リサーチ（DuckDB を利用）
  - モメンタム、ボラティリティ、バリュー計算
  - 将来リターン、IC（Information Coefficient）計算、統計サマリ
- AI モジュール（OpenAI）
  - ニュース NLU による銘柄センチメント（news_nlp）
  - マクロ＋MA200 による市場レジーム判定（regime_detector）
  - API 呼び出し時のリトライ・検証ロジック
- 運用支援ツール
  - .env 対話ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ペーパートレード検証レポート生成（tools/paper_verification_report.py）

## 必要条件
- Python 3.10+
- 推奨パッケージ（主要な機能を使う場合）:
  - duckdb
  - psutil
  - openai
  - PyYAML（validate_config の YAML 検証用）
- これらはプロジェクト側で requirements.txt にまとめている前提で pip install してください。（requirements.txt が無い場合は上記パッケージを個別にインストール）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

## セットアップ手順（簡易）
1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成して依存パッケージをインストール（上記参照）
3. 初期環境変数ファイルを作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（下記サンプル参照）
4. 設定の検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります
5. 必要な DB ファイル・ディレクトリ（data/ logs/）は起動スクリプトが自動作成する場合がありますが、権限等に注意してください

## 主要な環境変数（抜粋）
多くは .env で管理します。代表的なもの:

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL — DEBUG/INFO/...
- DB パス
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — 監視 DB（monitoring.db）デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 DB（paper_trading.db）
- Paper Trading
  - PAPER_FILL_MODE — instant / partial / never / reject（デフォルト: instant）
- OpenAI
  - OPENAI_API_KEY — news_nlp / regime_detector で使用
- 監視・停止
  - PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（開発用, 0/1）
  - MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト: 60）
- ログ
  - LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）

.env の一例（機密情報は伏せる）:
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

※ .env は絶対にバージョン管理にコミットしないでください。

## 使い方（実行例）

- 環境ファイル作成（対話ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）を使用し MockBrokerClient が選ばれます。
  - data/execution.pid に PID を書き、data/stop_requested.flag / data/kill.flag で外部停止制御があります。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると kill.flag を自動クリアします（注意: 本番では 0 推奨）。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 監視は常に本番用の sqlite_path を参照する仕様です（環境にかかわらず）。

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプションで期間指定や DB パス指定:
    - --from YYYY-MM-DD --to YYYY-MM-DD --db path/to/paper_trading.db

- ライブラリ関数（例）
  - ポートフォリオ構築:
    - from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes
  - リサーチ:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
  - AI:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

## 停止・キルスイッチの仕組み
- 外部から実行エンジンを停止するには data/kill.flag を作成します（KillSwitch により評価される）。
- run_monitoring/run_execution は stop_requested.flag（data/stop_requested.flag）や kill.flag の存在を検知して安全に停止します。
- execution は data/execution.pid に PID を書き込みます。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると Execution 起動時に既存の kill.flag をクリアします（本番では危険なので推奨しません）。

## ロギング
- 共通ユーティリティ kabusys.utils.logging_setup.setup_logging を通してログを設定します。
- デフォルト: コンソール出力 (stdout) ＋ 日次ローテーションするファイル出力（logs/<app_name>.log、30日分保持）
- ログレベルは LOG_LEVEL または setup_logging の引数で制御可能

## ディレクトリ構成（主なファイル）
src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings 管理
- config_setup.py          — .env 対話ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring ポーリング起動スクリプト
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py
  - regime_detector.py
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py (存在想定)
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py (存在想定)
- utils/
  - logging_setup.py
  - process_priority.py
- data/ (実行時に生成される / デフォルト配置)
  - monitoring.db (デフォルト SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - kill.flag, stop_requested.flag, execution.pid

（注）一部ファイルはスニペット内で参照されている想定のファイルが存在することを前提としています（例: trade_monitor.py, alert_manager.py など）。実際のリポジトリ状況に応じて補完してください。

## 運用上の注意
- KABUSYS_ENV=live の場合は本番口座に実際の発注が行われるため、設定（特に KILL_FLAG_CLEAR_ON_START、LINE 通知設定、API キーなど）を慎重に確認してください。
- .env は機密情報を含むため、絶対に Git 等の VCS にコミットしないでください。
- OpenAI API を利用する機能は API 呼び出しコスト・レイテンシ・レート制限に注意してください。API キーは適切に管理してください。
- DuckDB / SQLite ファイルへのアクセス権限やディスク容量に注意してください（ログ・DB の肥大化）。

---

問題や拡張要望があれば、どの機能についてドキュメントを追加するか指定してください。サンプルの .env テンプレートや起動スクリプトの具体的なオプション、各モジュールのより詳細な使用例も追加できます。