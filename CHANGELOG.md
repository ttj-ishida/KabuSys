# CHANGELOG

すべての重大な変更はここに記録します。フォーマットは「Keep a Changelog」に準拠します。  

リリース日付はソースコードから推測した最新開発日（このファイル作成日）を使用しています。

## [Unreleased]

## [0.1.0] - 2026-04-16
初回公開リリース。

### Added
- コア機能
  - kabusys パッケージの初期バージョンを追加（__version__ = 0.1.0）。
  - アプリケーション設定管理（kabusys.config.Settings）を追加。
    - .env / .env.local 自動読み込み（OS 環境変数を優先／保護）。
    - .env ファイルの堅牢なパーサ実装（export 先頭対応、クォート内エスケープ、インラインコメント処理など）。
    - 環境変数の必須チェックと各種検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
- 実行用スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイントを追加。
    - paper_trading 環境時は専用の paper_trading DB（PAPER_TRADING_SQLITE_PATH）/ MockBroker を使用して本番 DB と分離。
    - ExecutionEngine の組み立て（OrderRepository, OrderManager, RiskManager, Reconciler 等）。
    - 停止フラグ（data/stop_requested.flag）によるグレースフルシャットダウン処理。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はフォールバックして警告ログ）。
    - 監視処理は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を利用。
    - 停止フラグでループ終了、KeyboardInterrupt 対応。
- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder: BUY シグナル選別（select_candidates）、等配分/スコア加重（calc_equal_weights, calc_score_weights）。
  - risk_adjustment: セクター集中抑制（apply_sector_cap）、レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - position_sizing: 発注株数算出（calc_position_sizes）。  
    - risk_based / equal / score の配分方式対応。
    - 1 銘柄上限、lot_size 単位丸め、aggregate cap によるスケールダウン、端数配分ロジックを実装。
- リサーチ（kabusys.research）
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 接続を受け取り SQL+ウィンドウ関数で効率良く計算。
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ（calc_forward_returns, calc_ic, factor_summary, rank）。
    - rank は同順位を平均ランクで処理する実装。
    - calc_forward_returns は horizons の入力検査を行う（正値かつ <= 252）。
- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news を OpenAI API（gpt-4o-mini）でセンチメント解析して銘柄ごとの ai_score を生成・書き込みするロジックを追加。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）定義と計算ユーティリティ（calc_news_window）。
    - 記事集約、トークン肥大対策（記事数・文字数上限）、最大 20 銘柄ずつのバッチ送信、JSON Mode を前提としたレスポンス検証。
    - リトライ（429/ネットワーク/5xx）に対する指数バックオフ、スコア ±1.0 にクリップ、部分失敗時のテーブル保護（該当コードのみ置換）等のフェイルセーフ設計。
- ツール
  - tools/paper_verification_report: Paper Trading 検証レポート生成ツールを追加（CLI: python -m kabusys.tools.paper_verification_report）。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を計算して標準出力へレポート出力。
    - 日付フィルタ（--from / --to）対応、DB 存在チェック、各クエリの OperationalError を捕捉してフェイルセーフに動作。
    - 判定基準（閾値）と PASS/FAIL 判定ロジックを実装（コメントに閾値定義あり）。
- ユーティリティ
  - utils.process_priority: クロスプラットフォームでプロセス優先度・CPU affinity を設定するユーティリティを追加（set_process_priority, set_cpu_affinity）。
    - Windows / POSIX（Linux, macOS, FreeBSD）対応、権限不足等は警告ログでフォールバック。
- データベース
  - SQLite / DuckDB の接続を受けるコードを各所に追加。init_monitoring_db を呼んで監視テーブルの存在を保証する設計。
- logging
  - 起動時に INFO レベルで basicConfig をセットするスクリプト多数（run_*）。

### Changed
- なし（初回公開のため特段の互換破壊変更は無し）。ただし、実装上の挙動・設計上の注意点を以下に記載します（運用時の留意点）。
  - run_monitoring は KABUSYS_ENV にかかわらず「本番用 sqlite_path」を使用する設計になっているため、監視データが paper_trading 用 DB に記録されない点に注意。
  - .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされる（.git または pyproject.toml を探索）。テスト環境等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定。

### Fixed
- なし（初回公開）。コード内に環境値の検証・例外処理・ログ出力を多く含め、実運用での失敗を抑える設計を行っています（例: MONITOR_POLL_INTERVAL の不正値フォールバック、DuckDB/SQLite の OperationalError 捕捉等）。

### Deprecated
- なし

### Removed
- なし

### Security
- OpenAI API キーは引数優先 → 環境変数 OPENAI_API_KEY を参照する形で扱い、未設定時は明示的に ValueError を送出して処理を中断する設計。  
  （API キーの保護は運用上の注意事項）

---

補足（実装上の注記・既知の改善点）
- position_sizing.calc_position_sizes: price 欠損時の挙動に関して TODO コメントあり（前日終値や取得原価等のフォールバックを将来検討）。
- risk_adjustment.apply_sector_cap: "unknown" セクターは上限チェック対象外にしている設計上の判断を採用。
- news_nlp.score_news: 長い実装分の途中でソースが途切れている箇所が見られるため、実装の残り（記事集約フェーズの続きなど）が必要になる可能性がある（リポジトリ内の未完部分は今後補完予定）。
- DuckDB の executemany に関する注意（コメント記載あり）：パラメータが空だとエラーになるため事前チェックを行うこと。

[0.1.0]: https://example.com/compare/v0.0.0...v0.1.0

（注）上記は提供されたソースコードの内容から推測して作成した CHANGELOG です。実際のコミット履歴やリリースノートがある場合はそれに合わせて修正してください。