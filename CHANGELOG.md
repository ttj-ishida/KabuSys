CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠しています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Removed: 削除
- Security: セキュリティ関連

Unreleased
----------

（今後の変更をここに記載）

0.1.0 — 2026-04-17
------------------

Added
- 実行エントリ／デーモン
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。実行停止は data/stop_requested.flag で検知。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。スレッドでエンジンを実行し stop フラグで安全停止。paper_trading 環境では専用の MockBrokerClient と分離された SQLite DB（data/paper_trading.db デフォルト）を使用。

- 設定管理
  - kabusys.config.Settings を実装。.env 自動読み込み機能（プロジェクトルート検出 .git / pyproject.toml）を実装し、.env と .env.local の優先度を扱う。export 形式、クォート、インラインコメントなどに対応するパーサを実装。
  - 各種設定プロパティを追加（DB パス、PID ファイル、閾値、PAPER_FILL_MODE 検証、環境名 / ログレベルの検証など）。

- ポートフォリオ構築（純関数）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順＋タイブレークで選出。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア合計が 0.0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存保有を考慮、売却予定銘柄を除外、"unknown" セクターは除外しない挙動）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた乗数（未知のレジームは警告を出して 1.0 でフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: risk_based / equal / score に対応した株数算出。単元株（lot_size）で丸め、per-position 上限・aggregate 上限、cost_buffer（手数料・スリッページ見積）を加味したスケーリングと残差配分ロジックを実装。

- 研究（Research）モジュール
  - research.factor_research:
    - calc_momentum / calc_volatility / calc_value: DuckDB の prices_daily / raw_financials を利用してモメンタム、ボラティリティ、バリュー・ファクターを算出。窓サイズ不足時の None 返却など、堅牢な設計。
  - research.feature_exploration:
    - calc_forward_returns / calc_ic / factor_summary / rank: 将来リターン計算、IC（Spearman）計算、ファクター統計サマリなどを標準ライブラリのみで実装。
  - research パッケージ __init__ で zscore_normalize（data.stats 経由）を再エクスポート。

- AI ニュース NLP
  - ai.news_nlp:
    - calc_news_window: target_date に対するニュース収集ウィンドウ（JST→UTC 変換）を実装。
    - score_news: OpenAI（gpt-4o-mini）を用いたニュースのセンチメント集計・スコアリングの骨子を追加。バッチ処理、トークン肥大化対策（記事数・文字数制限）、リトライ（指数バックオフ）、レスポンス検証、スコアの ±1.0 クリップ、部分的な DB 書き換えで部分失敗に耐える設計などを導入。
    - API キー未設定時のバリデーションあり。ルックアヘッドバイアス防止のため datetime.today() を参照しない設計。

- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定。コマンドライン引数で期間・DB パスを指定可能。DB が存在しない／テーブルがない場合に耐性あり（OperationalError をキャッチして N/A 扱い）。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority: Windows / POSIX（Linux/Mac/FreeBSD）に対応したプロセス優先度設定を実装。権限不足や未対応 OS では警告を出してスキップ。
    - set_cpu_affinity: 指定コア数に固定するユーティリティを追加（権限や環境依存で失敗した場合は警告）。
  - パッケージ初期化ファイルの整備。

Changed
- run_monitoring: 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する意図を明記（開発環境での挙動に注意）。
- run_execution: paper_trading 環境時は paper_sqlite_path を使用し、本番 DB と明確に分離するように変更（デフォルト: data/paper_trading.db）。
- 設定の自動ロード順序は OS 環境変数 > .env.local > .env となり、OS 環境変数は保護される（上書き不可、.env.local は上書き可）。

Fixed
- 環境変数パーサの堅牢化:
  - export 付き行、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いを改善。
- MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）を検知して警告を出しデフォルトにフォールバックするよう修正（time.sleep に渡す不正値での例外回避）。
- portfolio.calc_score_weights: 全銘柄スコアが 0 の場合に等金額配分へフォールバックする挙動を追加（警告ログあり）。
- position_sizing の aggregate cap 処理: available_cash を超える場合にスケールダウンし、lot_size 単位で残余を大きい順に再配分することで再現性と安定性を向上。
- risk_adjustment.apply_sector_cap: 売却予定コードをエクスポージャー計算から除外するロジックを追加し、unknown セクターに対する扱い（制限を適用しない）を明示。
- process_priority: アクセス拒否や未実装例外発生時に警告を出して安全に継続するよう修正。
- research / tools SQL クエリや集計処理において、データ不足時に None を返すなど null 耐性を強化。

Removed
- なし（初回リリース）

Security
- OpenAI API キーやその他機微な値は環境変数経由で扱う設計。.env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト時の安全策）。

Notes / Todo / Known issues
- ai.news_nlp の内部実装は堅牢化済みだが、_fetch_articles 等の一部補助関数の実装箇所が継続実装を想定している（ファイル末尾で切れている可能性あり）。本番稼働前に完全な統合テストを推奨。
- portfolio.position_sizing の将来的拡張: 銘柄別 lot_size をサポートするための設計コメントあり（現在は全銘柄共通 lot_size を想定）。
- apply_sector_cap の価格欠損（price が 0.0）によるエクスポージャー過少見積りは TODO コメントで指摘されている。前日終値等のフォールバック導入を検討。
- run_monitoring は監視用 DB を本番パスで固定しているため、開発環境での操作時は注意。

貢献とクレジット
- コードベースの各モジュール（monitoring, execution, config, portfolio, research, ai, tools, utils）は初回リリースとしてまとまった機能群を提供します。今後の改善・バグ修正の貢献を歓迎します。