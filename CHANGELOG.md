# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

※以下はソースコードから推測して作成した初回リリース相当の変更履歴です。

## [Unreleased]

- （現時点の作業中・未リリースの変更はここに記載）

## [0.1.0] - 初回公開（推定）
リリース日: 未設定

### Added
- 基本アプリケーションパッケージ kabusys を追加
  - バージョン情報: __version__ = 0.1.0

- 実行用エントリポイント
  - run_execution.py
    - ExecutionEngine の起動スクリプトを提供。スレッドでエンジンを実行し、data/execution.pid に PID を管理。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory により環境に応じたブローカークライアントを生成（paper_trading では Mock を利用想定）。
    - RiskManager / OrderManager / Reconciler の初期化と組み立てを行う。
    - 停止フラグ（data/stop_requested.flag）検知でグレースフルに停止。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を設定可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する挙動を採用。
    - プロセス優先度を high に設定して起動。

- 設定管理・ユーティリティ
  - config.py
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）。
    - .env / .env.local の読み込み順と上書きルール（OS 環境変数保護）。
    - 強力な .env 行パーサ（export プレフィックス、引用符、エスケープ、インラインコメントの取り扱い対応）。
    - Settings クラスで環境変数アクセスをラップ（検証付きプロパティ群: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, pid/kill フラグパス, スレッショルド値, KABUSYS_ENV 値チェック等）。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新する CLI を提供。
    - 入力補助、既存 .env の読み込み・既存値再利用、シークレット項目のマスク表示、最終確認・保存機能を実装。

  - validate_config.py
    - 起動前チェック CLI を提供（必須環境変数、KABUSYS_ENV 検証、ログレベル検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、本番時のガード項目など）。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定する共通ユーティリティ。
    - LOG_LEVEL / LOG_DIR / 引数による上書き対応。ログディレクトリ作成失敗時はファイル出力をスキップするフェールセーフ。
  - utils/process_priority.py
    - Windows / POSIX（Linux, macOS, FreeBSD）向けにプロセス優先度設定を抽象化（high/normal/low）。
    - CPU affinity 設定関数も提供（最初の N コアに固定）。権限や未対応環境では安全にスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルの候補選定（スコア降順、同点は signal_rank でブレーク）、等配分・スコア加重配分関数を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用（既存ポジションのセクター露出計算、上限超過セクターの候補除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（"bull","neutral","bear" とフォールバック）。
  - portfolio/position_sizing.py
    - position size 計算ロジック（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的見積り。

- 研究系モジュール（分析用）
  - research/factor_research.py（ファクター計算の骨組みを実装）
    - Momentum / Value / Volatility / Liquidity 等の計算を行う設計（DuckDB の prices_daily / raw_financials を参照する想定）。
    - 主要定数（期間、スキャン範囲等）を定義。モメンタム計算関数の実装を開始。

- 運用ツール
  - tools/paper_verification_report.py
    - ペーパートレード DB（PAPER_TRADING_SQLITE_PATH）から検証レポートを生成する CLI。
    - 指標: システム稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ 等を算出し PASS/FAIL 判定を出力。
    - P95 計算関数、期間フィルタ、欠損時のフォールバックを実装。

- パッケージエクスポート
  - portfolio モジュールの主要関数を __init__.py で公開（select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier）。

### Changed
- （初回リリースのため変更履歴なし）

### Fixed
- （初回リリースのため修正履歴なし）

### Known issues / Notes
- run_monitoring は「監視は環境にかかわらず本番 sqlite_path を使用する」旨の設計。paper_trading などで監視 DB を分離したい場合は設定での対応が必要。
- position_sizing の _max_per_stock 計算は price が欠損（0 や None）の場合 0 を返す。将来は前日終値等のフォールバック価格を導入する予定（TODO コメントあり）。
- research/factor_research.py はファイル末尾が未完（実装途中で切れている）ため、完全実装は今後の作業が必要。
- .env 自動ロードはプロジェクトルートの検出に依存する。特殊配置や配布後に自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD フラグを用意。

---

もし差分をさらに細かく分けたい、リリース日・著者情報を付けたい、あるいは未実装部分（research モジュールなど）を「Known issues」としてより明確に記載したい場合はお知らせください。