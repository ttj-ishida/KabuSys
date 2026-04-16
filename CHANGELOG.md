# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
日付はリポジトリ内のバージョン情報・実装内容から推定しています。

## [Unreleased]

## [0.1.0] - 2026-04-16
初回公開（推定）。以下の主要機能と実装を追加・導入しました。

### Added
- 実行・監視ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度を "high" に設定して起動、KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB（data/paper_trading.db など）および MockBrokerClient を使用するよう分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関係なく本番 sqlite_path を使用する点に注意。
  - 両スクリプトとも停止フラグ（data/stop_requested.flag）や PID ファイルを用いた安全な起動/停止制御を実装。

- 設定管理（環境変数）
  - config.py: Settings クラスを導入し、各種環境変数（DB パス、API トークン、閾値、実行環境判定等）をプロパティ経由で提供。
  - .env 自動読み込み機能を追加（プロジェクトルート検出: .git / pyproject.toml を基準）。`.env` と `.env.local` の読み込み順/上書きルール、OS 環境変数の保護をサポート。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - .env パース機能強化: export プレフィックス、クォート文字列、インラインコメント、エスケープ処理に対応。
  - paper_trading 用設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等）、監視閾値（CPU/MEM/DISK）や kill/ pid 関連設定をプロパティで提供。各種値検証（有効な列挙値チェックなど）を実装。

- ポートフォリオ構築ユーティリティ
  - portfolio/portfolio_builder.py: シグナルの選定（select_candidates）および重み計算（等分配 calc_equal_weights、スコア重み calc_score_weights）を追加。スコアが全て 0 の場合は等配分にフォールバック。
  - portfolio/position_sizing.py: position sizing ロジックを実装。allocation_method（risk_based / equal / score）に対応。単元株（lot_size）丸め、1銘柄上限、aggregate cap、cost_buffer による保守的コスト見積もり、スケールダウン時の端数処理（残差に基づく追加配分）を実装。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap（既存ポジションのセクター別エクスポージャ算出と新規候補の除外）、market regime に応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear + フォールバック）を実装。

- 監視・ユーティリティ
  - utils/process_priority.py: クロスプラットフォームでのプロセス優先度設定（set_process_priority）と CPU affinity 固定（set_cpu_affinity）を追加。Windows / POSIX（Linux, Darwin, FreeBSD）に対応し、権限不足や未サポート環境は警告を出して安全にスキップ。

- リサーチ / ファクター計算
  - research/factor_research.py: DuckDB を用いたモメンタム・ボラティリティ・バリュー系ファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。200 日移動平均やATR、出来高平均などのウィンドウ処理は SQL ウィンドウ関数で実装。
  - research/feature_exploration.py: 将来リターン計算（calc_forward_returns）、IC（情報係数）計算（calc_ic）、ランク関数・ファクター統計サマリ（factor_summary）を追加。外部依存なしで純粋 Python + DuckDB SQL 実装。
  - research パッケージの __init__ で zscore_normalize（data.stats）と主要関数を公開。

- AI ニュース NLP
  - ai/news_nlp.py: raw_news から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）にバッチ送信してセンチメントスコアを ai_scores テーブルへ書き込む処理を実装。処理の特徴:
    - ニュースウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で計算。
    - 記事数・文字数トリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）によるトークン抑制。
    - 最大 20 銘柄ごとのバッチ送信、JSON Mode 出力期待、レスポンス検証。
    - 429 / ネットワーク断 / タイムアウト / 5xx を指数バックオフでリトライ。
    - スコアは ±1.0 にクリップ。部分的に成功した場合でも既存スコアを保護する書き込み戦略（対象コードを限定して置換）を採用。
    - API キーは引数または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError。

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。システム稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）などを計算して標準出力にレポート表示。CLI オプションで期間指定（--from/--to）と DB パス（--db）をサポート。P95 パーセンタイル計算、欠損データに対する耐性を実装。デフォルトの閾値（稼働率 99%、成功率 90% 等）による PASS/FAIL 判定を行う。

- パッケージ情報
  - pkg __init__.py にてバージョン __version__ を "0.1.0" として設定。

### Changed
- logging / エラーハンドリング
  - 起動スクリプトや各モジュールでログ出力を整備。重要な例外・リトライ失敗時には logger.exception / warning を使って詳細を記録。

### Fixed
- .env 読み込みの堅牢化
  - ファイル読み込み失敗時に warnings.warn を発行して処理継続するようにして、読み込み失敗でプロセスが致命的に停止しないよう改善。

### Notes / Important
- 監視（run_monitoring.py）は「環境にかかわらず本番 sqlite_path を使用する」実装になっています。開発・ペーパー環境での監視データ分離が必要な場合は環境変数やコードの設定を見直してください。
- paper_trading 動作時は ExecutionEngine が本番 DB を操作しないよう paper_sqlite_path を使用する設計です（本番 DB との分離が確保されます）。
- process priority / cpu affinity の設定は権限に依存し、失敗した場合は警告ログを出力してスキップします。
- AI ニュース NLP の処理は外部 API に依存するため、API 呼び出し回数やレイテンシに注意してください。OpenAI API キー管理・レート制限に留意が必要です。

---

もしリリースノートを別の粒度（細かいコミット別や、改修箇所ごとの影響範囲明示）で作成したい場合や、特に注記すべき既知の互換性問題があれば教えてください。