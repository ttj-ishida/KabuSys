KabuSys — 日本株自動売買システム（README）
====================================

概要
----
KabuSys は日本株の自動売買 / リサーチ / モニタリング用の軽量フレームワークです。  
主に以下を提供します。

- 発注実行（ExecutionEngine） — 本番 / ペーパートレード両対応
- モニタリング（System / Trade / Risk）と Kill Switch（安全停止）
- ポートフォリオ構築（銘柄選定・重み算出・ポジションサイズ計算）
- リサーチ（ファクター計算・特徴量探索）
- AI モジュール（ニュースセンチメントによるスコアリング / レジーム判定）
- ペーパートレード検証レポート生成ツール

このリポジトリは純粋関数群、DB 永続層、起動スクリプトを含み、実運用・検証の両方を想定して設計されています。

主な機能
--------
- ExecutionEngine
  - 実際のブローカー（kabuステーション等）と接続して発注
  - KABUSYS_ENV=paper_trading で MockBroker を使用し本番 DB と分離
  - リスク管理（ポジション上限、ドローダウン等）
- Monitoring
  - CPU/メモリ/ディスク/プロセス状態の定期記録
  - 注文ログ・リスクログの永続化（SQLite ベース）
  - Kill Switch（閾値超過で data/kill.flag に理由を書き込み、Execution を停止）
- Portfolio（純粋関数）
  - 候補選定、等重・スコア重み、リスク調整、ポジションサイズ計算
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を使用）
  - 将来リターン・IC（Information Coefficient）計算、統計サマリ
- AI（OpenAI）
  - ニュース記事を LLM でセンチメント評価 → ai_scores に保存
  - マクロ記事 + ETF MA200 乖離を組み合わせた市場レジーム判定
- ユーティリティ
  - .env 対話型ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成（tools.paper_verification_report）
- ロギング
  - 共通セットアップ（stdout + 日次ローテーションファイル）
  - ログディレクトリ： logs/<app_name>.log（既定）

動作要件
--------
- Python 3.10+
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（validate_config の YAML 検証に任意）
-（推奨）仮想環境の使用

セットアップ手順
--------------
1. リポジトリをクローン、ソースルートへ移動
   - この README はパッケージが src/kabusys 配下にある構成を前提としています。

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. インストール
   - pip install -e .    （パッケージ配布用の setup/pyproject がある場合）
   - 必要ライブラリを個別インストール:
     - pip install duckdb psutil openai PyYAML

4. .env の作成（必須環境変数を設定）
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参照して .env を用意してください。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict オプションで警告もエラー扱いにできます。

6. データディレクトリ
   - デフォルトの DB / flag / pid は data/ 配下に配置されます（必要なら手動で作成してください）。
   - ログは logs/ 配下に出力されます（自動作成されます）。

環境変数（主要）
----------------
以下はよく使う環境変数（抜粋）です。詳細は kabusys.config.Settings を参照してください。

- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY: OpenAI を使う場合に必須
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（デフォルト、monitoring 用）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- LOG_LEVEL: DEBUG/INFO/...
- LOG_DIR: ログ保存先
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant/partial/never/reject）
- KILL_FLAG_PATH: data/kill.flag（デフォルト）

使い方（起動・主要コマンド）
--------------------------
- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番 or ペーパーは KABUSYS_ENV で切替）
  - python -m kabusys.run_execution
  - 注意: 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中は data/execution.pid（既定）に PID を書きます。

- Monitoring を起動（バックグラウンド監視）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒）
  - 停止は data/stop_requested.flag を作成するか、KeyboardInterrupt

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH

- Research / AI API（ライブラリ呼び出し）
  - 例: DuckDB 接続を渡してファクター計算
    from kabusys.research import calc_momentum
    calc_momentum(conn, date(2026, 4, 1))

停止 / Kill Switch
------------------
- KillSwitch（自動）
  - 条件（ドローダウン超過、ポジション上限 等）を満たすと data/kill.flag に理由を書き込み ExecutionEngine に停止を促します。
- 手動停止フラグ
  - data/stop_requested.flag を作成すると run_execution/run_monitoring は次のループで停止します。

ログ
----
- ログは stdout（コンソール）と logs/<app_name>.log に日次ローテーションで出力されます。
- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一されます。

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定取得
  - config_setup.py         — .env 対話ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py      — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/               — Execution 関連（Engine, BrokerFactory, OrderManager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — レジーム判定（MA200 + マクロ NLP）
  - tools/
    - paper_verification_report.py

開発上の注意
------------
- DB スキーマ初期化はスクリプト内で自動的に行われます（init_monitoring_db）。
- 本番（live）モードでは設定ミスが重大になるため validate_config の実行を推奨します。
- AI 機能は OpenAI API を使用します。API キーの取り扱いには注意してください（.env を Git に含めないこと）。
- psutil などのシステムライブラリはプラットフォームごとに動作差異があるため、実運用環境で事前にテストしてください。

ライセンス / 貢献
-----------------
（この README にライセンス情報は含めていません。必要に応じて pyproject.toml / LICENSE を参照してください）

問題報告・改善提案
-----------------
不具合や提案があれば issue を立ててください。ロギングや validate_config により再現手順の把握が容易になるようログ出力を添えてください。

以上。必要であれば、実行例や systemd / docker-compose 用のサンプル unit を追加で作成します。どの形式が欲しいか教えてください。