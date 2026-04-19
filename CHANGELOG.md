CHANGELOG
=========

すべての重要な変更はここに記録します。フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-19
--------------------

Added
- パッケージ初期リリース。
- 環境・設定関連
  - .env の自動ロード実装（プロジェクトルート検出: .git / pyproject.toml を基準）。環境変数は OS > .env.local > .env の優先度で読み込まれる。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - 詳細な .env パーサ実装: export 形式、シングル/ダブルクォート、エスケープ、インラインコメントの処理に対応。
  - Settings クラスを導入し、環境変数の取得・検証を集中管理（J-Quants / kabuステーション / DB パス / モードフラグ / モニタ閾値 等）。
  - config_setup: 対話式ウィザードで .env を作成・更新する CLI を追加。シークレット項目は表示をマスクして保存。
  - validate_config: .env および config/*.yaml の存在・基本チェックを行う CLI を追加。--strict モードで警告をエラー扱いにできる。PyYAML が無い場合は YAML 検証をスキップする旨を警告する。

- 実行・監視ランナー
  - run_execution: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用し、本番 DB と完全分離。BrokerClientFactory を通じて MockBrokerClient 等を利用可能。停止フラグ（data/stop_requested.flag）検知で安全停止、PID ファイルへの対応。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用する旨を明確化。停止フラグ検知でループ終了。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio_builder: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全ゼロ時は等配分へフォールバック。
  - risk_adjustment: セクター集中制限 apply_sector_cap、マーケットレジームに基づく資金乗数 calc_regime_multiplier を実装。未知レジーム時は警告を出しフォールバック。
  - position_sizing: 株数決定ロジック calc_position_sizes を実装。allocation_method に "risk_based" / "equal" / "score" をサポート。単元株（lot_size）対応、コストバッファ（cost_buffer）を考慮した aggregate cap スケーリング、余剰の配分アルゴリズムを実装。

- ユーティリティ
  - logging_setup: 統一ログ設定ユーティリティを追加。コンソール（stdout）と日次ローテーションファイル（TimedRotatingFileHandler, 30 日保持）をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力にフォールバック。
  - process_priority: クロスプラットフォームのプロセス優先度設定ユーティリティを追加（Windows / POSIX の差異を吸収）。set_cpu_affinity（最初 N コアに固定）も提供。権限不足等は警告を出して安全にスキップ。

- ツール
  - tools/paper_verification_report: ペーパートレード検証レポート生成スクリプトを追加。稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計し PASS/FAIL 判定を出力。--from/--to/--db オプションに対応。

- リサーチ
  - research/factor_research: ファクター計算モジュール（Momentum / Value / Volatility / Liquidity）の設計とモメンタム計算関数骨子を追加。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。

Changed
- なし（初期リリース）

Fixed
- .env パーサの数多くのケース（export プレフィックス、クォートとエスケープ、インラインコメント）に対応し、従来の単純パースの不備を改善。

Security
- config_setup でシークレットの表示をマスク（****）し、.env を Git にコミットしない旨を明示。
- Settings._require により必須環境変数未設定時に明示的にエラーを出すことで不完全な起動を防止。

Notes
- 依存:
  - duckdb（分析/計算用）
  - psutil（プロセス優先度 / CPU affinity）
  - PyYAML（config/*.yaml の検証に任意で必要。未インストールでも動作するが検証はスキップされる）
- デフォルトファイルパス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db
  - ログディレクトリ: logs/
  - PID / stop フラグ: data/execution.pid, data/stop_requested.flag
- 挙動に関する重要な点:
  - run_monitoring は環境に関係なく Settings.sqlite_path（本番監視 DB）を使います。run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を使用して発注履歴を分離します。
  - MONITOR_POLL_INTERVAL は環境変数で上書き可能。0 以下や不正値はデフォルト（60 秒）へフォールバック。
  - process_priority / set_cpu_affinity は権限不足・未サポート OS の場合に警告を出してスキップします。
  - logging_setup はログディレクトリ作成失敗時にファイル出力を無効化してコンソール出力のみを継続します。

Known issues / TODO
- risk_adjustment.apply_sector_cap:
  - price_map に price が欠損（0.0）の場合にエクスポージャが過少見積りされ、期待通りにブロックされない可能性あり。将来的に前日終値や取得原価でのフォールバックを検討する旨コメントあり。
- position_sizing.calc_position_sizes:
  - 将来的に銘柄ごとの単元（lot_size）をサポートする拡張を予定（現在は全銘柄共通 lot_size）。
- research/factor_research:
  - ファイル末尾で実装が途中（切断）になっている箇所があります。実装の続きが必要。
- テスト・CI:
  - 本リリースにユニットテストや CI 設定は含まれていないため、運用前に重点的なテストを推奨。

Acknowledgements
- 本プロジェクトはシステム監視、発注エンジン起動、ポートフォリオ構築、ペーパートレード検証、設定管理など複数コンポーネントを含む初期実装をまとめたものです。今後の改善（テスト追加、細部の堅牢化、性能・エラー時の堅牢性強化）を予定しています。