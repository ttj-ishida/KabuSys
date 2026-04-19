# Changelog

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-19
初回リリース。日本株自動売買システム「KabuSys」の基盤機能を追加しました。

### Added
- パッケージエントリポイント / バージョン
  - パッケージメタ情報を追加（src/kabusys/__init__.py, __version__ = "0.1.0"）。

- 起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV による paper_trading と本番の切替。
    - paper_trading 時は専用 SQLite（data/paper_trading.db）に記録して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、ExecutionEngine をスレッドで実行、停止フラグ（data/stop_requested.flag）に対応。
  - 監視（Monitoring）起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を制御（デフォルト 60 秒）。
    - 停止フラグ検知、監視用 DB 初期化、SystemMonitor の単一ポーリング check_once() 実行ループを提供。

- 設定管理
  - robust な .env ロードと設定取得を実装（src/kabusys/config.py）。
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）に基づく .env 自動ロード（.env → .env.local）。
    - export 形式やクォート／コメントを考慮した .env パーサを実装。
    - Settings クラスで環境変数をラップ（各種パス、KABUSYS_ENV 検証、PAPER_FILL_MODE 検証、各種閾値、フラグ等）。
    - 環境変数自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

- 設定操作・検証用 CLI
  - 環境設定ウィザードを追加（src/kabusys/config_setup.py）。
    - 対話式に .env を生成・更新、既存値の再利用、シークレットのマスク表示、保存確認。
  - 設定検証ツールを追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DUCKDB/SQLITE パスの親ディレクトリチェック、config/*.yaml の存在と（PyYAML があれば）パース検証。
    - --strict モード（警告も失敗扱い）をサポート。

- ロギング / プロセス制御ユーティリティ
  - ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - ルートロガーに stdout 出力の StreamHandler と日次ローテーション（TimedRotatingFileHandler）を設定。
    - ログディレクトリ自動作成、作成失敗時はファイル出力を無効化して stdout のみで継続。
    - ログレベル / ログディレクトリ解決ルールを実装（引数 > 環境変数 > デフォルト）。
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX 系を吸収して set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
    - psutil を利用、権限不足等は警告ログでフォールバック。

- ポートフォリオ構築関連（純関数群）
  - 候補選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: score 降順・タイブレークルール実装。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重（スコア合計 0 の場合はフォールバック）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有からセクター別エクスポージャ算出、上限超過セクターの新規候補除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: "bull"/"neutral"/"bear" に対応する乗数（デフォルトフォールバックと警告）。
  - 株数決定・リスク制限（src/kabusys/portfolio/position_sizing.py）
    - allocation_method: "risk_based" / "equal" / "score" に対応。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウン、コストバッファ考慮、残差分配ロジックを実装。

- 分析 / レポートツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を算出。
    - 判定閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義して PASS/FAIL を出力。
    - コマンドライン引数で期間指定（--from/--to）および DB パス (--db) を受け付け。

- リサーチ（ファクター計算）の骨組み
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - モメンタム関連定数と calc_momentum の記述（prices_daily テーブルを想定）。モジュールは DuckDB 接続を受ける設計。

- その他
  - 空のパッケージ初期化ファイルを追加（src/kabusys/tools/__init__.py、src/kabusys/utils/__init__.py）。

### Changed
- なし（初回リリースのため既存変更はなし）

### Fixed
- なし（初回リリースのためバグ修正履歴はなし）

### Security
- なし

備考:
- 各コンポーネントは可能な限り本番 DB とペーパートレード DB を分離するよう設計されています（例: paper_trading 用 SQLite）。
- プラットフォーム差異（Windows / Linux / macOS）や権限不足ケースに対しては安全にフォールバックする実装が多く含まれています（ログディレクトリ作成失敗、プロセス優先度設定失敗等）。
- 将来的な拡張点や TODO コメント（例: position_sizing の銘柄別 lot_size、risk_adjustment の価格フォールバック）はソース内に記載しています。

[0.1.0]: https://example.com/project/releases/tag/v0.1.0  (リンクは必要に応じて差し替えてください)