# Changelog

すべての重要な変更は Keep a Changelog の原則に従って記録します。  
このファイルは、リポジトリ内のソースコードから推測して作成した変更履歴です（実際のコミット履歴が存在しない場合の推定内容を含みます）。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース — KabuSys の基本機能一式を実装しました。以下の主要機能・モジュールを含みます。

### Added
- パッケージ基盤
  - パッケージ version を `__version__ = "0.1.0"` として設定。
  - モジュール公開: data, strategy, execution, monitoring をエクスポート。

- 設定管理
  - `kabusys.config.Settings` クラスを追加。環境変数から設定を安全に取得するプロパティ群を提供（J-Quants / kabu API / DB パス / ログレベル / 環境判定等）。
  - 自動 .env ロード機能を実装（プロジェクトルート探索: `.git` または `pyproject.toml` を基準）。
  - .env パーサーを実装（`export` 構文、クォート付き値、インラインコメントの取扱い、保護された OS 環境変数の扱いをサポート）。
  - 環境変数ロードを無効化するフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。

- 設定ツール / 検証 CLI
  - `kabusys.config_setup` — 対話式ウィザードで `.env` を生成/更新する CLI。必須項目/任意項目のプロンプト、シークレットマスキング、確認→書き込みフローを提供。
  - `kabusys.validate_config` — 起動前検証ツールを追加。必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在・パースチェック（PyYAML がインストールされている場合）。`--strict` オプションで警告をエラー扱いにできる。

- 実行系 / モニタリング起動スクリプト
  - `kabusys/run_execution.py` — ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper 専用 SQLite（`PAPER_TRADING_SQLITE_PATH` またはデフォルト `data/paper_trading.db`）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（本番/モックの切替）。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立ててデーモンスレッドで実行。PID ファイル・停止フラグ（data/execution.pid, data/stop_requested.flag）管理を実装。
    - RiskManager の初期設定（最大ポジション比率、利用率、レート制限、サーキットブレーカー等）を用意。

  - `kabusys/run_monitoring.py` — SystemMonitor ポーリングループ起動スクリプトを追加。
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番の sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）および KeyboardInterrupt を考慮してクリーンに終了。

- ロギング / プロセス制御ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定する共通ユーティリティ。
    - ログレベルとログディレクトリの解決順序（引数 > 環境変数 > デフォルト）をサポート。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - `kabusys.utils.process_priority` を追加。
    - Windows / POSIX (Linux/Mac/FreeBSD) 間の差を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアに固定する機能を提供。権限不足や未対応環境でも安全にフォールバック。

- ポートフォリオ構築（Portfolio construction）
  - `kabusys.portfolio.portfolio_builder`
    - buy シグナルの候補選定 `select_candidates`（スコア降順、タイブレークは signal_rank）。
    - 重み計算: 等配分 `calc_equal_weights`、スコア加重 `calc_score_weights`（全スコア 0 の場合は等配分へフォールバック）。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限を実施する `apply_sector_cap`（既存保有を考慮、sell コードの除外、unknown セクターは制限を適用しない）。
    - 市場レジームに応じた投下資金乗数を返す `calc_regime_multiplier`（bull/neutral/bear のマップ、未知レジームは警告して 1.0 でフォールバック）。
  - `kabusys.portfolio.position_sizing`
    - `calc_position_sizes` を実装。allocation_method（"risk_based" / "equal" / "score"）に応じて買付株数を算出。
    - 単元株（lot_size）丸め、per-position 上限（max_position_pct）や aggregate cap（available_cash）によるスケーリング、cost_buffer（スリッページ/手数料見積り）をサポート。
    - リスクベース手法では stop_loss_pct, risk_pct を用いたポジション sizing を提供。

- 監視 / 解析ツール
  - `kabusys.tools.paper_verification_report` を追加。
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から稼働率、注文成功率、送信率、API レイテンシ（平均/最大/P95）等を集計して検証レポートを出力。
    - デフォルトしきい値を設け PASS/FAIL を判定（稼働率 99% / 成功率 90% / 送信率 95% / P95 レイテンシ 200 ms）。
    - CLI オプションで期間指定（--from/--to）や DB パス指定（--db）をサポート。

- リサーチ（ファクター計算）
  - `kabusys.research.factor_research` を新規追加（モメンタム等のファクター計算を DuckDB を用いて行う設計）。
    - モメンタム、MA200 乖離、ATR、出来高・流動性系などのファクター設計を意図。DuckDB の `prices_daily` / `raw_financials` テーブル参照で実装予定（関数設計と定数定義を含む）。（注: ファイル末尾で実装の続きを想定）

### Changed
- 実行・監視関連の設計方針
  - run_monitoring は実行環境に関わらず監視用の本番 sqlite_path を使用する方針を明示（運用上の一貫性確保）。
  - run_execution は paper_trading 時に本番 DB と完全分離するため専用 paper DB を使用。

### Fixed
- Settings / バリデーションの強化
  - `Settings.paper_fill_mode` で有効値チェックを追加し、不正値は ValueError を送出するように改善。
  - `Settings.env` / `log_level` で許容値チェックを行い、不正設定時に早期に検出するようにした。

### Documentation / UX
- CLI ヘルプ・メッセージ、.env ウィザードのプロンプト文を充実させ、初期セットアップから検証までの流れ（config_setup → validate_config）を明記。
- ログ出力のフォーマット・保存場所のデフォルトを明確化（logs/、日次ローテーション）。

### Security / Safety notes
- `.env` は絶対にリポジトリにコミットしない旨を config_setup の生成ヘッダに明記。
- `validate_config` は本番環境（KABUSYS_ENV=live）での注意喚起（LINE通知未設定、KILL_FLAG_CLEAR_ON_START の危険性）を行うガードを実装。

---

注意:
- 上記は提供されたソースコードから推測してまとめた CHANGELOG です。実際のコミットメッセージやマイルストーンが存在する場合は、それらに基づいて調整してください。
- factor_research モジュールなど一部は実装途中/続きが想定される箇所があります（ソース末尾の切れ等）。必要に応じて継続実装・テストを行ってください。