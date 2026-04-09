# Changelog

すべての注目すべき変更はこのファイルに記載します。
このプロジェクトは Keep a Changelog の形式に従います。
セマンティックバージョニングを採用します。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-09

### Added
- 基本パッケージ初期実装（kabusys v0.1.0）
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 環境変数・設定管理
  - src/kabusys/config.py
    - .env/.env.local 自動読み込み機能（プロジェクトルートを .git または pyproject.toml から検出）。
    - 読み込み優先度: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - .env パーサは export 形式、クォート／エスケープ、インラインコメント等に対応。
    - 必須変数検査（_require）や、PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL 等のバリデーションを実装。
    - 各種パス設定（DuckDB / SQLite / PID / Kill flag 等）、監視閾値、LINE / kabuAPI / J-Quants トークンなどの設定プロパティを提供。

- ポートフォリオ構築ロジック（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: スコア降順＋タイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分。スコア合計が0の場合のフォールバック（等配分）と警告出力。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター比率に基づく新規候補の除外（unknown セクターは適用除外）。
    - calc_regime_multiplier: market regime に対する投下資金乗数（bull/neutral/bear）と未知レジームのフォールバック。警告ログあり。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数算出、単元株（lot_size）丸め、per-position と aggregate の上限、コストバッファ考慮によるスケーリングと残差再配分。
    - risk_based では stop_loss_pct/risk_pct を利用した株数計算。
    - aggregate cap 超過時にスケールダウンし、残余で lot 単位配分を行うロジックを実装。
  - パッケージエクスポート: src/kabusys/portfolio/__init__.py で主要関数を公開。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離の算出（DuckDB prices_daily 使用）。不足データに対する None の扱い。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比の算出。true_range 計算で NULL 伝播を制御。
    - calc_value: raw_financials から直近財務データを取り出し PER / ROE を算出（prices_daily と結合）。
    - DuckDB を利用した高速集約 SQL ベース実装。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: target_date から指定ホライズン先の将来リターンを一度のクエリで取得。horizons のバリデーションを実装。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）算出。データ不足時は None を返す。
    - rank / factor_summary: ランク付け（同順位は平均ランク）およびカラム統計（count/mean/std/min/max/median）を標準ライブラリのみで実装。
  - エクスポート: src/kabusys/research/__init__.py で主要関数と zscore_normalize を公開（zscore_normalize は kabusys.data.stats から委譲）。

- AI（LLM）統合機能
  - src/kabusys/ai/news_nlp.py
    - raw_news テーブルから銘柄ごとに記事を集計し、OpenAI（gpt-4o-mini）でセンチメントを取得して ai_scores テーブルへ書き込むフローを実装。
    - バッチ処理（最大20銘柄/コール）、記事数・文字数上限（銘柄ごとに最大記事数/文字数でトリム）、JSON Mode を想定したレスポンス検証を実装。
    - 429/ネットワーク/タイムアウト/5xx を対象に指数バックオフでリトライ。その他エラーはフェイルセーフでスキップ。
    - スコアは ±1.0 にクリップ。部分失敗時の安全な DB 更新（対象コードのみ DELETE→INSERT）を実装。
    - OPENAI_API_KEY の必須チェック（引数 or 環境変数）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の MA200 乖離（70%）とマクロニュース LLM センチメント（30%）を合成して market_regime を算出・DBへ保存。
    - マクロニュースのキーワードフィルタ、最大記事数、LLM 呼び出し（gpt-4o-mini）、再試行・エラー時の macro_sentiment=0.0 フォールバックを実装。
    - レジームスコア合成ロジックと閾値に基づくラベル化（bull/neutral/bear）を実装。
  - 注意: news_nlp と regime_detector はそれぞれ独立した _call_openai_api 実装を持つ（モジュール間での内部関数共有を行わない設計）。

- 監視ログ永続化層（SQLite）
  - src/kabusys/monitoring/monitoring_db.py
    - init_monitoring_db: system_status, trade_logs, positions, risk_logs 等のテーブルとインデックスを冪等に作成するスクリプトを実装（SQLite）。

### Changed
- 初期リリースのため該当なし（新規追加のみ）。

### Fixed
- 初期リリースのため該当なし。

### Removed
- 該当なし

### Security
- OpenAI API キー等の機密情報は環境変数から取得する設計。自動 .env ロードは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Notes / Known limitations / TODO
- .env 読み込みはプロジェクトルート検出に __file__ の親ディレクトリを用いるため、汎用的だが特殊な配布環境では自動ロードがスキップされることがある。
- apply_sector_cap: price_map に価格ゼロがあるとエクスポージャー過小見積りとなり誤判定の恐れあり（TODO: 前日終値や取得原価でのフォールバックを検討）。
- position_sizing: 単元株（lot_size）は現状全銘柄共通に固定。将来的に銘柄別 lot_map に拡張する予定（TODO コメントあり）。
- AI モジュールは gpt-4o-mini を想定しているが、OpenAI SDK の将来変更により status_code 等の扱いが変わる可能性があるためエラー処理は堅牢化している。
- DuckDB executemany に関する互換性対応（空リストの扱い）を考慮した実装を行っている（ai_scores の書き込み処理）。
- news_nlp / regime_detector は API 呼び出しのミドル層として単純な retry/backoff 戦略を実装しているが、運用でのレート制御は利用側で行うことを推奨。
- research モジュールは pandas 等に依存せず標準ライブラリ + DuckDB のみで実装しているため、既存の分析ワークフローに組み込みやすい反面、大規模カバレッジでの最適化余地がある。

---

参考: Keep a Changelog — https://keepachangelog.com/ja/1.0.0/