# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。日付・内容は提供されたコードベースから推測して作成しています。

フォーマット:
- Added: 新機能
- Changed: 変更点（互換性に影響する可能性があるもの）
- Fixed: バグ修正
- Removed: 削除事項

## [Unreleased]

（現時点で未リリースの変更はありません）

---

## [0.1.0] - 2026-04-19

初回リリース。自動売買システム KabuSys の基本的なランタイム・ユーティリティ・ポートフォリオ構築・検証ツール群を含みます。

### Added
- コアパッケージ情報
  - パッケージのバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor 用のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔の上書きが可能（デフォルト 60 秒）。
    - 監視は環境設定に依存せず本番の sqlite_path を使用する仕様。
    - プロセス優先度を起動時に "high" に設定。
    - 停止制御にプロジェクト内の `data/stop_requested.flag` を監視。
    - sqlite3 および DuckDB への接続を確立し、監視用 DB の初期化を行う。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper-trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いて実際の/モックのブローカークライアントを生成し、OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動する。
    - プロセス優先度を "high" に設定し、停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）を扱う。
    - スレッドで ExecutionEngine を実行し、停止フラグ検知で安全に停止する制御を実装。

- 設定・環境変数管理
  - config.py
    - .env ファイルの自動読込（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 高度な .env パーサを実装（コメント、クォート、export プレフィックス、エスケープ対応）。
    - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - Settings クラスを実装し、各種環境変数（J-Quants, kabu API, LINE, DB パス, 監視・閾値設定, 実行環境 等）をプロパティとして提供。
    - Paper Trading 用の設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）をサポート。
    - 環境値の検証（有効値チェック、デフォルト値、Bool フラグの扱い等）を行う。

  - config_setup.py（対話式ウィザード）
    - .env の初期作成・更新を対話的に行うウィザードを追加。
    - J-Quants / kabu API / DB パス / ログレベル / KILL_FLAG_CLEAR_ON_START 等の項目を対話入力で設定し .env に書き出す。
    - 既存の .env 読込、シークレット項目のマスク表示、保存の確認を実装。

  - validate_config.py（検証 CLI）
    - .env と config/*.yaml の設定の事前検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、YAML パース（PyYAML があれば）を実施。
    - `--strict` オプションで警告をエラー扱いにする機能を追加。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
    - calc_score_weights はスコア合計が 0 の場合に等金額配分へフォールバックし警告を出力。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を追加（除外銘柄 / unknown セクターの扱い）。
    - 市場レジームに基づく資金乗数 calc_regime_multiplier を追加（bull/neutral/bear とフォールバック挙動）。

  - portfolio/position_sizing.py
    - 発注株数計算 calc_position_sizes を追加。
    - allocation_method="risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）を実装。
    - cost_buffer による手数料・スリッページ考慮、スケーリング後の端数補正アルゴリズムを実装。

  - portfolio/__init__.py で主要関数をエクスポート。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング初期化ユーティリティを追加。
    - stdout へ StreamHandler を出力し、日次ローテートの TimedRotatingFileHandler（デフォルト logs/<app>.log、30日保持）を設定。
    - ログレベル・ログディレクトリの解決順、ディレクトリ作成失敗時のフォールバック（コンソールのみ）を実装。
    - 既存ハンドラをクリアして二重設定を防止。

  - utils/process_priority.py
    - プロセス優先度および CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX (Linux/Mac/FreeBSD) を抽象化して nice / priority クラスを設定。
    - 許容レベル: "high" / "normal" / "low"。権限不足などの例外は警告にフォールバック。
    - set_cpu_affinity による先頭 N コアへの固定をサポート（未指定時は何もしない）。

- モニタリング DB 初期化
  - 複数の起動スクリプトで共通利用する monitoring_db 初期化呼び出しを行う（init_monitoring_db を使用して監視テーブルの存在を保証）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite DB から検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、APIレイテンシ（avg/max/P95）などを算出。
    - デフォルト閾値（稼働率 >= 99%, 成功率 >= 90%, 送信率 >= 95%, P95 <= 200 ms）を定義し PASS/FAIL 判定を出力。
    - 日付範囲フィルタ（--from, --to）、DB パス上書き（--db）をサポート。
    - latency の P95 計算と欠損データの扱いを実装。

- 研究/ファクター計算（草案）
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュールの骨組みを実装（モメンタム、MA200乖離、ATR、流動性等の設計）。
    - 関数 calc_momentum の記述開始（prices_daily テーブル参照）。（実装は途中まで）

### Changed
- より安全なデフォルトと保守性の向上
  - .env の自動ロードはデフォルトで有効だが、テスト時等に無効化できる仕組みを追加（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
  - ロギング設定でログディレクトリ作成失敗時にプロセス継続可能なフォールバックを実装。

### Fixed
- （初回リリースのため該当なし。コード中に例外や不整合が発生した場合はログ警告に落とし込み、安全にフォールバックする実装が多く含まれる。）

### Removed
- （初回リリースのため該当なし）

---

参照:
- 各モジュールのドキュメンテーション文字列とコード内コメントが挙動・設計の詳細を説明しています。README やさらなるリリースノートは今後のリリースで補完してください。