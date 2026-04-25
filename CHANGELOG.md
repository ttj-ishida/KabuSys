# CHANGELOG

すべての注記は Keep a Changelog の形式に準拠します。  
このファイルはコードベースの内容から推測して作成しています。実際のコミット履歴と差異がある場合があります。

## [Unreleased]

- なし（最新の公開バージョンは 0.1.0）

## [0.1.0] - 2026-04-25

Initial release — 日本株自動売買システム「KabuSys」の初期実装を追加。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
- 起動スクリプト / デーモン
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番用の sqlite_path を使用する設計。
    - 停止フラグファイル（data/stop_requested.flag）検知による安全停止をサポート。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper_trading 専用 DB（data/paper_trading.db）に分離して動作。
    - エンジン停止用の停止フラグと PID ファイル管理を実装。
- 設定管理
  - `kabusys.config.Settings`: 環境変数 / .env ファイルからの設定読み込みと検証用プロパティ群を追加。
    - DB パス、LINE 通知設定、監視閾値、ログレベル、環境種別（development/paper_trading/live）などをサポート。
    - `PAPER_FILL_MODE` などの制約チェックを実装（有効値チェック）。
  - 自動 .env 読み込み機能を追加
    - プロジェクトルート (.git または pyproject.toml を基準) を探査して `.env` / `.env.local` を自動読み込み。`KABUSYS_DISABLE_AUTO_ENV_LOAD` による無効化が可能。
  - 対話式設定ウィザード (`kabusys.config_setup`) を追加
    - `.env` の初期作成・更新支援、既存値の読み込み・マスク表示、保存機能を持つ。
- 設定検証ツール
  - `kabusys.validate_config` CLI を追加
    - 必須環境変数チェック、KABUSYS_ENV・LOG_LEVEL 等の妥当性チェック、DB パス親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML があれば中身も検証）。
    - `--strict` オプションで警告も失敗扱いにできる。
- ロギング / 実行環境ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`
    - stdout への StreamHandler（stdout を採用）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップ。
  - `kabusys.utils.process_priority`
    - Windows/Linux/macOS の差分を吸収するプロセス優先度設定、CPU affinity 設定ユーティリティを追加。`set_process_priority("high")` 等で優先度変更を試行する。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選別（score 降順 / tie-breaker）`select_candidates`
    - 等配分 `calc_equal_weights`
    - スコア正規化配分 `calc_score_weights`（全スコア 0 の場合は等配分にフォールバック）
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限 `apply_sector_cap`（既存ポジションのセクター暴露を計算し上限超過セクターの候補を除外）
    - レジームに応じた資金乗数 `calc_regime_multiplier`（bull/neutral/bear のマッピング）
  - `kabusys.portfolio.position_sizing`
    - `calc_position_sizes`：等配分 / スコア配分 / リスクベース配分に基づく株数計算、単元株丸め、aggregate cap によるスケーリングと端数調整ロジックを実装
  - `kabusys.portfolio.__init__` で主要関数を公開
- Paper Trading / 検証ツール
  - `kabusys.tools.paper_verification_report`
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から統計を集計して検証レポートを出力。
    - 指標：稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg/max/P95）など。閾値（P95 <= 200ms 等）による PASS/FAIL 判定。
    - 日付レンジフィルタ、PAPER_TRADING_SQLITE_PATH / --db オプション対応。
- データ / 研究基盤
  - `kabusys.research.factor_research` の下地を追加（モメンタム / Value / Volatility / Liquidity 計算に着手）
    - DuckDB を用いた prices_daily / raw_financials 参照の方針、モメンタム計算（関数シグネチャ）等を設計。実装途中（ファイル末尾で切れている）。
- DB 初期化
  - 監視テーブル等を保証する `monitoring.monitoring_db.init_monitoring_db` を起動スクリプトから呼び出す実装を追加（冪等動作を想定）。

### Changed
- ログ出力設計
  - stdout を優先する設計へ（cron 等での取り回しを考慮）。
  - 既存ハンドラは再設定時に flush/close 後削除することで二重登録を防止。
- 環境ファイル読み込みの挙動
  - `.env` のパース処理でシングル/ダブルクォート内のエスケープ、コメント扱い（クォート外かつ直前に空白がある場合のみ）を明示的に処理するように改良。
  - `.env.local` を `.env` より優先して上書き（OS 環境変数は保護される）。

### Fixed
- 環境変数パースにおけるいくつかのコーナーケースの扱いを改善
  - export 形式（export KEY=val）を受け入れるようにした。
  - 空行・コメント行の無視やキーが空の行のスキップなどの堅牢化。
- ポジション計算で単元株丸めや aggregate スケールダウン時の端数配分ロジックを実装して、利用可能現金を超過しないように修正。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

## 既知の制限 / 注意点（推測）
- config.auto-load はプロジェクトルート検出に依存するため、配布後にプロジェクトルートが見つからない環境では自動読み込みがスキップされる。
- `PAPER_FILL_MODE` は限定された値のみ受け付ける（instant/partial/never/reject）。無効値は起動時例外になる。
- `calc_position_sizes` の価格フォールバック未実装コメントあり（price が 0 の場合にエクスポージャーが過小評価される可能性）。
- research.factor_research の実装は途中（モメンタム計算の途中で切れている）。完全な計算は今後のコミットが必要。
- 一部の外部モジュール（psutil、duckdb、PyYAML など）に依存。環境により動作差異やインストールが必要。

---

参考: 主な CLI / エントリポイント
- python -m kabusys.run_monitoring
- python -m kabusys.run_execution
- python -m kabusys.validate_config [--strict]
- python -m kabusys.config_setup
- python -m kabusys.tools.paper_verification_report [--from DATE --to DATE --db PATH]

（以上）