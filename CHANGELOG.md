# Changelog

すべての重要な変更をここに記載します。フォーマットは "Keep a Changelog" に準拠します。

注意: 本 CHANGLEOG は現行コードベースから推測して作成しています（コミット履歴ではなく、ソースコードの内容に基づく要約です）。

## [Unreleased]

## [0.1.0] - 2026-04-18

### Added
- 全体
  - パッケージ初期リリース。日本株自動売買システム「KabuSys」の基本機能群を収録。
  - バージョン番号を `src/kabusys/__init__.py` にて `0.1.0` として定義。

- 起動スクリプト / デーモン
  - run_monitoring: システム監視用ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト `data/stop_requested.flag` ファイルの検知により制御。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番用の sqlite_path を使用する設計。
    - 例外時にログ出力して次のポーリングへ回復する堅牢化。
  - run_execution: 注文実行エンジン起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合はペーパートレード用の専用 SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離。
    - BrokerClientFactory により実運用/モックの切替を行う設計を採用。
    - スレッドで ExecutionEngine をデーモン実行し、`data/stop_requested.flag` により停止要求を検知して安全に停止。
    - PID ファイルサポート（`data/execution.pid`）を持つ。

- 設定管理
  - `kabusys.config.Settings` クラスを追加。環境変数をラップして型変換・妥当性チェックを提供。
    - `PAPER_FILL_MODE`（paper_trading の fill モード）など専用設定をサポート（値検証あり）。
    - 環境種別 `KABUSYS_ENV`、`LOG_LEVEL` の妥当性検証を実装。
    - 本番判定（is_live 等）・ペーパー判定（is_paper）用ヘルパを提供。
  - 自動 .env ロード:
    - プロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動読み込み（OS 環境変数を保護して上書き挙動を制御）。
    - `.env` の行パースを強化（`export KEY=...`、引用符扱い、エスケープ、インラインコメントの取り扱いなどに対応）。

- 設定ユーティリティ / CLI
  - `config_setup.py`: 対話式ウィザードで `.env` を初期作成・更新する CLI を追加。
    - 秘密項目（トークン等）はマスク表示、選択肢・デフォルト・説明文を備えた入力プロンプト。
    - `.env` テンプレート生成機能（ファイルヘッダ含む）。
  - `validate_config.py`: 起動前の設定検証 CLI を追加。
    - 必須環境変数の有無チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在と（PyYAML があれば）パース検証を実施。
    - `--strict` オプションで警告も失敗扱いにできる。

- ロギング / プロセス管理ユーティリティ
  - `utils/logging_setup.py`:
    - すべての起動スクリプトで共有できる一元的ロギング設定を提供。
    - stdout へ出力する StreamHandler（cron 等で stdout/stderr を統合する運用を想定）と、日次ローテーション（TimedRotatingFileHandler）によるファイル出力（既定 logs/、30 日保持）を設定。
    - ログディレクトリ作成失敗時はファイル出力を回避してコンソールのみで継続するフォールバックを実装。
  - `utils/process_priority.py`:
    - Windows / POSIX の差分を吸収してプロセス優先度を設定するユーティリティを追加。
    - CPU affinity 設定（最初の N コアにピン留め）機能を提供。
    - 権限不足や未対応 OS を考慮した安全な失敗（警告ログ）を実装。

- Portfolio 構築（純粋関数群）
  - `portfolio/portfolio_builder.py`:
    - シグナル選別（select_candidates: スコア降順、タイブレークルールあり）。
    - 重み計算（等分配 calc_equal_weights、スコア正規化 calc_score_weights。全スコアが 0 の場合のフォールバック warning）。
  - `portfolio/risk_adjustment.py`:
    - セクター集中上限を適用して候補を除外する apply_sector_cap を実装（unknown セクターは制限対象外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（`bull`/`neutral`/`bear` マッピング、未知レジームはフォールバック 1.0）。
  - `portfolio/position_sizing.py`:
    - 複数の配分方式に対応した発注株数計算（`risk_based`, `equal`, `score`）。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超過する場合のスケーリング）を実装。
    - cost_buffer を考慮した保守的見積り、スケール時の端数再配分アルゴリズム（残差に基づき lot 単位で追加）をサポート。

- Research / ファクター計算（骨格実装）
  - `research/factor_research.py`:
    - DuckDB 接続を受け取り、モメンタム / ボラティリティ / バリュー 等のファクターを計算する設計。
    - モメンタム計算関数 `calc_momentum`（関数シグネチャと設計注釈を含む）が追加（内部実装の一部が続く構造）。

- ツール
  - `tools/paper_verification_report.py`:
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなどを算出。
    - デフォルト DB: `PAPER_TRADING_SQLITE_PATH` 環境変数または `data/paper_trading.db`。
    - 基準値（稼働率 >= 99%、fill >= 90% など）による PASS/FAIL 判定を実装。

- DB / 分析
  - DuckDB を分析用 DB（`duckdb.connect`）として統合。Execution/Monitoring の両スクリプトで接続を確立する設計。

### Changed
- 設定読み込みのポリシー
  - `.env.local` を `.env` より優先して読み込み（OS 環境変数は protected として上書きされない）。
  - 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。

- ログ出力のデフォルトと挙動
  - StreamHandler を stdout に向けることで、cron/スケジューラからのログ収集運用を想定。

### Fixed
- 安全性・堅牢化
  - run_monitoring/run_execution で監視ループ・スレッド実行中の例外を捕捉してプロセスが落ちないように保護。
  - DB コネクションや DuckDB コネクションは finally ブロックで確実にクローズされるように変更。
  - `.env` パーサのクォート/エスケープ処理やインラインコメントの取り扱いを改善し、環境変数の読み間違いを防止。

### Security
- 秘密情報の取り扱い
  - `config_setup` の対話入力では秘密項目をマスク表示。`.env` ファイル生成時に注意書きを追加（Git にコミットしないよう注意喚起）。

### Known limitations / Notes
- research/factor_research.py はファイル末尾で一部が切れている（計算ロジックの続きが未表示/未完の可能性）。実運用前にファクター計算の完全実装とテストが必要。
- 一部の機能（例: ブローカークライアントの実装、ExecutionEngine 内部の詳細、monitoring_db のスキーマ定義など）はこの変更履歴作成時点のコードスニペットで詳細が確認できないため、実装済み・未実装の判定が困難。実際の運用では該当モジュールを確認してください。

----------

(このファイルはコード内容から推定して作成した CHANGELOG です。正確なリリースノートはコミット履歴 / リリースタグに基づいて生成してください。)