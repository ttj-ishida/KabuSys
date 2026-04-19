# Changelog

All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠します。  

なお、本内容はソースコードから推測して作成しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-19

### Added
- 実行スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視用 DB の一貫性確保）。
    - 停止フラグ（data/stop_requested.flag）検知による安全終了対応。
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を用いて paper_trading 専用 DB（data/paper_trading.db）に記録し、本番 DB と分離。  
    - 起動時にプロセス優先度を "high" に設定。停止フラグでエンジンを安全に停止する仕組みを実装。  
    - 実行 PID ファイル出力 (data/execution.pid) をサポート。

- 設定・環境変数管理
  - config.py: Settings クラスを追加し、環境変数から各種設定値を取得。  
    - 自動 .env ロード機能（プロジェクトルート検出: .git / pyproject.toml を基準）。  
    - .env と .env.local の読み込み順と上書きルールを実装（OS 環境変数は保護）。  
    - 各種プロパティ: J-Quants / kabuAPI / DB パス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）/ PID・Kill フラグパス / リソース閾値 / PAPER_FILL_MODE 等を提供。  
    - 簡易バリデーション（列挙値チェック）を実装。

- 設定ユーティリティ CLI
  - config_setup.py: 対話式 .env ウィザードを追加。  
    - 各設定項目の説明表示、既存 .env 読み込み、保存機能を提供。  
    - .env テンプレートの出力フォーマットを提供（.env を Git にコミットしない旨の注記を含む）。
  - validate_config.py: 起動前検証 CLI を追加。  
    - 必須環境変数の確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在・パース検証（PyYAML 利用時）。  
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。  
    - ルートロガーの既存ハンドラをクリアして二重出力を防止。  
    - StreamHandler (stdout) と TimedRotatingFileHandler（1日ローテート・30世代保持）を設定。  
    - LOG_DIR / LOG_LEVEL の解決順やファイルハンドラ作成失敗時のフォールバックを実装。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度・CPU affinity 設定ユーティリティを追加。  
    - Windows / POSIX (Linux/macOS/FreeBSD) に対応。nice 値や Windows 優先度クラスを適切に設定し、アクセス権限不足時は警告を出して続行。  
    - set_cpu_affinity() による CPU ピンニング機能を提供。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py: 候補選定と重み計算（等金額・スコア加重）を実装。
    - select_candidates(): スコア降順・タイブレークに signal_rank を使用。
    - calc_equal_weights(), calc_score_weights(): スコア合計が 0 の場合のフォールバックを警告付きで実装。
  - portfolio/risk_adjustment.py: セクター集中制限・レジーム乗数を実装。
    - apply_sector_cap(): 既存保有のセクター別エクスポージャを計算し、上限超過セクターの新規候補を除外（"unknown" セクターは除外しない）。sell_codes を考慮して当日売却予定銘柄をエクスポージャ計算から除外可能。  
    - calc_regime_multiplier(): "bull"/"neutral"/"bear" に対する乗数を返す（未知レジームはロギングのうえ 1.0 にフォールバック）。
  - portfolio/position_sizing.py: 株数決定ロジックを実装。  
    - allocation_method: "risk_based" / "equal" / "score" をサポート。  
    - risk_based ではリスク許容率 (risk_pct) と損切り率 (stop_loss_pct) に基づく計算を行う。  
    - per-position 上限 (max_position_pct)、aggregate cap（available_cash）を考慮し、lot_size（単元株）で丸めるロジックを実装。  
    - cost_buffer を用いた保守的なコスト見積り、スケーリング時の端数処理（残余キャッシュでの追加割当て）を実装。  
    - 将来的に銘柄別 lot_size をサポートするための TODO を明記。

- 解析・研究用モジュール
  - research/factor_research.py: ファクター計算モジュールの骨格を追加。  
    - Momentum / Value / Volatility / Liquidity の計画と定数を定義（MA・ATR・期間等）。  
    - DuckDB 接続を受け取る設計。calc_momentum の実装開始（ファイル末尾で未完の箇所あり、以降の実装は継続予定）。

- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。  
    - データベース (SQLite) から各種指標（稼働率・注文成功率・送信率・P95 レイテンシ・リスク却下数）を集計して判定（PASS/FAIL）を出力。  
    - CLI オプション --from / --to / --db をサポート。環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを指定可能。  
    - 判定基準（閾値）を定数として定義（稼働率 99% / 成立率 90% / 送信率 95% / P95 <= 200 ms）。

- パッケージ基礎
  - __init__.py: パッケージバージョンを 0.1.0 として定義。portfolio モジュールをパッケージ API としてエクスポート。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / Implementation details
- .env 解析はシェル風の簡易仕様をサポート（export プレフィックス、シングル/ダブルクォートのエスケープ処理、行内コメントを扱うルールなど）。既存の OS 環境変数は保護され、.env.local での上書きが可能。
- logging_setup は stdout を利用する設計になっており、cron / task scheduler での出力リダイレクト運用を考慮。
- process_priority, set_cpu_affinity は権限不足や未対応 OS を想定して例外を捕捉し、フォールバックログ出力で継続するように実装。
- research/factor_research.py の calc_momentum 実装は途中で終わっているため、以降のファクター計算（Value / Volatility / Liquidity）や完全実装は今後の作業。

## 既知の制約 / TODO
- factor_research.py の実装継続が必要（現在 calc_momentum の途中まで）。  
- position_sizing: 銘柄別単元（lot_size）の拡張、前日終値等の価格フォールバック処理は TODO。  
- monitoring は常に本番 sqlite_path を使用する仕様のため、開発/テストでの分離が必要な場合は運用手順を検討してください。

-------------------------------------------------------------------
この CHANGELOG はコードベースからの推測に基づき作成されています。実際の変更履歴やリリースノートはプロジェクトのコミットログ・リリース時の記録に基づいて更新してください。