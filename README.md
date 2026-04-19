# KabuSys

日本株向けの自動売買システム用ライブラリ / 起動スクリプト群です。  
このリポジトリは取引ロジック（ポートフォリオ構築・ポジションサイズ決定）、リサーチ（ファクター算出・特徴量解析）、AI を使ったニュースセンチメント評価、監視＆キルスイッチ、そして実行エンジンの起動スクリプトなどを含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 必須環境変数 / 設定
- セットアップ手順
- 使い方
  - 環境設定ウィザード
  - 設定検証
  - ExecutionEngine の起動（本番 / ペーパー）
  - Monitoring の起動
  - Paper Trading 検証レポート
  - ライブラリ API の利用例（リサーチ / ポートフォリオ等）
- ファイル／ディレクトリ構成
- 運用・運用時の注意点

---

プロジェクト概要
- KabuSys は日本株自動売買に関連するモジュールセットです。
- データ集計・分析（DuckDB）、監視ログ（SQLite）、発注実行（kabuステーション API またはモック）、AI を使ったニュース分析（OpenAI）などを組み合わせる設計になっています。
- 実行用スクリプトはプロセス優先度設定・ログ周りの統一設定・PID/kill フラグ管理など運用に配慮した実装です。

主な機能
- 環境変数 / .env の自動読み込み（kabusys.config）
- .env の対話式ウィザード（kabusys.config_setup）
- 起動前設定の静的検証 CLI（kabusys.validate_config）
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い paper_trading.db に記録（本番 DB とは分離）
- 監視プロセス起動スクリプト（run_monitoring.py）
  - ポーリングループ、MONITOR_POLL_INTERVAL で間隔上書き可能（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path を参照（環境に依らず）
- 監視関連
  - MonitoringDB（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard を管理
  - SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine
  - kill.flag による ExecutionEngine 停止機能
- ポートフォリオ構築
  - 候補選定、重み計算（等分・スコア加重）
  - セクター制限、レジーム乗数
  - ポジションサイズ計算（リスクベース、単元株丸め、aggregate cap）
- リサーチ
  - ファクター算出（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
- AI 関連
  - ニュースを OpenAI に送りセンチメントを算出・ai_scores へ書込み（news_nlp）
  - マクロ + ETF ma200 を利用した市場レジーム判定（regime_detector）
- ユーティリティ
  - ロギング設定（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定

必須環境変数（代表）
- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- OPENAI_API_KEY （AI 機能を使用する場合）
- KABUSYS_ENV: development | paper_trading | live（省略時は development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）

（.env.example を参考に .env を作成してください。kabusys.config_setup による対話作成を推奨します。）

---

セットアップ手順（開発環境想定）
1. Python を用意（推奨: 3.10+）
2. 仮想環境を作る
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - 代表的な依存:
     - duckdb
     - psutil
     - openai
     - PyYAML (設定検証でオプション)
   例:
     pip install duckdb psutil openai PyYAML
   （プロジェクトに requirements.txt がある場合はそれを使用してください）
4. .env を作成
   - 対話式:
     python -m kabusys.config_setup
   - もしくは手動で .env をルートに置く（.env.example を参考）
5. 設定を検証（任意）
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）
6. データディレクトリ（data）、ログディレクトリ（logs）は自動作成されますが、権限に注意してください。

---

使い方（主要コマンド例）

1) 環境設定ウィザード（.env 作成）
   python -m kabusys.config_setup

2) 設定検証
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict

3) ExecutionEngine を起動
   - 本番/開発/ペーパーは KABUSYS_ENV の値で切替
   - ペーパートレード時は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
   起動:
     python -m kabusys.run_execution
   停止:
     - data/stop_requested.flag を作成すると優雅に停止（run_execution が参照）
     - または監視側の KillSwitch が data/kill.flag を書き込むことで停止トリガーを送る

4) Monitoring を起動
   - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）
   起動:
     python -m kabusys.run_monitoring

5) Paper Trading 検証レポートの生成
   - デフォルト DB: data/paper_trading.db または環境変数 PAPER_TRADING_SQLITE_PATH
   例:
     python -m kabusys.tools.paper_verification_report
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

6) ライブラリ的に利用する（サンプル）
   - リサーチ: calc_momentum / calc_volatility / calc_value
     from kabusys.research import calc_momentum
     # DuckDB 接続を渡して使用
   - ポートフォリオ:
     from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes

ログ
- デフォルトは logs/<app_name>.log（app_name は起動時に指定、例: execution, monitoring）
- コンソールは stdout に出力されます（stderr ではない点に注意）
- 日次ローテート、過去 30 日分保持

停止フラグ / PID
- 実行/監視の停止や制御に次のファイルを使用します（デフォルトパスは Settings で変更可）
  - data/kill.flag : KillSwitch が書き込む本番停止フラグ（ExecutionEngine 停止トリガ）
  - data/stop_requested.flag : run_monitoring / run_execution が参照する汎用停止フラグ
  - data/execution.pid : ExecutionEngine が PID を書き込むファイル
- KillSwitch は条件（ドローダウン超過、ポジション上限超過など）を満たすと flag を書き込みます（冪等）

OpenAI（AI 機能）について
- OPENAI_API_KEY を環境変数に設定するか、関数呼び出しでキーを渡してください。
- API 呼び出しは冪等性・失敗フォールバック（失敗時はスコア 0.0 等）に配慮して実装されています。
- モデルは現状 gpt-4o-mini 想定（設定はモジュール内定数で管理）

ディレクトリ構成（主要部分）
- src/kabusys/
  - __init__.py
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング実行スクリプト
  - config.py                      — Settings / .env 自動読み込みロジック
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - utils/
    - logging_setup.py             — 共通ログ設定ユーティリティ
    - process_priority.py          — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py             — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py (存在)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (存在)
  - execution/                      — 発注・注文管理関連（broker_factory 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

（※ 上記は主要ファイルの抜粋です。詳細は src/kabusys 以下を参照してください）

運用上の注意
- KABUSYS_ENV=live の場合は設定に十分注意してください（validate_config は live の警告も出します）。
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- OpenAI キーや取引 API の資格情報は安全に管理してください。
- データベースのバックアップ、ログの監視、ディスク容量監視は必須です（monitoring モジュールは一部をカバーしますが、環境運用に合わせた補完が必要です）。
- run_monitoring は常に Settings.sqlite_path（本番用）を参照します。テスト目的で monitoring を実行する際は適切にパスを変更してください（環境変数または Settings を調整）。

---

追加情報 / 開発者向け
- コードはユニットテストの想定を取り入れた設計（外部 API 呼び出しを差し替えやすい構造）になっています。例えば news_nlp._call_openai_api や regime_detector の API 呼び出しをモックしてテスト可能です。
- DuckDB を用いた分析クエリは SQL + Python の組合せで実装されており、大量データの集計に適しています。
- ログディレクトリの作成に失敗した場合はコンソール出力のみで継続するフォールバック実装です。

---

問題・改善提案・コントリビュート
- バグ報告や改善提案は Issue を作成してください。プルリク歓迎です。
- セキュリティ関連の公開可能な問題は Issue ではなくプライベートにお知らせください。

---

README はここまでです。必要なら以下を追加できます:
- 具体的な requirements.txt（バージョン指定）
- docker-compose などコンテナ化手順
- より詳しい運用手順（systemd ユニット、ログローテーション設定例）