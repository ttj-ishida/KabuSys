CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」（https://keepachangelog.com/ja/1.0.0/）に準拠しています。

リリース日付はソースコードから推測して付与しています。実際のリリース運用に合わせて日付やバージョンを調整してください。

Unreleased
----------

（今後の変更をここに記載）

0.1.0 — 2026-04-19
------------------

Added
- 基本機能の初期実装（日本株自動売買システム「KabuSys」 v0.1.0 相当）
  - 実行用スクリプト
    - run_execution.py: ExecutionEngine を起動するエントリポイントを提供。環境に応じて
      - 本番/開発: 設定された SQLite / DuckDB を使用
      - ペーパートレード (KABUSYS_ENV=paper_trading): MockBrokerClient を使用し、data/paper_trading.db に完全分離して記録
    - run_monitoring.py: SystemMonitor のポーリングループを実行するエントリポイントを提供。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。
  - 設定管理
    - config.py: .env 自動読み込み（プロジェクトルート検出）・環境変数ラッパー Settings を実装。多数の設定プロパティ（DB パス、API トークン、しきい値など）を提供。
    - config_setup.py: 対話式 .env 作成/更新ウィザードを実装（秘密値マスク、選択肢、既存 .env の再利用対応）。
    - validate_config.py: 起動前チェック CLI を実装。必須環境変数の確認、KABUSYS_ENV やログレベルの妥当性チェック、config/*.yaml の存在・パース検証（PyYAML 未導入時はスキップ）、本番環境向けガードチェックなど。--strict オプションあり。
  - ポートフォリオ関連（純関数）
    - portfolio/portfolio_builder.py: 候補選定（スコア降順、タイブレーク）、等金額配分、スコア重み配分（全スコアが 0 の際は等金額にフォールバック）。
    - portfolio/risk_adjustment.py: セクター集中制限（既存保有比率に基づく候補除外）、市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。
    - portfolio/position_sizing.py: 発注株数算出ロジック（risk_based/equal/score）、単元株丸め、ポートフォリオ集約キャップによるスケーリングと残余分配ロジックを実装。手数料・スリッページのバッファ（cost_buffer）考慮。
  - 研究・ファクター計算（基盤）
    - research/factor_research.py: DuckDB 接続経由でモメンタム等のファクターを計算する骨格を実装（価格テーブル参照、P/R変換に関する定数等を定義）。（注: ソースは途中まで）
  - ツール
    - tools/paper_verification_report.py: ペーパートレード DB を解析して検証レポートを生成。稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを集計し、閾値（稼働率 99% など）に基づいて PASS/FAIL 判定を出力。日付フィルタ、--db オプション対応。
  - ユーティリティ
    - utils/logging_setup.py: 統一ログ設定ユーティリティ。stdout ストリームハンドラと日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - utils/process_priority.py: クロスプラットフォームでのプロセス優先度設定（Windows の priority class、POSIX の nice 値）、および CPU affinity 設定。権限や未サポート環境で安全にフォールバック。
  - 監視 DB 初期化 API（モジュール）を提供（monitoring/monitoring_db.py 参照呼び出しあり）。
  - パッケージ情報: __init__.py にバージョン指定 __version__ = "0.1.0"。

Changed
- 環境変数の読み込み挙動
  - 自動ロード順を OS 環境 > .env.local > .env として実装。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサーは export プレフィックス、引用符付き文字列のエスケープ、インラインコメント判定（クォート無し時の '#' は直前が空白/タブの場合にコメント）など、より堅牢な解析を行う。
- デフォルトパス
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視用): data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db（paper_trading 環境では専用 DB を使用）
- ログ出力
  - デフォルトで stdout（StreamHandler）を使用し、ファイルは logs/<app_name>.log に日次ローテーション（30 日保持）。ログディレクトリ作成失敗時にはファイルハンドラをスキップして警告出力。

Fixed
- 環境変数パースの不整合や空行・コメント処理の不具合に対応。引用符内のバックスラッシュエスケープを正しく取り扱うよう改善。
- monitor のポーリング間隔取得で不正値（0 や負値、非整数）が指定された場合に time.sleep に渡してクラッシュする問題を回避。無効時はデフォルト（60 秒）にフォールバックして警告を出力。
- process_priority や set_cpu_affinity が権限不足や未サポート環境で例外により停止する可能性をハンドリング。警告ログを残して処理を継続。
- apply_sector_cap / calc_score_weights / calc_regime_multiplier などでのフォールバックロジックを追加し、未知値やデータ欠損時に安全に動作するように改善（ログ出力で診断可能）。
- position_sizing の集約キャップ処理において、スケーリング後の単元株丸めと残余の配分処理（fractional remainders に基づく追加配分）を実装し、利用可能現金に収まるようにした。
- paper_verification_report の P95 計算と欠損値処理を強化。DB スキーマが存在しない場合でも例外を捕捉してレポート生成を続行可能。

Security
- 機密値（J-Quants トークン / kabu API パスワード / LINE トークン）は .env に保存する運用を想定。config_setup の説明に「.env を絶対に Git にコミットしないこと」を明示。

Performance
- run_execution / run_monitoring 起動時にプロセス優先度を "high" に設定することで、実行の安定性を改善（プラットフォームや権限により効果は異なる）。

Breaking Changes
- 監視（run_monitoring）は KABUSYS_ENV にかかわらず「本番用の sqlite_path」を使用する挙動が明示的に実装されています。ペーパートレードと監視 DB を分離したい場合は設定（SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）を確認してください。
- paper_trading 環境では ExecutionEngine が専用の PAPER_TRADING_SQLITE_PATH を使用するため、従来の単一 DB 前提の運用からは分離設計となります。

Notes / Implementation choices
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml による検出）を基準に行うため、CWD に依存せずパッケージ配布後も動作する設計。
- logging_setup は stdout を用いる設計（cron 等で stdout/stderr をまとめてリダイレクトする運用に配慮）。
- calc_regime_multiplier は未知のレジーム値に対して警告を出し 1.0 でフォールバック（安全側のデフォルト）。
- まだ未実装/途中の箇所（例: research/factor_research の一部）は存在し、今後の拡張を想定。

Acknowledgements
- 本 CHANGELOG はソースコードの実装内容から推測して作成しています。実際のコミット履歴・リリースノートとは差分がある可能性があります。実リリース時は Git のコミットメッセージや PR を基に正確な履歴を更新してください。