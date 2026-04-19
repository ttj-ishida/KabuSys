KabuSys
=======

日本株自動売買システムの小規模実装（リファレンス実装）
バージョン: 0.1.0

概要
----
KabuSys は日本株の自動売買・検証を目的としたコンポーネント群です。主な目的は以下です。

- ExecutionEngine による発注・注文管理（本番 / ペーパートレード対応）
- Monitoring によるシステム監視、アラート、Kill Switch（停止フラグ）制御
- Portfolio Construction（候補選定・配分・ポジションサイズ計算）
- Research（ファクター計算・特徴量解析）
- AI補助（ニュースセンチメント、レジーム判定） — OpenAI を利用
- 分析用に DuckDB、監視・履歴用に SQLite を利用

特徴（機能一覧）
----------------
- 実行（Execution）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - ブローカークライアント抽象化（BrokerClientFactory）
  - OrderManager / RiskManager / Reconciler を組み合わせた ExecutionEngine
  - PID ファイル管理（data/execution.pid）
- 監視（Monitoring）
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / プロセス生存確認
  - TradeMonitor: 注文滞留・約定異常などの検出（trade_logs）
  - RiskMonitor: ドローダウン／ポジション上限検出とリスクログ記録
  - KillSwitch: 条件に応じて data/kill.flag を書き込み、ExecutionEngine を安全停止
  - MonitoringEngine: 上記モニタを定期実行（ポーリング）
  - 監視ログ永続化: SQLite（monitoring.db）
- ポートフォリオ（Portfolio）
  - 候補選定、等金額・スコア加重配分
  - セクターキャップ適用、レジーム乗数計算
  - ポジションサイズ計算（リスクベース・等配分・スコア配分）
- 研究（Research）
  - Momentum / Volatility / Value 等ファクター計算（DuckDB の prices_daily / raw_financials）
  - 将来リターン計算、IC（情報係数）や統計サマリ
- AI（OpenAI）
  - news_nlp: ニュース記事を集約して LLM で銘柄別センチメントを算出 → ai_scores へ保存
  - regime_detector: ETF（1321）のMA乖離 + マクロニュースセンチメントで日次レジーム判定
  - API 呼び出しは堅牢化（リトライ・検証・フォールバック）済み
- ツール
  - config_setup: .env 作成ウィザード（対話式）
  - validate_config: 環境変数・config YAML の事前検証 CLI
  - paper_verification_report: ペーパートレード結果の集計レポート生成
- ユーティリティ
  - logging_setup: 統一的なログ設定（コンソール + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ

セットアップ手順
----------------
1. Python 環境の作成（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - （オプション）PyYAML を入れると validate_config が YAML の中身を検証可能:
     pip install pyyaml

   ※ requirements.txt は本リポジトリに含まれていないため、上記パッケージを目安にインストールしてください。

3. ディレクトリ（data, logs 等）の作成（通常は自動作成されますが権限を確認してください）
   - mkdir -p data logs

4. 環境変数の設定
   - 対話式ウィザードを推奨:
     python -m kabusys.config_setup
   - もしくは .env を手動作成（プロジェクトルート）:
     必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     推奨: KABUSYS_ENV（development | paper_trading | live）
     OpenAI を使う場合: OPENAI_API_KEY を設定

   自動ロード:
   - 起動時にプロジェクトルートの .env と .env.local が自動で読み込まれます（OS 環境変数を上書きしません）。
   - 自動ロードを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば修正して再度検証。--strict を付けると警告も失敗扱いになります。

使い方（起動例）
----------------
- ExecutionEngine を起動（通常実行）
  - python -m kabusys.run_execution

- ペーパートレードで起動（MockBroker を使用し paper DB を分離）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Monitoring を起動（ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60）
    例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- .env 作成ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを明示する場合: --db path/to/paper_trading.db
  - 環境変数: PAPER_TRADING_SQLITE_PATH でデフォルトを上書きできます

重要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- OPENAI_API_KEY: AI 機能用（任意。未設定なら AI 機能は使用不可）
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: 監視 DB デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB デフォルト data/paper_trading.db
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant|partial|never|reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）

データ・ログの既定パス
---------------------
- DuckDB: data/kabusys.duckdb
- Monitoring SQLite: data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db
- PID / Kill Flag: data/execution.pid, data/kill.flag
- ログディレクトリ: logs/（デフォルト、ログファイル名は <app_name>.log）

注意事項 / トラブルシューティング
---------------------------------
- ファイル/ディレクトリ書き込み権限を確認してください（logs/, data/）。
- OpenAI API を使う機能は OPENAI_API_KEY が必要です。未設定時は ValueError を返す箇所があります（AI 関連関数）。
- validate_config は PyYAML が無い場合 YAML の中身検証をスキップします（警告表示）。
- Monitoring は KABUSYS_ENV に依らず本番用 sqlite_path を使用します（監視ログは環境に依存しません）。
- ペーパートレードは本番 DB と分離して paper_sqlite_path に書き込みます（安全設計）。
- Kill Switch は条件が成立すると data/kill.flag を作成します。ExecutionEngine 起動時に clear 設定があると自動的に削除される場合があります（KILL_FLAG_CLEAR_ON_START）。

ディレクトリ構成（主なファイル）
-------------------------------
（プロジェクトルート）
- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数/設定のロードと Settings クラス
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py            — 共通ログ設定（コンソール+ファイルローテート）
    - process_priority.py         — プロセス優先度・CPU affinity 設定
  - execution/                     — 実行関連コンポーネント（BrokerClient 等）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - monitoring/
    - monitoring_db.py            — SQLite 永続層（テーブル定義・CRUD）
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
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                  — ニュースセンチメント（OpenAI利用）
    - regime_detector.py           — レジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py
  - data/                          — データ・DB ファイル（実行時に使用）
  - logs/                          — ログファイル（logs/<app_name>.log）

開発・拡張のヒント
------------------
- DuckDB に prices_daily / raw_financials / raw_news 等のテーブルを用意すると、research / ai 機能をローカルで試せます。
- AI 呼び出しはリトライ・検証を考慮した実装になっています。ユニットテスト時は _call_openai_api をモックしてください。
- Monitoring のテストは MonitoringEngine.run_once() を使うと簡単です（ポーリングループを回さず単発実行）。
- .env は決してリポジトリにコミットしないでください（config_setup でも注意書きをしています）。

ライセンス / 貢献
-----------------
本リポジトリのライセンス・貢献ポリシーはこの README に含まれていません。必要に応じて LICENSE を追加してください。

問い合わせ
---------
不具合報告や質問はリポジトリの Issue をご利用ください。