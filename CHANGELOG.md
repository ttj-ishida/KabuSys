# Changelog

すべての注目すべき変更は Keep a Changelog の方針に従って記載しています。  
日付は本リリース時点のタイムスタンプ（2026-04-24）です。将来的に追記する際は Unreleased セクションを使用してください。

## [Unreleased]

（今後の変更・予定をここに記載）

---

## [0.1.0] - 2026-04-24

初回公開リリース。自動売買システム KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、検証ツール群を含みます。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI ランチャーを追加。
    - KABUSYS_ENV=paper_trading 時は専用 paper DB（data/paper_trading.db、環境変数で上書き可）や MockBrokerClient を使用する挙動を導入。
    - 起動時にプロセス優先度を high に設定。
    - 停止制御用の stop flag（data/stop_requested.flag）および execution.pid を利用したプロセス管理を実装。
    - スレッドでエンジンを実行し、停止フラグ検知で優雅に停止するループを実装。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き対応（デフォルト 60 秒、入力検証とフォールバックあり）。
    - 監視データは環境に関わらず本番 sqlite_path を使用する（監視用 DB 初期化を行う）。
    - 停止フラグ検知・KeyboardInterrupt ハンドリング・例外時のログ出力を実装。

- 設定管理・初期化
  - config.py
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env/.env.local の読み込み順序、OS 環境変数の保護（上書き禁止）を実装。
    - 複数の設定プロパティを提供（J-Quants / kabu API / DB パス / paper trading 関連 / 監視閾値 / ログレベル / 環境判定など）。
    - PAPER_FILL_MODE の妥当性検証や各種閾値のデフォルト値を用意。
    - Settings クラスとグローバル settings インスタンスを追加。

  - config_setup.py
    - 対話式 .env 作成ウィザードを追加。既存 .env 読み込み、シークレットマスク表示、デフォルト値・選択肢をサポート。
    - .env の書き出しテンプレートを提供（Git に取り込まないよう注意喚起行を含む）。

  - validate_config.py
    - 起動前検証 CLI を追加（必須環境変数の存在確認、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ確認、config/*.yaml の存在と YAML パース検査）。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。コンソール(stdout)出力と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の優先解決、ハンドラ二重設定防止、ログディレクトリ作成失敗時のフォールバックを実装。

  - utils/process_priority.py
    - プラットフォームを吸収したプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を実装。
    - Windows / POSIX（Linux, macOS, FreeBSD）での差分処理、psutil 利用、アクセス権限や未サポート OS のフォールバックロジックを備える。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。
    - スコアが全て 0 の場合は等配分にフォールバックする警告挙動を実装。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（既存保有を考慮したセクター別時価計算、売却予定銘柄の除外対応、"unknown" セクターの扱い）。
    - 市場レジームに基づく投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をサポート、未知レジームはフォールバックと警告）。

  - portfolio/position_sizing.py
    - 銘柄ごとの発注株数計算 calc_position_sizes を実装。
    - allocation_method による risk_based / equal / score に対応。
    - リスクベース計算、1 銘柄上限(max_position_pct)、利用可能現金に応じた aggregate cap スケーリング、単元株(lot_size)丸め、手数料・スリッページ考慮用 cost_buffer、残余配分の再配分ロジックを実装。
    - 価格欠損時のスキップやログ出力を実装。

- 研究系 / ファクター計算（下地）
  - research/factor_research.py
    - モメンタム等のファクター計算モジュールのスケルトンを追加（Momentum, Value, Volatility, Liquidity を想定）。
    - DuckDB 接続を受け、prices_daily / raw_financials テーブルから計算する設計。モジュールは純粋関数形式で、外部 API には依存しない。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率(uptime)、注文成功率(fill rate)、送信率(send rate)、P95 レイテンシなどを集計し PASS/FAIL を判定する基準を実装（閾値はソース内で定義、デフォルト可変）。
    - 日付フィルタ (--from / --to) や --db オプション、DB 存在チェック、NULL/例外耐性を備える。
    - P95 計算ユーティリティを実装。

- パッケージメタ
  - __init__.py にてバージョンを "0.1.0" として設定。

### Changed
- ドキュメント/コメントの充実
  - 各モジュールに詳細な docstring と設計上の注釈（PortfolioConstruction.md 等への参照）を追加し、使い方や想定挙動を明確化。
- ログ出力の統一
  - すべての起動スクリプトから setup_logging を呼び出す設計により、ログ運用が統一された。

### Fixed
- 環境変数パーサの堅牢化
  - config._parse_env_line でシングル/ダブルクォート、エスケープ、inline コメントの取り扱いを改善。export プレフィックスに対応。

### Known issues / Notes
- research/factor_research.py は実装の骨格があり、calc_momentum の実装が一部未完／拡張が想定されています（将来的に全ファクター計算を実装予定）。
- 一部の挙動は実行環境（psutil 権限、ファイルシステム権限、環境変数の設定状況）に依存します。特にプロセス優先度設定やログディレクトリ作成は権限不足でスキップされる可能性がありますが、安全にフォールバックする実装になっています。
- 実運用時は validate_config と config_setup を用いて設定を確認・整備のうえ、KABUSYS_ENV や KILL_FLAG_CLEAR_ON_START 等の値を慎重に設定してください（validate_config は本番向けの注意喚起を行います）。

### Security
- 本リリースにおけるセキュリティ関連の特記事項はありません。機密値（API トークン・パスワード）は .env に保存する設計のため、.env をリポジトリに含めない運用を強く推奨します（config_setup にも注意書きを追加）。

---

著者: KabuSys 開発チーム
（この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴に基づく差分は別途 Git の履歴を参照してください。）