# Changelog

すべての変更は Keep a Changelog 規約に準拠しています。  
安定したリリース以外の変更は Unreleased に記載してください。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-21
初回リリース — KabuSys のコア機能を実装しました。主な追加点・仕様は以下の通りです。

### Added
- 基本パッケージ情報
  - パッケージバージョンを設定: `kabusys.__version__ = "0.1.0"`。

- 環境設定 / ロード
  - .env 自動読み込み機能を追加（プロジェクトルートは `.git` または `pyproject.toml` を基準に検出）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定することで無効化可能。
  - `.env` のパース機能を強化：
    - コメント行／空行を無視。
    - `export KEY=value` 形式に対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープを考慮。
    - クォート無しの値ではインラインコメントを柔軟に扱う（直前がスペース／タブの場合のみコメントとして扱う）。
  - 環境変数取得ユーティリティ `Settings` を追加（各種デフォルト値・バリデーションを含む）。
    - データベースパス（DuckDB / SQLite）、ログレベル、KABUSYS_ENV（development/paper_trading/live）等を管理。
    - Paper Trading 用の設定（`paper_sqlite_path`, `paper_fill_mode`）をサポート。

- 設定支援 CLI
  - 対話式ウィザード `kabusys.config_setup` を追加（`.env` の初期作成・更新を支援）。
    - 必須項目（J-Quants リフレッシュトークン、kabu API パスワード等）や任意項目を対話で設定可能。
    - 生成される `.env` に対して Git にコミットしない旨の注意を埋め込み。
  - 設定検証 CLI `kabusys.validate_config` を追加。
    - 必須環境変数の不足検出、`KABUSYS_ENV` / `LOG_LEVEL` の妥当性チェック、DuckDB/SQLite パスの親ディレクトリ存在チェックを実施。
    - `config/*.yaml` の存在確認と（PyYAML があれば）パース検証を行う。`--strict` で警告をエラー扱いに可能。

- ログ設定ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を追加。
    - stdout への StreamHandler（標準出力）と、日次ローテーション（TimedRotatingFileHandler）によるファイル出力を統一的に設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続するフォールバックを実装。
    - ログレベル・ログディレクトリの解決順を指定（引数 > 環境変数 > デフォルト）。

- プロセス優先度 / CPU affinity ユーティリティ
  - `kabusys.utils.process_priority` を追加。
    - クロスプラットフォームでの優先度設定 (`high` / `normal` / `low`) をサポート（Windows / POSIX に対応）。
    - CPU affinity 固定機能 `set_cpu_affinity` を提供（利用可能なコア数に基づき安全に処理）。
    - 権限不足や未対応環境では警告を出して安全にスキップ。

- 実行コンポーネント起動スクリプト
  - `run_execution.py` を追加（ExecutionEngine 起動ラッパー）。
    - 起動時にプロセス優先度を "high" に設定。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 専用 SQLite DB（デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離（MockBrokerClient を使用する想定）。
    - BrokerClientFactory を通じて適切なブローカクライアントを生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立ててデーモンスレッドで実行。停止フラグファイルによる安全停止に対応。
    - PID ファイルの取り扱い（`data/execution.pid` デフォルト）をサポート。

- 監視コンポーネント起動スクリプト
  - `run_monitoring.py` を追加（SystemMonitor ポーリングループ）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
    - 監視は常に本番用の sqlite_path を使用（環境に依存せず本番監視 DB を参照する設計）。
    - 停止フラグファイル検知でループを終了。例外はログに記録して次ポーリングへ継続。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を追加。
    - Paper Trading 用 SQLite（デフォルト `data/paper_trading.db`）から各種指標を集計してレポート出力（稼働率、注文成功率、送信率、レイテンシ等）。
    - P95 計算、閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）で PASS/FAIL 判定。
    - 日付フィルタ（--from / --to）およびカスタム DB パス（--db）をサポート。

- ポートフォリオ構築・リスク制御モジュール
  - ポートフォリオ関連の純粋関数群を追加（DB 参照なし、メモリ内計算）。
    - 候補選定: `select_candidates`（スコア降順、タイブレークに signal_rank）。
    - 重み計算: `calc_equal_weights`, `calc_score_weights`（全スコアが 0 の場合は等金額にフォールバックし WARNING）。
    - セクター集中制限: `apply_sector_cap`（既存保有のセクター時価が上限を超える場合、新規候補を除外。`unknown` セクターは適用除外）。
    - レジーム乗数: `calc_regime_multiplier`（`bull`/`neutral`/`bear` をマッピング、未知レジームは 1.0 でフォールバック）。
    - ポジションサイズ計算: `calc_position_sizes`
      - アロケーション方式 `"risk_based"`, `"equal"`, `"score"` をサポート。
      - 単元株（lot_size）で丸め、1銘柄上限、全体投下資金上限（aggregate cap）に応じたスケールダウンを実施。
      - cost_buffer による保守的なコスト見積り、残余キャッシュを用いた端数調整ロジックを実装。

- 研究用ファクタ計算（骨格）
  - `kabusys.research.factor_research` を追加（モメンタム / Value / Volatility / Liquidity 指標の計算方針とヘルパを実装中）。
    - DuckDB 接続を受け取り prices_daily などのテーブルから計算する方針。
    - モメンタム計算関数の雛形を追加（実装の続きを予定）。

### Changed
- 仕様上の分離を明確化
  - Paper Trading 実行時は発注機能と DB を本番から完全に分離（MockBroker + paper_trading DB）。
  - 監視ロジックは環境に依存せず常に監視用 DB を使用する旨を明確化。

### Fixed
- ロバスト性改善
  - ログディレクトリ作成やファイルハンドラ作成に失敗した場合でも標準出力ログで継続するようにフォールバック。
  - 環境変数パースの堅牢化（クォート・エスケープ・コメント処理の改善）。
  - process priority / cpu affinity 設定で権限不足や未実装の OS API に対して安全に処理をスキップし、警告を出すようにした。

### Notes / Breaking Changes
- .env 自動読み込みの動作
  - デフォルトでプロジェクトルートの .env / .env.local を自動読み込みします。自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 監視は本番用 sqlite_path を参照するため、ローカル開発で監視 DB を分離したい場合は `SQLITE_PATH` を明示的に指定してください（ただし実行スクリプトの設計上 monitoring は本番パスを使用することが想定されています）。

---

このリリースは初版のため、将来的に以下の点を拡張・改善する予定です:
- 研究用ファクタ計算の完全実装（duckdb クエリ最適化、欠損値ハンドリング等）
- Strategy / Execution の詳細なテスト・シミュレーション基盤
- 銘柄ごとの単元株サイズ拡張（stocks マスタの導入）
- モニタリング・アラートの通知チャネル（LINE 連携）強化

ご要望やバグ報告は issue を作成してください。