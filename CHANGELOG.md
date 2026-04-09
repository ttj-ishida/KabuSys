Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。本ファイルは「Keep a Changelog」形式に準拠します。

フォーマット
----------
各リリースには日付（YYYY-MM-DD）を付与します。セクションは少なくとも以下を含みます: Added, Changed, Fixed, Deprecated, Removed, Security（該当なしの場合は省略可）。

Unreleased
----------
（未リリースの変更はここに記載してください）

0.1.0 - 2026-04-09
------------------

Added
- パッケージ初期リリース。__version__ = "0.1.0" を設定。
- 環境・設定管理
  - 自動 .env ロード機能（プロジェクトルートを .git / pyproject.toml から検出して .env, .env.local を読み込む）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサの強化:
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - インラインコメントの扱い（クォート有無で異なるルール）。
  - Settings クラスを提供し環境変数を型変換して取得:
    - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、LINE_CHANNEL_ACCESS_TOKEN、LINE_USER_ID 等。
    - データベースパス用設定: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH。
    - Paper Trading 用の PAPER_FILL_MODE 検証（instant/partial/never/reject）。
    - 監視設定: PID/KILL フラグパス、しきい値（CPU/MEM/DISK）等。
    - システム環境判定: KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL 検証、is_live/is_paper/is_dev ユーティリティ。

- ポートフォリオ構築（純粋関数群、DB 非依存）
  - portfolio_builder:
    - select_candidates: スコア降順＋タイブレークで候補選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全銘柄スコアが 0 の場合は等分にフォールバックし警告ログ）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限（既存保有時価を計算し、上限超過セクターの新規候補を除外。'unknown' セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（'bull'/'neutral'/'bear'）に応じた投下資金乗数（デフォルト: bull=1.0, neutral=0.7, bear=0.3）。未知レジームはフォールバックして 1.0 に。
  - position_sizing:
    - calc_position_sizes: 複数の配分方式に対応（risk_based, equal, score）。
      - risk_based: 許容リスク率、損切り率から株数を計算。
      - equal/score: weight に基づく配分、per-position と aggregate のキャップに対応。
      - 単元株（lot_size）丸め、cost_buffer（手数料・スリッページ見積り）を考慮した合計コストのスケールダウン処理（端数処理は remainder に基づく再配分）。
      - 将来の拡張用に銘柄別 lot_size の TODO を明記。

- リサーチ / ファクター計算（DuckDB 接続を受け取る純粋関数群）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離（データ不足時は None）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率（部分窓でも算出、データ不足は None）。
    - calc_value: raw_financials から最新の財務データを取得して PER/ROE を計算（EPS がゼロ/欠損時は None）。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズンの将来リターンを一クエリで取得（horizons 検証あり）。
    - calc_ic: スピアマンランク相関（Information Coefficient）計算（有効レコード < 3 の場合は None）。
    - rank: 同順位を平均ランクにするランク関数（丸めで ties 検出を安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

  - 設計方針: DuckDB の prices_daily / raw_financials テーブルのみ参照し、外部 API に依存しない。

- AI 関連
  - news_nlp:
    - score_news: raw_news と news_symbols を集約し OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（ai_score）を生成して ai_scores テーブルへ書き込む。
    - 特徴:
      - ニュースウィンドウ計算（JST ベース → UTC 変換）。
      - 1 銘柄あたり記事数および文字数のトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
      - 最大 _BATCH_SIZE=20 銘柄単位でバッチ送信、JSON Mode（厳密 JSON）期待。
      - 429 / ネットワーク / タイムアウト / 5xx を対象とした指数バックオフリトライ。非リトライ例外はスキップして継続。
      - レスポンスバリデーション（JSON 抽出、"results" リスト、code の整合、スコア数値化、±1.0 にクリップ）。
      - DuckDB への書き込みは冪等 DELETE→INSERT（部分失敗時に既存スコアを保護）。
  - regime_detector:
    - score_regime: ETF 1321（日経連動 ETF）の MA200 乖離（重み 70%）とマクロニュース（LLM によるセンチメント、重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込む。
    - マクロ記事抽出はキーワードベース（複数キーワードの ILIKE 条件）、API 失敗時は macro_sentiment=0.0 でフォールバック。
    - レジームスコア合成と閾値に基づくラベリングを実装。
    - OpenAI 呼び出しは独立した private 関数で実装（モジュール間で共有しない設計）。

- 監視 DB 永続化層
  - monitoring_db:
    - init_monitoring_db: SQLite 接続に対して 5 テーブル + インデックスを冪等に作成するユーティリティを提供（system_status, trade_logs, positions, risk_logs を含む）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Known issues / Notes / TODO
- .env 自動ロードはプロジェクトルート検出に依存するため、パッケージ配布後にプロジェクトルートが見つからないと自動ロードをスキップする（意図的挙動）。
- .env パーサ:
  - クォート無しの値中の '#' は直前が空白/タブでない限りコメントと見なさない細かいルールあり。
- risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）だとエクスポージャーが過小評価され、ブロックを逃す可能性がある。将来的に前日終値や取得原価のフォールバックを検討。
- position_sizing:
  - 現状は全銘柄共通の lot_size（デフォルト 100）を使う。将来的に銘柄別 lot_size を持たせる拡張予定（TODO）。
- research モジュールは DuckDB のテーブル構造（prices_daily / raw_financials）に依存。外部 API は使用しない設計。
- AI モジュール:
  - OpenAI API のレスポンスは LLM により期待フォーマットを外れることがあり得るため、堅牢なバリデーションと部分失敗保護を実装しているが、完全な保証はない。
  - rate-limit / server error に対するリトライは一定回数の上限があり、上限到達時は該当チャンクをスキップする挙動。
- monitoring_db スキーマは将来の用途に合わせて拡張される可能性あり。

Authors / Contributing
- 初回リリース。詳細な貢献ガイドラインやテストケースはリポジトリ内ドキュメントに従ってください。

License
- （パッケージの license ファイルに従います。ここでは省略）

-----