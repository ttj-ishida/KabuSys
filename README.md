KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システム用ライブラリ／実行ツール群です。
このリポジトリは以下の主要機能を持ちます。

- 注文実行エンジン（ExecutionEngine）を起動してブローカーとやり取りするランナー
- システム監視（SystemMonitor）・取引監視（TradeMonitor）・リスク監視（RiskMonitor）を組み合わせた監視エンジン
- Paper Trading 用のログ集計・検証ツール（paper_verification_report）
- ポートフォリオ構築、ポジションサイジング、セクター調整などの純粋関数モジュール
- リサーチ用ファクター計算（momentum, volatility, value 等）
- ニュースを LLM（OpenAI）で評価してスコア化する AI モジュール（news_nlp）や市場レジーム検出（regime_detector）
- 環境設定ウィザード（.env 生成）、設定検証 CLI、統一的なログ設定ユーティリティ 等

特徴
----
- モジュール化された設計で、実行ロジック・監視・リサーチ・AI を分離
- Paper Trading と Live を明確に分離（Paper は専用 SQLite DB を使用）
- DuckDB をリサーチ／分析用 DB として利用
- OpenAI を利用したニュースセンチメント評価（エラー耐性／バッチ処理／検証付き）
- ログは stdout と日次ローテートファイル（logs/<app>.log）へ出力
- kill.flag / stop フラグによる外部停止制御をサポート

主な機能一覧
--------------
- 実行ランナー:
  - run_execution.py — ExecutionEngine 起動スクリプト（KABUSYS_ENV=paper_trading の場合は MockBroker）
- 監視ランナー:
  - run_monitoring.py — SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）
- 設定管理:
  - config_setup.py — .env を対話式に作成・更新するウィザード
  - validate_config.py — .env や config/*.yaml を起動前に検証する CLI
- Paper Trading 検証:
  - tools/paper_verification_report.py — ペーパートレードログを集計し PASS/FAIL レポートを出力
- ポートフォリオ構築:
  - portfolio/*.py — 候補選定、重み計算、セクター制約、ポジションサイズ決定ロジック
- リサーチ:
  - research/factor_research.py, feature_exploration.py — ファクター計算・IC 計算・統計サマリ
- AI:
  - ai/news_nlp.py — raw_news を LLM でスコア化して ai_scores に保存
  - ai/regime_detector.py — ETF とマクロニュースを組合せて市場レジーム判定
- 監視:
  - monitoring/* — monitoring DB の永続化、System/Trade/Risk モニタ、KillSwitch、Alert 管理
- ユーティリティ:
  - utils/logging_setup.py — 統一ログ設定
  - utils/process_priority.py — プロセス優先度設定（Windows / POSIX 対応）

セットアップ手順
----------------
前提
- Python 3.10 以上（コード内で | 型やその他新しい構文を使用）
- 適宜仮想環境を推奨（venv / pyenv 等）

1. リポジトリをクローンして作業ディレクトリへ移動
   - 例: git clone <repo> && cd <repo>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - 本リポジトリに requirements.txt が無い場合、少なくとも以下をインストールしてください:
     - duckdb
     - psutil
     - openai
     - pyyaml (config の YAML 検証を使う場合)
   - 例:
     - pip install duckdb psutil openai pyyaml

4. .env 作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に .env を手動作成
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=your_token
     - KABU_API_PASSWORD=your_kabu_password
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - OPENAI_API_KEY=sk-...

   注意:
   - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト用）。

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - strict モード: python -m kabusys.validate_config --strict

使い方
------
起動関連

- 監視ループ（SystemMonitor）を起動:
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring
  - 補足:
    - 監視は MONITOR_POLL_INTERVAL（秒、デフォルト 60）でポーリングします。
    - run_monitoring は monitoring 用の sqlite_path（Settings.sqlite_path）を本番用 / 環境に関わらず使用します。
    - 停止はプロジェクトルート/data/stop_requested.flag を作成すると監視ループが検知して終了します。

- Execution エンジンを起動:
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）にログを記録します（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在する場合は起動をせず終了します。
    - 実行中は PID が data/execution.pid（デフォルト）に書かれます。停止は stop flag を作成してください。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。--db オプションで別パスを指定可能。

AI / レジーム関連（プログラム呼び出し）
- ニューススコア化（プログラム的に呼ぶ）:
  - from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, target_date, api_key="...")

- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key="...")

ログ
- ログは標準出力（stdout）に出力され、logs/<app_name>.log に日次ローテーションで保存されます。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一的に行われます。
- LOG_LEVEL / LOG_DIR 環境変数で挙動を調整可能。

停止制御（Kill Switch / Stop Flag）
- KillSwitch: RiskMonitor がしきい値を超える（例: ドローダウン超過）と data/kill.flag に理由を書き込みます。ExecutionEngine はこのファイルを検知して安全停止するための仕組みです。
- 管理ファイル:
  - data/kill.flag — KillSwitch が書き込む停止フラグ
  - data/stop_requested.flag — ローカルの手動停止要求（run_* スクリプトがこれを検知して停止）
  - data/execution.pid — 実行中の ExecutionEngine の PID（起動スクリプトで指定可能）

ディレクトリ構成（主なファイル）
--------------------------------
以下は src/kabusys 配下の主要モジュールと簡単な説明です（完全な一覧はソースを参照してください）。

- src/kabusys/
  - __init__.py                      — パッケージ定義（__version__ 等）
  - config.py                         — 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py                   — .env 対話式ウィザード
  - validate_config.py                — 起動前設定検証 CLI
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - run_monitoring.py                 — SystemMonitor ポーリング起動スクリプト

- src/kabusys/ai/
  - news_nlp.py                       — ニュースを LLM でスコア化する処理
  - regime_detector.py                — 市場レジーム判定ロジック

- src/kabusys/monitoring/
  - monitoring_db.py                  — SQLite 監視 DB のスキーマ & 永続化 API
  - system_monitor.py                 — CPU/メモリ/ディスク・データ鮮度等の監視
  - trade_monitor.py                  — 取引ログの整合性・滞留注文検出（存在）
  - risk_monitor.py                   — ドローダウン・ポジション上限監視
  - kill_switch.py                    — Kill Switch 書き込み・評価
  - monitoring_engine.py              — 各 Monitor を束ねて実行

- src/kabusys/execution/
  - (ExecutionEngine, OrderManager, BrokerFactory 等の実装 - 起動用スクリプトから利用)

- src/kabusys/portfolio/
  - portfolio_builder.py              — 候補選定・重み付け
  - position_sizing.py                — 発注株数の算出（単元丸め・資金制約）
  - risk_adjustment.py                — セクターキャップ・レジーム乗数

- src/kabusys/research/
  - factor_research.py                — momentum/volatility/value 等のファクター計算（DuckDB 利用）
  - feature_exploration.py            — 将来リターン / IC / 統計サマリ

- src/kabusys/tools/
  - paper_verification_report.py      — Paper Trading の検証レポート生成 CLI

- src/kabusys/utils/
  - logging_setup.py                  — ルートロギング設定ユーティリティ
  - process_priority.py               — プロセス優先度 / CPU affinity 設定（psutil 使用）

注意事項・トラブルシューティング
---------------------------------
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須（validate_config で検出）
- PyYAML がインストールされていない場合、validate_config は YAML 内容検証をスキップしますが警告します。
- OpenAI 関連:
  - OPENAI_API_KEY を環境変数として設定するか、各関数呼び出し時に api_key を渡してください。
  - API 呼び出しはレート制限・一時エラーに対してリトライロジックが組み込まれていますが、クォータには注意してください。
- ファイル書き込み権限:
  - デフォルトで data/ や logs/ を作成しようとします。実行ユーザーに書き込み権限が必要です。
- Paper Trading と Live のデータ分離:
  - run_execution は paper_trading モードのとき PAPER_TRADING_SQLITE_PATH の DB を使用します。監視 DB は run_monitoring 実行時に Settings.sqlite_path（monitoring.db）を使用します（環境に依らず本番監視 DB を使う設計上の注意点あり）。

ライセンス・貢献
----------------
- 本 README はコードベースに基づく導入・運用ガイドです。実際の運用にあたってはテスト環境で十分に検証してください。
- 変更・追加機能がある場合は PR を作成してください（コードスタイル・テストを併記することを推奨）。

最後に
-----
まずは .env を作成し、python -m kabusys.validate_config で環境チェック、続けて python -m kabusys.config_setup で設定を整え、監視と実行をローカルで動かしてみてください。質問や補足説明が必要であれば教えてください。