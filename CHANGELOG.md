CHANGELOG
=========

すべての重要な変更をここに記載します。フォーマットは「Keep a Changelog」に準拠しています。

ルール:
- 影響の大きい変更はカテゴリ（Added / Changed / Fixed / Deprecated / Security）ごとに記載しています。
- 日付はこのリリースに合わせて付与しています（推測に基づく初回リリース記録）。

Unreleased
----------
（なし）

[0.1.0] - 2026-04-19
-------------------

Added
- 実行・監視用エントリポイントを追加
  - run_execution.py: ExecutionEngine を起動する CLI ランチャーを追加。プロセス優先度設定、SQLite/DuckDB 接続、BrokerClient の生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、スレッド実行と停止フラグ監視を実装。KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB に完全分離して動作する（PAPER_TRADING_SQLITE_PATH により上書き可能）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視 DB は環境に関係なく本番 sqlite_path を使用する挙動を明示。

- 設定管理・操作用ユーティリティを追加
  - config.py: Settings クラスによる環境変数管理を追加。プロジェクトルートの .env / .env.local を自動ロードする機能（CWD に依存せず .git / pyproject.toml を基準にプロジェクトルートを探索）。.env のパースは export 形式やクォート／エスケープ、インラインコメント等に対応。各種パス、Paper Trading 関連設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）、閾値（CPU/MEM/DISK）や PID / Kill Flag の設定を提供。
  - config_setup.py: 対話式ウィザードで .env ファイルを生成・更新する CLI を追加。機密値はマスク表示して入力可能。デフォルト値や選択肢を用意し、保存前の確認プロンプトを実装。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス、config/*.yaml の存在・パース（PyYAML がある場合）などを検査。--strict オプションで警告をエラー扱いにできる。

- ロギング・プロセス制御ユーティリティを追加
  - utils/logging_setup.py: ルートロガーに対して StreamHandler（stdout）と TimedRotatingFileHandler（ログ日次ローテーション）を統一設定するユーティリティを追加。ログディレクトリ自動作成、既存ハンドラのクリーンアップ、ファイルハンドラ作成失敗時のフォールバックを実装。ログファイルは日次ローテーションで 30 日保管。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 固定ユーティリティを追加。権限不足や未対応 OS の場合は警告を出して安全にスキップする挙動。

- ポートフォリオ構築関連の純粋関数群を追加（DB 参照なし）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等分配へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中キャップ適用（apply_sector_cap）、市場レジームに応じた投資乗数（calc_regime_multiplier）を実装。未知レジーム時はフォールバックで 1.0 を返す。
  - portfolio/position_sizing.py: position sizing ロジックを実装。allocation_method として "risk_based" / "equal" / "score" をサポートし、lot_size（単元）丸め、per-stock 上限、aggregate cap（利用可能現金を超えた際のスケーリング）を考慮。cost_buffer による保守的見積りをサポート。

- Paper Trading 向け検証レポートを追加
  - tools/paper_verification_report.py: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）からデータを集計し、稼働率（uptime）、注文成功率（fill rate）、送信率、レイテンシ（P95 など）、リスク却下回数を算出して標準出力にレポートを生成する CLI を追加。各指標の合否判定閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）を設定。P95 の計算、日付フィルタ (--from / --to)、DB パス指定オプションを提供。

- research/factor_research.py: DuckDB ベースのファクター計算モジュールの骨組み（モメンタム等）を追加（prices_daily / raw_financials を参照する設計）。

- パッケージメタ
  - __init__.py に __version__ = "0.1.0" を設定。

Changed
- 初期実装（初回リリース）として設計方針や CLI / ユーティリティの API を確立。
- logging_setup: 標準出力は stderr ではなく stdout を使用するように設計（cron 等とのリダイレクトを想定）。

Fixed
- .env 読み込みの安全性・堅牢性を改善
  - OS 環境変数が自動上書きされないよう protected セットを導入し、.env.local の上書きルール（override）をサポート。
  - プロジェクトルートが特定できない場合は自動ロードをスキップすることで配布後やテスト環境での不要な副作用を防止。
  - .env の行パーサーは export 形式、クォート、バックスラッシュエスケープ、コメント処理に対応して不正入力に対して堅牢化。

- 実行中の二重ログハンドラ設定を防ぐため、setup_logging が既存ハンドラを一度 flush/close してから再設定するようにした。

- process_priority / set_cpu_affinity は権限エラーや未対応 API に対して警告ログを出してスキップするようにして、起動失敗による致命的エラーを防止。

- run_monitoring / run_execution の停止処理を堅牢化（プロセス停止フラグ検知、KeyboardInterrupt ハンドリング、コネクションの確実なクローズ）。

Deprecated
- なし

Security
- config_setup が生成する .env ファイルに関して、ファイル先頭に「.env は絶対に Git にコミットしないこと」という注意書きを追加（自動生成内容）。
- Settings._require による必須環境変数不足時は ValueError を送出して明確に失敗する挙動にしている（起動前検証を推奨）。

Notes / 今後の改善案（コード内 TODO より）
- position_sizing.calc_position_sizes: 銘柄毎の単元（lot_size）を将来的に銘柄マスタで保持し、個別 lot_map を受け取る設計に拡張予定。
- risk_adjustment.apply_sector_cap: 価格が欠損（0.0）の場合にエクスポージャーが過少見積りされうるため、前日終値や取得原価などのフォールバック価格を使う拡張を検討。
- research/factor_research.py: モメンタム等の計算実装が途中（骨組みあり）であり、完全実装・テストが必要。

Reference
- 各 CLI の使い方やオプションは該当ファイルのトップドックストリングに記載されています（例: run_execution.py, run_monitoring.py, config_setup.py, validate_config.py, tools/paper_verification_report.py）。