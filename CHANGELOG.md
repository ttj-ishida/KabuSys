# CHANGELOG

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

最新リリース: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-20

最初の公開リリース。日本株自動売買フレームワークの基礎となる機能群を実装しました。

### Added
- 実行・監視エントリポイント
  - run_execution.py: ExecutionEngine を起動するデーモンスクリプトを追加。KABUSYS_ENV に応じて paper_trading 用 DB を分離し、BrokerClientFactory によるブローカ接続、OrderManager / RiskManager / Reconciler の組み立て、エンジンのスレッド実行・停止監視を行う。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能。停止フラグ検知で優雅に終了。
- 設定・環境管理
  - config.py: Settings クラスを導入し、アプリケーション設定を環境変数から安全に取得する機能を実装（各種パス・閾値・Paper Trading 用設定・KABUSYS_ENV 検証など）。
    - 自動 .env 読み込み機能を追加（プロジェクトルート検出 .git / pyproject.toml に基づく）。自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD に対応。
    - .env の読み込みは OS 環境変数を保護（上書き禁止）する仕組みを実装。
    - PAPER_FILL_MODE の検証、paper_sqlite_path 等のプロパティを提供。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを実装。既存値の読み込み、表示マスク（シークレット項目）、保存機能を備える。
  - validate_config.py: 起動前に設定不備を検出する CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DBパスの親ディレクトリ確認、config/*.yaml の存在・パースチェック（PyYAML 未導入時は警告）などを行う。--strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で選定。
    - calc_equal_weights / calc_score_weights: 等重配分・スコア加重配分を実装（スコア全0 の場合は等重にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中を制限するフィルタ。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を提供（bull/neutral/bear をサポート、未知レジームはフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 複数の配分方式（risk_based, equal, score）に基づく発注株数計算。lot_size（単元株）丸め、1銘柄上限・aggregate cap（利用可能現金）調整、cost_buffer（手数料・スリッページ想定）を考慮したスケーリングロジックを実装。
  - portfolio/__init__.py によるエクスポートを整備。
- ユーティリティ
  - utils/logging_setup.py:
    - 標準化されたログ設定ユーティリティを追加。コンソール出力（stdout）と日次ローテートファイル出力（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py:
    - プロセス優先度設定（Windows / POSIX 差分吸収）、CPU affinity 設定ユーティリティを追加。アクセス権限不足や未対応 OS の場合は安全にフォールバック。
- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均 / 最大 / P95）を算出し、基準値との比較結果を PASS/FAIL 形式で出力。--from / --to / --db オプションをサポート。
- 研究用モジュール（骨組み）
  - research/factor_research.py: DuckDB 接続を受けてファクター（Momentum / Value / Volatility / Liquidity）計算を行うための基礎実装を追加（Momentum 関連定数などを定義、関数シグネチャを用意）。※一部実装が継続開発中。

### Fixed
- .env 解析の堅牢化（config._parse_env_line）
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、行内コメントの取り扱い（クォート内を無視）、無効行のスキップを実装して .env の柔軟な記述に対応。
- ログ設定のフォールバック強化
  - ログディレクトリの作成に失敗した場合にファイルハンドラの作成をスキップし、コンソール出力のみで継続するようにした（デーモン環境での起動失敗回避）。

### Changed
- 初回リリースのため該当なし

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

注記:
- 本リリースは「機能的な基盤」を提供する初期バージョンです。Execution / Monitoring / Portfolio / 設定管理 / ロギング等の主要コンポーネントが揃っており、paper_trading（疑似発注）を用いた検証ワークフローが想定されています。  
- research/factor_research.py や一部の内部モジュール（monitoring_db, system_monitor, execution_engine 等の詳細実装）は本リリースで利用可能ですが、引き続き拡張・安定化が必要な箇所があります。