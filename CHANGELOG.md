# CHANGELOG

すべての注目すべき変更は Keep a Changelog の形式に従って記載しています。  
主にコードベースから推測できる機能追加・改善・修正・既知制約を日本語でまとめています。

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-11
初回リリース想定。システム全体の主要機能群を実装しました。以下はコードベースから推測できる主要な追加・改善点・注意点です。

### Added
- 全体
  - パッケージ初期リリース。バージョンは `kabusys.__version__ = "0.1.0"`。
  - DuckDB / SQLite を用いたローカル分析・監視・実行基盤を実装。

- 設定・環境読み込み
  - `kabusys.config.Settings`：環境変数をラップする設定クラスを提供。多数の設定プロパティ（DB パス、API トークン、PID ファイル、閾値、環境種別など）を定義。
  - 自動 .env ロード機能を実装（プロジェクトルート判定: `.git` または `pyproject.toml`。`.env` → `.env.local` の順で読み込み）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動ロード無効化可能。
  - `.env` パーサは `export KEY=val`、クォート、エスケープ、インラインコメント等に対応。

- 実行スクリプト
  - `run_execution.py`：ExecutionEngine 起動スクリプトを実装。`KABUSYS_ENV=paper_trading` の場合は paper_trading 用 DB を使用し MockBrokerClient を想定（本番 DB と分離）。
  - `run_monitoring.py`：SystemMonitor のポーリング起動スクリプトを実装。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能。監視は常に本番 sqlite_path を使用。

- 実行・監視ユーティリティ
  - `kabusys.utils.process_priority`：プロセス優先度（Windows / POSIX 差分吸収）と CPU affinity 設定ユーティリティを実装。`set_process_priority` / `set_cpu_affinity` を提供。権限不足等はワーニングでスキップ。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`：
    - select_candidates：BUY シグナルをスコア降順で選択（タイブレーク: signal_rank）。
    - calc_equal_weights / calc_score_weights：等金額・スコア加重の重み計算（スコア合計が 0 の場合は等配分にフォールバック）。
  - `kabusys.portfolio.risk_adjustment`：
    - apply_sector_cap：セクター集中制限で新規候補を除外するロジックを実装（既存保有評価時に売却予定銘柄を除外）。
    - calc_regime_multiplier：市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは 1.0 でフォールバック）。
  - `kabusys.portfolio.position_sizing`：
    - calc_position_sizes：allocation_method（risk_based / equal / score）に応じた発注株数計算。単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer（手数料・スリッページ見積）対応。余りの分配は fractional 残差順に lot 単位で割当てる仕組みを実装。

- リサーチ（DuckDB ベースのファクター計算）
  - `kabusys.research.factor_research`：
    - calc_momentum：1M/3M/6M リターン、200日移動平均乖離率（MA200）を DuckDB SQL ウィンドウ関数で計算。
    - calc_volatility：20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高変化率を計算。true_range の NULL 伝播を制御。
    - calc_value：raw_financials と price を統合して PER / ROE を算出（直近の財務レコードを銘柄毎に取得）。
  - `kabusys.research.feature_exploration`：
    - calc_forward_returns：複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで計算。
    - calc_ic：Spearman のランク相関（IC）を計算（レコード不足時は None）。
    - rank / factor_summary：ランク付け（同順位は平均ランク）・基本統計量（count, mean, std, min, max, median）を実装。
  - いずれも外部ライブラリに依存せず、DuckDB と標準ライブラリのみで実装。

- AI（LLM）関連
  - `kabusys.ai.news_nlp`：
    - raw_news から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルに書き込む処理を実装。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたり記事数上限・文字数上限でトークン肥大化対策。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）に対する指数バックオフ実装。API レスポンスの厳密なバリデーション（JSON 抽出・results 構造チェック・スコア数値化・±1.0 クリップ）。
    - DuckDB への書き込みは部分更新（対象コードのみ DELETE → INSERT）で、部分失敗時に既存スコアを保護。
    - OpenAI クライアント呼び出し点はテスト用に差し替え可能（_call_openai_api をモック可能）。
  - `kabusys.ai.regime_detector`：
    - ETF 1321（Nikkei-linked ETF）の MA200 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出はキーワードベース。LLM 呼び出しは失敗時に macro_sentiment=0.0 を用いるフェイルセーフ。
    - 市場レジームは冪等的に market_regime テーブルへ書き込み（トランザクション処理）。

### Changed
- ログ・起動動作
  - `run_execution.py` / `run_monitoring.py` 起動時にプロセス優先度を最初に "high" にセットするように統一。
  - 監視ループは MONITOR_POLL_INTERVAL を環境変数で上書き可能。値の検証（1 以上）を実施し、無効値はデフォルト 60 秒へフォールバックして警告。

- DB ハンドリング
  - monitoring 系の初期化（init_monitoring_db）を冪等に呼び出し、存在チェックを保証。
  - DuckDB と SQLite の両方を使用する設計（分析は DuckDB、監視/実行記録は SQLite）。
  - DuckDB executemany の挙動（空リスト不可）を考慮して条件分岐を追加。

### Fixed
- フェイルセーフ / バリデーション強化
  - 環境変数読み込み・パースの堅牢化（空行、コメント、export フォーマット、クォート内のエスケープ処理等に対応）。
  - OpenAI API レスポンスの不正（JSON 以外の混入等）に対して最外の {} を抽出するフォールバックを実装し、パース失敗はワーニングの上スキップ。
  - 各種計算関数でデータ不足時のフォールバック（例: MA200 データ不足時は中立値 1.0 を使う、スコア全て 0 のときは等配分にフォールバック）を実装。

### Known issues / Notes / TODO
- position_sizing.calc_position_sizes
  - price が欠損（0.0）の場合、エクスポージャーが過少見積りされブロックが外れる可能性あり。コメント中に「前日終値や取得原価などのフォールバック価格を使う拡張を検討」と記載あり。
  - 単元株（lot_size）は現状グローバル固定（デフォルト 100）。将来的に銘柄別 lot_size を stocks マスタに持たせる検討あり。

- AI モジュール
  - OpenAI API の呼び出しは外部サービス依存のため、API キー未設定時は明示的に例外を送出する（呼び出し側で適切に扱う必要あり）。
  - LLM の不確実性に伴い、バリデーションや部分失敗時の保護を実装しているが、誤った LLM 出力による誤判定のリスクは残る。

- プラットフォーム依存
  - process_priority の一部機能（優先度設定・cpu_affinity）は権限や OS に依存。対応していない OS ではスキップして警告を出す。

### Security
- 外部 API キー（J-Quants, OPENAI, Kabu API など）は Settings/環境変数で管理。`.env` 自動ロードにより OS 環境変数上書きを制御する仕組み（protected set）を用いている。

---

この CHANGELOG はコード内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。必要であれば、特定ファイルや変更点を指定いただければ、より詳細で正確な CHANGELOG を作成します。