# Changelog

すべての notable な変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に従います。

## [Unreleased]

## [0.1.0] - 2026-04-18
最初のリリース。KabuSys コア機能の初期実装を追加。

### Added
- パッケージ基盤
  - パッケージバージョンを `__version__ = "0.1.0"` として追加（src/kabusys/__init__.py）。
  - 公開モジュール一覧に主要サブパッケージを追加（data, strategy, execution, monitoring）。

- 実行スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - プロセス優先度を "high" に設定して起動。
    - KABUSYS_ENV が `paper_trading` の場合、paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）に分離して動作（MockBrokerClient の使用を想定）。
    - 停止フラグ (data/stop_requested.flag) の検知で安全に停止。
    - エンジン PID ファイル管理（data/execution.pid）。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視（monitoring）は環境にかかわらず本番の sqlite_path を使用する仕様。
    - 停止フラグファイル検知でループ終了。例外はログに記録して次サイクルへフォールバック。

- 設定管理
  - Settings クラスを追加（src/kabusys/config.py）。
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env パースは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントに対応。
    - 各種プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / env/log_level 判定 等）。
    - `paper_fill_mode` の検証（許容値: instant/partial/never/reject）。
    - `is_live` / `is_paper` / `is_dev` などの利便性プロパティ。
  - 設定ウィザード CLI（.env 生成）を追加（src/kabusys/config_setup.py）。
    - インタラクティブな対話式ウィザードで .env を生成/更新。
    - シークレット項目はマスク表示、選択肢・デフォルトのサポート、保存確認フローを実装。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検査、DB パスの親ディレクトリチェック、config/*.yaml の存在およびパース検証（PyYAML 利用可否考慮）。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ロギング/プロセス制御ユーティリティ
  - ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。
    - ログディレクトリ自動作成、作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベルとログディレクトリは引数 / 環境変数 / デフォルトの優先順位で決定。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX（Linux, macOS, FreeBSD）双方に対応するnice / priority 設定を行うラッパー。
    - set_process_priority(level: "high" | "normal" | "low")、set_cpu_affinity(cpu_count) を提供。
    - 権限不足等で失敗した場合は警告して継続。

- Portfolio（銘柄選定・配分・サイズ計算）
  - portfolio_builder: 候補選定・重み計算を追加（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates（スコア降順, tie-breaker: signal_rank）。
    - calc_equal_weights（等分配）、calc_score_weights（スコア比率配分、全スコアが 0 の場合は等分配にフォールバック）。
  - risk_adjustment: セクターキャップ適用・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap: 既存保有を基にセクター過集中を検出し新規候補を除外（"unknown" セクターは無視）。
    - calc_regime_multiplier: regime ("bull"/"neutral"/"bear") に応じた投下資金乗数を返す（未知時は 1.0 を返し警告）。
  - position_sizing: 株数算出ロジックを追加（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method に応じた計算 ("risk_based", "equal", "score")。
    - lot_size（単元株）で丸め、1 銘柄上限・aggregate cap（available_cash）でスケールダウン、cost_buffer を考慮。
    - risk_based は risk_pct / stop_loss_pct に基づくサイズ計算。
  - portfolio パッケージエクスポートを追加（src/kabusys/portfolio/__init__.py）。

- リサーチ/ファクター計算
  - ファクター計算モジュールの骨格を追加（src/kabusys/research/factor_research.py）。
    - Momentum / Value / Volatility / Liquidity を計画（DuckDB 経由で prices_daily / raw_financials を参照する設計）。
    - calc_momentum の実装開始（注: ファイル末尾で計算処理が途中の状態）。

- ツール
  - Paper Trading 用検証レポート生成 CLI を追加（src/kabusys/tools/paper_verification_report.py）。
    - PAPER_TRADING_SQLITE_PATH（または --db）からデータを読込、稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを計算してレポート出力。
    - Pass/Fail の閾値を定義（稼働率 99%、fill_rate 90%、send_rate 95%、P95 レイテンシ 200ms）。
    - SQL の存在チェックや OperationalError に耐性を持たせた実装。

- その他
  - tools パッケージ初期化ファイルを追加（src/kabusys/tools/__init__.py）。
  - utils パッケージ初期化ファイルを追加（src/kabusys/utils/__init__.py）。

### Changed
- （初回リリースのため変更点はありません）

### Fixed
- （初回リリースのため修正点はありません）

### Notes / Implementation details（実装上の注記）
- run_monitoring は Monitoring 用 DB 初期化を行い、duckdb 接続も確立する設計。monitor.check_once() の例外はログに残して次サイクルへ継続する。
- config の .env パーサは export 文やクォート、バックスラッシュエスケープ、インラインコメントを細かく扱う実装となっており、実運用での .env フォーマット差分に強い設計。
- position_sizing の aggregate スケールダウンは fractional remainder を用いて再配分するため、丸めの再現性（安定ソートキーとして code を併用）に配慮している。
- process_priority / logging_setup はエラー時にフォールバックして動作を続ける設計（権限やファイル作成失敗で致命的にならない）。

今後の予定（例）
- factor_research 内の各ファクター計算を完成させる（Value, Volatility, Liquidity 等）。
- ExecutionEngine / BrokerClient 実装の拡充とエンドツーエンドの統合テスト。
- 単体テスト・CI の整備、config/*.yaml のスキーマ検証追加。

[0.1.0]: 0.1.0 - 2026-04-18