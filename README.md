KabuSys — 日本株自動売買システム
===============================

このリポジトリは日本株向けの自動売買システム（研究・ポートフォリオ構築・発注・監視・補助ツール群）です。本 README はコードベースの主要機能、セットアップ、起動方法、ディレクトリ構成をまとめたものです。

プロジェクト概要
---------------
KabuSys は以下の責務を持つモジュール群で構成されています。

- strategy / research: ファクター計算、特徴量探索、将来リターンや IC（情報係数）の算出
- portfolio: 候補選定、重み算出、ポジションサイズ決定、セクター制限などのポートフォリオ構築ロジック
- execution: ブローカークライアントを使った発注エンジン、注文管理、リスク管理、照合（Reconciler）など（実行スクリプトあり）
- monitoring: システム稼働状況・注文ログ・リスク監視、kill switch など（監視ループ起動スクリプトあり）
- ai: ニュース NLP（OpenAI を用いたセンチメントスコアリング）、市場レジーム検出
- tools: ペーパートレード検証レポートなどの補助ツール
- utils: ログ設定・プロセス優先度設定などの共通ユーティリティ
- config: 環境変数/設定読み込み、.env ウィザード、設定検証ツール

主な設計方針:
- 本番/ペーパー/開発環境を環境変数 KABUSYS_ENV で切り替え
- DB は DuckDB（分析用）と SQLite（監視・発注ログ等）を利用
- LLM（OpenAI）を用いる部分は API キー必須で、失敗時はフェイルセーフで継続する設計

機能一覧
--------
主要機能（抜粋）：

- 環境設定
  - .env 対話ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]

- 実行 / 監視
  - ExecutionEngine 起動: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、paper_trading.db に記録（本番 DB と分離）
    - 停止フラグ data/stop_requested.flag を検知して安全停止
  - SystemMonitor / MonitoringEngine 起動: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）
    - 監視ログは SQLite（monitoring.db）に永続化

- 監視・リスク管理
  - システムリソース監視（CPU/メモリ/ディスク）、データ鮮度チェック
  - 注文滞留・約定異常チェック
  - ドローダウン・ポジション上限監視 → Kill Switch による停止（data/kill.flag）

- ポートフォリオ構築
  - 候補選定、等重/スコア重み、リスク基準に基づくポジションサイズ計算、セクター上限の適用

- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を使用）
  - 将来リターン計算、IC（スピアマンランク相関）や統計サマリー用ユーティリティ

- AI（OpenAI）
  - ニュース記事の銘柄単位センチメント算出（ai_scores テーブルへ書き込み）
  - マクロニュース＋ETF の MA 乖離から市場レジーム（bull/neutral/bear）判定

- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

セットアップ手順
---------------
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必須 (例):
     - duckdb
     - psutil
     - openai
   - オプション:
     - pyyaml (config/*.yaml の構文チェック用)
   - 例:
     - pip install duckdb psutil openai pyyaml

   （requirements.txt がある場合はそれを使用してください）

4. .env を作成
   - 対話ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - または .env.example を参考に .env を作成してルートに配置

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 本番前は --strict を付けると警告も FAIL 扱いになる:
     - python -m kabusys.validate_config --strict

6. DB 初期化
   - 起動スクリプトが起動時に必要なテーブルを作成します（monitoring 用テーブル等は init_monitoring_db により冪等作成されます）
   - DuckDB / SQLite のデフォルトパスは .env で上書き可能

環境変数（主なもの）
--------------------
Settings クラスに定義された主な環境変数（デフォルト値や説明）:

- KABUSYS_ENV: execution モード（development, paper_trading, live） — デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールを使う場合必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング秒数（run_monitoring で利用、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定振る舞い (instant|partial|never|reject)

例 (.env)
----------
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

使い方（起動コマンド）
--------------------

- 実行エンジン（ExecutionEngine）を起動:
  - python -m kabusys.run_execution
  - 振る舞い:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い paper_trading.db に記録し、本番 DB と完全に分離します
    - data/stop_requested.flag が存在すると起動せず終了します
    - 起動時に data/execution.pid を書きます（PID ファイル）

- 監視ループを起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を指定可能（秒）
  - 監視は monitoring DB（Settings.sqlite_path）にログを記録します

- .env ウィザード（対話的）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能

ログ
----
- ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging
- デフォルト: stdout と 日次ローテーションファイル（logs/<app_name>.log）に出力
- ログディレクトリは LOG_DIR 環境変数で変更可

停止 / Kill Switch
------------------
- 手動停止:
  - run_execution / run_monitoring はループ中に data/stop_requested.flag を検知すると安全に終了します（停止フラグファイルを作成）
- リスクによる停止（Kill Switch）:
  - RiskMonitor 等がしきい値を超えた場合、KillSwitch が data/kill.flag を書き込み、ExecutionEngine 側で検出して停止します
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアしますが、本番では推奨されません

ディレクトリ構成（主なファイル）
-------------------------------
（src/kabusys 以下の主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み & Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

  - utils/
    - logging_setup.py       — ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity

  - monitoring/
    - monitoring_db.py       — SQLite テーブル作成・読み書きラッパ
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （注文監視ロジック）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 管理
    - monitoring_engine.py   — 各 Monitor を束ねる

  - execution/
    - execution_engine.py    — ExecutionEngine（発注セッション）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py

  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数決定・単元丸め
    - risk_adjustment.py     — セクター制限・レジーム乗数

  - research/
    - factor_research.py     — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー

  - ai/
    - news_nlp.py            — ニュースセンチメントスコア算出（OpenAI）
    - regime_detector.py     — マクロ＋ETF MA からレジーム判定

  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

補足・運用上の注意
------------------
- OpenAI 等の外部 API を使う処理は API キーが必要です。キー漏洩に注意して .env は Git に入れないでください。
- 本番環境（KABUSYS_ENV=live）では kill switch や LINE 通知などを適切に設定してください（validate_config がチェックします）。
- DuckDB は分析用の大規模クエリに向いています。prices_daily / raw_financials / raw_news などのテーブル設計に合わせてデータをロードしてください。
- プロセス優先度設定 (psutil に依存) は権限により失敗することがあります。ログで警告されますが動作は継続します。

よく使うコマンドまとめ
--------------------
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- 起動（監視）: python -m kabusys.run_monitoring
- 起動（発注）: python -m kabusys.run_execution
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス・貢献
----------------
（この README には含まれていません。リポジトリの LICENSE ファイルを参照してください。）

---
README はここまでです。内部 API（関数引数や戻り値の詳細）や DB スキーマ、運用手順（起動監視スクリプトを systemd / Supervisor / cron で運用する方法等）について、必要であれば別途ドキュメントを作成します。どの詳細を追加しますか？