CHANGELOG
=========

すべての注目すべき変更点を記録します。このプロジェクトは Keep a Changelog の形式に準拠しています。

フォーマット:
  - 変更はカテゴリ別（Added, Changed, Fixed, Removed, Security）に記載
  - 日付はリリース日を示します

[Unreleased]
-------------

（現時点では未リリースの差分はありません）

[0.1.0] - 2026-04-19
-------------------

Added
- 基本実行スクリプトを追加
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。KABUSYS_ENV=paper_trading 時は専用のペーパートレード用 SQLite（data/paper_trading.db、環境変数で上書き可）を使用する。起動時にプロセス優先度を「high」に設定し、停止フラグ（data/stop_requested.flag）および PID ファイル管理を行う。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関係なく本番用 sqlite_path を使用する設計。

- 環境設定・検証用ユーティリティを追加
  - config_setup.py: .env の対話式ウィザード。既存 .env 読み込み、秘密値マスク表示、ファイル書き込みテンプレート生成を行う。
  - validate_config.py: 起動前チェック CLI。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在・パース（PyYAML がある場合）などを検証。--strict オプションで警告を FAIL 扱いにできる。

- 設定管理コンポーネントを追加
  - config.py: .env 自動ロード（.env → .env.local、OS 環境変数保護）、高度な .env 行パーサ、Settings クラスを実装。各種環境変数（J-Quants、kabuAPI、DB パス、paper_trading 設定、監視閾値など）取得 API を提供。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

- ロギング・プロセス管理ユーティリティを追加
  - utils/logging_setup.py: stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler をルートロガーに設定。ログディレクトリ作成失敗時はファイルハンドラをスキップして継続するフェイルセーフを備える。LOG_LEVEL / LOG_DIR の解決順を実装。
  - utils/process_priority.py: Windows / POSIX を吸収したプロセス優先度設定（high/normal/low）と CPU affinity 設定を提供。psutil のアクセス権限不足・未対応プラットフォームを考慮して安全にフォールバックする。

- ポートフォリオ構築関連の純粋関数群を追加（DB 参照なし）
  - portfolio/portfolio_builder.py: BUY シグナル選別 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア合計が 0 の場合は等配分にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中上限適用 (apply_sector_cap)、市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装。レジームに対するデフォルトマッピング（bull=1.0, neutral=0.7, bear=0.3）を提供。
  - portfolio/position_sizing.py: 各銘柄の発注株数決定ロジックを実装（allocation_method: risk_based / equal / score）。単元株（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer による保守的見積りなどをサポート。価格欠損時はログを出してスキップ。

- Paper Trading 検証レポートツールを追加
  - tools/paper_verification_report.py: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から集計して検証レポートを生成する CLI。稼働率、注文成功率、送信率、P95 レイテンシ等を算出し、閾値に基づき PASS/FAIL を判定。期間指定 (--from / --to) と DB パス指定 (--db) をサポート。デフォルト閾値をスクリプト内に定義（例: uptime >= 99%、fill_rate >= 90%、P95 <= 200ms）。

- research/factor_research.py（骨子）を追加
  - DuckDB を用いたファクター計算モジュールの骨子を実装（モメンタム、MA200乖離、ATR、流動性指標等を想定）。prices_daily / raw_financials テーブルのみ参照する設計。注: ファイル末尾で実装途中（切れている箇所あり）。

Changed
- データベース接続と分離
  - run_monitoring は監視用途の DB 接続に settings.sqlite_path（本番用の sqlite_path）を常に使用する設計を明記。run_execution は paper_trading 環境時に settings.paper_sqlite_path を使い本番 DB と明確に分離する。
- .env ロード挙動
  - プロジェクトルート検出ロジックを導入（.git または pyproject.toml を探索）、プロジェクト外でのパッケージ配布後も動作するように安定化。OS 環境変数は保護され、.env.local による上書きを許可。export KEY= 形式やクォート内のエスケープに対応する行パーサを導入。
- ロギング設定
  - 既存ハンドラを一旦 flush/close してから削除・再設定することで二重出力を防止。StreamHandler は stdout に出力する方針（cron 等でのリダイレクトを考慮）。
- プロセス優先度
  - 各起動スクリプトで最初に set_process_priority("high") を呼ぶように統一。アクセス拒否や未対応 OS の場合は警告ログを出してスキップする堅牢化。

Fixed
- .env パーサの堅牢化
  - コメント処理、クォート内のバックスラッシュエスケープ対応、不正行のスキップ等を実装し、.env の解釈ミスによる誤設定を防止。
- init_monitoring_db の起動時呼び出しを明示
  - run_execution / run_monitoring の起動時に init_monitoring_db(sqlite_conn) を呼び、監視用テーブルが存在することを冪等に保証する（存在しない場合の初期化）。
- run_execution の停止制御
  - 起動前に停止フラグが既に立っている場合はエンジンを起動せず帰るようにして誤起動を防止。スレッド監視ループ中に停止フラグを検知したら engine.stop() を呼ぶようにした。

Notes
- research/factor_research.py の calc_momentum 関数実装はファイル末尾で途中（start_da... の切れ）になっているため、完全実装は今後の作業となります。
- 一部の TODO コメント（例: price フォールバック、銘柄別 lot_size のサポート）が残っており将来的な改善候補です。
- デフォルト値や閾値（risk, max_position_pct, log ローテート日数 30 など）はソース内にハードコードされています。運用環境に合わせて環境変数化や config ファイル化を検討してください。

署名
----
KabuSys チーム

(注: 本 CHANGELOG は提供されたコード内容から推測して作成しています。運用上の正確な変更履歴が必要な場合はコミット履歴やリリースノートを参照してください。)