# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはプロジェクトのソースコードから推測して作成しています。

## [Unreleased]
- 文書化・実装途中の項目やマイナー調整
  - research/factor_research.py の calc_momentum 実装がソース内で途中（切り出し）になっており、引き続き実装・テストが必要。

## [0.1.0] - 2026-04-23

### Added
- 実行/監視用スクリプトを追加
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプト。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を使用）。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。BrokerClientFactory によりブローカークライアントを生成（Mock を使う想定）。
    - execution.pid の PID ファイル管理と data/stop_requested.flag による停止フラグ検出に対応。
    - SQLite（monitoring DB）と DuckDB に接続し、監視テーブルの初期化（init_monitoring_db）を行う。
    - ExecutionEngine を別スレッドで実行し、停止フラグ検知時に安全に停止。

  - src/kabusys/run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下や不正な値はデフォルトにフォールバックして警告ログを出力。
    - 監視は KABUSYS_ENV にかかわらず production 用 sqlite_path（Settings.sqlite_path）を使用する設計。
    - stop flag（data/stop_requested.flag）を検知してループ終了。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理・検証・ウィザード
  - src/kabusys/config.py
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。.env と .env.local の読み込み順を実装（OS 環境変数は保護）。
    - export KEY=val 形式や引用符付き値（バックスラッシュエスケープ対応）、コメント処理を含む堅牢な .env 行パーサを実装。
    - Settings クラスで各種設定をプロパティとして提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE 等）。PAPER_FILL_MODE の値検証を追加（instant/partial/never/reject）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。

  - src/kabusys/validate_config.py
    - 起動前の設定検証 CLI。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パス親ディレクトリ存在チェック、config/*.yaml の存在および（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードを実装。
    - --strict オプションで警告を失敗扱いにできる。

  - src/kabusys/config_setup.py
    - 対話式 .env 作成/更新ウィザード CLI。
    - 各設定項目のプロンプト、既存 .env の読み込み、値の確認、.env ファイル書き出し（テンプレート）を実装。
    - .env を絶対に Git にコミットしない旨の注意を出力。

- ポートフォリオ構築・位置決めロジック（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順、タイブレークで signal_rank）を実装。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコアが 0 の場合は等金額にフォールバック）を実装。

  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有のセクター比率が閾値を超える場合に新規候補を除外）を実装。unknown セクターは制限対象外としている点を明記。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear マッピング）を追加（未知レジームは警告ログを出して 1.0 にフォールバック）。

  - src/kabusys/portfolio/position_sizing.py
    - 株数決定ロジック calc_position_sizes を実装。
    - allocation_method として "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）で丸め、per-position と aggregate のキャップ、コストバッファを考慮したスケーリングと残差処理（fractional remainder に基づく追加配分）を実装。
    - price 欠損時のスキップやログ出力あり。

  - src/kabusys/portfolio/__init__.py による公開 API 統合。

- ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 統一的なロギング設定ユーティリティを実装。
    - StreamHandler を stdout に設定（cron 等での取り扱い配慮）、TimedRotatingFileHandler による日次ローテーション（30 日分保持）をサポート。
    - 既存ハンドラをクリアして重複を防止、ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。

  - src/kabusys/utils/process_priority.py
    - psutil を使ったプラットフォーム非依存のプロセス優先度設定（Windows / POSIX の抽象化）および CPU affinity 固定機能を提供。
    - アクセス権限不足や未対応 OS の場合は警告ログでスキップ。

- ペーパートレード検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から指標を集計してレポートを出力する CLI。
    - システム稼働率、注文成功率（Filled / Created）、送信率（Sent / Created）、リスク却下数、レイテンシ（avg/max/P95）を計算し、閾値に基づいて PASS/FAIL を判定。
    - P95 値計算、日付フィルタ、DB 存在チェックを実装。

- その他
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を追加。

### Changed
- .env 読み込みロジックの改善（既存の OS 環境変数を保護しつつ .env.local を上書き可能にする挙動などを明確化）。
- logging_setup: 既存ハンドラを flush/close してから削除することで多重出力の問題を防止。

### Fixed
- .env パーサで以下をサポートして堅牢性を向上:
  - export プレフィックス対応
  - シングル/ダブルクォート内のバックスラッシュエスケープ処理
  - クォートなし値におけるインラインコメント認識（'#' の前が空白ならコメント扱い）
- process_priority / logging_setup 等で発生しうる例外（アクセス拒否、作成失敗等）を捕捉してフォールバックするように改善。

### Notes
- 監視 (run_monitoring.py) は KABUSYS_ENV にかかわらず Settings.sqlite_path（デフォルト: data/monitoring.db）を使用します。本番・検証環境での挙動に注意してください。
- 実行 (run_execution.py) は paper_trading モード時に paper_sqlite_path（デフォルト: data/paper_trading.db）を用いて発注履歴等を本番 DB と分離します。
- PAPER_FILL_MODE の有効値は instant / partial / never / reject の 4 種。環境変数で設定可能で、無効値は例外を送出します。
- .env の自動ロードはデフォルトで有効。自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- research/factor_research.py はファクター計算機能の骨格（定数・関数インターフェース）が存在しますが、一部実装が途中のため本格運用前に完成・テストが必要です。

--- 

（この CHANGELOG はソースコードから推測して作成しています。実際のリリース履歴と差異がある場合は適宜修正してください。）