# KabuSys — 日本株自動売買システム（README）

このリポジトリは日本株向けの自動売買システム「KabuSys」のコア部品群です。  
監視（Monitoring）、実行（Execution）、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などのモジュールを含み、ローカル・ペーパートレード・本番の切替を意識した設計になっています。

## プロジェクト概要
- モジュール化された自動売買システムのコアライブラリ群（Python）。
- DuckDB を使った分析処理、SQLite を使った監視／取引ログ永続化。
- OpenAI（gpt-4o-mini など）を利用したニュースセンチメント評価・レジーム判定機能を備える（API キー必須）。
- 本番環境とペーパートレード環境は DB を分離しており、安全に検証が可能。
- 監視 → Kill Switch によるエンジン停止、アラート発行、稼働率・レイテンシ分析などの運用機能を提供。

## 主な機能一覧
- 環境設定ウィザード（.env の対話式生成）: kabusys.config_setup.run_wizard
- 設定検証 CLI（.env や config/*.yaml のチェック）: kabusys.validate_config
- 実行エンジン起動スクリプト: run_execution.py
  - KABUSYS_ENV による paper_trading / live 切替（paper_trading 時は MockBrokerClient を使用）
  - 発注管理、リスク制御、リコンサイル等の組立
- 監視ループ起動スクリプト: run_monitoring.py
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリング
  - MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）
- 監視データ永続化（SQLite）: kabusys.monitoring.monitoring_db
  - system_status / trade_logs / risk_logs / positions / dashboard 等のテーブル管理
- RiskMonitor / KillSwitch / MonitoringEngine による自動保護（ドローダウン・ポジション上限など）
- ポートフォリオ構築ロジック（候補選定・重み付け・ポジションサイズ計算）
  - kabusys.portfolio: select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- リサーチ用ファクター計算: kabusys.research (momentum / volatility / value 等)
- AI：ニュース NLP（ai.news_nlp.score_news）と市場レジーム判定（ai.regime_detector.score_regime）
  - OpenAI API（OPENAI_API_KEY）を利用（未設定時は例外）
  - API エラーに対するリトライやフォールバック実装あり
- ツール: Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

## 必要条件（推奨）
- Python 3.10+
- パッケージ（代表例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証に必要だが必須ではない）
- SQLite（標準ライブラリで利用）
- ネットワーク接続（OpenAI API を使う場合）

（requirements.txt はこのリポジトリに含まれていない想定のため、上記パッケージを pip でインストールしてください。）

例:
pip install duckdb psutil openai PyYAML

## セットアップ手順（ローカルでの素早い準備）
1. リポジトリをクローン:
   git clone <this-repo-url>
   cd <repo-root>

2. 仮想環境作成（任意）:
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール:
   pip install duckdb psutil openai PyYAML

4. 初期 .env を作成:
   - 対話式ウィザードを使う（推奨）:
     python -m kabusys.config_setup
   - もしくは .env を手動作成（例）:
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_kabu_password_here
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO

5. data / logs ディレクトリの作成（スクリプト実行時に自動作成される場合ありが、手動で作っておくと権限問題が出にくい）:
   mkdir -p data logs

6. 設定検証:
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いにできます。

## 使い方（主要な実行例）
- 実行エンジン（ExecutionEngine）を起動:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は paper_trading DB（data/paper_trading.db がデフォルト）に記録され、本番 DB と分離されます。
  - 実行中の PID は data/execution.pid に書き込まれます。停止には data/stop_requested.flag を作成するか Kill Switch による kill.flag を利用。

- 監視ループを起動:
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は本番 sqlite_path（Settings.sqlite_path）を使います（KABUSYS_ENV に依らず本番 DB に記録）。

- 設定ウィザード（.env 作成）:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別 DB を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可。

- AI モジュールの利用（プログラムから呼び出し）:
  from kabusys.ai import score_news
  # DuckDB 接続と対象日、API キーを渡して実行
  score_news(conn, date(2026,4,1), api_key="...")

  - OPENAI_API_KEY が環境変数にある場合は api_key を省略可能。

## 主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
- OPENAI_API_KEY（AI モジュールを使う場合必須）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔（秒）、デフォルト 60）

注意: .env を作成する際は .env を Git にコミットしないでください（config_setup.py のヘッダにも注記あり）。

## 運用・停止フラグ
- data/stop_requested.flag: run_execution / run_monitoring が監視している停止フラグ（存在するとループを終了）。
- data/kill.flag: KillSwitch が書き込む停止理由のフラグ（主に本番保護）。
- data/execution.pid: 実行エンジンの PID（run_execution が書き込む）。

## ログ設定
- ログは stdout とファイル（logs/<app_name>.log）に日次ローテーションで出力されます（kabusys.utils.logging_setup.setup_logging）。
- ログディレクトリは環境変数 LOG_DIR で上書き可能（デフォルト: logs/）。
- LOG_LEVEL 環境変数で出力レベルを指定できます。

## ディレクトリ構成（抜粋）
（src/kabusys 以下の主要ファイル／モジュールを示します）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック（Settings）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化（テーブル作成・CRUD）
    - monitoring_engine.py   — 各 Monitor を束ねる実行ループ
    - system_monitor.py      — システム状態 / データ鮮度チェック
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — Kill Switch ロジック（kill.flag 書き込み）
    - trade_monitor.py       — （取引監視ロジック；実装に依存）
    - alert_manager.py       — （通知管理；実装に依存）
  - execution/               — ExecutionEngine / OrderManager 等（起動ロジック）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/                    — スキーマ定義や pipeline（DuckDB 用）等（実装に依存）
  - utils/
    - logging_setup.py
    - process_priority.py

（上記は主要ファイルの一覧であり、実装の全ファイルはソースツリーを参照してください。）

## 開発・拡張のヒント
- 自動で .env をロードする仕組みがあり（config.py）、プロジェクトルートを基準に .env / .env.local を読み込みます。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを抑止できます。
- DuckDB を使った解析関数は副作用を持たない純関数設計を意識しています（テストが書きやすい）。
- AI 呼び出しはリトライやパース耐性を持たせており、部分失敗時に既存データを破壊しないよう書き込みロジックで配慮しています。
- 実稼働時は KABUSYS_ENV=live の設定と LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）の確認を忘れないでください。validate_config はその確認を支援します。

## ライセンス・貢献
- この README での説明はコードベースの理解を助けることが目的です。実際の運用・配布・ライセンスについてはリポジトリの LICENSE ファイルやプロジェクトポリシーに従ってください。
- バグ報告・機能提案は Issue を立ててください。Pull Request は歓迎します。

---

問題や不明点があれば、どの部分についてさらに詳しくドキュメント化すべきか教えてください。README の補足（例: 環境変数の完全リスト、実運用チェックリスト、Docker / systemd ユニット例など）も追加できます。