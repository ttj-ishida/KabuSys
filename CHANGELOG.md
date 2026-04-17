# Changelog

すべての重要な変更は Keep a Changelog のガイドラインに従って記載しています。  
慣例: 変更はカテゴリ別（Added, Changed, Fixed, Deprecated, Removed, Security）で整理しています。

## [Unreleased]

### Added
- 全体
  - パッケージ初期設計に基づく主要コンポーネント群を実装（Execution / Monitoring / Portfolio / Research / AI / Tools / Utils）。
- 起動スクリプト
  - run_execution: ExecutionEngine 起動用スクリプトを追加。paper_trading 環境向けに専用 SQLite を使用する挙動をサポート（settings.is_paper により切替）。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。
- 設定管理
  - config.Settings を実装。環境変数・.env/.env.local 自動ロード、必須キー検証（_require）、各種設定プロパティ（DB パス・ペーパートレーディング設定・監視閾値など）を提供。
  - .env パーサの実装: export 構文・クォート対応・インラインコメント処理などに対応する堅牢なパーサを追加。
- 実行コンポーネント
  - BrokerClientFactory（抽象化により本番クライアント／MockBroker の切替を実現）。
  - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の骨格実装を追加。ExecutionEngine は別スレッドで run_session を実行し、停止フラグで安全停止できる。
- 監視
  - monitoring DB 初期化ユーティリティ（init_monitoring_db）呼び出しを起動スクリプトに組み込み。run_monitoring は環境に関係なく本番 sqlite_path を監視用に使用。
- ポートフォリオ構築
  - portfolio モジュールを追加:
    - portfolio_builder: 候補選定（select_candidates）・等重（calc_equal_weights）・スコア重み（calc_score_weights）を実装。スコア全てが 0 の場合は等重にフォールバックして警告を出す。
    - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装。未知レジームは警告の上でフォールバック。
    - position_sizing: 単元株丸め、リスクベース／等重／スコアベースの発注株数計算、集計キャップ（available_cash 超過時のスケーリング）を実装。cost_buffer を考慮した保守的見積りをサポート。
- リサーチ
  - research モジュールを追加:
    - factor_research: モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR/出来高/出来高比）、バリュー（PER/ROE）を DuckDB の SQL 組み合わせで計算する関数群を実装。
    - feature_exploration: 将来リターン計算、IC（Spearman のランク相関）計算、ファクター統計サマリ、ランク関数を実装。
  - 計算は DuckDB 接続を受け取る純粋関数設計（外部 API 不使用）。
- AI（ニュース NLP）
  - news_nlp: raw_news を OpenAI（gpt-4o-mini）でスコアリングして ai_scores に書き込む処理を追加。バッチ処理、トークン肥大化対策（記事数／文字数制限）、リトライ方針（429/5xx/ネットワーク等に対する指数バックオフ）、レスポンスバリデーション、スコアの ±1.0 クリップなどを設計。
  - calc_news_window により JST ベースのニュースウィンドウ（前日 15:00 ～ 当日 08:30）を UTC に変換するユーティリティを提供。
- ツール
  - tools/paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシなどを算出し PASS/FAIL を判定する。コマンドライン引数で期間・DB パスを指定可能。
- ユーティリティ
  - utils/process_priority: プロセス優先度設定（Windows / POSIX の差分吸収）と CPU affinity 固定ユーティリティを追加。アクセス権限や未対応 OS の扱いは警告で安全にスキップ。

### Changed
- 設定ローディング順序を明確化: OS 環境変数 > .env.local > .env。OS 環境変数は保護（上書き不可）として扱う。
- run_monitoring の動作: Monitoring は実行環境にかかわらず本番 sqlite_path を使用する仕様に明確化。

### Fixed
- 環境変数パースの堅牢化: クォート内のバックスラッシュエスケープ処理や、クォートなしでのインラインコメント（#）判定の改善により .env パーサの誤読を軽減。
- calc_score_weights: スコア合計が 0.0 の場合に等金額配分へフォールバックし、ログ警告を出すように修正（ゼロ除算防止）。
- calc_regime_multiplier: 未知のレジーム値を受けた際に警告して 1.0 にフォールバックするように修正。
- position_sizing:
  - 単元株（lot_size）での丸め処理や per-stock 上限計算を整備。
  - aggregate cap スケーリング後の残差配分を安定化（remainder による lot 単位の追加配分）。
- utils/process_priority:
  - 未対応 OS の場合や権限不足時に例外を送出せずログ警告で処理をスキップするように改良。
  - set_cpu_affinity が指定コア数 > 利用可能コア数の扱いを調整（全コア使用の旨ログ出力）。
- tools/paper_verification_report:
  - DB 接続時のテーブル欠損に対する try/except を導入し、テーブルが存在しない場合でもレポート生成を継続できるように改善（N/A 表示）。

### Security
- news_nlp: OpenAI API キーは引数または環境変数（OPENAI_API_KEY）から解決。未設定時は明示的な ValueError を発生させることで誤設定を検出可能に。

### Documentation
- 各モジュールに詳細な docstring と設計ノート（PortfolioConstruction.md / StrategyModel.md 等参照箇所の言及）を追加し、関数仕様・制約を明記。

## [0.1.0] - 2026-04-17

初回公開リリース（パッケージバージョン __version__ = 0.1.0）として以下を含む。

### Added
- パッケージの基本構成を追加（kabusys パッケージ、サブモジュール群）。
- 上記 Unreleased に記載の主要機能群を本リリースに含む（ExecutionEngine 起動、SystemMonitor ポーリング、ポートフォリオ構築/サイズ決定、リサーチ関数群、ニュース NLP、ユーティリティ、ツール等）。
- パッケージエクスポート（kabusys.__init__.py）に基本情報と公開 API を整備。

### Fixed
- 初期実装段階での既知の挙動（環境変数の取り扱い・エッジケース）について基礎的な例外処理とフォールバックを追加。

---

注記:
- 本 CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴やイシュートラッキングに基づくものではありません。必要に応じて日付・バージョン・項目をプロジェクトの実際の履歴に合わせて調整してください。