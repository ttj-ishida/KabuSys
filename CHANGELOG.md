CHANGELOG
=========

すべての重要な変更は "Keep a Changelog" のフォーマットに従って記載しています。  
このプロジェクトはセマンティックバージョニングを使用します。

[Unreleased]
------------

- （現時点のコードベースは初回公開相当の状態として 0.1.0 にまとめています。今後の変更はここに記載してください。）

[0.1.0] - 2026-04-18
--------------------

Added
- 初版リリース。
- 環境設定・読み込み機能を追加
  - .env 自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - .env パーサ（export 付き行、クォート、エスケープ、行内コメントの扱いに対応）。
  - Settings クラスを追加し、環境変数から各種設定を取得するラッパーを提供（DBパス、APIトークン、ログレベル、環境判定、paper_trading 用設定など）。
- 対話式設定ウィザード（config_setup.py）
  - .env の初期作成・更新を支援する CLI を追加。既存値の再利用、シークレットのマスク表示、保存確認などに対応。
- 設定検証ツール（validate_config.py）
  - 必須/任意環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検証、DBパスや config/*.yaml の存在チェック、`--strict` オプション。
  - PyYAML 未導入時は YAML 検証をスキップして警告出力。
- 実行系・監視用エントリスクリプトを追加
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を利用し、MockBroker を想定して本番 DB と分離。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。
- ロギング・プロセス制御ユーティリティを追加
  - utils.logging_setup: コンソール（stdout）と日次ローテーションファイルハンドラをルートロガーへ設定。ログディレクトリ作成失敗時のフォールバック対応。
  - utils.process_priority: psutil を用いたプロセス優先度設定（Windows / POSIX の差分吸収）、CPU affinity 設定ユーティリティ。
- ポートフォリオ構築ライブラリを追加（pure functions）
  - portfolio.portfolio_builder: 候補選定（スコア降順）と等金額／スコア加重の重み計算。
  - portfolio.risk_adjustment: セクター上限適用ロジック、レジーム乗数（bull/neutral/bear）算出。
  - portfolio.position_sizing: 発注株数計算（risk_based / equal / score）、単元株丸め、aggregate cap によるスケールダウン実装。
- Paper Trading 検証レポート（tools.paper_verification_report）
  - paper_trading DB から稼働率、注文成功率、送信率、レイテンシ指標（平均/最大/P95）を算出して標準出力にレポート出力。期間フィルタ、閾値判定を内蔵。
- research.factor_research（骨格）を追加
  - DuckDB を利用したファクター計算モジュールの骨格（モメンタム等の計算を想定）。
- パッケージメタ情報
  - __version__ = "0.1.0" を設定。

Changed
- .env 読み込み優先順を明確化
  - OS 環境変数 > .env.local > .env の順で解決。既存の OS 環境変数は保護される（protected）。
- run_execution の DB 接続
  - paper_trading モード時は paper_sqlite_path を使用して本番 DB と論理的に分離。
- run_monitoring の DB 接続
  - 監視（monitoring）は環境にかかわらず本番用 sqlite_path を使用する設計に明示。
- ロギングの既存ハンドラ処理
  - setup_logging は既存ハンドラを一旦 flush/close してから削除・再設定し、二重出力の防止を図る。
- ログ出力先
  - コンソール出力は stdout を使用（stderr ではなく）。cron などのリダイレクト運用を想定。
- process_priority の堅牢化
  - psutil の Windows 固有定数が存在しない環境でのフォールバック、アクセス権限がない場合の警告で失敗をスキップ。
- paper_verification_report のエラー耐性
  - テーブルが存在しない場合（sqlite3.OperationalError）でも安全に N/A を表示するフォールバック実装。

Fixed
- 環境変数値の検証とデフォルトフォールバック
  - MONITOR_POLL_INTERVAL のパースで無効値（非整数や 0 以下）を検知した場合、警告ログを出してデフォルト（60 秒）にフォールバックするよう修正。
  - Settings.paper_fill_mode の許容値チェックを追加し、無効値時に明確な ValueError を送出。
  - Settings.env / log_level の妥当性チェックを強化（無効値で ValueError）。
- .env パーサの改善
  - クォートされた値内のバックスラッシュエスケープ処理、閉じクォートの検出、インラインコメントの扱いを改善。
  - export KEY=val 形式への対応を追加。
- 設定検証ツール（validate_config）
  - 必須環境変数がプレースホルダ値のままの場合に警告を出すように変更。
  - 本番環境用ガード（LINE トークン未設定、KILL_FLAG_CLEAR_ON_START=1 の危険性）を追加。
- portfolio ロジックの安定化
  - calc_score_weights: 全銘柄のスコア合計が 0 の場合に等金額配分へフォールバックし警告を出すように修正。
  - calc_regime_multiplier: 未知のレジーム値に対して 1.0 フォールバックおよび警告を追加。
  - calc_position_sizes: 価格データ欠損時（None または <=0）に該当銘柄をスキップする安全策を追加。aggregate cap のスケールダウン時に remainder を考慮して単元株（lot_size）単位で追加配分するロジックを実装して過剰切り捨てを緩和。
  - apply_sector_cap: "unknown" セクターはセクター上限適用対象外とし、売却予定銘柄を露出計算から除外する対応を追加。
- utils.logging_setup の堅牢化
  - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで稼働し続けるように修正。失敗時は標準エラーに警告を出力。
- run_execution / run_monitoring の停止フラグ挙動を明確化
  - 起動時に停止フラグが既に存在する場合の早期終了処理を追加。実行中は定期的に停止フラグを監視して graceful shutdown を行う。

Security
- .env ファイルの取り扱いに関する注意書きを config_setup の出力に追加（.env を Git にコミットしないことを明示）。

Notes / Known limitations
- research.factor_research はモジュールの骨格が含まれているが、完全な実装（SQL クエリの最終化など）は残っています。
- 一部の外部依存（psutil、duckdb、PyYAML）が環境にない場合、該当機能は限定的に動作するか警告を出してフォールバックします。
- 単元株（lot_size）は現状全銘柄共通の固定値（デフォルト 100）で運用を想定。将来的に銘柄別の単元対応を検討。

----------

この CHANGELOG はコードの内容から推測して作成しています。実際のコミット履歴や変更履歴が存在する場合は、その履歴に基づいて差分を反映することを推奨します。