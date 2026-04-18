# CHANGELOG

すべての非互換な変更は大きな見出しで、後方互換の変更や修正は小見出しで記載します。  
フォーマットは "Keep a Changelog" に準拠しています。

全リリース:
- [Unreleased]
- [0.1.0] - 2026-04-18

## [Unreleased]
（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーション基盤を追加
  - パッケージ情報: kabusys パッケージ（__version__ = 0.1.0）。
  - 起動用スクリプト:
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番の sqlite_path を使用。
    - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、ペーパートレード用 DB を使用して本番 DB から分離して実行。
  - CLI ユーティリティ:
    - kabusys.config_setup: .env の対話式ウィザード（初期作成/更新）を提供。
    - kabusys.validate_config: .env および config/*.yaml の事前検証 CLI（--strict オプションで警告を FAIL 扱いに可能）。
    - kabusys.tools.paper_verification_report: ペーパートレード用検証レポート生成スクリプト（期間指定可）。稼働率、注文成功率、送信率、API レイテンシ（P95）などを集計・判定。
  - 設定管理:
    - kabusys.config.Settings: 環境変数読み込みとラッパー。自動でプロジェクトルートの .env/.env.local を読み込む（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。多くの設定プロパティ（DB パス、KABUSYS_ENV、ログレベル、Paper Trading 関連設定等）を提供。
    - .env パーサはクォート付き値のエスケープや inline コメントの扱いに対応。
  - ロギング・プロセス制御ユーティリティ:
    - kabusys.utils.logging_setup.setup_logging: stdout ストリームハンドラ + 日次ローテートするファイルハンドラ (TimedRotatingFileHandler) をルートロガーへ設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - kabusys.utils.process_priority: クロスプラットフォームでプロセス優先度（high/normal/low）および CPU affinity を設定するユーティリティ。アクセス権限により設定失敗した場合は警告でスキップ。
  - DB 接続関連:
    - SQLite と DuckDB の両方を利用する設計を導入（monitoring 用 SQLite、分析用 DuckDB）。
    - ペーパートレード時は paper_sqlite_path により本番 DB と完全に分離する動作をサポート。
  - ポートフォリオ構築モジュール:
    - kabusys.portfolio.portfolio_builder
      - select_candidates: BUY シグナルをスコア降順で選出（タイブレークは signal_rank）。
      - calc_equal_weights: 等金額配分。
      - calc_score_weights: スコア加重配分（スコア合計が 0 の場合は等金額へフォールバック）。
    - kabusys.portfolio.risk_adjustment
      - apply_sector_cap: セクター集中制限を適用し、上限超過セクターの候補を除外（unknown セクターは除外対象外）。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear マップ）を提供。未知レジームは 1.0 にフォールバック。
    - kabusys.portfolio.position_sizing
      - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数計算、単元株（lot_size）丸め、1銘柄上限・総投下上限（aggregate cap）のスケールダウンロジック、コストバッファ考慮、手数料/スリッページを見越した保守的見積もり等を実装。
    - portfolio パッケージは上記関数群をエクスポート。
  - リサーチ・ファクター計算の下地
    - kabusys.research.factor_research: Momentum/Value/Volatility/Liquidity ファクター計算を想定したモジュールの土台。DuckDB 接続を受け prices_daily / raw_financials を参照する設計。モメンタム計算（関数 calc_momentum）の実装開始（ターゲット日ベースの 1M/3M/6M リターン、MA200 乖離等の算出を想定）。
  - 監視・実行の停止・PID 管理
    - run_* スクリプトはプロジェクト内 data/stop_requested.flag 等のフラグファイルを監視し、安全に停止する仕組みを備える。ExecutionEngine は実行スレッドをデーモンで起動し、停止フラグ検知で engine.stop() を呼ぶ。

### Changed
- （初回リリースのため該当なし）

### Fixed
- robust な .env パーシング／読み込み処理を実装
  - export KEY=val 形式、クォート中のバックスラッシュエスケープ、インラインコメントの扱い、既存 OS 環境変数保護（protected）等に対応。
- ログディレクトリ作成失敗時のフォールバック処理を追加（ファイルハンドラ作成に失敗してもコンソールログは維持）。

### Security
- 機密値（J-Quants トークン、kabu API パスワード、LINE トークン等）は .env に保存する前提だが、config_setup の出力ヘッダに「.env を絶対に Git にコミットしないこと」と明示している。

### Notes / Known limitations
- research/factor_research の実装は継続中（モジュールの一部は未完/拡張予定）。
- position_sizing の lot_size は現状全銘柄共通の想定。将来的に銘柄別 lot_map に対応する予定（TODO コメントあり）。
- apply_sector_cap は価格情報が欠損 (0.0) の場合にエクスポージャーを過少評価してしまう可能性があり、将来的にフォールバック価格（前日終値等）の導入を検討中。
- process_priority / set_cpu_affinity は権限やプラットフォーム依存で動作しない場合があり、その際は警告を出してスキップする。

---

開発者向け:
- CLI 実行例:
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - 監視プロセス起動: python -m kabusys.run_monitoring
  - 実行エンジン起動: python -m kabusys.run_execution
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

追加の履歴やリリース日・差分は今後のコミットで更新してください。