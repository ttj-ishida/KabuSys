# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

## [0.1.0] - 2026-04-23

初回リリース

### Added
- 全体
  - パッケージ初期版を追加。バージョン: `kabusys.__version__ = "0.1.0"`。

- 環境設定 / 設定読み込み
  - .env ファイル（および .env.local）の自動ロード機能を実装。プロジェクトルートは `.git` または `pyproject.toml` を基準に探索して検出する（`kabusys.config._find_project_root`）。
  - .env パーサーを実装（`kabusys.config._parse_env_line`）。次の特徴をサポート:
    - export プレフィックス（`export KEY=val`）
    - シングル/ダブルクォート内のエスケープ処理
    - インラインコメントの扱い（クォート有無で挙動を分離）
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - 設定ラッパークラス `Settings` を実装（`kabusys.config.Settings`）。J-Quants / kabu API / DB パス / 監視しきい値など主要設定をプロパティとして提供。
    - `paper_fill_mode` のバリデーション（"instant" / "partial" / "never" / "reject"）
    - `env` のバリデーション（development / paper_trading / live）
    - `is_live` / `is_paper` / `is_dev` フラグ

- 設定ウィザード / 検証 CLI
  - 対話式 `.env` 作成・更新ウィザードを追加（`python -m kabusys.config_setup`）。
    - 初期項目定義、既存 .env 読み込み、シークレット入力、保存確認、.env ファイル生成を実装。
  - 設定検証 CLI を追加（`python -m kabusys.validate_config`）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML インストール有無で分岐）、本番向け追加ガードを実装。
    - `--strict` オプションで警告を失敗扱いにできる。

- 実行用スクリプト
  - 実行エンジン起動スクリプト（`src/kabusys/run_execution.py`）を追加。
    - `Settings` を用いた設定取得、プロセス優先度を High に設定（`kabusys.utils.process_priority.set_process_priority`）。
    - Paper Trading 環境では専用 SQLite（`PAPER_TRADING_SQLITE_PATH` / default: `data/paper_trading.db`）を使用し、本番 DB と分離。
    - `BrokerClientFactory` を経由したブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てと起動ループ（デーモンスレッド）を実装。
    - 停止フラグ（`data/stop_requested.flag`）と PID ファイル（`data/execution.pid`）に対応。

  - 監視ループ起動スクリプト（`src/kabusys/run_monitoring.py`）を追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト: 60秒）。不正な値は警告してデフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV に依らず本番用 `sqlite_path` を使用する旨の取り扱い。
    - SQLite / DuckDB の接続初期化、`SystemMonitor` の単回チェック `check_once()` をポーリングループで呼出し、停止フラグで終了。

- ロギング・プロセス管理ユーティリティ
  - ロギング初期化ユーティリティ（`kabusys.utils.logging_setup.setup_logging`）を追加。
    - stdout ストリームハンドラ（StreamHandler）と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力を省略してコンソールのみで継続。
    - ログレベルおよびログディレクトリの解決順をドキュメント化（引数 > 環境変数 > デフォルト）。

  - プロセス優先度 / CPU affinity ユーティリティ（`kabusys.utils.process_priority`）を追加。
    - Windows / POSIX の違いを吸収して優先度を設定（"high"/"normal"/"low"）。
    - `set_cpu_affinity(cpu_count)` で最初の N コアにピン留めする機能を追加。
    - 権限不足や未対応環境時は警告してスキップ。

- ポートフォリオ構築（純粋関数群）
  - 銘柄候補選定・重み付け（`kabusys.portfolio.portfolio_builder`）
    - select_candidates, calc_equal_weights, calc_score_weights を実装。スコア合計が 0 の場合のフォールバックを実装（等分配）。
  - セクター集中制限・レジーム乗数（`kabusys.portfolio.risk_adjustment`）
    - apply_sector_cap（既存保有からセクター暴露を計算して候補を除外、"unknown" セクターは除外対象としない）
    - calc_regime_multiplier（"bull"/"neutral"/"bear" に対する乗数、未知値は 1.0 でフォールバック）
  - 株数決定・リスク制限・単元丸め（`kabusys.portfolio.position_sizing`）
    - calc_position_sizes を実装（allocation_method="risk_based" / "equal" / "score" をサポート）。
    - lot_size 単位で丸め、max_position_pct / max_utilization による per-position および aggregate 上限、cost_buffer を用いた保守的見積り、合計超過時のスケーリングと残差処理（fractional 残差に基づく追加配分）を実装。

- Paper Trading ツール
  - 検証レポート作成スクリプト（`kabusys.tools.paper_verification_report`）を追加。
    - Paper Trading 用 SQLite（環境変数 `PAPER_TRADING_SQLITE_PATH` または `--db` オプション）から各種指標を算出:
      - システム稼働率（uptime）、注文成功率・送信率、リスク却下数、レイテンシ（avg/max/P95）など。
    - 判定基準（閾値）を定義し、PASS/FAIL 判定を出力。
    - 日付フィルタ（--from / --to）に対応。P95 計算ロジックを実装。

- リサーチ / ファクター計算（初期実装）
  - `kabusys.research.factor_research` を追加（ファクター計算の骨組み）。
    - モメンタム/MA/ATR/出来高等の計算を実装する方針と定数を定義。`calc_momentum` の雛形および定数を含む（prices_daily / raw_financials を想定した DuckDB 参照モデル）。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / 注意事項
- run_monitoring は MONITOR_POLL_INTERVAL の値が不正（例: 0 や文字列）だった場合にログ警告を出しデフォルトの 60 秒にフォールバックします。
- run_monitoring は監視 DB に production 用の `sqlite_path` を常に使用します（KABUSYS_ENV と独立）。
- run_execution は KABUSYS_ENV=paper_trading の場合、MockBroker を使用して paper_trading 用 DB に記録する設計になっており、本番 DB と分離されます。
- process priority / CPU affinity の設定は権限や OS の違いにより実行できない場合があります。失敗時は警告ログが出力されます。
- `.env` は絶対にリポジトリにコミットしないでください（config_setup のヘッダにも警告を記載）。

今後の予定（例）
- research モジュールの各ファクター実装完了（momentum, volatility, value, liquidity）。
- Execution / Monitoring コンポーネントの統合テスト、BrokerClient 実装の追加（実ブローカー連携 / モックの整理）。
- ドキュメント（運用手順、デプロイ手順、設定例）の充実。

---