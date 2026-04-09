Changelog
=========

すべての変更履歴をここに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-09
--------------------

Added
- パッケージ初期リリース。
- 環境・設定管理モジュールを追加（kabusys.config）。
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env パーサは export 文、引用符内のエスケープ、行内コメント処理などに対応。
  - OS 環境変数を保護する機能（protected keys）を実装。
  - 必須設定取得時に未設定なら ValueError を送出する _require() を提供。
  - 各種設定プロパティを提供（J-Quants / kabuステーション / LINE / DB パス / Paper Trading 設定 / 監視閾値 / ログレベル / 環境種別判定等）。
  - 設定値のバリデーション（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）。

- ポートフォリオ構築モジュールを追加（kabusys.portfolio）。
  - select_candidates: BUY シグナルをスコア降順でソートし上位 N を選択（同点時は signal_rank でタイブレーク）。
  - calc_equal_weights: 等金額配分を計算。
  - calc_score_weights: スコア加重配分を計算。全スコアが 0 の場合は等金額配分へフォールバックして WARNING を出力。
  - apply_sector_cap: セクター集中度（既存ポジションの時価ベース）に応じて新規候補を除外するロジック。unknown セクターは上限適用対象外。
  - calc_regime_multiplier: 市場レジーム（bull / neutral / bear）に応じた投下資金乗数を返す（未知レジームは警告ログ後フォールバック 1.0）。

- ポジションサイズ決定モジュールを追加（kabusys.portfolio.position_sizing）。
  - calc_position_sizes: 複数の allocation_method をサポート（"risk_based" / "equal" / "score"）。
  - risk_based: 許容リスク率 / 損切り率に基づく株数計算。
  - equal/score: 重み（weights）に基づく割当て、per-position 上限・aggregate cap（利用可能現金）・lot_size（単元）考慮。
  - aggregate cap 超過時はスケールダウンし、lot_size 単位で残差配分を行うアルゴリズムを実装。
  - price が無効（None または <=0）の場合はスキップして安全に動作。
  - 将来拡張用に lot_size を銘柄別にする TODO を明記。

- リサーチ（ファクター計算）モジュールを追加（kabusys.research）。
  - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を prices_daily から計算。データ不足時は None。
  - calc_volatility: 20日 ATR（true range の平均）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。必要行数未満は None を返す。
  - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算（EPS が 0/欠損 の場合 PER は None）。
  - research パッケージは zscore_normalize を kabusys.data.stats からエクスポート。
  - 各関数は DuckDB 接続を受け取り SQL + Python で動作するよう設計（外部 API にはアクセスしない）。

- 特徴量探索モジュールを追加（kabusys.research.feature_exploration）。
  - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得するクエリを実装。horizons 引数の検証あり。
  - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。データ不足（有効レコード < 3）時は None。
  - rank: 同順位は平均ランクを与えるランク付けユーティリティ（浮動誤差対策に round で正規化）。
  - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算。

- AI 関連機能を追加（kabusys.ai）。
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメントスコアを生成し ai_scores に書き込む。
    - バッチ処理（最大 _BATCH_SIZE=20）で API 呼び出し、1銘柄あたり最大記事数／最大文字数でトリム。
    - API 呼び出しは再試行（429・ネットワーク・タイムアウト・5xx）を実装（指数バックオフ）。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code/score の型検査、スコアを ±1.0 にクリップ）。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定の場合は ValueError。
    - フェイルセーフ設計：API 失敗やパース失敗は例外を投げずそのチャンクをスキップし、処理継続。
    - DuckDB への書き込みは部分更新（対象コードのみ DELETE → INSERT）し、部分失敗で他コードのスコアを保護。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組み合わせてレジーム判定（bull/neutral/bear）。
    - マクロニュース抽出はキーワードベース（複数キーワード）で title を取得。記事がない場合は LLM 呼び出しをスキップして macro_sentiment=0.0。
    - LLM 呼び出しは再試行（429/ネットワーク/タイムアウト/5xx）を行い、最終的に失敗した場合は macro_sentiment=0.0 へフォールバック。
    - レジームスコアを計算し market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI API キーは引数または環境変数から解決。未設定時は ValueError。

- 監視ログ永続化層を追加（kabusys.monitoring.monitoring_db）。
  - SQLite を使った Monitoring DB 初期化関数 init_monitoring_db を実装。以下を含むテーブルを冪等に作成:
    - system_status（記録時刻、CPU/メモリ/ディスク、プロセス状態）
    - trade_logs（取引ログ、client_order_id、状態等）
    - positions（保有ポジション、平均取得価格、更新時刻）
    - risk_logs（リスク関連ログ） 等（スキーマは初期化スクリプト内に定義）。
  - 必要なインデックスも作成。

Changed
- パッケージメタ情報を追加（kabusys.__init__ に __version__ = "0.1.0" と __all__ を設定）。

Fixed
- （初版のため既知のバグ修正履歴なし）

Security
- OpenAI API キーの取り扱いは環境変数または明示引数のみとし、キー未設定時は例外で通知することで誤操作を抑止。

Notes / Implementation details / Behavior
- ルックアヘッドバイアス防止:
  - news_nlp, regime_detector は datetime.today()/date.today() を参照せず、外部から与えられた target_date を基に処理する。
  - regime_detector の prices_daily クエリは date < target_date の排他条件でルックアヘッドを防止。
- ログ出力:
  - 計算不能・データ不足・API エラー等のケースで適宜 logger.warning/info/debug を出す設計。
- フェイルセーフ:
  - AI API の失敗やパースエラーは大域的な例外にしない（スコア算出対象外として継続）方針。
- 将来の拡張点（コード内 TODO）:
  - 銘柄別単元（lot_size）を stocks マスタ等から取得する拡張の余地。
  - position_sizing の price フォールバック（前日終値や取得原価）による精度向上。

References
- プロジェクト内ドキュメント参照: PortfolioConstruction.md, StrategyModel.md 等（コード内コメントに言及あり）。