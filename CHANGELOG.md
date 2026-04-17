# CHANGELOG

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠します。

注: この CHANGELOG は現在のコードベースから推測して作成したものであり、実際のコミット履歴に基づくものではありません。

## [Unreleased]

- ドキュメント化・整理中の小改善や TODO が存在します（ソース内の TODO コメント参照）。
- ai/news_nlp モジュールの処理途中（スコアリングフローの一部が未完の状態）に関する追加作業が必要です。

## [0.1.0] - 2026-04-17

### Added
- 基本パッケージ初期実装を追加（kabusys v0.1.0）。
  - パッケージメタ情報を src/kabusys/__init__.py に追加（__version__ = "0.1.0"）。
- 実行・監視エントリポイント
  - run_execution.py: ExecutionEngine を起動するためのスクリプトを追加。
    - 環境による DB 分離：paper_trading モード時は専用の paper_trading.db を使用。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立てとバックグラウンドスレッドでの実行管理。
    - 停止フラグファイル (data/stop_requested.flag) の検出による安全停止処理。
    - プロセス優先度を高（"high"）に設定する初期化処理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視系は環境にかかわらず本番用 sqlite_path を使用する仕様。
    - 停止フラグ検出、例外捕捉、DB のクローズ処理を含む堅牢なループ実装。
- 設定管理
  - config.py: .env 自動ロード機能を実装（プロジェクトルートの検出: .git / pyproject.toml）。
    - .env / .env.local を OS 環境変数と適切な優先度で読み込む。
    - 行パースの堅牢化（コメント・クォート・export 形式対応、エスケープ処理）。
    - Settings クラスを導入し、環境変数のラップとバリデーションを提供（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視しきい値等）。
    - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL の妥当性チェック。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 候補選択・等金額・スコア加重配分の関数を追加（select_candidates, calc_equal_weights, calc_score_weights）。
  - portfolio.risk_adjustment: セクターキャップ適用・レジーム乗数計算を追加（apply_sector_cap, calc_regime_multiplier）。
  - portfolio.position_sizing: 発注株数決定ロジックを実装（risk_based / equal / score の配分方式、単元株丸め、aggregate cap スケーリング、cost_buffer 対応）。
  - モジュールエクスポートを追加（kabusys.portfolio）。
- 研究・リサーチ機能
  - research.factor_research:
    - Momentum / Volatility / Value ファクター計算関数を追加（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上の prices_daily / raw_financials を用いた SQL ベース実装。
  - research.feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、ランク付けユーティリティ（rank）、統計サマリ（factor_summary）を追加。
    - pandas 等に依存せず標準ライブラリのみで完結する設計。
  - research パッケージの __all__ に必要な関数を公開。
- ツール
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率・注文成功率・送信率・レイテンシ（P95）などを算出するクエリと判定基準を実装。
    - 閾値（稼働率 99%、成交率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
    - コマンドライン引数で期間指定（--from, --to）や DB パス指定（--db）に対応。
- AI ニューススコアリング（下地実装）
  - ai/news_nlp.py:
    - ニュース収集ウィンドウ計算（calc_news_window）と OpenAI を用いたスコアリングの設計（score_news）を追加。
    - バッチサイズ、モデル、リトライ・バックオフ、トークン肥大化対策（記事数・文字数制限）、スコアクリップ等の定数を定義。
    - 設計方針（JSON 出力厳守、部分失敗耐性、ルックアヘッドバイアス回避）を明記。
    -（注）score_news の処理はコード断片の状態で一部実装途中。
- ユーティリティ
  - utils.process_priority:
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
    - Windows / POSIX (Linux, Darwin, FreeBSD) の差異を吸収し psutil ベースで優先度や CPU affinity を設定。
    - 権限不足や未サポート OS の場合は警告を出してスキップする安全設計。

### Changed
- （当初リリースのため変更履歴は無し）コード中に将来の改善点や TODO コメントを追加:
  - position_sizing: lot_size 将来的拡張のための TODO。
  - risk_adjustment: price 欠損時のフォールバック価格使用についての注記。

### Fixed
- .env 読み込み処理でのエスケープ・クォート・コメント処理を改善（行パースの堅牢化により .env の不正解釈を回避）。

### Known issues / Notes
- ai/news_nlp.score_news がファイル末尾で途中になっており、記事取得・API 呼び出し・DB 更新の完成が必要です。現状は設計・定数・ウィンドウ計算まで実装済み。
- 一部の SQL クエリは DuckDB 側のスキーマ依存（prices_daily, raw_financials, trade_logs 等）。本番で利用するには DB スキーマとデータの準備が必要です。
- process_priority の設定は OS 権限に依存します。権限不足時は警告ログのみ。

### Security
- 特になし（環境変数や API キーの取り扱いは Settings / score_news で明示的に環境変数参照を行う設計）。

---

変更点や追加された機能について不明な点や詳細な記述を追記したい項目があれば、どのモジュールを優先して詳細化するかを指示してください。