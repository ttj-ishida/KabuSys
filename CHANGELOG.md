# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。重要な変更点・追加機能を日本語で記載しています。

全般的な注意:
- 本リリースはパッケージバージョン 0.1.0（src/kabusys/__init__.py の __version__）に対応します。
- リリース日: 2026-04-17

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-17

### Added
- 基本ランタイム / 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、MockBrokerClient を利用して本番 DB と分離。
    - 実行中の停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を扱うロジックを実装。スレッドでエンジンを起動し、停止フラグ検知で安全停止。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告。
    - 監視 DB は環境にかかわらず本番の sqlite_path を使用（監視は本番 DB を参照する設計）。
    - 停止フラグ検知でループを終了、例外はロギングして次ポーリングへ継続。

- 設定・環境管理
  - config.py:
    - .env 自動ロード機能を追加（プロジェクトルート検出に .git / pyproject.toml を使用）。OS 環境変数を保護して上書きを制御。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - Settings クラスを提供し、環境変数から各種設定を取得するユーティリティを実装（DB パス、PID ファイルパス、監視閾値、env/log_level 判定、paper_trading 関連など）。
    - PAPER_FILL_MODE のバリデーション（"instant" | "partial" | "never" | "reject"）と PAPER_TRADING_SQLITE_PATH デフォルトを追加。
  - config_setup.py:
    - 対話式 .env 作成/更新ウィザードを追加。
    - 項目定義（KABUSYS_ENV / JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / DB パス / LINE トークン等）と .env 書き込みロジックを実装。
    - 既存値の読み込み・マスク表示、保存確認、.env に注意書き（Git にコミットしない）を出力。

- 設定検証ツール
  - validate_config.py:
    - .env と config/*.yaml の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ存在チェック、YAML のパースチェック（PyYAML が無い場合は警告）、本番環境向けの追加ガードを実装。
    - --strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順、同点は signal_rank 昇順で上位 N を選定。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア正規化による加重配分。全スコアが 0 の場合は等配分へフォールバックし警告。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクターごとの既存保有比率が上限（デフォルト 30%）を超える場合、同セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは 1.0 にフォールバックして警告。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた買付株数決定ロジックを実装。
      - risk_based: risk_pct, stop_loss_pct を用いたリスクベース算出。
      - equal/score: 重みと max_utilization を使った配分。
      - lot_size 単位で丸め、1 銘柄上限（max_position_pct）や aggregate cap（available_cash）を考慮してスケーリング。cost_buffer を使った保守的コスト見積りと残差処理も実装。

- 研究 / ファクター計算
  - research/factor_research.py:
    - DuckDB 接続を受け取り、prices_daily / raw_financials を基にファクターを計算するユーティリティを追加。
    - momentum（1M/3M/6M リターン、MA200 乖離）と volatility（ATR20、相対 ATR、20 日平均売買代金、出来高比）の計算関数を実装。データ不足時の None 返却、集計ウィンドウとスキャン幅を定義。

- 運用ツール
  - tools/paper_verification_report.py:
    - ペーパートレード実行結果に対する検証レポート生成スクリプトを追加。
    - DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）からシステム安定性、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計し、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL を判定して出力。
    - 日付フィルタ（--from/--to）と --db オプションをサポート。

- ユーティリティ
  - utils/process_priority.py:
    - プロセス優先度設定ユーティリティを追加。Windows と POSIX（Linux, Darwin, FreeBSD）に対応し、psutil を使用して nice / priority を設定。設定失敗時は警告を出してスキップ。
    - set_cpu_affinity: 指定コア数での CPU affinity 設定（失敗時は警告）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

---

補足:
- 仕様・設計の注記は各モジュール内の docstring に記載されています（例: PortfolioConstruction.md / StrategyModel.md 参照箇所の注記）。
- .env の取り扱い・秘密情報の管理（シークレット項目のマスク、.env を Git にコミットしない注意など）に留意してください。