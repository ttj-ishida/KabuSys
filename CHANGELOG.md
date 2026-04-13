# Changelog

すべての変更は Keep a Changelog 規約に準拠して記載しています。  
このファイルはコードベースの現在の状態から機能・修正・設計方針を推測して作成しています。

全般的な注意
- 日付はこのコードベースの参照日（2026-04-13）を基準にしています。
- バージョンはパッケージ定義（kabusys.__version__ = "0.1.0"）に合わせています。

## [Unreleased]
- 小さな改善やドキュメント整備、テスト追加などを予定。

## [0.1.0] - 2026-04-13

### Added
- 基本パッケージの初期実装を追加。
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"。
- 設定管理（kabusys.config.Settings）を実装。
  - .env / .env.local ファイルの自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - OS 環境変数を保護する protected オプション（.env.local が OS 環境を上書きしない）。
  - 環境変数パース機能の強化（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理）。
  - 必須項目取得用の _require() と各種プロパティ（DBパス、APIトークン、PID/KILLフラグパス、閾値、環境種別判定 等）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化機能。
  - 値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）の実装。
- 実行用スクリプトを追加。
  - run_execution.py: ExecutionEngine の起動スクリプト。
    - 環境に応じたブローカークライアント選択（paper_trading 環境では MockBrokerClient を使用し、専用 SQLite DB に記録）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - duckdb 接続を渡して解析用 DB を利用。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はフォールバックして警告を出力。
    - Monitoring は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する設計。
    - check_once() 実行時の例外を捕捉してループ継続する堅牢化。
- プロセス優先度 / CPU affinity ユーティリティを追加（kabusys.utils.process_priority）。
  - set_process_priority(level)（Windows / POSIX の差分吸収、アクセス拒否等の例外を警告してスキップ）。
  - set_cpu_affinity(cpu_count)（最初の N コアにピン留め、権限不足時は警告してスキップ）。
- 監視 DB 初期化ユーティリティ（monitoring_db.init_monitoring_db）を使用する設計（起動時に監視用テーブルを保証）。
- Portfolio モジュール（kabusys.portfolio）を実装。
  - portfolio_builder:
    - select_candidates: スコア降順の候補選定（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights（score が全て 0 の場合は等分配にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限のフィルタリング（売却予定銘柄を除外、"unknown" セクターは制限を適用しない）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数。
  - position_sizing:
    - calc_position_sizes: risk_based / equal / score の配分方式を実装。単元株（lot_size）丸め、1銘柄上限、aggregate cap スケーリング（コストバッファ考慮）を実装。
- リサーチ（kabusys.research）モジュールを実装。
  - factor_research: calc_momentum, calc_volatility, calc_value（DuckDB で prices_daily / raw_financials を参照）。
  - feature_exploration: calc_forward_returns, calc_ic（Spearman ランク相関）, factor_summary, rank（同順位は平均ランク）。
  - DuckDB を利用した SQL ベースのファクター計算とパフォーマンス配慮（スキャン範囲のバッファ等）。
- AI ニュース NLP スコアリング（kabusys.ai.news_nlp）を追加。
  - raw_news / news_symbols を集約して OpenAI API (gpt-4o-mini) にバッチ送信し、銘柄ごとに -1.0〜1.0 のスコアを ai_scores テーブルへ書き込み。
  - バッチサイズ、記事文字数上限、記事数上限、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスの厳密な JSON バリデーション、スコアのクリップなどの安全策を実装。
  - target_date ベースのニュースウィンドウ計算（JST を基準に UTC に変換し DB 比較）。
  - APIキー未設定時は ValueError を送出。
- ツール: Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）。
  - paper_trading DB から稼働率、注文成功率、送信率、P95 レイテンシ等を集計して標準出力にレポートを生成。
  - パス指定（--db）、期間指定（--from / --to）に対応。データ不足時は N/A を表示。
  - 判定基準（閾値）を定義し PASS/FAIL 判定を出力。
- DuckDB / SQLite を併用する設計を導入（分析用: duckdb, 軽量ログ/監視用: sqlite）。

### Changed
- 環境分離ポリシーの明確化。
  - paper_trading 環境では paper 専用 SQLite（デフォルト data/paper_trading.db）を使用して本番データと完全分離。
  - 監視プロセスは環境にかかわらず本番の sqlite_path を使用する設計（監視の一貫性確保）。
- 設定読み込みの優先順位を明示化（OS環境 > .env.local > .env）。.env.local は .env を上書き可能。
- 各種計算関数・集計関数がデータ欠損に対して None を返すなど堅牢な振る舞いに。

### Fixed
- 複数の堅牢化・フォールバックを実装。
  - MONITOR_POLL_INTERVAL の不正値（0 や負値、数値以外）を検出してデフォルトにフォールバックし警告を出力。
  - process_priority 設定で未対応 OS や権限不足時に例外を投げず警告してスキップ。
  - Execution / Monitoring のループで発生した例外を捕捉して次のポーリング / シャットダウンまで継続。
  - DuckDB executemany 前のパラメータ空チェックや SQLite の OperationalError を捕捉してレポート生成が失敗してもフォールバックする実装。
- ファクター計算やレポート生成における境界条件（データ不足、0除算、NULL 伝播）を適切に扱うよう修正。
  - TR（true_range）計算で high/low/prev_close のいずれかが NULL の場合は NULL を保持して過大評価を防止。
  - ATR / MA 計算でウィンドウに必要な行数が足りない場合は None を返す。

### Security
- 環境変数の自動読み込みを必要に応じて無効化できる KABUSYS_DISABLE_AUTO_ENV_LOAD を提供（テスト環境向け）。
- OPENAI_API_KEY が未設定の場合は早期にエラーを出すことで、意図しない挙動や誤った外部 API 呼び出しを防止。

### Notes / Known limitations
- position_sizing の lot_size は現在グローバル固定（将来的に銘柄別 lot_map へ拡張予定）。
- apply_sector_cap の価格欠損（0.0）の場合、エクスポージャーが過小見積もられる可能性があり TODO コメントで将来的な改善を示唆。
- ai.news_nlp の実装は API レートやコストの現実運用を想定したチューニングが必要（バッチサイズやリトライポリシー等）。
- research モジュールは DuckDB 上の prices_daily/raw_financials に依存するため、データの整備が必要。

---

（以降のリリース履歴は今後の変更に合わせて追記してください。）