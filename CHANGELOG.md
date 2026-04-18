# Keep a Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。
https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
（現在未リリースの変更はここに記載します）

## [0.1.0] - 2026-04-18
初回リリース

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトルートの `data/stop_requested.flag` によるフラグ検知で行う。
    - 監視用 DB は環境に関係なく本番用の `sqlite_path` を使用する設計。
    - DuckDB 接続を併用。
    - 予期しない例外はログに残して次ポーリングへ継続する安全なループ構成。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、専用の paper trading DB（`data/paper_trading.db` がデフォルト）に記録することで本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定し、PID ファイル管理（`data/execution.pid`）と停止フラグ検知による安全停止を実装。
    - ExecutionEngine をデーモンスレッドで実行し、停止フラグで engine.stop() を呼んで安全に終了。

- 設定管理
  - config.py
    - 環境変数・設定管理クラス `Settings` を提供。各種設定（J-Quants、kabu API、LINE、DB パス、監視閾値、環境判定等）をプロパティ経由で取得。
    - プロジェクトルート検出 (`.git` または `pyproject.toml`) に基づく自動 `.env` ロード機能（`.env` と `.env.local` の読み込み、OS 環境変数を保護）。
    - `.env` ファイルの行解析器は引用符・エスケープ・コメント等に対応。
    - `paper_fill_mode` の妥当性チェックや `KABUSYS_ENV` / `LOG_LEVEL` の検証を実装。
  - config_setup.py
    - 対話式ウィザードで `.env` を初期作成／更新する CLI を追加（`python -m kabusys.config_setup`）。
    - 項目定義、既存 .env の読み込み、一括保存機能を実装。秘密情報は表示マスク。

- 設定検証
  - validate_config.py
    - 起動前に `.env` と `config/*.yaml` を検証する CLI を追加（`python -m kabusys.validate_config`）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ確認、YAML ファイルの存在確認および（PyYAML があれば）パース検証を行う。
    - `--strict` オプションで警告も失敗（exit 1）扱いにできる。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 通知設定確認、KILL_FLAG_CLEAR_ON_START の警告等）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（スコア降順）`select_candidates`、等配分 `calc_equal_weights`、スコア加重 `calc_score_weights` を実装。
    - スコアが全て 0 の場合は等配分にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py
    - セクター別上限適用 `apply_sector_cap`（既存保有のセクターエクスポージャー計算と候補除外）。
    - レジームに応じた投下資金乗数 `calc_regime_multiplier`（"bull"/"neutral"/"bear" マップ、未知レジームは 1.0 をフォールバック）。
  - portfolio/position_sizing.py
    - 株数計算 `calc_position_sizes` を実装（risk_based / equal / score の allocation_method に対応）。
    - 単元株（lot_size）での丸め、1 銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）、cost_buffer を考慮した保守的見積り、残差処理による追加配分ロジックを実装。

- 研究／ファクター計算
  - research/factor_research.py
    - ファクター計算モジュールの骨格を実装（モメンタム、MA200乖離、ATR、流動性等を想定）。DuckDB 接続を受け prices_daily / raw_financials を参照して計算する方針。
    - モメンタム計算関数のインターフェース（calc_momentum）を追加（実装途中の箇所あり）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。任意期間フィルタ（--from / --to）や DB パス指定 (--db) に対応。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を集計、閾値判定（稼働率 99% 等）して PASS/FAIL を出力。
    - P95 計算、データ存在チェック、DB の OperationalError に対する耐性を実装。

- ロギングとプロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定するユーティリティを追加。
    - 既存ハンドラをクリアして二重設定を防止。ログレベル／ログディレクトリは引数・環境変数で解決。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップして stdout のみで継続。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度を設定するユーティリティ `set_process_priority` と CPU affinity 設定 `set_cpu_affinity` を追加。
    - psutil を利用し、アクセス権限不足や未対応環境では警告ログを出してスキップする安全実装。

- DB 初期化
  - monitoring/monitoring_db.init_monitoring_db を利用して、監視用テーブルが存在することを保証する初期化処理をエントリポイントで呼び出し（冪等）。

### Changed
- （該当なし）初回リリースのため過去変更はありません。

### Fixed
- （該当なし）初回リリースのため修正履歴はありません。

### Security
- .env ファイルに関する注意書き
  - config_setup にて生成される .env は絶対に Git にコミットしないよう明記。
  - 環境変数の自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` によって無効化可能（テスト時の安全措置）。

### Notes / Known limitations
- research/factor_research.py は一部実装（calc_momentum の内部実装が切れている箇所）が残っており、完全なファクター計算の実装は今後の作業を想定。
- position_sizing の価格欠損（price が 0.0 の場合）の扱いについて TODO コメントがあり、将来的にフォールバック価格の導入を検討する必要あり。
- プロセス優先度・CPU affinity の設定は OS 権限や環境に依存し、失敗した場合はログ警告でスキップされる。

---

（以降のリリースでは、Unreleased セクションに変更を追加し、適宜バージョンを切って日付を付与してください。）