README
=====

概要
----
KabuSys は日本株向けの自動売買システム（ライブラリ兼起動スクリプト群）です。  
主要な機能は市場データ解析、ポートフォリオ構築、ポジションサイジング、発注実行、監視・アラート、AI を使ったニュースセンチメント評価などを含みます。  
本リポジトリはライブラリとしての再利用性を重視しており、CLI/デーモン風に起動するスクリプト群を提供します。

主な特徴
--------
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
  - 等配分 / スコア加重 / リスクベースの算出ロジック
  - セクターキャップ、レジーム乗数の適用ロジック
- リサーチモジュール（DuckDB を用いたファクター計算）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン、IC、ファクター統計サマリの算出
- AI モジュール（OpenAI を利用）
  - ニュース記事のセンチメントスコア化（news_nlp）
  - マクロ + ETF MA による市場レジーム判定（regime_detector）
- 発注実行エンジン（ExecutionEngine 起動スクリプト）
  - KABUSYS_ENV=paper_trading のときはモックブローカーを使用し、本番 DB と分離（data/paper_trading.db）
  - リスク管理（ポジション上限・ドローダウン等）
- 監視エンジン（Monitoring）
  - システム稼働・データ鮮度・トレード健全性の定期チェック
  - Kill Switch（条件発生で data/kill.flag を書いて ExecutionEngine を停止可能）
- 運用ツール
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール

セットアップ手順
----------------
前提
- Python 3.10 以上（PEP 604 の型記法を使用）
- SQLite は標準で利用可能
- 推奨ライブラリ（最低限）:
  - duckdb
  - psutil
  - openai (AI 機能利用時)
  - PyYAML（config/*.yaml 検証を行う場合）

手順（例）
1. リポジトリをクローンし、仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール:
   - pip install duckdb psutil openai pyyaml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

3. .env の初期作成:
   - python -m kabusys.config_setup
     - 対話形式で .env を生成できます。生成後は .env を Git にコミットしないでください。

4. 設定検証:
   - python -m kabusys.validate_config
   - 問題があれば修正して再実行（--strict オプションで警告も失敗扱いにできます）

5. データディレクトリとログディレクトリの確認:
   - デフォルトの DB/ログパスは .env のデフォルトに従います（例: data/kabusys.duckdb, data/monitoring.db, logs/）
   - ログは kabusys.utils.logging_setup によって logs/<app_name>.log に日次ローテートで出力されます。

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
  - paper_trading のとき発注はモックに分離され、paper_trading DB に記録されます
- OPENAI_API_KEY（AI 機能を使う場合）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- MONITOR_POLL_INTERVAL（監視ループのポーリング間隔（秒）、デフォルト 60）
- LOG_LEVEL（ログレベル: DEBUG/INFO/...）

使い方（起動・ツール）
---------------------
主な起動コマンド（パッケージモードで実行）:
- 監視ループを起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（例: export MONITOR_POLL_INTERVAL=30）

- 実行エンジンを起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使い paper_trading DB に記録します
  - 起動時に data/stop_requested.flag が存在すると起動を行いません
  - 停止は data/stop_requested.flag を書くことで検出して安全に停止できます

- .env 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: env の PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

ログ / データファイル
- ログ: logs/<app_name>.log（app_name は execution / monitoring 等）
- 監視 DB: data/monitoring.db（Settings.sqlite_path、monitoring 用テーブル群を自動作成）
- DuckDB: data/kabusys.duckdb（分析用）
- ペーパートレード DB: data/paper_trading.db（paper_trading モード時に分離）
- 停止フラグ: data/stop_requested.flag（プロセス間の停止シグナル）
- Kill Switch: data/kill.flag（監視が書き込むと ExecutionEngine に停止シグナル）

実運用上の注意
- KABUSYS_ENV=live 設定時は特に注意して設定を確認してください（validate_config に guard 警告あり）。
- kill.flag の自動クリアは危険（KILL_FLAG_CLEAR_ON_START はデフォルト 0 を推奨）。
- OpenAI API の呼び出しは費用が発生します。AI 機能を運用する場合は API キー管理とコスト監視を行ってください。
- process_priority（高優先度設定）や CPU affinity 設定はプラットフォーム依存で失敗する場合があります（権限不足時など）。警告ログが出ますが実行は継続します。
- Paper Trading モードは本番 DB と分離されますが、設定ミスに備え .env の値を必ず確認してください。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数 / Settings 管理。自動で .env を読み込む仕組みを持つ（プロジェクトルート検出ベース）。
- config_setup.py
  - .env の対話式ウィザード（python -m kabusys.config_setup）
- validate_config.py
  - 起動前の設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト（本番 / paper_trading 切替）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト
- ai/
  - news_nlp.py      — ニュースセンチメント集約・OpenAI 呼び出し、結果を ai_scores に書き込み
  - regime_detector.py — マクロ + ETF MA によるレジーム判定（market_regime 書き込み）
- monitoring/
  - monitoring_db.py — SQLite による永続化層（テーブル作成・読み書き API）
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py  — （トレード監視ロジック、コードベース内に参照あり）
  - risk_monitor.py   — ドローダウン・ポジション上限監視
  - kill_switch.py    — Kill Switch（kill.flag 管理）
  - monitoring_engine.py — 複数モニタを束ねるエンジン
  - alert_manager.py  — （通知・アラート送信のラッパ、コードベース内に参照あり）
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - 発注ロジック・リスク制御・ブローカー抽象化
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py   — 株数決定・単元丸め・集計キャップ
  - risk_adjustment.py   — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — Momentum/Volatility/Value 等のファクター計算（DuckDB 前提）
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- data/ (生成実行時に作られる想定)
  - monitoring.db (SQLite)
  - kabusys.duckdb (DuckDB)
  - paper_trading.db (paper_trading 用 SQLite)
  - execution.pid / stop_requested.flag / kill.flag 等の運用ファイル
- logs/
  - execution.log, monitoring.log 等（setup_logging により自動生成）

開発・拡張のヒント
------------------
- DuckDB 接続を渡す設計が多く、分析は DB 側（SQL）で効率的に処理する前提です。テスト時は小さな DuckDB ファイルで検証できます。
- OpenAI 呼び出しは再試行ロジック・レスポンス検証を実装済みですが、API 仕様変更や別ベンダーの採用時はラッパ関数を置換してください（テスト用に patch しやすい設計）。
- monitoring_db.init_monitoring_db は冪等でマイグレーション（カラム追加）も含んでいます。DB スキーマ変更時はここを拡張してください。
- 各モジュールは純粋関数（副作用少）で設計されている箇所が多く、ユニットテストが書きやすい構造です。

サポート / 問い合わせ
--------------------
- README の内容で分からない点がある場合は、該当モジュールの docstring を参照してください（各ファイル先頭に設計・使い方の説明があります）。
- 実行時のログ（logs/）がトラブルシューティングの第一手段です。エラー発生時はログを参照してください。

以上。