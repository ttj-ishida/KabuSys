# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  

注: この CHANGELOG はソースコードの内容から推定して作成しています。

## [Unreleased]

### Added
- run_monitoring 起動スクリプトを追加
  - SystemMonitor のポーリングループを起動するスクリプト。
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト: 60 秒）。
  - 停止はプロジェクト内の `data/stop_requested.flag` によるフラグ検出で行う。
  - Monitoring は KABUSYS_ENV にかかわらず本番用の `sqlite_path` を使用する旨を明示。

- run_execution 起動スクリプトを追加
  - ExecutionEngine を起動するスクリプト。
  - `KABUSYS_ENV=paper_trading` の場合は専用の Paper Trading SQLite（デフォルト: `data/paper_trading.db`）を使用して本番 DB と分離。
  - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み合わせて ExecutionEngine を構成。
  - 停止フラグ検出により実行中のエンジンを安全に停止。

- 環境設定関連 CLI を追加
  - config_setup: 対話式ウィザードで .env を作成・更新するツール。
  - validate_config: .env と `config/*.yaml` の事前検証ツール。`--strict` オプションで警告も失敗扱いに可能。

- 設定管理 (kabusys.config)
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）に基づく .env 自動読み込み（`.env.local` の優先適用を含む）。
  - .env パーサを実装：`export KEY=val`、クォート内のエスケープ、インラインコメント対応、保護付き上書き機構をサポート。
  - Settings クラスで環境変数をラップ。型変換・バリデーション（`KABUSYS_ENV`、`LOG_LEVEL`、`PAPER_FILL_MODE` 等）を提供。
  - `settings` 単一インスタンスを提供。

- ロギングユーティリティ (kabusys.utils.logging_setup)
  - ルートロガーに対して StreamHandler（stdout）と TimedRotatingFileHandler（日次・30世代保持）を設定。
  - ログディレクトリ自動作成、失敗時はファイル出力をスキップしてコンソールのみで稼働。
  - ログレベル解決順（引数 > 環境変数 > デフォルト）を実装。

- プロセス優先度ユーティリティ (kabusys.utils.process_priority)
  - Windows/Linux/macOS に対応したプロセス優先度設定（`high`/`normal`/`low`）と CPU affinity 設定補助。
  - アクセス拒否等の例外は警告ログを出して安全にスキップ。

- ポートフォリオ構築ライブラリ (kabusys.portfolio)
  - portfolio_builder: 候補選定 (`select_candidates`)、等分配 (`calc_equal_weights`)、スコア加重 (`calc_score_weights`) の純粋関数を追加。スコアが全て 0 の場合は等分配へフォールバック。
  - risk_adjustment: セクター集中上限適用 (`apply_sector_cap`) と市場レジーム乗数 (`calc_regime_multiplier`) を追加。未知セクターは除外の対象としない。未知レジームは 1.0 にフォールバック。
  - position_sizing: 株数算出ロジック (`calc_position_sizes`) を追加。リスクベース/等分/スコア配分をサポートし、単元株（lot_size）丸め、個別上限・合計投下額（aggregate cap）スケーリング、手数料・スリッページ見積り用の cost_buffer を考慮。

- Paper Trading 検証レポートツール (kabusys.tools.paper_verification_report)
  - Paper Trading 用 SQLite から指標（稼働率、注文成功率、送信率、レイテンシ等）を集計して標準出力にレポートを生成。
  - P95 計算、期間フィルタ (--from / --to)、閾値による PASS/FAIL 判定を実装。
  - デフォルト閾値: 稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。

- research/factor_research の骨格を追加
  - DuckDB を用いた価格・財務データに基づくファクター計算（モメンタム/ボラティリティ/価値/流動性）を想定した設計。関数は DuckDB 接続を受け取り純関数的に動作する設計。

### Changed
- ログ出力を stdout に明示的に向けるように変更（cron/Task Scheduler との相性を考慮）。
- run_monitoring/run_execution 起動時にプロセス優先度を早期に `high` に設定するように統一。
- run_monitoring: MONITOR_POLL_INTERVAL の不正値に対して警告を出しデフォルトにフォールバックする堅牢化を追加。

### Fixed
- .env 自動読み込み時に OS 環境変数を上書きしない保護機構（protected keys）を実装。`.env.local` は `override=True` で OS 環境変数を上書きしないよう配慮。
- process_priority の未対応 OS に対する動作を警告ベースでスキップするようにして起動失敗しないよう改善。
- position_sizing の合計コスト超過時のスケールダウンと残余配分ロジックを実装して、端数処理と単元株制約に対応。

### Documentation
- 各モジュールに docstring を追加し、挙動・引数・返り値・注意点を明記。
- config_setup の出力テンプレートと使用方法を明示。

### Security
- .env の生成テンプレートに「絶対に Git にコミットしないこと」を明記。

## [0.1.0] - 2026-04-20

初回リリース相当。上記の機能群をまとめて公開。

### Added
- 初期バージョンとして以下を実装・公開:
  - コア実行スクリプト: run_execution, run_monitoring
  - 設定管理: kabusys.config, config_setup, validate_config
  - ロギング/プロセスユーティリティ: logging_setup, process_priority
  - ポートフォリオ構築ライブラリ: portfolio_builder, risk_adjustment, position_sizing
  - Paper Trading 検証ツール: tools.paper_verification_report
  - 解析基盤向け: research.factor_research（骨格）
  - パッケージメタ情報: __version__ = 0.1.0

### Changed
- 仕様上の重要点:
  - Monitoring は環境にかかわらず本番用 sqlite（`SQLITE_PATH`）を参照する仕様。
  - Paper Trading は本番 DB と完全に分離した専用 SQLite (`PAPER_TRADING_SQLITE_PATH`) を使用。

### Known limitations / Notes
- 一部モジュール（例: research.factor_research）は実装途中の関数が存在する（ファイル末尾で途切れている可能性あり）。使用時は内容を確認してください。
- .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされる。
- ログディレクトリ作成やファイルハンドラ作成に失敗した場合はコンソールログのみで継続する設計。

---

今後のリリースでは以下を検討しています:
- strategy / execution の統合テストとドキュメント整備
- ファクター計算モジュールの完成、duckdb ベースの高速化チューニング
- 単体テスト、型ヒントの充実、CI ワークフローの追加

もし実装の詳細や特定ファイルの変更点をさらに掘り下げてほしい箇所があれば教えてください。