Keep a Changelog
=================

すべての注目すべき変更をバージョンごとに記録します。
このファイルは "Keep a Changelog" の慣習に準拠しています。

フォーマット:
- 変更はカテゴリ（Added, Changed, Fixed, ...）ごとに分類しています。
- 日付はリリース日を表します。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-19
-------------------

Added
- 初期リリース: KabuSys 日本株自動売買システムの基盤モジュールを追加。
- 起動スクリプト:
  - run_execution.py — ExecutionEngine の起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用の SQLite（デフォルト: data/paper_trading.db）に分離して記録する。
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。監視は環境にかかわらず本番 sqlite_path を使用する実装。
- 設定・環境変数管理:
  - config.py: .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）、環境変数の堅牢なパース機能（クォート・エスケープ・インラインコメント対応）、Settings クラス（各種環境設定をプロパティとして提供）を追加。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加（秘密値マスク、選択肢、デフォルト値、.env 出力フォーマット）。
  - validate_config.py: 設定検証 CLI を追加（必須環境変数、KABUSYS_ENV 値、LOG_LEVEL、DB パス、config/*.yaml の存在とパースなどを検査。--strict オプションで警告も失敗扱い）。
- ロギング・ユーティリティ:
  - utils/logging_setup.py: 統一ロギングセットアップを追加。StreamHandler を stdout に出力、TimedRotatingFileHandler による日次ローテーション（30日保持）、環境変数や引数による log_dir/log_level 解決、既存ハンドラのクリア処理。
- プロセス優先度・CPU設定:
  - utils/process_priority.py: Windows/Linux（POSIX）差分を吸収するプロセス優先度設定（high/normal/low）と CPU affinity 設定ユーティリティを追加。権限不足や未対応環境では安全にフォールバック。
- ポートフォリオ構築ライブラリ:
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア全0 の場合のフォールバック警告あり。
  - portfolio/risk_adjustment.py: セクター集中制限適用 (apply_sector_cap)、市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装。未知レジーム時のフォールバックやログ出力あり。
  - portfolio/position_sizing.py: 発注株数計算 (calc_position_sizes) を実装。allocation_method (risk_based/equal/score)、lot_size（単元株丸め）、cost_buffer を考慮した aggregate cap スケーリング、スケールダウン時の端数配分ロジックなどを含む。
  - portfolio/__init__.py: 上記関数群をエクスポート。
- Paper Trading 検証ツール:
  - tools/paper_verification_report.py: paper_trading SQLite を参照して稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数等を集計し、PASS/FAIL 判定付きレポートを標準出力に出力。期間フィルタ（--from / --to）、DB パス指定（--db / 環境変数）対応。デフォルトの合格基準（稼働率99% 等）を定義。
- 監視 DB 初期化ヘルパ:
  - monitoring/monitoring_db.py（参照されているが詳細はコード内で利用）を利用して起動時に監視テーブルの存在を保証（冪等）。
- research モジュール（ファクター計算）:
  - research/factor_research.py にモメンタム等のファクター計算関数の雛形（calc_momentum 等）を追加（DuckDB を用いる設計、prices_daily/raw_financials を参照）。

Changed
- （初期リリースのため該当なし）

Fixed
- .env パーサーは export プレフィックス、引用符付き文字列のバックスラッシュエスケープ、インラインコメントの扱い等に対応し、一般的な .env 形式の取り扱いを強化。
- logging_setup: ログディレクトリ作成失敗時はファイル出力をスキップし、stderr に警告を出して StreamHandler（stdout）のみで継続するよう安全化。
- process_priority: 未対応 OS や権限不足時の例外をキャッチして警告ログを出すことで起動失敗を防止。

Deprecated
- （なし）

Removed
- （なし）

Security
- （なし）

Notes / 備考
- run_monitoring は監視用 DB（sqlite_path）を環境にかかわらず使用します。監視と実行エンジンの DB 分離は run_execution 側で KABUSYS_ENV=paper_trading 時に paper_sqlite_path を使用することで実現しています。
- Settings クラスは環境変数のバリデーションを行い、不正値に対しては明示的に ValueError を送出します（例えば KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。
- validate_config.py は PyYAML が未インストールの場合に YAML 検証をスキップして警告を出します。CI 等で厳密に検証したい場合は PyYAML を依存に追加してください。

今後の予定（例）
- research モジュールの完全実装（ファクター計算の SQL 実装完了、正規化ユーティリティとの統合）。
- ExecutionEngine / BrokerClient 実装のテスト増強、Paper Trading のシミュレーションカバレッジ拡張。
- 単体テスト・統合テストの追加と CI ワークフロー導入。