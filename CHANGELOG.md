# Changelog

すべての重要な変更点をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-09

### Added
- 基本パッケージ初回リリース。
- パッケージメタ情報を追加
  - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
  - パッケージ公開用に主要サブパッケージを __all__ で宣言。

- 環境変数 / 設定管理モジュールを追加（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml により探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用）。
  - .env パーサは export 形式、クォート文字、エスケープ、行内コメントなどに対応。
  - 読み込み時は既存 OS 環境変数を保護する protected 機構を実装（.env の上書きを制御）。
  - 必須キー取得時に未設定なら ValueError を送出する _require() を提供。
  - 各種設定プロパティを提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, PAPER_FILL_MODE 等）。
  - KABUSYS_ENV のバリデーション（development / paper_trading / live）や LOG_LEVEL の検証機構を実装。
  - PAPER_FILL_MODE の有効値チェックとエラーメッセージを実装。

- ポートフォリオ構築モジュールを追加（src/kabusys/portfolio/）
  - portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順にソート。スコア同率時は signal_rank の昇順でタイブレーク。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を実装。全スコアが 0 の場合は等配分へフォールバックし警告ログを出力。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中上限をチェックし、超過セクターの新規候補を除外（"unknown" セクターは制限を適用しない）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を実装。未知レジームは警告のうえ 1.0 にフォールバック。
  - position_sizing.py
    - calc_position_sizes: risk_based / equal / score の各割当方式をサポート。単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケーリング、コストバッファ（cost_buffer）考慮、価格欠損時のスキップなどを実装。
    - スケールダウン時は lot_size 単位で再配分するアルゴリズムを実装し、残差配分は再現性のある順序で行う。

- 研究（Research）モジュールを追加（src/kabusys/research/）
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離を DuckDB 上の prices_daily テーブルから計算。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を慎重に扱う実装。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（最新財務レコードの取得ロジックを含む）。
  - feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンをまとめて単一クエリで取得。horizons のバリデーションあり。
    - calc_ic: スピアマンのランク相関（IC）を計算。レコード不足や定数分散の場合は None を返す。
    - rank: 同順位の平均ランクを返すランク関数（浮動小数丸め誤差対策の round(v,12) を使用）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算。
  - research パッケージの __init__ で zscore_normalize（kabusys.data.stats 由来）を再エクスポート。

- AI 関連モジュールを追加（src/kabusys/ai/）
  - news_nlp.py
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとにセンチメント（-1.0〜1.0）を算出し ai_scores テーブルへ書き込むワークフローを実装。
    - タイムウィンドウ計算（JST 基準 → UTC 変換）と記事トリミング（_MAX_ARTICLES_PER_STOCK、_MAX_CHARS_PER_STOCK）。
    - バッチ処理（最大 _BATCH_SIZE=20）・JSON Mode を使った堅牢なレスポンス検証・スコアクリップ、リトライ（429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフ）。
    - DuckDB への書き込みは部分置換（対象コードのみ DELETE → INSERT）で冪等性と部分失敗時の保護を実装。DuckDB executemany の空リスト制約に対応。
  - regime_detector.py
    - ETF 1321 の ma200 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジームを判定（'bull' / 'neutral' / 'bear'）。
    - マクロキーワードで raw_news をフィルタし、LLM 呼び出しは記事がある場合のみ行う。API 失敗時は macro_sentiment = 0.0 にフォールバック。
    - レジーム判定結果を market_regime テーブルへ冪等に書き込むトランザクション処理を実装。
  - ai パッケージの __init__ で score_news をエクスポート。
  - 両モジュールとも OpenAI クライアント呼び出しはテストで差し替え可能に実装（_call_openai_api を個別に定義）。

- 監視ログ永続化レイヤを追加（src/kabusys/monitoring/monitoring_db.py）
  - SQLite 接続に対して 5 テーブル（system_status / trade_logs / positions / risk_logs / ...）と必要なインデックスを作成する init_monitoring_db を実装（冪等実行）。
  - テーブルは監視用途のみ（ビジネスロジックを持たない読み書き層）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Important behavior
- OpenAI API を使う機能（news_nlp, regime_detector）は API キーが必須。api_key を引数で渡すか環境変数 OPENAI_API_KEY を設定する必要がある。未設定時は ValueError を送出する箇所あり。
- .env 自動読み込みはパッケージロード時に一度実行される。テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して無効化可能。
- DuckDB / SQLite に依存する機能は、期待するテーブルスキーマ（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime 等）が存在する前提で動作する。
- レジーム／ファクター計算はルックアヘッドバイアス対策として target_date の扱いに注意して実装されている（target_date 未満のデータのみを使用する等）。

---

今後のリリースではテストカバレッジ、エラーハンドリングの拡張、銘柄ごとの lot_size を銘柄マスタで扱う拡張、パフォーマンス改善（DuckDB のクエリ最適化）などを予定しています。