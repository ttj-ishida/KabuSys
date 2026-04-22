# CHANGELOG

すべての重要な変更点は Keep a Changelog の形式で記載しています。  
リリースの内容はコードベースから推測して記載しています。

全般的な注意
- 本 CHANGELOG はリポジトリ内のソースコード（src/kabusys 以下）を元に推測して作成しています。実際のコミット履歴とは異なる場合があります。

## [0.1.0] - 2026-04-22

### Added
- パッケージ初期リリースとして以下の機能・モジュールを追加。
  - 実行スクリプト
    - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。  
      - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
      - 起動時にプロセス優先度を "high" に設定し、PID ファイル・停止フラグを用いた安全停止をサポート。
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。  
      - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト: 60 秒）。  
      - 監視は環境にかかわらず本番 sqlite_path を使用する設計（監視 DB は常に production DB を参照）。
  - 設定・環境管理
    - config.Settings クラスを追加し、環境変数（.env/.env.local の自動読み込み含む）から設定を取得する仕組みを実装。
      - 自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行う。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - 各種設定プロパティを定義（J-Quants、kabu API、LINE、DuckDB/SQLite パス、Paper Trading の挙動、監視閾値、ログレベルなど）。
      - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, KILL_FLAG_CLEAR_ON_START などの環境変数をサポート。
    - config_setup: 対話式ウィザード（python -m kabusys.config_setup）で .env の作成・更新を支援する CLI を追加。
      - 入力補助、既存 .env の読み込み、シークレット値のマスク表示、保存前確認を実装。
      - .env 生成時にセクション化されたテンプレートを書き出す。
    - validate_config: 起動前の設定検証 CLI（python -m kabusys.validate_config）を追加。
      - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベルの検証、DB パスの親ディレクトリチェック、config/*.yaml の存在・パースチェック（PyYAML 未導入時は警告）などを実施。
      - --strict オプションで警告も失敗として扱える。
  - ロギング・プロセス管理ユーティリティ
    - utils.logging_setup.setup_logging を追加。
      - stdout 出力の StreamHandler と、日次ローテート（TimedRotatingFileHandler, 30 日保持）のファイルハンドラをルートロガーに設定。
      - ログレベル / ログディレクトリの解決順序を定義（引数 > 環境変数 > デフォルト）。
      - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - utils.process_priority によりプラットフォーム差を吸収したプロセス優先度設定と CPU affinity 設定を提供。
      - Windows / POSIX(Linux/Mac/FreeBSD) に対応する nice/HIGH_PRIORITY_CLASS のマッピング、アクセス権限エラー時のフォールバック動作を実装。
  - ポートフォリオ構築ライブラリ（pure functions）
    - portfolio.portfolio_builder: 候補選定と重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
      - calc_score_weights は全スコアが 0 の場合に等金額配分にフォールバックし警告を出す。
    - portfolio.risk_adjustment: セクター集中制限 (apply_sector_cap) とレジーム乗数 (calc_regime_multiplier) の実装。
      - apply_sector_cap は既存保有と売却予定銘柄を考慮し、"unknown" セクターは制限の対象外とする。
      - calc_regime_multiplier は "bull"/"neutral"/"bear" をマップし、未知のレジームは 1.0 でフォールバック。
    - portfolio.position_sizing: 発注株数計算（calc_position_sizes）を実装。
      - risk_based / equal / score の配分方式をサポート。
      - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金に収めるスケーリング）、コストバッファ考慮、端数配分ロジックを実装。
  - 研究用モジュール
    - research.factor_research: ファクター計算の骨格を追加（モメンタム、MA200、ATR、流動性などを計画）。DuckDB 経由で prices_daily / raw_financials を参照する設計。
  - ツール類
    - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。
      - デフォルト DB は data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH / --db で上書き可）。
      - 指標: 稼働率 (uptime_pct)、注文成功率 (fill_rate)、送信率 (send_rate)、P95 レイテンシなどを算出し、PASS/FAIL 判定を行う。しきい値はソース内定数で定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。
      - 日付フィルタ (--from / --to) をサポート。
  - パッケージメタ
    - __version__ を "0.1.0" に設定。

### Changed
- ログ出力は stdout を既定の StreamHandler に使用（stderr ではない）。
  - cron / 外部スケジューラで stdout/stderr を一本化して扱う運用を想定。
- .env 自動読み込みの挙動を明示
  - 読み込み順序: OS 環境変数 > .env.local > .env。既存 OS 環境変数は保護される（上書き不可）。
  - .env のパースはクォート、export プレフィックス、インラインコメント、エスケープシーケンスに対応する堅牢な実装を採用。

### Fixed
- 起動スクリプトの資源クリーンアップを確実化
  - run_monitoring/run_execution で例外や KeyboardInterrupt 発生時に SQLite/DuckDB コネクションを確実に close するように実装。

### Deprecated
- なし（初回リリースのため該当なし）

### Removed
- なし（初回リリースのため該当なし）

### Security
- .env ファイルは絶対に Git にコミットしない旨を config_setup のテンプレートで強調（ツール側で注意喚起を追加）。

---

補足（実装上の注意点・設計意図）
- run_monitoring は監視 DB に対して「環境にかかわらず本番 sqlite_path を使用する」設計で、監視データの一元化を図っています。一方 run_execution は paper_trading 環境では専用 DB を使用し発注履歴を分離します。
- process_priority 設定や CPU affinity は権限や OS に依存するため、失敗した場合は警告を出して安全にフォールバックします。
- portfolio/position_sizing の aggregate スケーリングや lot_size 単位の丸め処理は、実際の注文実行時に過不足が出ないよう慎重に設計されていますが、価格欠損や lot_size の銘柄別違いに対する TODO コメントが残されています。
- research.factor_research はファクター計算の方針と一部実装を含みますが、ファイルの末尾に未完成の箇所（スニペット切れ）が見られます。将来的に完全実装が必要です。

もし特定の変更点をより詳細にしたい、あるいはリリースノートの英語版を作成したい場合は教えてください。