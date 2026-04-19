CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]: https://example.com/compare/v0.1.0...HEAD
[0.1.0]: https://example.com/releases/tag/v0.1.0

0.1.0 - 2026-04-19
------------------

Added
- 基本機能の初期実装を追加（初回リリース相当）。
  - 実行系 / 監視系エントリポイント
    - run_execution.py
      - ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は Paper Trading 用の専用 SQLite（data/paper_trading.db または 環境変数 PAPER_TRADING_SQLITE_PATH）を使用する分離設計。
      - エンジンは別スレッドで起動し、data/stop_requested.flag による安全停止処理、実行中 PID ファイル（data/execution.pid）管理をサポート。
      - 起動時にプロセス優先度を "high" に設定。
    - run_monitoring.py
      - SystemMonitor 用のポーリングループを提供する起動スクリプトを追加。
      - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL でオーバーライド可能（デフォルト: 60秒）。不正値は警告してデフォルトにフォールバック。
      - 監視 DB は環境にかかわらず本番 sqlite_path を使用する（監視データは常に本番 DB に記録される想定）。
      - 停止フラグ（data/stop_requested.flag）検知でループを終了し、安全に DB 接続をクローズ。

  - 設定管理・CLI
    - config.py
      - 環境変数 / .env 読み込みロジックを実装（プロジェクトルートを .git または pyproject.toml から探索）。
      - .env 自動読み込みを行うが、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - 複雑な .env パース（export 対応、クォート内エスケープ処理、インラインコメントの扱い等）を実装。
      - Settings クラスで各種設定プロパティを提供（DB パス、PID/kill flag パス、しきい値、環境判定、PAPER_FILL_MODE のバリデーション等）。
    - config_setup.py
      - 対話式 .env 生成ウィザードを提供。既存 .env を読み込んで編集可能。生成時の注意事項（.env をコミットしない等）を出力。
    - validate_config.py
      - 起動前検証 CLI を追加。必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在および YAML パース（PyYAML がない場合は検証をスキップして警告）等を実施。
      - --strict オプションで警告を FAIL 扱い（exit(1)）にできる。

  - ロギング・プロセス管理ユーティリティ
    - utils/logging_setup.py
      - 統一的なログ設定ユーティリティを追加。
      - stdout への StreamHandler と 日次ローテーション（TimedRotatingFileHandler）を組み合わせて設定。デフォルトログディレクトリは logs/、30日間保持。
      - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで動作。
      - LOG_LEVEL / LOG_DIR / 引数での上書きをサポート。
    - utils/process_priority.py
      - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定を追加（psutil を利用）。
      - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足や非対応環境では安全にスキップして警告を出力。

  - Portfolio 関連（純粋関数群）
    - portfolio/portfolio_builder.py
      - 候補選定 select_candidates、等分配 calc_equal_weights、スコア加重 calc_score_weights を追加。
    - portfolio/risk_adjustment.py
      - セクター集中制限 apply_sector_cap、マーケットレジームに応じた乗数 calc_regime_multiplier を追加。
      - 未知のレジーム時は 1.0 でフォールバックし警告を出力。
    - portfolio/position_sizing.py
      - position sizing のロジックを実装。allocation_method に応じて "risk_based", "equal", "score" をサポート。
      - lot_size（単元株）で丸め、max_position_pct / max_utilization / cost_buffer による上限・スケールダウン処理を実装。
      - aggregate cap 超過時はスケールして端数を lot 単位で再配分するアルゴリズムを実装。
      - price 欠損時のスキップ、ログ出力など堅牢化を考慮。将来的な拡張 TODO（銘柄別 lot_size など）あり。
    - portfolio/__init__.py で主要 API をエクスポート。

  - Paper Trading 検証ツール
    - tools/paper_verification_report.py
      - Paper Trading 用の検証レポート生成スクリプトを追加。
      - デフォルト DB は data/paper_trading.db。--db で上書き可能。
      - システム稼働率、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を集計して PASS/FAIL 判定を出力（デフォルト基準値をコード内に定義）。
      - 欠損テーブルやデータ不足に対して堅牢に動作するよう各クエリで OperationalError をキャッチしてフォールバック。

  - Research（ファクター計算）基盤
    - research/factor_research.py
      - Momentum, Value, Volatility, Liquidity の計算方針・定数を定義し、DuckDB 接続を受ける方式で設計。
      - 実装はモジュール構成およびインターフェースを確立（実装の一部は継続実装の必要あり）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （該当なし）

Notes / 補足
- .env 自動読み込み
  - デフォルトではプロジェクトルートの .env と .env.local をロードする。OS 環境変数は保護され .env.local の override でも上書きされない。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- PAPER_FILL_MODE
  - Paper Trading の MockBroker 動作モードを環境変数 PAPER_FILL_MODE で指定可能（instant | partial | never | reject）。無効値は ValueError を投げます。
- 監視 DB の扱い
  - run_monitoring は環境に関わらず設定された sqlite_path（デフォルト data/monitoring.db）を使用します。監視データを開発用 DB と混同しないよう注意してください。
- ログ出力
  - ディレクトリ作成・ファイル出力に失敗した場合でもコンソール出力は継続します（失敗しても起動が止まらない設計）。
- 既知の制約・TODO
  - portfolio.position_sizing: 銘柄別の lot_size をサポートする拡張が将来の課題として残っています。
  - risk_adjustment.apply_sector_cap: price_map に 0.0 が入っているとエクスポージャーが過少見積りされる可能性があるため、価格フォールバックロジックの追加を検討中。
  - research/factor_research.py は設計済みだが実装が途中（ファイル終端付近で未完）であるため、完全なファクター計算を行うには追加実装が必要。
  - process_priority の設定は権限や OS に依存するため、失敗時は警告が出て処理を継続します。

Migration / Upgrade notes
- 既存の .env をプロジェクトルートに置くと自動で読み込まれます。OS 環境変数が優先される点に注意してください。
- Paper Trading 用 DB は production DB と明確に分離されています。paper_trading 環境で実行する場合は PAPER_TRADING_SQLITE_PATH を設定してください。

Contributors
- コードベースの内容から自動生成しています（実際の貢献者名は含まれていません）。

[Unreleased]: https://example.com/compare/v0.1.0...HEAD
[0.1.0]: https://example.com/releases/tag/v0.1.0