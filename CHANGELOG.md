CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に従って記載しています。
リリース日や内容はソースコードの実装内容から推測して記載しています。

Unreleased
----------
（現時点で未リリースの変更はありません）

0.1.0 - 2026-04-09
-----------------

Added
- 基本パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として公開。

- 環境変数 / 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込み（OS 環境変数 > .env.local > .env の優先度）。
  - プロジェクトルートを .git または pyproject.toml を基準に __file__ から探索する実装（CWD 非依存）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサーの実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォートとバックスラッシュエスケープ対応
    - 行内コメント処理（クォート有無での挙動差分）
  - 環境値取得ユーティリティ Settings クラスを提供（プロパティ経由で各種設定を取得）。
  - 必須キーチェック（_require）により未設定時は ValueError を発生。
  - デフォルトや検証ロジックを含む各種設定:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須項目
    - KABU_API_BASE_URL, LINE_*、DB パス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）等のデフォルト値
    - PAPER_FILL_MODE の有効値チェック（instant/partial/never/reject）
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証
    - リソースしきい値（CPU/MEMORY/DISK）や監視用パスの取得

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルを score 降順、同点は signal_rank 昇順でソートして上位 N を返す。
    - calc_equal_weights: 等金額配分（各銘柄 weight = 1/N）。
    - calc_score_weights: スコア比率で配分。全スコアが 0 の場合は等金額にフォールバックし WARNING を出力。
  - risk_adjustment:
    - apply_sector_cap: 現状ポジションを基にセクター別エクスポージャーを計算し、1セクターの比率が上限を超える場合に新規候補を除外。unknown セクターは除外対象にしない。
    - calc_regime_multiplier: market regime（'bull'/'neutral'/'bear'）に応じた乗数（1.0/0.7/0.3）を返す。未知レジームはフォールバックで 1.0、警告ログを出力。
  - position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" | "equal" | "score"）に基づき発注株数を算出。
    - risk_based: 許容リスク率・損切り幅から目標株数を計算し単元（lot_size）で丸める。
    - equal/score: ウェイトに基づく割当て、max_position_pct／max_utilization を考慮。
    - aggregate cap 実装: 全銘柄のコストが available_cash を超える場合はスケールダウンし、端数は lot_size 単位で残差の大きい順に追加配分。
    - cost_buffer（手数料・スリッページ見積）を考慮した保守的コスト見積もり。
    - 単元丸めや price の欠損時のスキップ処理、_max_per_stock による per-stock 上限。

  - パッケージエクスポート: select_candidates / calc_equal_weights / calc_score_weights / calc_position_sizes / apply_sector_cap / calc_regime_multiplier を公開。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離の計算。DuckDB の prices_daily を使用。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。true_range 計算は high/low/prev_close の NULL 伝播を考慮。
    - calc_value: raw_financials から最新の財務データを結合し PER / ROE を計算（PBR・配当は未実装）。
    - SQL を活用した効率的な集計と、データ不足時の None フォールバック。
  - feature_exploration:
    - calc_forward_returns: target_date の終値から指定ホライズン（デフォルト [1,5,21]）後のリターンをまとめて取得。horizons の検証あり。
    - calc_ic: ファクター値と将来リターンのスピアマン順位相関（Spearman ρ）を計算。有効レコードが 3 件未満時は None を返す。
    - rank: 同順位は平均ランクを割り当てる実装（丸め誤差対策として round を使用）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリーを提供。
  - research パッケージのエクスポートに zscore_normalize（kabusys.data.stats から）を含む。

- AI 関連（kabusys.ai）
  - news_nlp:
    - ニュース記事を OpenAI（gpt-4o-mini）でセンチメントスコア化し ai_scores テーブルへ書き込み。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window。
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約（最大件数・最大文字数でトリム）。
    - 最大 _BATCH_SIZE（20）銘柄ずつバッチ送信。API 呼び出しは JSON Mode を期待。
    - 429・ネットワーク断・タイムアウト・5xx を対象に指数バックオフでリトライ。その他エラーは失敗としてスキップ。
    - レスポンスの厳密なバリデーション（JSON パース、results リスト、code/score の型・既知コードチェック、数値変換、±1.0 クリップ）。
    - 書き込みは冪等性を考慮して対象コードのみ DELETE → INSERT（トランザクション）を実行し、部分失敗時に他コードを保護。
    - テスト容易性のため _call_openai_api を patch して差し替え可能な設計。
  - regime_detector:
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出はマクロキーワード群でタイトルをフィルタ。最大記事数を制限。
    - LLM 呼び出しは独立実装（news_nlp と内部関数を共有しない）。
    - API 失敗時は macro_sentiment=0.0 にフォールバックし、処理を継続（フェイルセーフ）。
    - 判定結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - テスト容易性のため _call_openai_api を patch して差し替え可能。

- 監視ログ永続化（kabusys.monitoring）
  - monitoring_db.init_monitoring_db:
    - SQLite 用の監視用テーブル群（system_status, trade_logs, positions, risk_logs 等）とインデックスを作成するスクリプトを提供（冪等）。
    - 監視・トレード・ポジション情報の永続化基盤を整備。

Changed
- （初期リリースのため特記する変更履歴はなし）

Fixed
- （初期リリースのため特記する修正はなし）

Deprecated
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Security
- OpenAI API キーの取り扱いは api_key 引数または環境変数 OPENAI_API_KEY を要求。未設定時は明示的な例外（ValueError）を発生させる箇所あり。
- .env 読み込み時、OS 環境変数は保護（protected）される実装。自動読み込み無効化フラグあり。

Notes / Known limitations / TODOs
- 一部実装で将来的な拡張のための TODO コメントあり:
  - position_sizing: 銘柄ごとの単元（lot_size）を将来的に銘柄マスタで扱う設計に拡張予定。
  - risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少評価される可能性があるため前日終値等のフォールバックを検討。
- DuckDB の executemany に空リストを渡せないバージョン互換の考慮など、実運用での互換性を意識した実装になっている。
- news_nlp / regime_detector は外部 API（OpenAI）に依存するため、API スキーマや SDK の変更には注意が必要（エラー処理である程度耐性あり）。

Acknowledgements
- 設計ノートやコメント内で参照されるドキュメント（PortfolioConstruction.md、StrategyModel.md 等）が実装方針の根拠として多数存在します。リポジトリ内ドキュメントと合わせて参照してください。