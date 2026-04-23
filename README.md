KabuSys
======

日本株向けの自動売買／リサーチ基盤の一部を実装した Python パッケージです。
本リポジトリには、実行エンジン・監視（Monitoring）・ポートフォリオ構築・リサーチ・AI（ニュースNLP・レジーム判定）
および関連ユーティリティが含まれます。

この README はソースコードを元にした概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

プロジェクト概要
---------------
KabuSys は以下のような責務を持つモジュール群で構成されます。

- ExecutionEngine: 注文生成〜発注〜約定管理（本番/ペーパートレード切替対応）
- Monitoring: システム安定性・注文履歴・リスク（ドローダウン／ポジション数等）を定期監視しアラート／Kill Switch を運用
- Portfolio: 銘柄選定・重み算出・ポジションサイズ決定・セクター制約・レジーム調整
- Research: DuckDB を用いたファクター計算・特徴量解析ユーティリティ
- AI: ニュースの NLP によるセンチメント算出や市場レジーム判定（OpenAI API 利用）
- Utils: ロギング設定、プロセス優先度・CPU affinity 設定などの共通処理
- Tools: ペーパートレード検証レポート生成スクリプト等

主な設計方針:
- 本番 DB とペーパートレード DB は分離（KABUSYS_ENV=paper_trading の場合は専用 SQLite を使用）
- DuckDB を分析用に利用（prices_daily / raw_financials 等のテーブルを想定）
- .env により環境変数で設定を行い、config_setup.py による対話的作成をサポート
- モジュールは「できるだけ副作用を持たない純粋関数／明確な永続化層」を意識して設計

機能一覧
--------
主な機能（抜粋）:

- 実行関連
  - ExecutionEngine の起動スクリプト（python -m kabusys.run_execution）
  - ブローカー実装を環境に応じて切り替え（paper_trading → MockBrokerClient）
  - 注文管理（OrderRepository / OrderManager / Reconciler / RiskManager）

- 監視関連
  - SystemMonitor: CPU/メモリ/Disk・Execution プロセスの死活・データ鮮度監視
  - TradeMonitor: 注文の滞留検出・約定異常検出（trade_logs 参照）
  - RiskMonitor: ドローダウン検出、ポジション上限監視
  - KillSwitch: しきい値超過で data/kill.flag を書き込むことで ExecutionEngine を停止
  - MonitoringEngine: 上記をポーリングしてアラート発信・Kill Switch 評価

- ポートフォリオ構築
  - 銘柄選定、等重／スコア加重の重み計算
  - リスクベースの株数算出、単元株（lot）丸め、集約上限スケーリング
  - セクターキャップ適用、レジームに応じた投下資金乗数

- リサーチ / ファクター計算
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB を参照）
  - 将来リターン・IC（Information Coefficient）計算、ファクター統計サマリ

- AI
  - ニュース記事を OpenAI（gpt-4o-mini）でスコアリングして ai_scores テーブルへ書き込み
  - 市場レジーム判定（ETF ma200 乖離 + マクロニュースセンチメントの合成）

- ツール
  - ペーパートレード検証レポート生成スクリプト（python -m kabusys.tools.paper_verification_report）
  - .env 対話式ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）

- ユーティリティ
  - 統一的なログ設定（stdout と日次ローテーションファイル出力）
  - プロセス優先度・CPU affinity の簡易設定

セットアップ手順
----------------
以下は一般的なローカル開発/実行手順の例です。実際の依存パッケージは requirements.txt / pyproject.toml を参照してください。

1. リポジトリをクローン:
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境を作成・有効化:
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール:
   pip install -r requirements.txt
   またはパッケージ化されている場合は:
   pip install -e .

   ※ OpenAI API を使う場合は openai SDK が必要です（ソースでは OpenAI クラスを使用）。

4. .env の作成（対話式ウィザード推奨）:
   python -m kabusys.config_setup
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - KABUSYS_ENV: development / paper_trading / live のいずれか

5. 設定検証:
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

6. データディレクトリ
   デフォルトで以下パスを使用します（.env で上書き可能）:
   - DuckDB: data/kabusys.duckdb
   - Monitoring SQLite: data/monitoring.db
   - Paper trading SQLite: data/paper_trading.db
   - ログディレクトリ: logs/
   - Kill flag / pid 等: data/kill.flag, data/execution.pid, data/stop_requested.flag

使い方
------
エントリポイント（例）:

- 実行エンジン（ExecutionEngine）を起動:
  KABUSYS_ENV=paper_trading で起動すると MockBrokerClient を使用しペーパートレード DB（data/paper_trading.db）に分離して記録されます。
  python -m kabusys.run_execution

  特記事項:
  - 起動時に data/stop_requested.flag が存在する場合は起動しません。
  - プロセス優先度は起動直後に "high" に変更されます（set_process_priority）。

- 監視ループを起動:
  MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書きできます（デフォルト 60 秒）。
  python -m kabusys.run_monitoring

  監視は常に本番 sqlite_path（SQLITE_PATH）を使用します（KABUSYS_ENV に依らない）。

- .env の対話式作成:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ペーパートレード検証レポート生成:
  python -m kabusys.tools.paper_verification_report
  期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  DB 指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール（ニューススコア、レジーム判定）
  いずれも OpenAI API キーが必要（引数または環境変数 OPENAI_API_KEY）。
  例: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=...)
       kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

停止・Kill Switch
- 実行を強制停止するために data/kill.flag が使用されます（KillSwitch）。
- run_execution/run_monitoring スクリプトは data/stop_requested.flag を見て停止する仕組みになっています（外部で作成すると安全に停止できます）。
- KillSwitch.clear() は kill.flag を削除します（Execution 起動時に自動でクリアする挙動は KILL_FLAG_CLEAR_ON_START による設定で制御）。

ログ
- ログは stdout（コンソール）と logs/<app_name>.log（日次ローテーション、30 日保持）に出力されます。
- ログレベルは LOG_LEVEL 環境変数または .env の設定で制御します。

重要な環境変数（抜粋）
-----------------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨 / 重要:
- KABUSYS_ENV: development | paper_trading | live
  - paper_trading: MockBrokerClient を使用し paper_trading DB に記録（本番 DB と完全分離）
  - live: 本番運用（実取引）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI モジュール使用時）
- LOG_LEVEL（例: INFO, DEBUG）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔の上書き）
- KILL_FLAG_CLEAR_ON_START（0 or 1、本番では 0 推奨）

監視 DB（monitoring）
- monitoring_db.init_monitoring_db() で以下テーブルを作成（冪等）:
  - system_status, trade_logs, positions, risk_logs, dashboard
- 既存 DB にカラムを追加する簡易マイグレーション処理（peak_value, latency_ms の追加）あり

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュール（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                # .env 自動ロード・Settings クラス
  - config_setup.py          # .env 対話式ウィザード
  - validate_config.py       # 設定検証 CLI
  - run_execution.py         # ExecutionEngine 起動スクリプト
  - run_monitoring.py        # SystemMonitor ポーリングループ起動スクリプト

  - execution/               # 実行エンジン周り（OrderManager 等）
  - monitoring/
    - monitoring_db.py       # SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py

- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  (validate_config.py で存在チェックと YAML パース検証を行います。)

補足 / 運用上の注意
-------------------
- 本番（live）環境での実行時は KILL_FLAG_CLEAR_ON_START=0 を推奨します。自動クリアは危険です。
- AI モデルの呼び出し（OpenAI）は API レート制限やエラーに対してリトライ／フォールバック実装がありますが、API キーと課金設定は十分に注意してください。
- run_execution / run_monitoring はプロセス優先度を設定します。実行環境の権限によっては設定に失敗する場合があります（警告ログのみ）。
- DB パス・ログディレクトリ等の親ディレクトリが存在しない場合、起動時に自動作成される場合がありますが validate_config で事前確認することを推奨します。

ライセンス・貢献
----------------
（ここにプロジェクトのライセンスやコントリビューション手順を記載してください）

以上。この README はコードベースの現状を把握するためのサマリです。実運用時は該当する config/*.yaml や .env.example を参照し、テスト環境で十分に検証してから本番へ移行してください。