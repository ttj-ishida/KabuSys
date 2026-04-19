# KabuSys

日本株向けの自動売買システム（モジュール群）です。ポートフォリオ構築、ポジションサイジング、監視・アラート、ペーパートレード検証、AI を用いたニュースセンチメントや市場レジーム判定などを目的としたライブラリ／起動スクリプト群を含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（コマンド／スクリプト）
- 主要環境変数
- ディレクトリ構成（概要）
- トラブルシューティング / 注意点

---

## プロジェクト概要

KabuSys は以下の領域をカバーする Python パッケージです。

- 戦略リサーチ（DuckDB を用いたファクター計算、将来リターン算出、IC 計算など）
- ポートフォリオ構築（候補選定、重み算出、セクターキャップ適用、レジーム調整）
- 発注・実行（ExecutionEngine、ブローカーファクトリによりペーパートレード/実運用を切替）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor、SQLite に監視ログを永続化）
- Kill Switch（条件により ExecutionEngine に安全停止シグナルを送る）
- AI モジュール（OpenAI を使ったニュースセンチメント / 市場レジーム評価）
- ツール（ペーパートレードの検証レポート生成等）
- ユーティリティ（ロギング設定、プロセス優先度/CPU affinity 設定、設定読み込みウィザード等）

設計方針として、可能な限り「ルックアヘッドバイアスを防ぐ」実装（target_date を明示して external date を参照しない等）や、フェイルセーフ（API 失敗時に安全側で継続）を重視しています。

---

## 主な機能

- Settings クラスによる .env / 環境変数読み込みとバリデーション
- 対話式 .env 作成ウィザード（config_setup.py）
- 設定検証 CLI（validate_config.py、--strict オプションあり）
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動（paper_trading 環境の分離対応）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔制御）
- 監視 DB（SQLite）レイヤ（monitoring_db.py）と各種 Monitor（system / trade / risk）
- KillSwitch による停止フラグの書き込み／チェック（data/kill.flag）
- AI モジュール
  - news_nlp: OpenAI を用いたニュースセンチメント集約と ai_scores 書込
  - regime_detector: ETF MA とマクロニュースの LLM センチメントを合成して market_regime を判定
- 研究モジュール（research）: ファクター計算・前方リターン・IC・統計サマリ
- ポートフォリオ（portfolio）: 候補選定、等重/スコア重み、リスク調整、ポジションサイズ計算
- ツール: paper_verification_report による検証レポート生成

---

## セットアップ手順（ローカル開発向け）

前提:
- Python 3.10+（型注釈で Union "|"/型ヒントを使用しているため）
- DuckDB、psutil、openai、（検証用に）PyYAML などが必要

1. 仮想環境を作る
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - requirements.txt がある場合: pip install -r requirements.txt  
     （ない場合は少なくとも次をインストールしてください）
     - pip install duckdb psutil openai

   - 開発時に config YAML の検証を使うなら:
     - pip install pyyaml

3. リポジトリルートに移動して .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは手動で `.env` を作成（下にサンプルを記載）

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合: python -m kabusys.validate_config --strict

5. データディレクトリ（logs / data 等）は自動作成されますが、権限に注意してください。

---

## 使い方（起動スクリプトとツール）

基本はパッケージとしてモジュール実行します。

- 環境ファイル作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- ExecutionEngine（実行/ペーパートレード）
  - python -m kabusys.run_execution
  - 実行前に data/stop_requested.flag が存在すると起動をスキップします。
  - ExecutionEngine は Settings.is_paper に応じて paper_sqlite_path を使用（paper_trading 環境は本番 DB と完全分離）。

- Monitoring（監視ループ）
  - python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔: 60 秒。環境変数で上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

ログ:
- setup_logging により stdout と日次ローテートされたログファイルに出力されます。
- デフォルトログディレクトリ: logs/
- ログファイル名は app_name によって logs/<app_name>.log（例: logs/execution.log）

停止 / Kill Switch:
- KillSwitch は監視側から data/kill.flag を作成し ExecutionEngine 側に停止シグナルを送ります（実行側は起動時に kill flag をクリアするかどうか設定可能）。
- 全プロセス共通の stop ファイル: data/stop_requested.flag を作成すると run_* スクリプトのループを停止します（両スクリプトともチェックしています）。

---

## 主要環境変数（抜粋）

重要な環境変数とデフォルト:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants API 用リフレッシュトークン

- KABU_API_PASSWORD (必須)
  - kabuステーション API パスワード

- KABUSYS_ENV
  - 実行環境: development | paper_trading | live
  - デフォルト: development

- DUCKDB_PATH
  - DuckDB ファイルパス
  - デフォルト: data/kabusys.duckdb

- SQLITE_PATH
  - 監視 DB (SQLite) パス
  - デフォルト: data/monitoring.db

- PAPER_TRADING_SQLITE_PATH
  - Paper Trading 用 SQLite（ExecutionEngine が paper_trading の場合に使用）
  - デフォルト: data/paper_trading.db

- PAPER_FILL_MODE
  - Paper trading の MockBroker の約定モード
  - 有効値: instant | partial | never | reject
  - デフォルト: instant

- LOG_LEVEL
  - ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)
  - デフォルト: INFO

- LOG_DIR
  - ログ出力先ディレクトリ（setup_logging で使用）
  - デフォルト: logs/

- OPENAI_API_KEY
  - OpenAI を使用するモジュール（news_nlp / regime_detector）が参照する API キー

- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔（秒）
  - デフォルト: 60（1秒未満や 0 は無効でデフォルトへフォールバック）

- KILL_FLAG_CLEAR_ON_START
  - ExecutionEngine 起動時に既存の kill.flag を自動でクリアするか（1: クリア、0: しない）
  - 本番では 0 を推奨

ログイン／外部 API:
- OPENAI_API_KEY をセットしておかないと AI モジュールはエラーになります（エラーはフェイルオープンで処理する箇所もありますが、明示的にセットすることを推奨）。

.env の例（.env に保存する変数のサンプル）
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要構成です（抜粋）。

- kabusys/
  - __init__.py
  - config.py                       — 環境変数 / .env 読み込み・Settings
  - config_setup.py                 — 対話式 .env ウィザード
  - validate_config.py              — 設定検証 CLI
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py   — ペーパートレード検証レポート
  - ai/
    - news_nlp.py                    — ニュース NLP / OpenAI スコアリング
    - regime_detector.py             — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py               — SQLite 監視 DB レイヤ
    - monitoring_engine.py           — 各 Monitor を束ねるエンジン
    - system_monitor.py              — システム状態・データ鮮度監視
    - risk_monitor.py                — ドローダウン・ポジション上限監視
    - trade_monitor.py                — （注文監視ロジック, ファイル内未表示箇所）
    - kill_switch.py                 — kill.flag 書き込みユーティリティ
    - alert_manager.py               — （アラート送信管理: LINE など、ファイル内未表示箇所）
  - execution/
    - execution_engine.py            — ExecutionEngine（起動・セッション管理）
    - broker_factory.py              — ブローカークライアント生成（Mock/実口座切替）
    - order_manager.py               — 注文管理
    - order_repository.py            — 注文永続化
    - reconciler.py                  — ブローカーと DB を突合
    - risk_manager.py                — 実行時リスク管理
  - portfolio/
    - portfolio_builder.py           — 銘柄選定・スコアソート
    - position_sizing.py             — 発注株数計算（単元丸め・aggregate cap）
    - risk_adjustment.py             — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py             — ファクター計算（momentum/value/volatility）
    - feature_exploration.py         — 将来リターン / IC / 統計
  - utils/
    - logging_setup.py               — 統一ログ設定（stdout + 日次ローテート）
    - process_priority.py            — プロセス優先度 / CPU affinity 設定

（上記以外にもヘルパー／リポジトリ実装が含まれます）

---

## トラブルシューティング / 注意点

- ログディレクトリ作成に失敗するとファイル出力が無効になり stdout のみになります。権限を確認してください。
- psutil による優先度設定や CPU affinity 設定は権限不足で失敗することがあります（警告が出ますが処理は継続します）。
- DuckDB / SQLite のパスはデフォルトで data/ 配下。別パスを使用する場合は .env で更新してください。
- Paper Trading は本番 DB と分離されます（settings.is_paper = True のときに paper_sqlite_path を使う）。
- OpenAI を利用する AI モジュールは API キーが必須です。キー未設定時は例外を投げるか、フェイルセーフで 0.0 を使う設計の箇所があります。ログを確認してください。
- run_monitoring のポーリング間隔は MONITOR_POLL_INTERVAL 環境変数（秒）で上書き可能。無効値（0 や負数、非数）はデフォルト 60 秒にフォールバックします。
- 停止フラグ:
  - data/stop_requested.flag: ループ駆動スクリプトを停止させるためのフラグ（外部から停止したいときに作成）
  - data/kill.flag: KillSwitch が書き込み、ExecutionEngine に安全停止を要求する（実行側で明示的に取り扱います）
- validate_config.py により本番環境に入る前に環境変数や重要なファイルの存在チェックができます。--strict モードは警告も失敗扱いします。

---

もし README にさらに追記してほしい項目（例: API の詳細、ExecutionEngine のシーケンス図、設定ファイルのサンプル YAML、テスト手順など）があれば教えてください。必要に応じて追記・詳述します。