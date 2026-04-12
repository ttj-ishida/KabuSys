# CHANGELOG

このファイルは Keep a Changelog の形式に準拠して作成しています。  
（コードベースの内容から推測して記載しています。実際の変更履歴と差異がある場合があります）

全般メモ
- 初期リリース相当の内容をまとめています（パッケージバージョン: 0.1.0）。
- 各エントリはコード内の実装・ドキュメンテーションおよび挙動から推測して記載しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-12
### Added
- コア機能
  - kabusys パッケージの初期リリース（__version__ = 0.1.0）。
  - アプリケーション設定管理モジュール（kabusys.config）
    - .env / .env.local の自動ロード（プロジェクトルート検出: .git または pyproject.toml）
    - 強力な .env ラインパーサ（export 形式、クォート・エスケープ、インラインコメント考慮）
    - 必須環境変数チェック用の _require ユーティリティ
    - 設定値のラッパー（DB パス、Paper Trading 関連、監視用閾値、環境種別判定など）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート

- 実行 / 監視ランナー
  - run_execution.py
    - ExecutionEngine の起動スクリプト
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite DB を使用（本番 DB と分離）
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て
    - RiskManager に対するデフォルト RiskConfig を提供（rate limiting, circuit breaker 等含む）
    - duckdb 接続の初期化サポート
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動用スクリプト
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）
    - 監視用 DB は環境に関わらず本番 sqlite_path を使用する設計（意図的分離）

- 監視 DB 初期化ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db を通じた監視用テーブルの冪等初期化呼び出しを各ランナーで使用

- ポートフォリオ構築関連（kabusys.portfolio）
  - portfolio_builder
    - select_candidates: スコア降順 + signal_rank によるタイブレークで候補選定
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全スコア0 のフォールバック警告）
  - risk_adjustment
    - apply_sector_cap: セクター別集中上限の適用（売却予定銘柄を除外可能、"unknown" セクターは上限適用除外）
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に基づく投下資金乗数
  - position_sizing
    - calc_position_sizes: allocation_method（risk_based, equal, score）に基づく株数決定
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）でのスケーリング、cost_buffer による保守的見積り、端数配分ロジックを実装

- 研究・ファクター計算（kabusys.research）
  - factor_research
    - calc_momentum, calc_volatility, calc_value: DuckDB の prices_daily / raw_financials テーブル参照による各種ファクター算出
    - 複数ウィンドウ長・欠損時の None 処理、200 日移動平均や ATR 等の実装
  - feature_exploration
    - calc_forward_returns: 将来リターン計算（任意ホライズン、入力検証あり）
    - calc_ic: スピアマンランク相関（IC）計算（データ欠損や ties の扱いに注意）
    - factor_summary / rank: 基本統計量・ランク変換ユーティリティ
  - research パッケージとして必要な関数を公開

- ニュース NLP（kabusys.ai.news_nlp）
  - AI によるニュースセンチメントスコア生成機能
    - OpenAI（gpt-4o-mini）を用いたバッチスコアリング（最大バッチサイズ 20）
    - タイムウィンドウの計算（前日 15:00 JST ～ 当日 08:30 JST）
    - 記事数・文字数上限（1 銘柄あたり記事数・文字数のトリム）によるトークン肥大化対策
    - 429/ネットワーク/5xx 等に対する指数バックオフ・リトライの基本方針
    - レスポンスの JSON バリデーション、スコアの ±1.0 クリップ、DuckDB への安全な書き込み（部分失敗時の既存スコア保護）
    - API キー未設定時の明確な例外メッセージ（OPENAI_API_KEY 環境変数／引数による設定）

- ユーティリティ
  - utils.process_priority
    - Windows / POSIX (Linux, macOS, FreeBSD) に対応したプロセス優先度設定（high/normal/low）
    - CPU affinity 設定のユーティリティ（cpu_count 引数、例外時の警告スキップ）
    - 権限不足や未対応環境で安全にフォールバックする実装

- ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成 CLI（--from/--to/--db オプション）
    - 稼働率・注文成功率・送信率・P95 レイテンシ等の算出と PASS/FAIL 判定ロジック
    - DB 存在チェック、SQL 実行エラー時のフォールバック（テーブル未存在時に N/A 等で処理継続）

### Changed
- （初期リリースのため該当なし）

### Fixed
- 設計上の堅牢化（初期実装として以下を想定）
  - .env 読み込みでファイルが開けない場合は警告を出してスキップ（warnings.warn）
  - MONITOR_POLL_INTERVAL の不正値（0/負数/非整数）に対する警告とデフォルトフォールバック（60 秒）
  - process_priority / cpu_affinity の実行で権限不足や未実装の API に対し警告を出し処理を続行（アプリ停止を防ぐ）
  - research / factor 計算や position sizing 等でデータ不足時に None を返すことで上位呼び出しで安全に扱えるように設計

### Security
- OpenAI API キーは環境変数または明示的引数で供給する設計。未設定時に ValueError を送出して明示的に扱う。

---

注記・既知事項（コードから推測）
- monitoring は環境に関わらず本番 sqlite_path を使用する実装になっているため、テスト時は注意が必要（意図的設計か確認を推奨）。
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄別拡張の TODO が存在）。
- apply_sector_cap は price_map に price が欠損（0.0）の場合に過少見積りのリスクをコメントで指摘しており、将来のフォールバック価格導入を検討している。
- ai.news_nlp の実装はリトライ・バリデーション等多くの堅牢化をしているが、実稼働では API レートやコストに留意が必要。

（以上）