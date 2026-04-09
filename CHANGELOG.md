Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

変更履歴
--------

Unreleased
- なし

0.1.0 - 2026-04-09
------------------

Added
- パッケージ初期リリース。
  - バージョン: 0.1.0（src/kabusys/__init__.py）。
- 環境・設定管理モジュール（src/kabusys/config.py）。
  - .env ファイルおよび環境変数から設定を読み込み、自動ロード機能を提供。
  - 自動ロードの探索はパッケージの位置（__file__）を基準に .git または pyproject.toml を探索してプロジェクトルートを特定（CWD 非依存）。
  - 読み込み順序: OS環境変数 > .env.local > .env。既存OS環境変数は protected として上書きされない設計。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用）。
  - .env パーサは export KEY=val 形式、シングル/ダブルクォート、エスケープ、インラインコメントの扱いなどに対応。
  - 設定値取得用 Settings クラスを提供。必須キーチェック（_require）やバリデーション（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）を実装。
  - デフォルト値や Path の expanduser 処理を提供（例: DUCKDB_PATH, SQLITE_PATH 等）。
- ポートフォリオ構築（src/kabusys/portfolio/*）。
  - select_candidates: BUY シグナルのスコア順ソート・上位 N 抽出。
  - calc_equal_weights / calc_score_weights: 等分配およびスコア加重配分（全スコアがゼロの場合は等分配にフォールバックし WARNING）。
  - apply_sector_cap: セクターごとの既存エクスポージャを計算し、1セクター上限超過時に新規候補をブロック（sell_codes による当日売却予定の除外対応）。"unknown" セクターは制限の対象外。
  - calc_regime_multiplier: market regime に基づく投下資金乗数（bull/neutral/bear → 1.0/0.7/0.3、未知は 1.0 にフォールバック）。
  - calc_position_sizes: 発注株数計算（allocation_method: "risk_based" / "equal" / "score"）、
    - 単元株丸め（lot_size、デフォルト 100）、
    - 1銘柄上限、aggregate cap によるスケールダウン（cost_buffer を考慮）、
    - lot_size 単位での再配分ロジックと再現性を考慮した残差処理。
  - 将来的な拡張点をコメントで記載（銘柄別 lot_size など）。
- リサーチ / ファクター計算（src/kabusys/research/*）。
  - calc_momentum: 1M/3M/6M リターンおよび 200 日移動平均乖離を DuckDB 上で計算。データ不足時は None を返す。
  - calc_volatility: 20日ATR（平均真の範囲）、相対ATR、20日平均売買代金、出来高比率を計算。必要行数に満たない場合は None を返す。
  - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を計算（最新の報告日以前の財務データを使用）。
  - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で取得。horizons の検証あり（正の整数かつ <= 252）。
  - calc_ic / rank / factor_summary: スピアマン IC（ランク相関）、ランク計算（同順位は平均ランク）、および基本統計量（count/mean/std/min/max/median）を標準ライブラリのみで実装。
  - zscore_normalize は kabusys.data.stats から再エクスポート。
- AI 関連機能（src/kabusys/ai/*）。
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols からニュースを銘柄別に集約し、OpenAI（gpt-4o-mini）を用いてセンチメントを算出。
    - バッチ処理（最大 20 銘柄/リクエスト）、1銘柄あたり最大記事数・文字数でトリム（デフォルト: 10 件 / 3000 文字）。
    - API 呼び出しのリトライ（429、ネットワーク、タイムアウト、5xx を対象に指数バックオフ）、失敗時はスキップして継続（フェイルセーフ）。
    - レスポンスは JSON モード前提だが前後テキスト混入に対する回復処理を実装。結果は ±1.0 にクリップ。
    - 書き込みは部分失敗に耐える方式（対象コードのみを DELETE → INSERT で置換）。DuckDB executemany の制約回避処理あり。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError。
  - レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の ma200 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で 'bull'/'neutral'/'bear' を判定。
    - マクロニュースはタイトルをキーワードで抽出（複数キーワード定義あり）、記事なし時は LLM 呼び出しをスキップして macro_sentiment=0.0。
    - API リトライ／フォールバックの実装（失敗時は macro_sentiment=0.0）。
    - 判定結果を market_regime テーブルへ冪等書き込み。
- モニタリング永続化層（src/kabusys/monitoring/monitoring_db.py）。
  - SQLite を用いたテーブル作成ユーティリティ（system_status, trade_logs, positions, risk_logs 等のスキーマ作成／インデックス作成）。冪等性あり（CREATE IF NOT EXISTS）。

Changed
- 初回リリースにつき該当なし。

Fixed
- 初回リリースにつき該当なし。

Deprecated
- 初回リリースにつき該当なし。

Removed
- 初回リリースにつき該当なし。

Security
- OpenAI キーは外部に出力しない設計。API キー未設定時は明示的にエラーを出すかフェイルセーフ（モジュールによる）で処理継続。

注意事項 / 既知の制限
- env 読み込み
  - プロジェクトルートが特定できない場合は自動ロードをスキップする（配布後の振る舞いを安全にするため）。
- .env パーサは多くのケースに対応するが、POSIX シェルと完全互換ではない可能性あり。
- price の欠損値（0.0）がある場合、apply_sector_cap のエクスポージャー算出で過少見積りが発生する可能性があり、将来的にフォールバック価格（前日終値等）を導入する予定（コード内に TODO）。
- calc_position_sizes の単元丸めは現状全銘柄共通の lot_size を採用。将来的に銘柄別単元対応へ拡張予定（コード内に TODO）。
- news_nlp / regime_detector の LLM 呼び出しは外部 API に依存するため、実行環境で適切な OPENAI_API_KEY とネットワーク接続が必要。
- AI モジュールは API 失敗時に部分的な結果しか得られない場合があるが、既存の DB データを保護するように書き込み処理を設計している（部分的な DELETE/INSERT）。
- DuckDB / SQLite のバージョン差による executemany 等の挙動差に注意（互換性回避のための実装あり）。

開発メモ / 将来の改善案
- 銘柄別 lot_size のサポート（stocks マスタに lot_size を持たせる）。
- price 欠損時のフォールバックロジック（前日終値・取得原価）。
- .env パーサの更なる堅牢化（より厳密なシェル互換性）。
- AI モジュールのユニットテスト強化（_call_openai_api の patch を利用したモックテスト充実）。

問い合わせ
- バグ報告・機能要望はリポジトリの Issue へお願いします。