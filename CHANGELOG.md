# Changelog

すべての注目すべき変更点を記録します。  
形式は「Keep a Changelog」に準拠しています。  

- リリースポリシー: 不変の初期リリースとして v0.1.0 を記載しています。  
- 日付はコード確認日（2026-04-18）を使用しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-18

### Added
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用して本番データと分離。
    - broker クライアントを BrokerClientFactory 経由で生成して依存コンポーネント（OrderRepository / OrderManager / RiskManager / Reconciler）を組み立て、ExecutionEngine を別スレッドで実行。
    - 停止制御は data/stop_requested.flag と data/execution.pid を使用（停止フラグの検知でエンジン停止）。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path（デフォルト: data/monitoring.db）を使用。
    - 停止は data/stop_requested.flag の存在で検知。
- 設定管理 / 初期化ツール
  - config.py
    - 環境変数ラッパー Settings を提供（各種既定値・検証ロジックを含む）。
    - .env 自動ロード機能（プロジェクトルートを .git / pyproject.toml で検出）を実装。優先順位: OS > .env.local > .env。自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - .env 行パーサーは export プレフィックス、クォート文字、エスケープ、行内コメント等に対応。
    - PAPER_TRADING 関連設定: PAPER_FILL_MODE（instant/partial/never/reject）と PAPER_TRADING_SQLITE_PATH をサポート。
    - 監視閾値や PID / kill flag のパス等の取得プロパティを提供。
  - config_setup.py
    - 対話式ウィザードで .env を生成/更新する CLI を追加（項目: KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LINE 通知設定 など）。
    - 秘匿項目はマスク表示、デフォルト値・選択肢対応、保存前の確認プロンプトを実装。
  - validate_config.py
    - 起動前に .env と config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在チェック、YAML パース検査（PyYAML がインストールされていない場合は警告）等を実装。
    - `--strict` オプションで警告も失敗扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 全アプリ共通のログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler, 30 日保持）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - ログレベルとログディレクトリは引数・環境変数で指定可能（優先順を明記）。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度を設定するユーティリティを追加。psutil を利用し、許可されない操作は警告でスキップ。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity 関数を提供。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - シグナル選定（スコア降順、タイブレークは signal_rank）関数 select_candidates、等金額配分 calc_equal_weights、スコア比率配分 calc_score_weights を実装。
    - スコア全体が 0 の場合は等金額にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有のセクター別エクスポージャーに応じて新規候補を除外）を実装。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear）を実装。未知レジームは 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - 発注株数決定ロジック calc_position_sizes を追加（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer（手数料・スリッページ見積）を考慮した安全な配分ロジックを実装。
- 研究 / 指標
  - research/factor_research.py（実装開始）
    - DuckDB を用いたファクター計算モジュールの骨子を追加（モメンタム / MA200 / ATR / 流動性等の算出を想定）。設計方針と定数を定義。
- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を集計し、閾値（稼働率 >=99%、成功率 >=90%、送信率 >=95%、P95 <=200ms）で PASS/FAIL 判定を出力。
    - 日付フィルタ（--from / --to）および DB パス指定（--db / 環境変数）をサポート。
- DB/分析基盤
  - DuckDB を分析用ストアとして導入（Settings.duckdb_path、各スクリプトで接続）。
  - 監視 / トレードログ用に SQLite を使用（Settings.sqlite_path / paper_sqlite_path）。

### Changed
- プロジェクト構成
  - パッケージ初期バージョンを 0.1.0 として公開（src/kabusys/__init__.py に __version__ を設定）。
- ログ出力の統一
  - 全起動スクリプトは setup_logging を呼び出してルートロガーを統一的に設定するように変更（Stream + File、stdout 使用）。

### Fixed
- 安全機能
  - run_execution と run_monitoring 共に data/stop_requested.flag の存在を監視し、フラグ検知で安全にシャットダウンする仕組みを実装して強制停止への対応を改善。
- .env パーサー
  - export プレフィックスやクォート内のバックスラッシュエスケープ、行内コメントの扱い等の解析ロジックを実装して .env 読み込みの堅牢性を向上。

### Documentation
- CLI ヘルプ / スクリプト内 docstring に利用方法・環境変数・既定値を明記。config_setup と validate_config の利用手順も案内。

### Security
- .env ファイルは生成時に Git へコミットしないよう警告を出力する（config_setup のヘッダコメント）。

### Notes / Implementation details
- 環境変数とファイルパスのデフォルト:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_DIR: logs/
- PAPER_FILL_MODE の有効値: "instant", "partial", "never", "reject"（不正値は例外）。
- process_priority は権限不足や未サポート OS の場合は警告を出して失敗を許容（動作継続）。
- ログファイルは日次ローテーションで 30 日分保持。ログディレクトリ作成に失敗した場合はファイルロギングを無効化して stdout のみで継続。
- validate_config は PyYAML が未インストールの場合に YAML 内容検査をスキップし警告を出す。

---

この CHANGELOG は、提供されたコードベースの実装・設計コメント・ドキュメント文字列から推測して作成しています。実際のリリースノート作成時はコミット履歴やリリース方針に基づき調整してください。