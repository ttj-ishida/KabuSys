README
======

概要
----
KabuSys は日本株向けの自動売買プラットフォームのコードベースです。本プロジェクトは以下の主要機能を提供します。

- 注文実行のための ExecutionEngine（本番 / ペーパートレード対応）
- システム監視（CPU/メモリ/ディスク・データ鮮度・プロセス監視）と監視ループ
- リスク監視（ドローダウン・保有上限など）と Kill Switch（危険時の停止）
- ポートフォリオ構築（候補選定、配分計算、ポジションサイジング、セクター制約）
- リサーチ / ファクター計算（モメンタム、ボラティリティ、バリュー等）
- ニュース NLP を使った銘柄センチメント評価（OpenAI 経由）
- ペーパートレード検証レポート生成ツール
- 設定ウィザード（.env の生成）・設定検証ツール

特徴
----
- 本番とペーパートレードを分離（DB も分離）
- DuckDB を分析用 DB、SQLite を監視 / 注文ログ用 DB として併用
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント / レジーム判定（オプション）
- ロギングはコンソール + 日次ローテートファイル出力で統一
- Kill Switch により自動で ExecutionEngine を停止可能（冪等・安全設計）
- 設定支援 CLI（.env ウィザード / validate）

セットアップ手順
--------------
1. リポジトリをチェックアウトしてプロジェクトルートへ移動

2. Python 環境（推奨: 3.10+）を用意
   - 仮想環境を使うことを推奨します
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - requirements.txt がない場合は少なくとも下記をインストールしてください:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML (設定ファイルの検証を行う場合)
   例:
     pip install duckdb psutil openai PyYAML

4. 初期設定 (.env) の作成
   - 対話式ウィザードを使う:
     python -m kabusys.config_setup
   - 生成される .env には J-Quants トークンや kabuステーション API パスワード等の
     機密値を含むため、絶対に Git にコミットしないでください。

5. 設定検証（必須環境変数や config/*.yaml の確認）
   python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     python -m kabusys.validate_config --strict

6. 必要なデータディレクトリ作成（例）
   mkdir -p data logs

7. OpenAI を使う場合
   - 環境変数 OPENAI_API_KEY を .env に設定するか、score_news / score_regime の引数で渡します。

基本的な使い方
--------------

環境変数 / .env の要点
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- よく使う:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパー取引用 SQLite（paper_trading 時）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/…）
  - OPENAI_API_KEY: OpenAI を利用する場合

起動スクリプト
- 監視ループ（SystemMonitor）を起動:
  python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）
  - 監視は monitoring DB（SQLITE_PATH）に永続化します
  - 停止方法: プロジェクトルート/data/stop_requested.flag を作成すると監視ループが終了します

- 実行エンジン（ExecutionEngine）を起動:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、PAPER_TRADING_SQLITE_PATH に記録します（本番 DB と分離）
  - 起動時に data/stop_requested.flag が存在する場合は起動しません
  - エンジンは内部で pid ファイル（data/execution.pid デフォルト）を生成します

ツール / CLI
- 設定ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ペーパートレード検証レポート:
  python -m kabusys.tools.paper_verification_report
  期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  DB 指定:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

ライブラリ API（主なもの）
- AI / ニューススコア:
  from kabusys.ai.news_nlp import score_news
  - 引数: duckdb 接続, target_date, api_key(optional)
  - OpenAI API キーが必要（引数または環境変数 OPENAI_API_KEY）

- レジーム判定:
  from kabusys.ai.regime_detector import score_regime
  - 同様に DuckDB 接続と target_date を渡して実行

- ポートフォリオ:
  from kabusys.portfolio import (
      select_candidates, calc_equal_weights, calc_score_weights,
      calc_position_sizes, apply_sector_cap, calc_regime_multiplier
  )

- リサーチ:
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

ロギング
- デフォルトは logs/<app_name>.log（日次ローテート、30日保持）と標準出力
- 環境変数 LOG_DIR でログディレクトリを変更可能
- ログレベルは LOG_LEVEL または setup_logging の引数で調整

停止・Kill Switch
- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）は KillSwitch により書き込まれ、ExecutionEngine に対する停止シグナルとなります
- run_monitoring / run_execution はプロジェクトルート/data/stop_requested.flag を検出して安全に停止します
- KILL_FLAG_CLEAR_ON_START=1 を設定すると（本番では推奨しない）、起動時に kill.flag を自動でクリアします

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings 管理（.env 自動読み込みロジック含む）
- config_setup.py          — .env 対話ウィザード
- validate_config.py       — 設定検証 CLI
- run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py         — ExecutionEngine 起動スクリプト

subpackages:
- ai/
  - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py     — 市場レジーム判定（MA + マクロ NLP）
- monitoring/
  - monitoring_db.py       — SQLite 監視 DB テーブル定義・永続化ヘルパ
  - system_monitor.py      — CPU/メモリ/ディスク・データ鮮度・プロセス監視
  - risk_monitor.py        — ドローダウン / ポジション上限監視
  - trade_monitor.py       —（注文監視ロジック、ファイル内参照有り）
  - monitoring_engine.py   — 各 Monitor を束ねるエンジン
  - kill_switch.py         — Kill Switch 実装
  - alert_manager.py       —（アラート送信ロジック、ファイル内参照有り）
- execution/
  - execution_engine.py    — ExecutionEngine（起動・セッション管理）
  - order_manager.py       — 発注管理
  - order_repository.py    — 注文ログ / 永続化
  - broker_factory.py      — ブローカークライアント生成（Mock / 実ブローカー）
  - reconciler.py          — 注文状態整合
  - risk_manager.py        — 発注時のリスク制約
- portfolio/
  - portfolio_builder.py   — 候補選定・スコアソート
  - position_sizing.py     — 株数決定・資金スケール
  - risk_adjustment.py     — セクター制約・レジーム乗数
- research/
  - factor_research.py     — ファクター計算（momentum/volatility/value）
  - feature_exploration.py — IC / ファクター統計
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - logging_setup.py       — ログセットアップユーティリティ
  - process_priority.py    — プロセス優先度 / CPU affinity 設定

注意事項 / 運用上のポイント
------------------------
- .env（機密情報）は絶対に Git にコミットしないでください
- KABUSYS_ENV により挙動が変わります。特に live（本番）では設定を慎重に確認してください
- monitoring は Settings.env にかかわらず sqlite_path（本番 DB）を使用する設計箇所があります（run_monitoring 内の挙動に注意）
- OpenAI を使う処理は API 呼び出しに費用が発生します。rate limit・エラー処理は実装済みですが使用時は考慮してください
- ローカルでテストする際は KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数を 1 にすると自動 .env 読み込みを抑制できます

サンプル .env（最低限）
---------------------
# KabuSys 簡易サンプル .env
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-xxxx...

問い合わせ / コントリビュート
----------------------------
不具合報告、改善提案、パッチは GitHub 上のプルリクエストでお願いします。運用に関わる重大な変更（Kill Switch / DB スキーマ など）は事前に議論をお願いします。

以上が本リポジトリの README です。必要に応じて、実際の requirements.txt、起動 systemd ユニット例、DB 初期データ生成スクリプトなどのドキュメントも追加できます。必要であれば作成します。