# Changelog

すべての重大な変更をここに記録します。本ドキュメントは Keep a Changelog の形式に従います。  

最新リリース: 0.1.0

## [Unreleased]

（今後の変更をここに記載）

---

## [0.1.0] - 2026-03-31

初回リリース。

### Added
- パッケージ基盤
  - パッケージ名: kabusys。パッケージ __init__ で public API として "data", "strategy", "execution", "monitoring" を公開。
  - バージョン定義: __version__ = "0.1.0"。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定をロードする Settings クラスを追加。
  - 自動ロード機構:
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を自動読み込み（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - OS 環境変数を保護する protected キーセットを導入して .env.local による上書きから守る。
  - .env パーサは以下に対応:
    - 空行・コメント行（先頭の # ）を無視。
    - export KEY=val 形式を許可。
    - シングル・ダブルクォート内のバックスラッシュエスケープ処理と対応する閉じクォートの検出。
    - クォートなしの場合、インラインコメント（#）をスペース/タブ前提で除去。
  - Settings による各種環境変数プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH（デフォルト path を返す）
    - 監視用: PID_FILE_PATH、CPU/MEMORY/DISK の閾値（パーセント）
    - システム設定: KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL の検証、および is_live/is_paper/is_dev プロパティ
  - 未設定の必須環境変数参照時に ValueError を送出する _require ユーティリティ。

- AI モジュール (kabusys.ai)
  - ニュース NLP (kabusys.ai.news_nlp)
    - raw_news / news_symbols を集約して銘柄ごとのテキストを生成し、OpenAI の gpt-4o-mini（JSON mode）へバッチで問い合わせて銘柄別センチメント（ai_score）を ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ: target_date の前日 15:00 JST 〜 当日 08:30 JST（内部は UTC で比較する calc_news_window を提供）。
    - バッチ処理: 最大 _BATCH_SIZE（20）銘柄ずつ送信、1銘柄あたりの記事数と文字数を上限（_MAX_ARTICLES_PER_STOCK=10, _MAX_CHARS_PER_STOCK=3000）でトリム。
    - JSON レスポンスの堅牢なバリデーション (_validate_and_extract) と、余計な前後テキストが混入した場合の復元ロジック（最外の {} を抽出）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ（最大回数 _MAX_RETRIES）。
    - API 呼び出しは _call_openai_api を経由（テスト用にモック可能）。
    - DuckDB への書き込みは冪等性を意識（対象コードのみ DELETE → INSERT）し、DuckDB executemany の空リスト制約に配慮。
    - API キーは引数で注入可能。未設定時は環境変数 OPENAI_API_KEY を参照し、未設定だと ValueError。

  - マーケットレジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動）の直近200日終値から ma200_ratio を計算し（ルックアヘッド回避のため target_date 未満のみ使用）、マクロセンチメント（news_nlp を用いた LLM 評価）と組み合わせて日次の市場レジーム（bull/neutral/bear）を判定。
    - 合成式: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)（重み: MA 70%, マクロ30%）。
    - マクロニュースは raw_news からキーワードフィルタ（_MACRO_KEYWORDS）で抽出し、最大 _MAX_MACRO_ARTICLES（20）件を LLM へ送信。
    - OpenAI 呼び出しは gpt-4o-mini、JSON レスポンスのパース、エラー時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - 結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）し、DB 書き込み失敗時には ROLLBACK を試行。

- データ基盤 (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルに基づく営業日判定ユーティリティを提供。
    - 提供関数: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB に値がない場合は曜日ベース（週末除外）でフォールバック。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）やバックフィル・先読みのための定数を導入。
    - 夜間バッチ: calendar_update_job が jquants_client（kabusys.data.jquants_client）から差分取得して market_calendar を更新（_backfill と sanity check を実装）。

  - ETL / パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを導入し、ETL の取得・保存結果、品質チェック結果、エラー情報を集約して返す。
    - 差分取得・バックフィル・品質チェックを想定した設計（jquants_client と quality モジュールに依存）。
    - 内部ユーティリティ: テーブル存在確認や最大日付取得など。

- Research（因子分析） (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を prices_daily から計算。データ不足時は None。
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio を計算（ATR の NULL 伝播やカウント制御を考慮）。
    - calc_value: raw_financials から最新財務を結合し PER / ROE を計算（EPS=0 や欠損は None）。
    - DuckDB のウィンドウ関数を活用した実装と、target_date ベースの算出（ルックアヘッド回避）。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 各ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を用いて一括算出。horizons のバリデーションあり（1〜252）。
    - calc_ic: ファクター値と将来リターン間の Spearman ランク相関（IC）を計算。行数不足や分散ゼロは None を返す。
    - rank: 同順位は平均ランクで扱うランク付けユーティリティ（round(..., 12) により浮動小数丸めの ties を安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ。

- テスト容易性・堅牢性
  - OpenAI 呼び出しは各モジュール内の _call_openai_api を通す設計で、テスト時に patch して差し替え可能。
  - LLM レスポンスの冗長なテキスト混入や型の不整合を許容して復元・バリデーションするロジックを実装。
  - DB 書き込みはトランザクション制御（BEGIN/COMMIT/ROLLBACK）を行い、部分失敗時に既存データを不必要に消さない実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーの取り扱いは引数注入または環境変数 OPENAI_API_KEY を使用。未設定時はエラーを明示的に発生させ安全性を確保。

---

注意:
- 本 CHANGELOG は提示されたソースコードの実装内容から推測して作成しています。実際のリリースノートとして使用する場合は、追加の検証・補足情報（実装者コメント、リリース日、既知の制限や移行手順など）を反映してください。