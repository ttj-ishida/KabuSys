# KabuSys

日本株向けの自動売買 / 研究基盤ライブラリ群および起動スクリプト群です。  
本リポジトリは、実運用向けの ExecutionEngine（発注系）・Monitoring（監視系）、研究用モジュール（ファクター計算・特徴量解析）や AI ベースのニュース NLP モジュールなどを含みます。

バージョン: 0.1.0

--------------------------------------------------------------------------------
目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動 / CLI）
- 環境変数（主要項目）
- ディレクトリ構成
- 注意事項 / 運用メモ
--------------------------------------------------------------------------------

## プロジェクト概要
KabuSys は以下の責務を持つモジュール群で構成されています。
- ExecutionEngine: ブローカークライアントを通じた発注処理（本番 / ペーパートレード対応）
- Monitoring: システム稼働監視、注文モニタ、リスク監視、Kill Switch（停止フラグ）など
- Portfolio: 銘柄選定・配分・ポジション決定（等重、スコア加重、リスクベース等）
- Research: DuckDB を使ったファクター計算・将来リターン計算・IC（情報係数）等
- AI: ニュース記事の NLP スコアリング（OpenAI を利用）および市場レジーム判定
- Tools: ペーパートレードの検証レポート生成スクリプト 等
- Utils: ロギング設定、プロセス優先度設定 等のユーティリティ
- Config: 環境変数/.env の読み込み・検証・ウィザード

設計方針は「本番リスクを分離したフェイルセーフ」「ルックアヘッドバイアスの排除」「DB への冪等書き込み」「外部 API の失敗に対する堅牢なリトライ/フォールバック」です。

## 主な機能一覧
- ExecutionEngine 起動スクリプト（kabusys.run_execution）
  - KABUSYS_ENV により paper_trading モード時は MockBroker を使用し、ペーパートレード DB に記録
  - プロセス優先度を高く設定、PID ファイル管理、停止フラグ監視
- Monitoring 起動スクリプト（kabusys.run_monitoring）
  - システム（CPU/Memory/Disk）、発注ログ、リスク（ドローダウン・ポジション数）を定期記録
  - KillSwitch を評価して必要に応じて data/kill.flag を作成
  - MONITOR_POLL_INTERVAL でポーリング間隔変更可能
- MonitoringDB: SQLite による監視ログ永続化（テーブル作成・マイグレーション対応）
- RiskMonitor / TradeMonitor / SystemMonitor / MonitoringEngine: 監視ロジック群
- AI: news_nlp（ニュースを LLM でセンチメント化して ai_scores に書き込み）、regime_detector（市場レジーム判定）
- Research: calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic など
- Portfolio: 候補選定、重み計算、ポジションサイズ算出、セクターキャップ適用
- CLI ツール:
  - python -m kabusys.config_setup : .env の対話式作成/更新ウィザード
  - python -m kabusys.validate_config : 起動前の設定検証（--strict オプションあり）
  - python -m kabusys.tools.paper_verification_report : ペーパートレード検証レポート生成

## セットアップ手順（ローカル開発向け）
1. Python 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必須（最低限）:
     - duckdb
     - psutil
     - openai
   - 任意（YAML 検証や拡張時に必要）:
     - PyYAML
   - インストール例:
     - pip install duckdb psutil openai PyYAML

   （リポジトリに requirements.txt や pyproject.toml がある場合はそちらを利用してください。）
   
3. パッケージのインストール（開発用）
   - リポジトリルートから:
     - pip install -e .

   もしくは、インストールを行わない場合は、実行時に PYTHONPATH を通す:
     - PYTHONPATH=src python -m kabusys.validate_config

4. .env の用意
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに `.env` を作成。主要なキーは下記参照。

5. DB/データディレクトリ
   - デフォルトで `data/` 配下（sqlite / duckdb / pid / flag 等）を使用します。必要に応じて `.env` の `DUCKDB_PATH` / `SQLITE_PATH` / `PAPER_TRADING_SQLITE_PATH` を変更してください。
   - ログは `logs/` に出力されます（設定により変更可）。

## 使い方（主要なコマンド）
プロジェクトルートで実行する想定です（`src` をパッケージルートとしている場合は PYTHONPATH を通してください）。

- .env 作成ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - 厳密モード（警告をエラー扱い）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（発注エンジン）
  - 本番/ペーパーは KABUSYS_ENV によって自動切替
  - python -m kabusys.run_execution
  - 動作中に停止したい場合:
    - monitoring の KillSwitch または手動で data/kill.flag を作成
    - run_execution は `data/stop_requested.flag` を検知すると終了します

- Monitoring 起動（監視ループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（例: export MONITOR_POLL_INTERVAL=30）

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB オプション指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI / 研究モジュールはライブラリ関数として呼び出して利用します（例: kabusys.ai.score_news, kabusys.research.calc_momentum 等）。

### 実行時の注意点
- 実行スクリプトは起動時にプロセス優先度を "high" に設定します（プラットフォームによっては権限が必要で失敗することがありますが、警告にフォールバックします）。
- run_execution/run_monitoring はそれぞれ `data/stop_requested.flag` の存在でループを抜けます（安全なシャットダウン手段）。
- ExecutionEngine は paper_trading モードのとき `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）を使用して本番 DB と分離します。

## 主要な環境変数（概要）
（.env で管理。config_setup で作成できます）

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants API 用のリフレッシュトークン

- KABU_API_PASSWORD (必須)
  - kabuステーション API パスワード

- KABU_API_BASE_URL (任意)
  - デフォルト: http://localhost:18080/kabusapi

- KABUSYS_ENV (推奨)
  - 値: development | paper_trading | live
  - デフォルト: development

- DUCKDB_PATH
  - デフォルト: data/kabusys.duckdb

- SQLITE_PATH
  - デフォルト: data/monitoring.db

- PAPER_TRADING_SQLITE_PATH
  - ペーパートレード専用 SQLite（paper_trading 時に使用）
  - デフォルト: data/paper_trading.db

- PAPER_FILL_MODE
  - ペーパートレードの約定動作: instant | partial | never | reject
  - デフォルト: instant

- LOG_LEVEL
  - DEBUG / INFO / WARNING / ERROR / CRITICAL
  - デフォルト: INFO

- OPENAI_API_KEY
  - news_nlp / regime_detector 等で使用。指定がないと該当機能は例外になります（あるいはフォールバック挙動）。

- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔（秒）
  - デフォルト: 60

- KILL_FLAG_CLEAR_ON_START
  - 起動時に kill.flag を自動クリアするフラグ（開発用。production では 0 推奨）

その他、細かい設定は config/*.yaml（システム設定等）やコード内のデフォルトを参照してください。

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要モジュール構成です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/.env 読み込みと Settings オブジェクト
  - config_setup.py           — .env 対話ウィザード CLI
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト

  - ai/
    - news_nlp.py             — ニュースを LLM でスコアリングし ai_scores へ書込
    - regime_detector.py      — 市場レジーム判定（LLM + MA200 合成）
  - monitoring/
    - monitoring_db.py        — SQLite テーブル作成 / MonitoringDB ラッパ
    - monitoring_engine.py    — Monitor を束ねるポーリングエンジン
    - system_monitor.py       — CPU/Memory/Disk / データ鮮度チェック
    - risk_monitor.py         — ドローダウン・ポジション数監視
    - trade_monitor.py        — （注文周りのチェック・未約定等）※詳細はソース参照
    - kill_switch.py          — kill.flag の作成/クリア
    - alert_manager.py        — （アラート送信の管理、LINE 等）※実装ファイル参照
  - execution/
    - execution_engine.py     — ExecutionEngine 本体（セッション管理）
    - broker_factory.py       — ブローカクライアント生成（本番/Mock 切替）
    - order_manager.py        — 注文管理
    - order_repository.py     — 注文履歴保存
    - reconciler.py           — 注文差分解消等
    - risk_manager.py         — 発注前リスクチェック
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — ポジションサイズ算出
    - risk_adjustment.py      — セクター上限・レジーム乗数
  - research/
    - factor_research.py      — ファクター計算（momentum/value/volatility）
    - feature_exploration.py  — 将来リターン / IC / 統計サマリ
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py        — 統一ロギング設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ

- config/
  - system_config.yaml, data_config.yaml, ... （テンプレ/例: config_setup で生成）

- data/
  - monitoring DB / paper DB / pid / flags（実行時に作成されます）
- logs/
  - 実行ログ（<app_name>.log、日次ローテーション）

## 注意事項 / 運用メモ
- 本番運用（KABUSYS_ENV=live）時は .env に本番用の認証情報を配置し、KILL_FLAG_CLEAR_ON_START を 0 にしてください。
- OpenAI を使う機能は API コスト・レート制限が発生します。API キー管理・リトライ設定に注意してください。
- monitoring / execution はそれぞれ `data/stop_requested.flag` の存在で安全に終了します。CI/デプロイ環境ではこの停止フラグ方式を使って制御できます。
- Monitoring は環境に依らず（KABUSYS_ENV にかかわらず）本番の sqlite_path を使用する設計になっています。ペーパートレード DB と分離したい場合は設定を確認してください。
- DB マイグレーション（monitoring_db のカラム追加等）は起動時に自動で補完するロジックがありますが、大きな変更を行う場合はバックアップを推奨します。

---

不明点や README に追記してほしい情報（例: 実運用の Docker 化手順、CI/CD の設定例、より詳細なアーキテクチャ図など）があれば教えてください。README を用途に合わせて追記・整形します。