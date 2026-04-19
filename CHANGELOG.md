# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。慣例としてバージョンごとに主要な追加・変更・修正点を記載しています。

全般的注意
- このリリースはパッケージバージョン 0.1.0 に対応します（src/kabusys/__init__.py の __version__）。
- 日付は本 CHANGELOG 作成日付です。

## [0.1.0] - 2026-04-19

### Added
- 基本アプリケーションと CLI
  - パッケージ初期リリース。モジュール群と実行用スクリプトを追加。
  - 実行スクリプト:
    - run_execution.py — ExecutionEngine 起動スクリプト。KABUSYS_ENV に応じて paper_trading 用の分離 DB を使用し、MockBrokerClient を利用する挙動をサポート。PID ファイル（data/execution.pid）と停止フラグ（data/stop_requested.flag）を用いた安全停止を実装。
    - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番用 sqlite_path を使用する仕様。
  - 管理用 CLI:
    - config_setup.py — .env を対話的に作成/更新するウィザード。
    - validate_config.py — .env と config/*.yaml の起動前検証ツール（--strict オプションあり）。
    - tools.paper_verification_report — Paper Trading 用の検証レポート生成スクリプト（期間指定、DB パス指定可能）。

- 設定・環境読み込み
  - config.py: 環境変数/ .env 自動ロード機構を追加（プロジェクトルート検出 .git / pyproject.toml 基準）。.env/.env.local の読み込み順序を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード抑止対応。
  - .env パーサ: export プレフィックス・クォート文字列（シングル/ダブル）のエスケープ、インラインコメントの扱い、無効行スキップ等に対応する堅牢なパース実装を追加。
  - Settings クラス: 各種設定プロパティを提供（J-Quants, kabu API, DB パス, PID/kill flag, しきい値、環境/ログレベル判定、paper_trading 関連設定など）。PAPER_FILL_MODE 等のバリデーション実装。

- ログ・プロセス管理ユーティリティ
  - utils/logging_setup.py: ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30世代保持）を設定する共通セットアップを追加。ログディレクトリ作成失敗時はファイル出力を安全にスキップ。
  - utils/process_priority.py: Windows/Linux/Mac の差分を吸収するプロセス優先度設定（high/normal/low）と CPU affinity 設定ユーティリティを追加。権限不足等の失敗は警告でスキップ。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で選択。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分の計算（スコア全 0 の場合のフォールバック警告あり）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: 同一セクターの集中上限チェック（unknown セクターは除外しない）。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear とフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に対応した株数算出。単元株（lot_size）で丸め、1 銘柄上限・aggregate cap（利用可能現金）超過時のスケーリング、cost_buffer（手数料・スリッページ見積り）反映、再配分ロジック（端数処理）を実装。

- 研究用ファクター計算
  - research/factor_research.py: DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 等のファクター計算を行う設計を追加（prices_daily, raw_financials テーブル参照、日数定数・ウィンドウの定義を含む）。（注: モジュール内に未完の実装箇所あり）

- Paper Trading 周り
  - ExecutionEngine 側で paper_trading 環境を想定した専用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）使用を実装。監視テーブルは init_monitoring_db で冪等に初期化。
  - tools.paper_verification_report.py: Paper Trading の稼働率・注文成功率・送信率・レイテンシ（P95 など）を集計・判定するレポート生成器。閾値（稼働率 99%、fill_rate 90%、send_rate 95%、P95 latency 200ms）を定義。

### Changed
- ログ出力の標準化
  - 全起動スクリプトが utils.logging_setup.setup_logging を呼び出すことでログフォーマット・ファイル出力が統一された。

- DB 接続ポリシー
  - run_monitoring は環境にかかわらず本番用 sqlite_path を使用する仕様を明示（運用上の意図的決定）。
  - run_execution は paper_trading 時に専用 SQLite を使用して本番 DB と完全に分離する設計に変更。

### Fixed
- .env ファイル読み書きの堅牢化
  - config_setup の読み込み/書き込み処理を実装し、既存値のマスク表示や秘密項目の扱いを整備。読み込み時に export プレフィックスや引用符を適切に扱うようにした。

### Security
- 機密情報の取り扱い
  - config_setup の対話ウィザードでシークレット項目をマスク表示。README/注意文で .env を Git にコミットしない旨を明示。

### Notes / Implementation details
- 停止フラグ機構:
  - data/stop_requested.flag を監視して安全に監視ループ・エンジンを停止する実装（run_monitoring / run_execution 共通）。
- validate_config:
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス親ディレクトリ存在チェック、config/*.yaml の存在・YAML パース検証（PyYAML が無ければ警告）等を行う。
- いくつかのモジュールには今後の改善余地や TODO コメントあり（例: price の欠損時のフォールバック、銘柄別単元拡張、research モジュールの未完実装など）。

---

今後の予定（例）
- research/factor_research の完成（ファクター計算の SQL 実装完了）
- ExecutionEngine / BrokerClient の統合テスト・エンドツーエンド検証
- 単体テストと CI の整備、型チェックの強化

（以上）