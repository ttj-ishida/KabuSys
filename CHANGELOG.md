Keep a Changelog に準拠した CHANGELOG.md（日本語）
※コードベースから推測して作成しています。実際のコミット履歴ではなく、リリース内容の要約です。

Keep a Changelog
=================
すべての重要な変更はこのファイルに記録されます。
このプロジェクトは https://keepachangelog.com/ja/ に準拠します。

[Unreleased]
-------------

（無し）

[0.1.0] - 2026-04-09
--------------------

Added
- パッケージ初期リリース。
- 基本情報
  - パッケージメタ情報を追加: kabusys.__version__ = 0.1.0、主要モジュールを __all__ でエクスポート。
- 環境変数 / 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ロード機能を実装。
  - 自動ロード順序: OS環境変数 > .env.local > .env。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサは export 形式対応、クォート内のエスケープ処理、インラインコメント処理を実装。
  - 設定アクセスをラップする Settings クラスを提供（例: settings.jquants_refresh_token）。
  - 各種プロパティのバリデーション（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL など）。未設定や不正値時は ValueError を送出。
  - パス系設定は Path オブジェクトを返す（expanduser 対応）。
- ポートフォリオ構築 (src/kabusys/portfolio)
  - portfolio_builder
    - select_candidates: buy シグナルをスコア降順（同点は signal_rank 昇順）でソートして上位 N を選択。
    - calc_equal_weights: 等金額配分（各銘柄 1/N）。
    - calc_score_weights: スコア加重配分。全銘柄スコアが 0 の場合は等金額にフォールバックし警告を出力。
  - risk_adjustment
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合、新規候補を除外するロジック（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear に対応、未知ラベルは 1.0 でフォールバック）。
  - position_sizing
    - calc_position_sizes: weight / equal / score / risk_based の各方式に対応した株数計算を実装。
    - 単元（lot_size）で丸め、per-position 上限・aggregate cap、cost_buffer（手数料・スリッページ考慮）をサポート。
    - aggregate cap 超過時のスケーリングロジック（スケールダウン→端数の lot_size 分配ロジック）。
- リサーチ / ファクター計算 (src/kabusys/research)
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率（データ不足時は None）を DuckDB 上で算出。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を算出。true_range の NULL 伝播を考慮。
    - calc_value: raw_financials から最新の財務指標を取得して PER/ROE を計算（EPS 欄が 0/NULL の場合は PER を None）。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得。horizons のバリデーションあり。
    - calc_ic: factor と forward returns を code で結合して Spearman のランク相関（IC）を計算。レコード数 < 3 の場合は None を返す。
    - rank / factor_summary: 同順位は平均ランクで処理するランク関数、各カラムの基本統計量（count/mean/std/min/max/median）を計算。
  - DuckDB を前提とした純粋関数群（外部 API 不使用）。出力は (date, code) をキーとする dict のリスト。
- AI 関連機能 (src/kabusys/ai)
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news + news_symbols を用いて銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルに書き込む機能を実装。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）、1銘柄あたり記事数と文字数のトリム制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - API 呼び出しは JSON mode を利用し、JSON パースの堅牢化（前後の余分なテキストから最外側の {} を抽出する等）を実装。
    - レスポンス検証: results フィールド、各要素の code/score の型確認、未知コードは無視、スコアは ±1.0 にクリップ。
    - リトライ戦略: 429, ネットワーク断, タイムアウト, 5xx に対して指数バックオフ（_MAX_RETRIES）。
    - DuckDB への書き込みは冪等性を考慮し、対象コードのみ DELETE → INSERT のトランザクションで実行。DuckDB executemany の空リスト制約に対応した保護処理を実装。
    - フェイルセーフ: API/パース失敗時は当該チャンクをスキップし、他銘柄の処理を継続。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の MA200 乖離（_MA_WEIGHT=0.7）とマクロニュース LLM センチメント（_MACRO_WEIGHT=0.3）を合成して日次で regime_label を判定（'bull'/'neutral'/'bear'）。
    - マクロ記事はキーワード検索（_MACRO_KEYWORDS）で抽出、最大 _MAX_MACRO_ARTICLES 件を LLM に渡して macro_sentiment を算出。記事無し時は LLM 呼び出しをスキップして 0.0 を使用。
    - LLM 呼び出し・リトライは news_nlp と同様の堅牢化（例外別処理、5xx のみ再試行など）。
    - score_regime は冪等的に market_regime テーブルへ書き込む（BEGIN / DELETE / INSERT / COMMIT）。APIキー未設定時は ValueError を送出。
- 監視データベース（src/kabusys/monitoring/monitoring_db.py）
  - SQLite ベースの監視ログ永続化レイヤを実装。
  - system_status / trade_logs / positions / risk_logs 等のテーブル作成スクリプト（CREATE TABLE IF NOT EXISTS と各種 INDEX）を提供（冪等）。
  - ビジネスロジックを持たない単純な読み書き層として設計。

Changed
- （初回リリースのため無し）

Fixed
- （初回リリースのため無し）

Deprecated
- （初回リリースのため無し）

Removed
- （初回リリースのため無し）

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で解決。未設定時は API 呼び出し前に明示的にエラー（ValueError）を出すことで誤用防止。

Notes / Known issues / TODOs
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合に exposure が過少評価される問題について TODO コメントあり。将来的に前日終値や取得原価でフォールバックする検討が示されている。
  - lot_size は現状グローバルで 100 を想定。将来的に銘柄別 lot_map の導入を検討。
- .env パーサはかなり厳密だが、非常に複雑な .env フォーマットの全ケース（特殊なエスケープ等）を完全に網羅しているかは要確認。
- DuckDB executemany のバージョン差異（空リストバインドの挙動）に対する保護処理を実装しているが、実行環境の DuckDB バージョンによって動作確認が必要。
- AI モジュールは外部 API（OpenAI）に依存しており、API 仕様変更やモデルリストの変更により調整が必要になる可能性がある。
- market_regime._calc_ma200_ratio は data が不足する場合に中立（1.0）でフォールバックする設計。データ品質が重要。

Exported Public API（主な関数 / クラス）
- kabusys.settings (Settings インスタンス)
- kabusys.portfolio.select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- kabusys.research.calc_momentum, calc_volatility, calc_value, zscore_normalize (kabusys.data.stats からの再エクスポート), calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.ai.score_news
- 監視 DB 初期化: init_monitoring_db

補足
- 各モジュールは「DB 参照なし」で完結する純粋関数として設計されている部分（portfolio 等）と、DuckDB/SQLite を必要とするリサーチ・AI・監視部分が混在しています。ユニットテスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD を使って環境設定の自動ロードを抑止することが可能です。