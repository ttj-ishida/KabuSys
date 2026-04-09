# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

## [Unreleased]

（現在の差分はありません。次回リリースに追記してください。）

## [0.1.0] - 2026-04-09

初回公開リリース。以下の主要機能・モジュールを追加しました。

### Added
- パッケージ基礎
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージの主要サブモジュールをエクスポート（data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を追加。
    - プロジェクトルート判定は `.git` または `pyproject.toml` を基準（__file__ 起点で親ディレクトリを探索）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能（テスト用）。
    - .env パーサは `export KEY=val`、クォート・エスケープ、インラインコメントの処理に対応。
    - OS 環境変数を保護するため protected キー集合を使用した安全な上書き制御を実装。
  - 必須環境変数取得 `_require()`（未設定時は ValueError を送出）。
  - 各種設定プロパティを提供（J-Quants、kabuステーション、LINE、DB パス、監視閾値、システム環境など）。
    - `PAPER_FILL_MODE` の入力検証（有効値: instant|partial|never|reject）。
    - `KABUSYS_ENV`（development/paper_trading/live）と `LOG_LEVEL` の値検証。
    - DB パスは Path オブジェクトで提供（デフォルト値あり）。

- ポートフォリオ構築（kabusys.portfolio）
  - 銘柄選定・配分ロジック（純関数群、DB 参照なし）
    - select_candidates: スコア降順で上位 N を選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア加重配分を計算。全スコアが 0 の場合は等金額配分にフォールバック（警告ログ）。
  - リスク調整（セクター上限、レジーム乗数）
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合に新規候補を除外（unknown セクターは無視）。
      - 当日売却予定銘柄（sell_codes）をエクスポージャー計算から除外可能。
      - 価格欠損時の注意（TODO: フォールバック価格の検討）。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に基づく投下資金乗数。未知のレジームは 1.0 でフォールバック（警告ログ）。
  - ポジションサイジング
    - calc_position_sizes: 複数の allocation_method をサポート（risk_based / equal / score）。
      - risk_based: 許容リスク率と損切り率からベース株数を算出。
      - equal/score: ウェイトに基づく割当。ポートフォリオ上限・単元株（lot_size）丸め、単銘柄上限や aggregate cap を考慮。
      - cost_buffer（スリッページ・手数料想定）を加味した保守的なコスト見積りとスケーリング。
      - aggregate cap 超過時はスケールダウンし、残余キャッシュで端数補正（lot_size 単位で再配分）。
      - 将来の拡張 TODO: 銘柄別 lot_size をサポートする設計への拡張案あり。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンと 200 日移動平均乖離を DuckDB 上で計算（データ不足時は None）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高変化率を計算（NULL の伝播やカウントに注意）。
    - calc_value: raw_financials から最新財務データを取得して PER, ROE を計算（EPS が 0/欠損時は None）。
    - 各関数は prices_daily / raw_financials のみ参照し、外部 API に依存しない。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得（SQL で LEAD を使用）。horizons の入力チェックを実装。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算。十分なデータがなければ None を返す。
    - rank: 同順位は平均ランクで処理（round で誤差対策）。
    - factor_summary: count/mean/std/min/max/median を計算するシンプルな統計サマリ。

- AI（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - calc_news_window: target_date に対するニュース収集ウィンドウ（JST→UTC 変換）を提供。
    - score_news: raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ保存する処理を実装。
      - バッチ処理（最大 _BATCH_SIZE = 20 銘柄／コール）、1 銘柄あたり記事数・文字数のトリム制御。
      - OpenAI 呼び出しはリトライ（429、ネットワーク断、タイムアウト、5xx）を指数バックオフで実施。その他の例外はフォールトしてスキップ。
      - レスポンスの厳格なバリデーション（JSON 抽出、results リスト、code の一致、score の数値化、±1.0 クリップ）。
      - 書き込みは対象コードのみを DELETE → INSERT で置換（部分失敗時に他コードの既存データを保護）。
      - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。
    - テスト容易性のため、OpenAI 呼び出し箇所は差し替え可能（内部関数を patch してテスト可能）。
  - レジーム判定（kabusys.ai.regime_detector）
    - score_regime: ETF 1321（国内日経連動 ETF）の 200 日 MA 乖離（70% 重み）とマクロニュース LLM センチメント（30% 重み）を合成して日次レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする処理を追加。
      - ma200_ratio は target_date 未満のデータのみを使用（ルックアヘッド防止）。
      - マクロニュースはキーワードフィルタでタイトルを抽出し LLM でセンチメント評価（記事がなければ macro_sentiment=0.0）。
      - LLM 呼び出しはリトライ実装。API 失敗時はフォールバック値を用いる（例外を上位に投げない仕様）。
      - API キーの解決は news_nlp と同様（引数 or OPENAI_API_KEY）。
      - 最終スコアは所定の閾値でラベリング（BULL/BEAR/NEUTRAL）し DB に書き込む。書き込み時は BEGIN/DELETE/INSERT/COMMIT を実施し、失敗時は ROLLBACK を試行。

- 監視ログ永続化（kabusys.monitoring.monitoring_db）
  - SQLite を使った監視ログ DB 初期化関数を追加。
    - 5 テーブル＋インデックスを作成する（冪等）：system_status, trade_logs, positions, risk_logs ...（スキーマ作成のための executescript を実装）。
    - ビジネスロジックは持たず読み書きのみを想定。

- モジュール公開 / エクスポート
  - kabusys.portfolio、kabusys.research、kabusys.ai の public API を __init__ で整理・エクスポート（主要関数を外部から利用可能に）。

### Changed
- 初回リリースにあたり、コードは外部依存（DuckDB, openai）を前提に設計。research モジュールは外部依存ライブラリ（pandas 等）を使わない設計で実装。

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （該当なし）

### Removed
- （該当なし）

### Security
- OpenAI API キーは明示的に引数で渡すか環境変数で設定する方式。キーファイル等の自動読み込みは行わないため、取り扱いに注意。

### Notes / Known issues / TODO
- apply_sector_cap: price_map に価格が欠損（0.0）だとエクスポージャーが過少見積りされ、ブロックが緩くなる可能性あり。将来的に前日終値や取得原価をフォールバックする拡張を検討。
- calc_position_sizes: 現状 lot_size はグローバル固定。将来的に銘柄別 lot map を受け取る拡張を想定（TODO コメントあり）。
- DuckDB への executemany はバージョン依存の制約（空リスト不可）があるため、ai モジュールでは書き込み前に空チェックを行っている。
- OpenAI 呼び出しは外部サービスに依存するため、ネットワーク障害や API の変更により挙動が変わる可能性あり。テスト時は内部呼び出し関数のモックを推奨。

---

このリリースは初期実装を含むため、運用投入前に実運用データでの十分な検証を推奨します。必要があれば CHANGELOG に追記・修正を行ってください。