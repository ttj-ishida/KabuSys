# CHANGELOG

すべての変更は Keep a Changelog 規約に従って記載しています。  
期間表記はリポジトリ内の実装状況から推測して作成しています。

## [Unreleased]

### Added
- 実装作業中 / 要確認
  - news_nlp.score_news の処理途中でファイルが切れているため、OpenAI API によるニューススコアリングの詳細な書き込み処理・エラーハンドリングはまだ完成していない可能性があります（src/kabusys/ai/news_nlp.py）。
  - position_sizing の将来的改良点（銘柄ごとの lot_size を取り扱う拡張など）が TODO コメントとして残されています（src/kabusys/portfolio/position_sizing.py）。

### Known issues
- news_nlp モジュールが途中で切れているため、実行時エラーや未完成ロジックが残る可能性があります。
- 一部の TODO コメント（価格フォールバック等）は未実装のため、データ欠損時の挙動に注意が必要です。

---

## [0.1.0] - 2026-04-16

### Added
- 基本パッケージ初期リリース（KabuSys 0.1.0）
  - パッケージバージョンを定義（src/kabusys/__init__.py: __version__ = "0.1.0"）。

- 実行/監視用エントリポイント
  - run_execution: ExecutionEngine の起動スクリプトを実装。環境に応じて paper_trading 用 DB 分離や MockBrokerClient の利用を想定（src/kabusys/run_execution.py）。
    - paper_trading 環境では paper_sqlite_path を使用して本番 DB と完全分離。
    - エンジンはスレッドで実行し、プロセス間停止フラグ（data/stop_requested.flag）を監視して安全に停止可能。
    - 実行中 PID を data/execution.pid に記録する想定（pid_file 経由）。
    - RiskManager 初期設定（デフォルト値）を組み込み、初期ポートフォリオ値を broker.get_available_cash() で取得。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを実装（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する点を明示。
    - 停止フラグの検出、例外発生時のログ出力を実装。

- 設定管理モジュール
  - Settings クラスを実装し、環境変数・.env ファイルの読み込みと検証を担当（src/kabusys/config.py）。
    - プロジェクトルートを .git / pyproject.toml から自動検出して .env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env ファイルのパースは export 付き、クォート内のバックスラッシュエスケープ、インラインコメント処理などに対応。
    - 必須環境変数未設定時は明確なエラーを投げる _require() を実装。
    - 各種パスや閾値、環境名（development/paper_trading/live）やログレベルの検証を実装。
    - PAPER_FILL_MODE に対する値検証（instant/partial/never/reject）。

- モニタリング DB 初期化連携
  - init_monitoring_db を使用して監視用テーブルの存在を冪等に保証（呼び出し箇所: run_monitoring/run_execution）。

- Tools
  - paper_verification_report: Paper Trading 検証レポート生成ツールを実装（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出して標準出力へレポート化。
    - デフォルト DB パスは data/paper_trading.db、コマンドラインで --from/--to/--db によるフィルタが可能。
    - 基準値（稼働率 99%、成功率 90%、送信率 95%、P95 200ms）を定義し PASS/FAIL 判定を行う。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio_builder:
    - select_candidates: BUY シグナルのソート/選択ロジック（スコア降順、signal_rank によるタイブレーク）（src/kabusys/portfolio/portfolio_builder.py）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（スコア合計が 0 の場合は等金額フォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中度に基づく候補除外ロジック（売却予定銘柄の除外や "unknown" セクター扱いの挙動を明示）（src/kabusys/portfolio/risk_adjustment.py）。
    - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に応じた投下資金乗数（デフォルトのマッピングと未知レジーム時のフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に対応した株数算出ロジック、単元株丸め、per-stock 上限・aggregate cap によるスケーリング、残差を考慮した追加配分アルゴリズムを実装（src/kabusys/portfolio/position_sizing.py）。
    - cost_buffer により手数料・スリッページ見積りを加味した保守的な計算をサポート。
    - 将来拡張点として銘柄別 lot_size を想定した TODO を記述。

- 研究/リサーチ機能
  - research.factor_research:
    - calc_momentum / calc_volatility / calc_value: DuckDB 上の prices_daily / raw_financials テーブルを参照して各種ファクターを計算。200日移動平均、ATR、出来高指標、PER/ROE 等を算出（src/kabusys/research/factor_research.py）。
  - research.feature_exploration:
    - calc_forward_returns: 将来リターンを複数ホライズンで一度に計算する汎用クエリ。
    - calc_ic / rank: スピアマンランク相関（IC）計算とランク変換の実装。
    - factor_summary: count/mean/std/min/max/median の統計サマリー計算（標準ライブラリのみで実装）（src/kabusys/research/feature_exploration.py）。
  - research.__init__.py で外部公開 API を整理。

- AI / ニュース NLP（初期実装）
  - news_nlp:
    - ニュースウィンドウ計算（JST → UTC 変換）とスコアリング設計を実装（src/kabusys/ai/news_nlp.py）。
    - OpenAI (gpt-4o-mini) を想定したバッチ送信設計、バッチサイズ、トークン肥大化対策（記事数・文字数制限）、429/ネットワーク/5xx に対する指数バックオフリトライの方針を実装。
    - レスポンスバリデーション、 ±1.0 へのクリップ、ai_scores テーブルへの差分置換（DELETE→INSERT）を設計。
    - 実装中におけるセーフガード（API キー未設定時の ValueError など）を実装。

- ユーティリティ
  - process_priority:
    - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを実装（Windows と POSIX 系を抽象化）（src/kabusys/utils/process_priority.py）。
    - CPU affinity 設定補助（set_cpu_affinity）を実装。権限不足等は警告ログでスキップ。
    - 呼び出し側は文字列レベル ("high"/"normal"/"low") で指定するだけで OK。

### Changed
- 丁寧なデフォルト・フォールバック実装
  - 環境変数の不正値や欠落に対してデフォルト or 明確な例外を返す実装を多数追加（MONITOR_POLL_INTERVAL、PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等）。
  - .env 読み込みは OS 環境変数を保護する考慮（protected 引数）で実装。

### Fixed
- ロバストネス強化
  - run_monitoring/run_execution での DB 接続後に finally で接続を確実に閉じるように実装。
  - process_priority 等で AccessDenied や未対応機能を捕捉し、プロセス起動の致命的失敗を避けるため警告に落とす実装。
  - paper_verification_report: 空データやテーブル未存在時に sqlite3.OperationalError を捕捉して安全にレポートを作成するように実装。

### Removed
- なし（初期リリース想定のため）

### Security
- 環境変数読み込みで OS 環境変数を保護する仕組みを導入（.env の上書き制御）。
- OpenAI API キー未設定時に明確なエラーを出すことで意図しないリクエスト漏洩を防止。

---

注記:
- 多くのモジュールは DuckDB / SQLite を前提としており、テーブル構成（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, system_status, trade_logs, risk_logs など）に依存します。実行前にスキーマとデータの準備が必要です。
- news_nlp モジュールはファイル末尾が途中で途切れており、完全な動作確認が必要です。実運用前に該当箇所の実装完了と単体テストを推奨します。
- 一部の計算（position_sizing の価格フォールバックや銘柄別 lot_size など）は将来の拡張を想定して TODO コメントが残されています。

もしこの CHANGELOG をリポジトリの実際のコミット履歴やリリースノートに合わせてさらに正確に整形したい場合は、コミットログやリリース日、未完成箇所の優先度などの追加情報を教えてください。