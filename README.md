README
=====

概要
----
KabuSys は日本株向けの自動売買システムのコードベースです。  
主な目的は、銘柄選定・ポジション構築・発注制御・監視・検証・研究支援を統合することです。  
このリポジトリには以下の主要コンポーネントが含まれます。

- ExecutionEngine（発注エンジン）: 実際の発注またはペーパートレードの実行
- Monitoring（監視）: システム稼働状況・注文状況・リスク監視と Kill Switch
- Portfolio モジュール: 候補選定、重み計算、ポジションサイズ算出、セクター制限
- Research モジュール: ファクター計算・特徴量探索・IC 等の解析ユーティリティ
- AI モジュール: ニュース NLP（OpenAI）を用いたセンチメント評価／レジーム判定
- ユーティリティ: ロギング設定、プロセス優先度設定、設定読み込み/ウィザード/検証等

特徴一覧
---------
- 環境別動作:
  - KABUSYS_ENV により development / paper_trading / live を切替可能
  - paper_trading 時は MockBrokerClient を使用し、監視・発注状態を本番 DB と分離
- 環境設定ウィザード（.env の対話生成）と設定検証 CLI
- 監視（Monitoring）:
  - system_status / trade_logs / positions / risk_logs / dashboard を SQLite に永続化
  - リスク（ドローダウン、ポジション数上限）を自動検出し Kill Switch を発動
  - ExecutionEngine の停止フラグ管理（stop_requested.flag / kill.flag）
- ポートフォリオ構築:
  - 候補選定、等重 / スコア加重、リスクベースのポジション決定
  - セクター上限・レジーム乗数による調整
- リサーチ:
  - Momentum / Volatility / Value ファクター、将来リターン計算、IC（スピアマン）
  - DuckDB 経由で大規模データを効率的に集計
- AI（OpenAI）連携:
  - ニュース記事をまとめて LLM でスコア化（gpt-4o-mini を想定）
  - マクロセンチメント + MA200 乖離で市場レジーム判定
  - API 呼び出しはリトライ・フェイルセーフ実装

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo_url>

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt がある場合: pip install -r requirements.txt
   - 必須ライブラリ（例）: duckdb, psutil, openai, pyyaml（機能に応じて）
     ※ requirements.txt がない場合は、用途に応じて個別にインストールしてください。

4. .env の作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
     → ウィザードに従って .env を生成します（.env はリポジトリへコミットしないでください）。

5. 設定検証
   - python -m kabusys.validate_config
   - 問題がある場合はメッセージに従って .env や config/*.yaml を修正してください。
   - --strict を付けると警告もエラー扱いになります。

6. データディレクトリの準備
   - デフォルトの DB / ログディレクトリは次のとおりです（変更は .env で可能）。
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログ: logs/
   - 必要に応じてディレクトリを作成してください。スクリプトが自動作成する箇所もあります。

環境変数（主なもの）
-------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD       — kabuステーション API パスワード
- 動作切替:
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - PAPER_FILL_MODE: instant | partial | never | reject  （paper_trading 用）
- DB / ログ:
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
  - LOG_LEVEL (DEBUG/INFO/...)
  - LOG_DIR（ログ出力先）
- AI:
  - OPENAI_API_KEY — OpenAI を使う機能に必要（news_nlp, regime_detector）
- 監視/制御:
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0/1)
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）: run_monitoring で使用
- その他:
  - PID_FILE_PATH（ExecutionEngine 用 pid ファイルパス）

使い方（主要コマンド）
--------------------
- 環境ウィザード（.env を対話生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）

- 発注エンジン起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い data/paper_trading.db に記録されます

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH（省略時は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

- AI 機能（プログラムから直接呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ※ OpenAI API キーが必要（環境変数 OPENAI_API_KEY または引数で与える）

停止と Kill Switch
-----------------
- run_execution / run_monitoring はプロジェクトルートの data/stop_requested.flag を監視しています。停止したい場合はこのファイルを作成すると優雅にシャットダウンします（手動で削除/クリアしてください）。
- KillSwitch（リスク超過による強制停止）は data/kill.flag を書き込みます。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動でクリアします（本番では 0 推奨）。

ログ
----
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力され、stdout へも出力されます（設定は kabusys.utils.logging_setup.setup_logging を通じて制御）。
- LOG_LEVEL/LOG_DIR 環境変数で挙動を調整できます。

ディレクトリ構成（主要ファイル / モジュール）
-------------------------------------------
src/kabusys/
- __init__.py
- config.py
  - .env 自動読み込み、Settings クラスで設定を提供
- config_setup.py
  - .env の対話式ウィザード
- validate_config.py
  - 起動前の設定検証 CLI
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading の場合は専用 DB を使用）
- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度・CPU affinity 設定
- monitoring/
  - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — システム稼働・データ鮮度チェック
  - trade_monitor.py — （注文滞留や約定異常検出）※実装が入っている想定
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の管理
  - monitoring_engine.py — 各モニタを束ねる実行エンジン
  - alert_manager.py — アラート送信（LINE等）※実装が入っている想定
- execution/
  - execution_engine.py — 発注エンジン（EngineConfig 等）
  - broker_factory.py — ブローカークライアント生成（Mock を含む）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注/リスク管理関連
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数算出・単元丸め・スケーリング
  - risk_adjustment.py — セクター制限・レジーム乗数
- research/
  - factor_research.py — Momentum/Volatility/Value 等の計算
  - feature_exploration.py — 将来リターン計算・IC 等
- ai/
  - news_nlp.py — OpenAI を使ったニュースセンチメントスコア化
  - regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント）
- tools/
  - paper_verification_report.py — ペーパートレードの検証レポート生成ツール
- data/（実行時に利用）
  - stop_requested.flag, kill.flag, execution.pid, 各種 DB ファイル（data/kabusys.duckdb 等）
- logs/（デフォルトログ出力先）

開発上の注意
------------
- .env は機密情報を含むため絶対にコミットしないでください。
- OpenAI を利用する機能は API コストとレイテンシが発生するため注意して運用してください。API呼び出しはリトライ・フェイルセーフが入っていますが、設定とログを十分に確認してください。
- 本番運用（KABUSYS_ENV=live）の場合は Kill Switch や通知設定（LINE）を必ず確認してください。
- Paper trading モードは実際の発注を行わないことを意図していますが、DB 分離やモックの動作は設定に依存します。運用前に paper_trading で十分な検証を行ってください。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ にて管理（現状: 0.1.0）。
- ライセンス表記や外部依存の注意点はリポジトリの LICENSE / README（上位）を参照してください。

問い合わせ
--------
実装詳細や運用ルールに関する質問、実行方法や設定に関する不明点はリポジトリの管理者へ問い合わせてください。