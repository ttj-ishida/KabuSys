# Changelog

すべての重要な変更はこのファイルに記録します。本ドキュメントは「Keep a Changelog」規約に準拠します。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]

（現時点のコードベースは初回公開に相当するため、主要な変更は 0.1.0 に含めています）

## [0.1.0] - 2026-03-28

初回公開リリース。本バージョンは日本株のデータ取得・ETL・リサーチ・AIベースのニュースセンチメント解析・市場レジーム判定・マーケットカレンダー管理などの基盤機能を含みます。

### Added
- パッケージの初期化と公開 API
  - パッケージルートにバージョン情報を追加（kabusys.__version__ = "0.1.0"）。
  - 公開モジュール一覧を kabusys.__all__ に設定（"data", "strategy", "execution", "monitoring"）。

- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルート自動検出、.env / .env.local 読み込み）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサーは export プレフィックス・引用符内のエスケープ・インラインコメント等に対応。
  - Settings クラスを提供し、主要な設定項目をプロパティとして公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）, LOG_LEVEL の検証
    - ヘルパープロパティ: is_live / is_paper / is_dev

- AI モジュール（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp.score_news）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを評価。
    - バッチ（最大20銘柄）での API 呼び出し、各銘柄は最大記事数・文字数でトリム。
    - JSON Mode を利用した厳格なレスポンスバリデーション（results リスト・code/score 検証）。
    - リトライ (429 / ネットワーク断 / タイムアウト / 5xx) は指数バックオフ。その他エラーは該当チャンクをスキップ（フェイルセーフ）。
    - スコアは ±1.0 にクリップ。書き込みは冪等（DELETE → INSERT）で部分失敗時に既存データを保護。
    - テスト容易性のため OpenAI 呼び出しは _call_openai_api を patch で差し替え可能。
    - 時刻ウィンドウ計算（JSTの前日15:00〜当日08:30 に対応）を calc_news_window として提供。
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定。
    - マクロキーワードを用いて raw_news からタイトルを抽出し OpenAI（gpt-4o-mini）でマクロセンチメントを評価。
    - API エラー時は macro_sentiment=0.0 のフェイルセーフ、内部で最大リトライ回数を指定。
    - レジームの計算結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - テスト容易性のため OpenAI 呼び出し単位をモジュール内で分離。

- データ / ETL（kabusys.data）
  - ETL 結果を表すデータクラス ETLResult を公開（kabusys.data.etl 経由で再エクスポート）。
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得、バックフィル、品質チェック（quality モジュール連携）を想定した設計。
    - DuckDB に対する最大日付取得等のユーティリティを実装。
    - ETLResult に品質問題・エラーの要約を含める機能。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを用いた営業日判定 API: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - J-Quants API からの差分フェッチを行う calendar_update_job（バックフィルと健全性チェックを含む）。
    - DB にデータがない場合は曜日ベースのフォールバック（土日非営業）を使用する堅牢な設計。

- リサーチ / ファクター（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M、ma200乖離）、Volatility（20日ATR、相対ATR、出来高比等）、Value（PER, ROE）を DuckDB の prices_daily / raw_financials から計算する関数を提供:
      - calc_momentum, calc_volatility, calc_value
    - データ不足時の None 処理、営業日スキャンバッファ等を考慮した実装。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns、可変ホライズン対応）
    - IC 計算（calc_ic: スピアマンランク相関）、ランク変換ユーティリティ rank
    - 統計サマリー（factor_summary）
  - いずれも外部ライブラリに依存せず、DuckDB と標準ライブラリのみで実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーの取り扱いは引数または環境変数 OPENAI_API_KEY から取得し、未設定時は ValueError を投げて呼び出し側で扱えるようにしています。
- 環境変数の自動読み込みでは既存の OS 環境変数を保護するロジックを導入（.env.local の override を制御）。

### Notes / Design decisions / Known limitations
- ルックアヘッドバイアス対策として、いかなる処理も内部で datetime.today() / date.today() を直接参照せず、関数呼び出し時に target_date を明示的に与える設計を採用。
- OpenAI 呼び出しは JSON Mode（response_format={"type": "json_object"}）を前提にしているが、稀に前後に余計なテキストが混在するケースへの復元ロジックを実装。
- ai_score と sentiment_score は現フェーズでは同値で格納する設計（将来的に差分化の余地あり）。
- calc_value では現バージョンで PBR や配当利回りは未実装。
- DuckDB 側の executemany に関する互換性（空リスト不可など）を考慮した実装を行っているため、DuckDB のバージョン差異に対して安定性を確保。
- テストの容易さを重視し、外部 API 呼び出し（OpenAI）は各モジュールで patch 可能なヘルパー関数を用意。

### Developers / Contributors
- 初回開発によるリリース（ソースコードからの推測で記載）。

---

今後のリリースでは、ストラテジー実装、実行エンジン（kabu ステーション連携）、監視 / アラート機能の強化、さらに財務指標の拡張（PBR・配当利回り等）やテストカバレッジ向上を予定しています。