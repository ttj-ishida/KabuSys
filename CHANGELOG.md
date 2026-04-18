# CHANGELOG

すべての変更は Keep a Changelog のガイドラインに準拠して記載しています。  
主にコードベースの最初の公開リリース相当の変更を、ソースコードから推測してまとめています。

なお、本ファイルはコード内容から推測した変更点を記載しており、実際のコミット履歴とは差異がある可能性があります。

---

## [Unreleased]

### Added
- プロジェクト全体の初期実装を追加
  - パッケージバージョン: `kabusys.__version__ = 0.1.0`

- 環境設定・設定管理
  - Settings クラスを実装して環境変数から各種設定を取得可能に（J-Quants / kabu API / DB パス / 監視閾値など）。
  - .env 自動ロード機能を実装（プロジェクトルート検出: .git / pyproject.toml を探索）。`.env` と `.env.local` の読み込み順をサポートし、OS 環境変数を保護する仕組みを導入。
  - .env パース機能を強化（export プレフィックス対応、シングル/ダブルクォート中のエスケープ、インラインコメント処理）。

- 環境設定ウィザード CLI
  - `kabusys.config_setup` に対話式ウィザードを実装。`.env` の初期作成・更新を支援。
  - 主要設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）をインタラクティブに入力・保存可能。
  - `.env` の読み込み・書き込みロジックを提供（既存値の再利用・シークレットマスク表示等）。

- 設定検証 CLI
  - `kabusys.validate_config` に設定検証ツールを実装。必須環境変数の確認、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パース検査（PyYAML があれば内容検証）を行う。
  - `--strict` オプションで警告もエラー扱いにできる。

- 起動スクリプト
  - `run_execution.py`
    - ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、SQLite / DuckDB 接続、BrokerClientFactory 経由のブローカークライアント構築、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、エンジンのスレッド実行と停止フラグ検知を実装。
    - `KABUSYS_ENV=paper_trading` 時は paper_trading 専用 SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と完全分離する挙動を導入。
    - 起動時に停止フラグが立っている場合は起動を中止する安全措置。
  - `run_monitoring.py`
    - SystemMonitor を定期ポーリングで実行するスクリプトを追加。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可能。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を利用する設計（監視は常に本番データを対象とする想定）。
    - 停止フラグ検知、例外捕捉、プロセス優先度設定、接続クローズ処理を実装。

- ロギング・プロセス運用ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`
    - コンソール（stdout）と日次ローテーションされるファイル出力（TimedRotatingFileHandler）をルートロガーに設定するユーティリティ。
    - LOG_DIR / LOG_LEVEL の優先順位解決、ログディレクトリ自動作成、既存ハンドラのクリア処理を実装。
  - `kabusys.utils.process_priority`
    - プラットフォーム差分を吸収したプロセス優先度設定（Windows の priority class / POSIX の nice 値を設定）と、CPU affinity 設定ユーティリティを提供。
    - アクセス許可や未対応環境向けに失敗時は警告でスキップする堅牢性を実装。

- ポートフォリオ構築ロジック（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - シグナル選定（score 降順、signal_rank によるタイブレーク）、等金額配分、スコア加重配分（スコア全て 0 の場合は等金額にフォールバック）を実装。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限を適用する apply_sector_cap を実装（当日売却予定銘柄の除外、"unknown" セクターは上限適用しない）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピング、未知レジームは警告して 1.0 フォールバック）。
  - `kabusys.portfolio.position_sizing`
    - allocation_method（"risk_based" / "equal" / "score"）に基づく株数決定ロジックを実装。
    - 単元株（lot_size）丸め、銘柄上限・アグリゲート上限（available_cash）に対するスケーリング、cost_buffer を考慮した保守的見積り、スケール時の優先配分ロジックを導入。
    - 価格欠損時のスキップやログ出力を含む堅牢化。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report`
    - Paper Trading の SQLite DB（デフォルト `data/paper_trading.db`）から期間指定で検証レポートを生成する CLI を実装。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、API レイテンシ（avg/max/P95）などを集計。
    - Pass/Fail 基準（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200 ms）を実装し、判定結果を出力。
    - CLI 引数 `--from`, `--to`, `--db` をサポート。

- 研究用ファクタ計算（初期実装）
  - `kabusys.research.factor_research` にモメンタム等のファクター計算モジュールを追加（設計方針、定義・定数、calc_momentum の実装開始）。DuckDB 接続を受け prices_daily / raw_financials を参照する設計。

### Changed
- DB 初期化の冪等化を保証
  - 監視・実行起動時に init_monitoring_db を呼び、監視テーブルの存在を担保する（存在しても問題ないように冪等で初期化）。

### Fixed
- 環境変数読み込みの堅牢化
  - .env パーサーでクォート中のエスケープやインラインコメントの扱いを改善し、より多様な .env 記述に耐えるように修正。
- ログディレクトリ作成失敗時の挙動を改善
  - 作成失敗時はファイルハンドラをスキップし、コンソール出力のみで継続するようにして起動失敗を回避。

### Notes / Known issues
- research.calc_momentum の実装は途中（ソースコード末尾が中断）であり、ファクター計算の完全実装は未完。
- 一部 TODO コメント（例: position_sizing の価格フォールバックや銘柄別 lot_size 対応）が残る。
- 本番環境（KABUSYS_ENV=live）での運用時は `validate_config` による事前検証を強く推奨。特に LINE 通知設定や KILL フラグの自動クリア設定には注意。

---

## [0.1.0] - 2026-04-18

Initial public release（上記 Unreleased の内容をリリース相当として固定）。

- 上記の Added / Changed / Fixed をこのバージョンに含む。

---

セマンティックバージョン管理 (SemVer) を想定しています。リリースに合わせてこの CHANGELOG を更新してください。