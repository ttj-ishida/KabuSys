CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
安定版のリリースポリシー: 破壊的変更がある場合は明示します。

Unreleased
----------

（現在なし）

0.1.0 - 2026-04-23
------------------

Added
- 基本機能としての初期リリース。
- 実行・監視ランナー
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全に分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - Engine は PID ファイル（data/execution.pid）を書き、停止フラグ（data/stop_requested.flag）で安全に停止可能。
  - run_monitoring.py
    - SystemMonitor を定期ポーリングする監視スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト: 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用の sqlite_path を使用して監視データを記録。
    - 停止フラグファイルを検出してループを終了する仕組みを実装。

- 設定管理
  - config.py
    - .env 自動読み込み実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - OS 環境変数優先、.env.local を .env の上書きとして読み込む挙動を採用。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
    - 環境変数パーサは export 付き行やクォート・エスケープ、インラインコメントの扱いを考慮。
    - 各種設定プロパティ（DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等）を提供。入力検証（有効値チェック）を行う。

- 設定ユーティリティ / CLI
  - config_setup.py
    - 対話式の .env 作成ウィザードを追加。よく使う環境変数を質問形式で設定可能。
    - 既存 .env を読み込んで Enter で既存値を再利用、入力中断時の安全な挙動を実装。
    - .env のテンプレート書き込み（秘密値はマスク表示）。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および（PyYAML があれば）パース検証を行う。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルの順位付け select_candidates。
    - 等配分 calc_equal_weights、スコア加重 calc_score_weights（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（当日売却予定銘柄の除外、unknown セクターの扱いなど）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知レジームは警告してフォールバック）。
  - portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に応じた株数計算。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap、コストバッファを考慮したスケーリング、端数配分ロジックを実装。
    - price 欠損時のスキップやログ出力の考慮。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギングセットアップを提供（StreamHandler -> stdout、TimedRotatingFileHandler -> 日次ローテート、30 日保持）。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - set_process_priority(level) により Windows / POSIX を吸収したプロセス優先度設定を提供。
    - set_cpu_affinity(cpu_count) により最初の N コアにプロセスをピン留めする機能を実装。
    - 権限不足や未対応 OS の場合は警告して安全にスキップ。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs を参照して稼働率（uptime）、注文成功率（fill rate）、送信率、レイテンシ（avg/max/P95）等を集計。
    - 閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義して PASS/FAIL 判定を出力。
    - --from/--to/--db オプションをサポート。DB 存在確認とエラーハンドリングを実装。

- データリサーチ
  - research/factor_research.py（部分実装）
    - DuckDB を使ったファクター計算の骨子（モメンタム、MA200、ATR、ボリューム系等）の設計と一部実装。關数は DuckDB 接続と target_date を受け取り、prices_daily / raw_financials を参照する方針。

- パッケージメタ
  - __init__.py にバージョン __version__ = "0.1.0" を設定。
  - kabusys.portfolio パッケージエクスポートを整理。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Security
- 機密情報の取り扱いに関する注意をドキュメント化（.env は絶対に Git にコミットしない旨を config_setup のヘッダに明記）。

Notes / 実装上の注意
- run_monitoring は監視データ記録に settings.sqlite_path（本番用）を常に使う設計。環境にかかわらず監視データを一元化したい用途を想定しているため意図的な動作。
- PAPER_FILL_MODE の値検証や KABUSYS_ENV / LOG_LEVEL の妥当性チェックを行い、不正値は早期に例外を出す（安全性向上）。
- 一部の関数（例: research/factor_research.calc_momentum）は実装途中（ファイル末尾で切れている）であり、今後のリリースで完成予定。
- ログディレクトリや SQLite/DuckDB の親ディレクトリが存在しない場合、警告を出して起動時に自動作成するやすい設計。起動時の OS 権限などにより作成できない場合はファイル出力のフォールバック挙動がある。

リリースノートは実装内容から推測して作成しています。実際のコミット履歴や issue と合わせて微調整してください。