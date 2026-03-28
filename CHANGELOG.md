# Changelog

すべての重要な変更は Keep a Changelog の方針に従って記載します。  
現在のバージョン: 0.1.0（初回リリース）

※ 日付はコードスナップショット作成日を使用しています: 2026-03-28

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買プラットフォームのコア機能を提供します。主な追加点は以下のとおりです。

### Added
- パッケージ構成
  - パッケージ名: kabusys（__version__ = 0.1.0）。
  - package-level export: data / strategy / execution / monitoring を公開。

- 環境設定 / ロード
  - 自動 .env ロード機能（プロジェクトルートの .git または pyproject.toml を検出して .env / .env.local を読み込む）。
  - 環境変数パーサーは export 構文、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - Settings クラスを提供し、主要設定値をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live 検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL 検証）
    - is_live / is_paper / is_dev の便宜プロパティ
  - 必須環境変数未設定時は ValueError を発生させて早期検出。

- AI（自然言語処理）モジュール
  - kabusys.ai.news_nlp
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメントスコアを算出。
    - バッチ処理: 最大20銘柄 / チャンク、1銘柄あたり最大10記事・3000文字にトリム。
    - リトライ/バックオフ: 429・ネットワーク断・タイムアウト・5xx は指数バックオフでリトライ。
    - レスポンス検証: JSON パース、results 配列、code/score の存在、既知コードの照合、数値検証。
    - スコアは ±1.0 にクリップ。取得したスコアのみ ai_scores テーブルへ置換的に書き込み（DELETE → INSERT、部分失敗時に既存データを保護）。
    - calc_news_window(target_date) により JST ベースのニュースウィンドウ（前日15:00〜当日08:30）を UTC naive datetime で返却。
    - テスト容易性: _call_openai_api をモック差替え可能。

  - kabusys.ai.regime_detector
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と macro ニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio の計算は target_date 未満のデータのみ使用（ルックアヘッド防止）。
    - マクロニュースは news_nlp.calc_news_window を使ってウィンドウを算出し、タイトルをキーワードフィルタで取得。
    - OpenAI 呼び出し（gpt-4o-mini）を使って JSON 出力（{"macro_sentiment": 数値}）を期待。API 失敗時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）。
    - レジームスコア合成後、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - API キー引数または環境変数 OPENAI_API_KEY からキーを解決。未設定時は ValueError。

- データ（Data platform）モジュール
  - kabusys.data.calendar_management
    - JPX カレンダー管理機能（market_calendar テーブルの読取/更新ヘルパー）。
    - 営業日判定ロジック: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。DB の market_calendar がない場合は曜日ベースのフォールバック（土日非営業日）。
    - next/prev_trading_day は最大探索日数制限（_MAX_SEARCH_DAYS）で無限ループ防止。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等で更新（バックフィル、健全性チェックを実装）。
  - kabusys.data.pipeline / etl
    - ETLResult データクラスを公開（pipeline.ETLResult を etl モジュールで再エクスポート）。
    - ETL パイプラインの設計に基づくユーティリティ（差分取得、保存、品質チェック用フック）。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得等。
    - デフォルトのバックフィルやカレンダー先読み等の定数を定義。

- 研究（Research）モジュール
  - kabusys.research.factor_research
    - モメンタム（1M/3M/6M）、ma200 乖離、ATR（20日）、平均売買代金、出来高比率などのファクター計算関数を提供:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - DuckDB SQL を活用して prices_daily / raw_financials を参照し、(date, code) ベースの辞書リストで返却。
    - 不足データは None を返すように設計。
  - kabusys.research.feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク付けユーティリティ（rank）、ファクター統計サマリ（factor_summary）を提供。
    - calc_ic はスピアマン相関（ランクの Pearson）を実装、最小有効サンプル数は3。
    - 外部ライブラリに依存せず純粋 Python / DuckDB 実装。

- 共通実装上の注意点（設計方針）
  - すべてのアルゴリズムはルックアヘッドバイアス防止のため datetime.today() / date.today() を内部参照しない（外から target_date を受け取る設計）。
  - DB 書き込みは冪等性を重視（削除→挿入、トランザクション制御、ROLLBACK のハンドリング）。
  - OpenAI 呼び出しまわりは堅牢性を重視し、429/ネットワーク/タイムアウト/5xx をリトライ、その他はフォールバックして継続する設計。
  - DuckDB を前提とした SQL と executemany の注意（空リスト回避など）に対応。

### Changed
- （なし、初回リリース）

### Fixed
- （なし、初回リリース）

### Deprecated
- （なし）

### Removed
- （なし）

### Security
- OpenAI API キーや各種トークンは環境変数で管理し、未設定時は明示的に例外を投げることで誤動作を防止。
- .env ロード時に既存の OS 環境変数を保護する機能（protected set）を実装。

### Notes / Limitations
- 実運用には DuckDB データベース（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials 等）のスキーマと事前データが必要です。
- jquants_client や quality モジュール等の外部依存（J-Quants API クライアント）は別途実装／設定が必要です。
- OpenAI 呼び出しは gpt-4o-mini（JSON mode）を前提としているため、API 仕様変更に応じたメンテナンスが必要です。
- 一部の関数はテスト容易性のために内部の API 呼出し関数を patch 可能にしています（例: _call_openai_api）。

---

著者: kabusys 開発チーム（コード内ドキュメントに基づき作成）