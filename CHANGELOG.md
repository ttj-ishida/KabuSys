# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

注: 内容はリポジトリ内のソースコード（コメント・実装）から推測して作成しています。

## [0.1.0] - 2026-04-19

### Added
- 全体
  - 初回リリース相当のコードベースを追加。
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"` を導入。

- 実行/監視関連
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用して paper_trading 専用 DB（既定: `data/paper_trading.db`）に記録する振る舞いをサポート。
    - 停止フラグ（`data/stop_requested.flag`）の検出による安全停止処理を実装。
    - 実行中の PID 管理 (`data/execution.pid`) をサポート。
    - プロセス優先度を起動直後に high に設定する処理を追加。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用の sqlite_path を使用する仕様（明示的に実装）。
    - 停止フラグ（`data/stop_requested.flag`）によるループ終了処理を実装。
    - 例外発生時のログ記録と継続処理を実装。

- 設定管理
  - config.py: 環境変数/設定管理モジュールを追加。
    - `.env` / `.env.local` の自動読み込み（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。
    - 自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - 複雑な `.env` のパースに対応（`export` プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理など）。
    - 各種プロパティを提供（J-Quants / kabuステーション / LINE / DB パス / モニタ閾値 / 環境判定など）。
    - `PAPER_FILL_MODE` の検証ロジック（有効値: `"instant" | "partial" | "never" | "reject"`）。
    - `is_live` / `is_paper` / `is_dev` 等のユーティリティ属性。
  - config_setup.py: 対話式の `.env` 作成・更新ウィザードを追加。
    - シークレット項目のマスク表示、選択肢/デフォルトのサポート、既存 `.env` の読み込み。
    - 生成される `.env` のテンプレートと保存処理を実装。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数のチェック、`KABUSYS_ENV` / `LOG_LEVEL` の値検証、DB パスの親ディレクトリ存在チェック、`config/*.yaml` の存在および（PyYAML があれば）パース検証。
    - `--strict` オプションで警告も失敗扱いにできる。
    - 本番環境 (`KABUSYS_ENV=live`) 向けの追加ガード（LINE 未設定や Kill Switch 設定などの警告）。

- ロギング / プロセス制御
  - utils/logging_setup.py: 共通ロギング設定ユーティリティを追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。
    - ログディレクトリの自動作成・失敗時のフォールバック（コンソールのみ）処理を実装。
    - 既存ハンドラのクリア処理を実装し二重設定を防止。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux/macOS/FreeBSD）向けの差分吸収。
    - `set_process_priority(level)` と `set_cpu_affinity(cpu_count)` を提供。
    - 権限不足などで設定できない場合は警告ログでフォールバック。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py:
    - 候補選定 (`select_candidates`)、等配分 (`calc_equal_weights`)、スコア加重配分 (`calc_score_weights`) を追加。
    - スコアが全て 0 の場合のフォールバック警告を実装。
  - portfolio/risk_adjustment.py:
    - セクター上限チェックで新規候補を除外する `apply_sector_cap` を追加。
    - 市場レジームに応じた投下資金乗数を返す `calc_regime_multiplier` を追加（`bull`/`neutral`/`bear` マッピング、未知レジームは警告してフォールバック）。
  - portfolio/position_sizing.py:
    - リスクベース / 等配分 / スコア配分に対応する `calc_position_sizes` を追加。
    - 単元株（lot_size）丸め、個別/総合上限（max_position_pct / max_utilization）、コストバッファ考慮のスケールダウンアルゴリズムを実装。
    - 端数処理で残余キャッシュを用いた追加配分（再現性確保のため安定ソート）を実装。

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - `system_status` / `trade_logs` / `risk_logs` から稼働率・注文成功率・送信率・レイテンシ等を集計。
    - P95 計算、閾値判定（稼働率 99%、成功率 90% 等）による PASS/FAIL 判定を実装。
    - コマンドライン引数 `--from`/`--to`/`--db` をサポート。

- リサーチ
  - research/factor_research.py: ファクター計算モジュールを追加（Momentum / Value / Volatility / Liquidity を想定、DuckDB を用いた計算設計）。
    - モメンタム計算用の定数や関数スケルトン（例: calc_momentum）を実装（実装途中のファイルあり）。

### Changed
- なし（初回リリースのため該当なし）。ただし、各モジュールは設計注記（TODO）やフォールバックロジックを含む。

### Fixed
- なし（初回リリースのため該当なし）。

### Deprecated
- なし。

### Removed
- なし。

### Security
- なし（明示的なセキュリティ修正はコードからは確認できず）。

## 注記 / 使用上の重要ポイント
- 環境変数の自動ロードはデフォルトで有効。テスト等で無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- `.env` の生成時に秘密情報はマスクされますが、`.env` 自体は決して Git にコミットしないでください（config_setup.py のヘッダにも警告あり）。
- run_execution/run_monitoring は起動時にプロセス優先度を high に設定しようとしますが、権限不足等で設定できない場合は警告でフォールバックします。
- Paper Trading 用 DB は本番 DB と分離されているため、ペーパートレード実行時のデータは `PAPER_TRADING_SQLITE_PATH`（既定 `data/paper_trading.db`）に保存されます。
- ログはデフォルトで `logs/` に出力（ファイル出力に失敗した場合は標準出力のみ）。ログレベルやログディレクトリは環境変数 `LOG_LEVEL` / `LOG_DIR` で上書き可能です。

もしリリースノートに加えたい追加の観点（たとえば「既知の制限」や「今後の計画」）があれば教えてください。コード中の TODO 事項や未実装箇所も抜粋して追記できます。