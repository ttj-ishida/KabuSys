# KabuSys

日本株自動売買システムの一部コンポーネント群（設定管理、監視、実行エンジン起動スクリプト、ポートフォリオ構築、リサーチ、AI ユーティリティ等）。

注意: この README は src/kabusys 配下のコードベースをもとに作成しています。実行前に .env を作成し、必要な環境変数を設定してください。

## プロジェクト概要
- 自動売買の実行エンジン（ExecutionEngine）と監視（Monitoring）コンポーネントを含む。
- Paper Trading モード（KABUSYS_ENV=paper_trading）を持ち、本番 DB と分離された専用 SQLite を利用可能。
- DuckDB を分析・リサーチ用に使用し、prices_daily / raw_financials 等を参照してファクター計算や特徴量探索を行う。
- OpenAI を用いたニュース NLP（センチメント集約）や市場レジーム判定のユーティリティを備える。
- 監視データやログは SQLite（monitoring.db）へ永続化され、監視エンジンは kill.flag を使って ExecutionEngine の強制停止を行える。

## 主な機能一覧
- 設定管理
  - .env 自動読み込み（プロジェクトルートから .env / .env.local）
  - 対話式設定ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 実行 / 監視
  - run_execution: ExecutionEngine 起動、paper_trading モードで MockBroker を使用
  - run_monitoring: SystemMonitor をポーリングして監視データを記録
  - MonitoringEngine: System / Trade / Risk 各 Monitor の統合ポーリングとアラート判定
  - KillSwitch: ドローダウン等の重大アラートで kill.flag を書き込み ExecutionEngine を停止
- データベース永続化（SQLite）
  - monitoring_db: system_status / trade_logs / positions / risk_logs / dashboard の作成・操作
- ポートフォリオ構築
  - 候補選定、等重・スコア加重の重み計算、ポジションサイズ計算、セクターキャップ、レジーム乗数などの純粋関数群
- リサーチ
  - Momentum / Volatility / Value 等ファクター計算（DuckDB 接続を受け取る）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI
  - news_nlp: ニュース記事を OpenAI に送り銘柄ごとのセンチメントを ai_scores テーブルへ書込む
  - regime_detector: ETF を基に MA 乖離 + マクロセンチメントで日次レジーム判定
- ツール
  - paper_verification_report: ペーパートレード DB を集計して PASS/FAIL 判定のレポートを出力

## 必要要件（依存）
- Python 3.9 以上を想定（型アノテーションや一部 API を考慮）
- パッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config/*.yaml の検証時に使用）
- SQLite は Python 標準ライブラリの sqlite3 を使用
- ネットワーク接続（OpenAI API を使う場合）

requirements.txt がない場合は手動でインストールしてください:
```
pip install duckdb psutil openai PyYAML
```

## セットアップ手順
1. リポジトリをクローン / 配布ファイルを展開する
2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install duckdb psutil openai PyYAML
   ```
4. 対話式ウィザードで .env を作成（推奨）
   ```
   python -m kabusys.config_setup
   ```
   - 対話で J-Quants トークンや kabuステーション API パスワード、KABUSYS_ENV などを設定します。
5. 設定検証を実行
   ```
   python -m kabusys.validate_config
   ```
   - --strict を付けると警告も失敗扱いになります。
6. 必要ディレクトリを作成（通常は logging/migration が自動で作られますが手動で準備する場合）
   - data/ （SQLite DB、pid/flag を配置）
   - logs/ （ログ出力先）
   ```
   mkdir -p data logs
   ```

## 環境変数（主要）
- 必須（validate_config 参照）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用系:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
- DB パス:
  - DUCKDB_PATH（例: data/kabusys.duckdb）
  - SQLITE_PATH（監視用、例: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、例: data/paper_trading.db）
- Paper Trading:
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- OpenAI:
  - OPENAI_API_KEY（news_nlp / regime_detector で使用）
- 監視制御:
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする場合は "1"（本番では推奨しない）
- その他:
  - PID_FILE_PATH: ExecutionEngine の pid ファイルパス（デフォルト: data/execution.pid）
  - LOG_DIR: ログディレクトリ（デフォルト: logs/）

（詳しい項目やデフォルト値は kabusys.config.Settings を参照してください）

## 使い方（起動とツール）
- 実行エンジン起動（ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用して PAPER_TRADING_SQLITE_PATH に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動を行わず終了します。
  - プロセス優先度は実行時に "high" に設定されます（可能な範囲で）。

- 監視ポーリング起動（SystemMonitor）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は常に settings.sqlite_path（監視 DB）を使用します（環境に依存せず本番 DB を利用）。

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート（DB 集計）
  ```
  python -m kabusys.tools.paper_verification_report
  # 期間指定 (例)
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 関連（プログラムから呼び出し）
  - ニュースセンチメント集約:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="...")  # conn は DuckDB 接続
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="...")

  OpenAI API を使う場合は OPENAI_API_KEY を設定してください（または関数引数で渡す）。

## ログ / データ
- ログ:
  - デフォルトは logs/<app_name>.log（日次ローテーション、30日保持）
  - console は stdout（root ロガーに StreamHandler を設定）
  - ログレベルは LOG_LEVEL または setup_logging() の引数で制御
- データ:
  - SQLite 監視 DB: data/monitoring.db（デフォルト）
  - Paper Trading DB: data/paper_trading.db（paper_trading 時）
  - DuckDB: data/kabusys.duckdb（分析用）
- フラグ / PID:
  - data/kill.flag: ExecutionEngine 停止用 kill flag（KillSwitch により書込）
  - data/stop_requested.flag: 起動スクリプトがループを終了するためのローカル停止フラグ（run_monitoring/run_execution で使用）
  - data/execution.pid: 実行エンジンの PID ファイル（ExecutionEngine 起動時に使用）

## ディレクトリ構成
（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                   -- 環境変数 / Settings
    - config_setup.py             -- .env 対話式ウィザード
    - validate_config.py          -- 設定検証 CLI
    - run_execution.py            -- ExecutionEngine 起動スクリプト
    - run_monitoring.py           -- SystemMonitor ポーリング起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py           -- （実装あり）
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py           -- （実装あり）
    - execution/
      - execution_engine.py       -- （実装あり）
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py
    - data/                        -- 実行時に使用する data/ 以下のファイル（DB・flag・pid 等）

（実際のリポジトリ構成はプロジェクトルートの pyproject.toml / setup.py 等も参照してください）

## 運用上の注意 / ヒント
- 本番（KABUSYS_ENV=live）では kill.flag や KILL_FLAG_CLEAR_ON_START の設定に注意してください。validate_config は live 時に注意喚起を出します。
- Paper Trading モードは本番 DB と分離されますが、設定ミスによりパスが競合しないよう .env を確認してください。
- OpenAI を利用する機能は API 利用料が発生します。rate limit やエラー時のリトライロジックは組み込まれていますが、キーの管理には注意してください。
- ロギング設定は kabusys.utils.logging_setup.setup_logging を各起動スクリプトで呼んで統一しています。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。

## トラブルシューティング
- .env 自動読み込みが不要・妨げになる場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- PyYAML 未インストール時、validate_config は YAML 内容検証をスキップします（警告が出ます）。
- DuckDB / SQLite の操作で "executemany に空リスト不可" の制約回避がコード内に実装されています。DB マイグレーションは init_monitoring_db() で冪等的に行われます。

---

その他、各モジュールの実装や追加の運用手順についてはソース内の docstring（コメント）を参照してください。必要であれば README の拡張（デプロイ手順、systemd / supervisor 用ユニット例、CI / テスト手順など）も作成します。どの情報を追加したいか教えてください。