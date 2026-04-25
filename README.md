README
======

概要
----
KabuSys は日本株向けの自動売買／研究プラットフォームのコードベースです。  
バックグラウンドでの注文実行（ExecutionEngine）、システム監視（Monitoring）、ファクター計算・研究、ポートフォリオ構築、AI（ニュースセンチメント／レジーム判定）などのモジュールを含みます。

主な特徴
--------
- ExecutionEngine（実行エンジン）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - ブローカークライアント抽象化（Mock 対応）
  - リスク管理・注文管理・再突合（reconciler）
- Monitoring（監視）
  - プロセス・システムリソース監視、データ鮮度チェック
  - トレードログ / リスクログの永続化（SQLite）
  - KillSwitch による安全停止（フラグファイル）
- Portfolio（ポートフォリオ構築）
  - 候補選定、重み付け、ポジションサイジング、セクター制限等
- Research（研究）
  - DuckDB を用いたファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン計算、IC 計算、統計サマリ
- AI
  - ニュースセンチメント（OpenAI）を銘柄別にスコアリング
  - マクロニュースとETF MA によるレジーム判定
- ユーティリティ
  - ロギング設定、プロセス優先度 / CPU affinity 設定
  - .env 対話式ウィザード / 設定検証 CLI
  - ペーパートレード検証レポート生成スクリプト

動作要件（概略）
----------------
- Python 3.9+
- 主要 Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証を行う場合）
- （任意）J-Quants / kabuステーション 接続設定（実行時に環境変数で設定）

セットアップ手順
----------------
1. リポジトリを取得して、仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストールします（プロジェクトに requirements.txt がある場合はそれを使用）。
   例:
   - pip install duckdb psutil openai PyYAML

3. .env を作成します（推奨: 対話式ウィザードを使用）。
   - python -m kabusys.config_setup
   これにより .env が生成されます。必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を適切に設定してください。

4. 設定の検証:
   - python -m kabusys.validate_config
   - 警告もエラーとして扱いたい場合は --strict を付ける: python -m kabusys.validate_config --strict

主要な環境変数（要点）
--------------------
（.env に設定する主なキー）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY（AI 機能を使う場合に必須）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
  - paper_trading の場合、ExecutionEngine は専用の PAPER_TRADING_SQLITE_PATH を使用
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用、デフォルト: data/monitoring.db） — Monitoring は常に本番 sqlite_path を使用します
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START（0/1: 起動時に kill.flag をクリアするか）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔を秒で上書き、デフォルト 60）

自動 .env 読み込み
------------------
- プロジェクトルート（.git または pyproject.toml がある場所）から .env / .env.local を自動的に読み込みます。
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

実行方法
--------
- ExecutionEngine（発注エンジン）起動:
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に書き込み、本番 DB と分離されます。
    - 起動時に data/stop_requested.flag が既に存在する場合は起動を行いません。
    - 停止は監視側の stop flag（data/stop_requested.flag）を置くことで検知され、エンジンに停止命令を送ります。

- Monitoring（監視ループ）起動:
  - python -m kabusys.run_monitoring
  - オプション:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き（デフォルト 60 秒）
  - 注意:
    - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path（SQLITE_PATH）を使用して監視テーブルを初期化します。
    - 停止は data/stop_requested.flag を作成するとループを抜けます。

- 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - --strict を指定すると警告も失敗扱い（exit 1）

- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定:
    - --db PATH （なければ環境変数 PAPER_TRADING_SQLITE_PATH / data/paper_trading.db を使用）

停止方法（フラグファイル）
------------------------
- 停止要求（手動）:
  - プロジェクトの data ディレクトリに stop flag を作る:
    - touch data/stop_requested.flag
  - run_execution と run_monitoring の両方がこのファイルを参照して起動ループを終了します（デーモン的実行時の安全停止手段）。

- KillSwitch（自動基準による停止）:
  - Monitoring による判定（例: ドローダウン超過）で KillSwitch が data/kill.flag を書き込みます。
  - kill.flag が存在すると ExecutionEngine 側での起動挙動や運用上の取り扱いに影響します（環境変数 KILL_FLAG_CLEAR_ON_START を参照して起動時の自動クリア等の運用が可能）。

ログ
---
- デフォルトのログ出力先: logs/
- 各アプリケーション（execution / monitoring など）は logs/<app_name>.log に日次ローテーションで出力されます。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一して行われます。

ライブラリ的なモジュール利用例
----------------------------
- 研究用ファクター計算:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - これらは DuckDB 接続と日付を受け取り、純粋関数的に結果を返します（DB に副作用なし）。
- ポートフォリオ構築:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier

注意点 / 運用メモ
----------------
- Monitoring は監視テーブルの初期化（init_monitoring_db）を行います。監視 DB のパスは Settings.sqlite_path（SQLITE_PATH）で指定します。
- ExecutionEngine はペーパートレード時に paper_trading DB を使って本番 DB と分離するよう設計されています。
- OpenAI を使う機能（ニューススコア、レジーム判定）は OPENAI_API_KEY が必須です。API の呼び出しはリトライやフォールバックを実装していますが、API キーがないと例外になります。
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup.py でも明示されています）。
- ログディレクトリや data ディレクトリの作成に失敗した場合、ファイル出力をスキップしてコンソール出力のみで継続する場合があります（logging_setup の仕様）。

ディレクトリ構成（抜粋）
-----------------------
- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定読み込みロジック（.env 自動ロード）
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py                — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py         — レジーム判定（MA + マクロ NLP）
  - portfolio/
    - portfolio_builder.py       — 候補選定 / 重み付け
    - position_sizing.py         — 発注株数計算
    - risk_adjustment.py         — セクター制限 / レジーム乗数
  - research/
    - factor_research.py         — Momentum / Value / Volatility 計算（DuckDB）
    - feature_exploration.py     — 将来リターン / IC / 統計
  - monitoring/
    - monitoring_db.py           — SQLite ベースの永続化層（監視ログ）
    - system_monitor.py          — システム状態 / データ鮮度監視
    - trade_monitor.py           — トレード監視（ログ解析）
    - risk_monitor.py            — ドローダウン / ポジション上限監視
    - kill_switch.py             — フラグファイルによる停止シグナル生成
    - monitoring_engine.py       — 各 Monitor を束ねるエンジン
    - alert_manager.py           —（通知管理: LINE 等 — 実装参照）
  - execution/                    — 発注関連（broker_factory, execution_engine, order_manager, risk_manager 等）
  - data/                         — 初期データ / runtime ファイル（data/*.db, *.pid, *.flag）※ 実行時に作成
  - logs/                         — ログ出力先（デフォルト）

付録：よく使うコマンド例
-----------------------
- .env の作成（ウィザード）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution 起動（フォアグラウンド）:
  - python -m kabusys.run_execution

- Monitoring 起動（フォアグラウンド）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 停止（手動）:
  - touch data/stop_requested.flag

- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または DB を指定: python -m kabusys.tools.paper_verification_report --db ./data/paper_trading.db

お問い合わせ / 貢献
------------------
- README に記載の注意事項を守り、.env を漏洩しないよう注意してください。  
- バグ修正・機能追加は PR を歓迎します。コード内のドキュメント（docstring）に従って実装してください。

以上。必要であれば、README に含めるサンプル .env のテンプレートや運用フロー（デプロイ手順、systemd / supervisor 用のユニット例）を追記します。どの情報がさらに欲しいか教えてください。