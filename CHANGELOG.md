# Changelog

すべての重要な変更はここに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

## [Unreleased]
- 今後の変更点をここに記載します。

## [0.1.0] - 2026-04-23
初回リリース（ベース機能実装）

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 設定管理
  - 環境変数・.env 読み込み/管理を行う `kabusys.config.Settings` を実装。
    - 自動 .env ロード（プロジェクトルート検出: .git / pyproject.toml）を行う。無効化は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
    - 必須/オプションの環境変数、デフォルト値、型変換、検証（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE など）をサポート。
    - 本番・ペーパートレード判定 (`is_live`, `is_paper`, `is_dev`) と各種パス（DuckDB, SQLite, PID ファイル等）取得を提供。

- 起動スクリプト / 実行系
  - ExecutionEngine 起動スクリプト `run_execution.py`
    - `KABUSYS_ENV=paper_trading` のときは専用の paper trading SQLite を使用し、本番 DB と分離（`PAPER_TRADING_SQLITE_PATH`）。
    - ブローカークライアント作成ファクトリ、OrderRepository/OrderManager/RiskManager/Reconciler 等の組み立てとエンジン起動を実装。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止、PID ファイル管理、スレッドでのエンジン実行を実装。
    - RiskManager のデフォルト設定（例: max_position_pct, max_utilization, rate_limit_per_sec 等）。
  - SystemMonitor 起動スクリプト `run_monitoring.py`
    - 環境にかかわらず監視は本番用 sqlite_path を使用（監視 DB は常に本番 DB パスで初期化）。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可（デフォルト 60 秒）。不正値は警告してデフォルトを使用。
    - 停止フラグ検知、例外発生時のログとリカバリを実装。

- 設定・検証ツール
  - 対話式 .env 作成・更新ウィザード `config_setup.py`
    - 対話で主要環境変数を入力して `.env` を生成。
    - シークレット項目はマスク表示、デフォルト表示、キャンセル処理などに対応。
  - 設定検証 CLI `validate_config.py`
    - .env と config/*.yaml の検証ロジックを備え、必須環境変数のチェック、パスの存在チェック、YAML パース（PyYAML が無ければスキップ）、本番時の追加ガード（LINE 通知設定等）を実装。
    - `--strict` オプションで警告を FAIL 扱いに可能。

- ロギングユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテート、30 日保管）を設定。
    - ログレベル/ログディレクトリは引数、環境変数、デフォルトの優先順位で解決。
    - ファイルハンドラ作成失敗時はコンソール出力のみで継続。

- プロセス優先度 / CPU affinity
  - `kabusys.utils.process_priority`
    - Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収してプロセス優先度を設定（"high" / "normal" / "low"）。
    - CPU affinity を最初の N コアに固定する機能を提供。
    - 権限不足や未対応 OS の場合は警告して安全にスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定 `select_candidates`（スコア降順、同点は signal_rank 順でブレーク）
    - 重み計算 `calc_equal_weights`, `calc_score_weights`（スコア合計が 0 の場合は等金額にフォールバック）
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限 `apply_sector_cap`（既存保有比率が閾値を超えるセクターの新規候補除外）
    - レジーム乗数 `calc_regime_multiplier`（bull/neutral/bear に対応、未知値は警告して 1.0 フォールバック）
  - `kabusys.portfolio.position_sizing`
    - 発注株数算出 `calc_position_sizes`
      - allocation_method: "risk_based"（リスクベース） / "equal" / "score" をサポート
      - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）に基づくスケーリング、cost_buffer（手数料・スリッページ見積り）考慮
      - 価格未取得時のスキップ、現保有との差分のみ発注候補算出

- リサーチ / ファクター計算（基盤）
  - `kabusys.research.factor_research`（モメンタム / MA / ATR / ボラティリティ等の計算を想定）
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを算出する設計。
    - P95 等の統計計算ユーティリティや期間バッファ設定を含む（実装の一部が含まれる）。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report`
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から統計を抽出してレポート生成。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を計算し PASS/FAIL 判定を行う。
    - 日付フィルタ、DB パス指定オプション、閾値による合否判定を実装。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Notes / 動作上の留意点
- 監視（monitoring）は環境にかかわらず監視用の sqlite_path（デフォルト: data/monitoring.db）を使用します。開発環境での混在を避けるため、本番監視 DB を別途管理してください。
- ExecutionEngine は paper_trading 環境時に専用の paper_trading DB（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離します。
- .env ファイルには機密情報が含まれるため、絶対に Git 等にコミットしないでください（config_setup にも注記あり）。
- process_priority / cpu_affinity の設定は OS と権限に依存します。権限不足時は警告が出て処理は継続します。

---

この CHANGELOG はコードベースの内容から推測して作成しています。将来的なリリースでは実際の変更差分に基づいて適宜更新してください。