# CHANGELOG

すべての notable な変更は「Keep a Changelog」形式で記録しています。  
現在のリリース履歴は下記の通りです。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

Initial release — KabuSys の最初の公開版です。自動売買システムのコア起動スクリプト、設定管理、ポートフォリオ構築ユーティリティ、検証ツール群、ログ・プロセスユーティリティなどを含みます。

### Added
- 基本パッケージとバージョン
  - パッケージのバージョンを `__version__ = "0.1.0"` として追加。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御はプロジェクトの `data/stop_requested.flag` ファイルで行う。
    - 監視は KABUSYS_ENV にかかわらず本番用の `sqlite_path` を使用する設計。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を利用し、paper_trading 用 SQLite（デフォルト: `data/paper_trading.db`）を使用して本番 DB と分離。
    - エンジンはデーモン Thread で実行され、停止フラグ検知で安全に停止する。
    - PID ファイルの扱い（`data/execution.pid`）を行う。

- 設定管理・自動ロード
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルート（.git / pyproject.toml）探索に基づく）。
    - .env / .env.local の読み込み順序とオーバーライドのルールを実装（OS 環境変数は保護）。
    - `.env` 行パーサは `export KEY=val`、クォート文字列（バックスラッシュエスケープ対応）、コメント処理などに対応。
    - Settings クラスで主要な設定値をプロパティとして提供（J-Quants・kabu API、DB パス、paper_fill_mode の検証、監視しきい値、環境判定など）。
    - `settings` のシングルトンインスタンスを提供。

- 環境設定ウィザード・検証ツール
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を提供。
    - シークレット入力、既存 .env 読み込み、デフォルト提示、保存確認機能を搭載。
  - validate_config.py
    - 起動前の設定検証 CLI を提供（必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL 値検証、DB パスの親ディレクトリチェック、config/*.yaml の存在と（PyYAML 有りなら）パース検証、本番時ガード項目のチェック等を実施）。
    - `--strict` フラグで警告も失敗扱いにできる。

- ポートフォリオ構築ライブラリ
  - kabusys.portfolio
    - portfolio_builder.py
      - select_candidates: BUY シグナルのスコアソートと上位抽出。
      - calc_equal_weights, calc_score_weights: 等分配・スコア加重配分（全スコアが 0 の場合のフォールバックを含む）。
    - risk_adjustment.py
      - apply_sector_cap: セクター集中制限ロジック（既存保有を考慮したブロック）。
      - calc_regime_multiplier: マーケットレジームに応じた投下資金乗数（bull/neutral/bear）。
    - position_sizing.py
      - calc_position_sizes: リスクベース / equal / score ベースの発注株数計算。lot_size、max_position_pct、max_utilization、cost_buffer（手数料・スリッページ想定）などを考慮したスケーリング・丸めロジックを実装。

- 監視・ログ・プロセスユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（デフォルト daily, 30 保持）を設定。既存ハンドラのクリア処理を実装。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py
    - set_process_priority(level) を提供し、Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収してプロセス優先度を設定。
    - set_cpu_affinity(cpu_count) を提供（最初の N コアに固定）。
    - 権限不足や未対応環境では警告を出して安全にスキップ。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト: `data/paper_trading.db`）から統計を集計して人間向けレポートを出力する CLI を実装。
    - システム稼働率、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなどを算出し、閾値に基づく PASS/FAIL 判定を行う。
    - 日付フィルタ、DB パス指定オプションをサポート。

- 研究モジュール（初期実装）
  - research/factor_research.py
    - ファクター計算（モメンタム、MA200乖離、ATR、出来高等）のための設計と一部実装。DuckDB 接続を受け取って prices_daily / raw_financials テーブルを参照する方針。

### Changed
- N/A（初版のため変更履歴はありません）

### Fixed
- N/A（初版のため修正履歴はありません）

### Security
- 環境変数取り扱いに注意したデフォルト設定と `.env` の取扱いメッセージ（.env を絶対にコミットしない旨）をウィザードとドキュメントに明示。

### Notes / Design decisions
- 環境分離:
  - 監視（monitoring）は KABUSYS_ENV にかかわらず監視用の本番 sqlite path を参照する設計（監視データは一元管理）。
  - エンジン（execution）は paper_trading 時に paper 用 DB を使い、本番 DB と完全分離。
- .env 自動読み込みはデフォルトで有効だが、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると無効化できる（テスト用途想定）。
- ロギングは stdout を基準にしている（cron / scheduler のログリダイレクトを想定）。
- process_priority / CPU affinity の設定は失敗時に安全にスキップし、運用上の致命的な停止を避ける。

---

今後の予定（検討中）
- research/factor_research の完全実装（ファクター計算ロジックの完成）。
- ExecutionEngine / BrokerClient の詳細実装・テストカバレッジ拡充。
- config/*.yaml のテンプレート生成スクリプトの整備とドキュメント強化。
- 単体テスト・CI での自動検証パイプライン構築。