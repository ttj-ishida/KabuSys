# CHANGELOG

すべての重要な変更を Keep a Changelog の形式で記載します。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買およびデータパイプラインのコア機能を実装しました。

### Added
- パッケージ初期化
  - kabusys パッケージのバージョンを 0.1.0 として公開。パッケージの公開 API は data, strategy, execution, monitoring を意図的に外部公開（src/kabusys/__init__.py）。

- 環境設定管理（kabusys.config）
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。既存の OS 環境変数は保護される。
  - .env パーサを実装（export 形式、クォート内エスケープ、インラインコメント対応）。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - 必須設定を取得するユーティリティ _require と Settings クラスを提供。
  - Settings が参照する主な環境変数:
    - JQUANTS_REFRESH_TOKEN（J-Quants API）
    - KABU_API_PASSWORD, KABU_API_BASE_URL（kabuステーション）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Slack通知）
    - DUCKDB_PATH, SQLITE_PATH（データベースパス）
    - KABUSYS_ENV（development / paper_trading / live）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を元に銘柄ごとのニューステキストを集約・トリムし、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込み。
  - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたり最大記事数/文字数制限、JSON Mode を利用した厳密 JSON パース。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ付きリトライ実装。
  - レスポンスのバリデーション機能（results リスト、code の確認、スコア数値性検証、±1.0 へのクリップ）。
  - テスト容易性のため API 呼び出し関数を差し替え可能に実装（unittest.mock.patch を想定）。
  - 公開 API: score_news(conn, target_date, api_key=None)、calc_news_window(target_date)。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成し、日次で market_regime テーブルへ冪等的に書き込み。
  - マクロキーワードによる raw_news フィルタリング、OpenAI 呼び出し、スコア合成、閾値に基づくラベリング(bull / neutral / bear)。
  - API エラー・パース失敗時は macro_sentiment=0.0 としてフェイルセーフに継続。
  - 公開 API: score_regime(conn, target_date, api_key=None)。

- データ ETL（kabusys.data.pipeline / kabusys.data.etl）
  - ETL の実行結果を表す ETLResult データクラスを実装（取得件数、保存件数、品質問題、エラー集約）。
  - 差分取得、バックフィル方針、品質チェックとの連携を想定した設計（実装はモジュール内ユーティリティを含む）。
  - DuckDB 上のテーブル存在確認、最大日付取得ユーティリティなどを実装。

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - market_calendar テーブルを基に営業日判定 / 前後営業日の計算 / 期間内営業日取得を実装。
  - calendar_update_job による J-Quants からの差分取得 → 冪等保存（バックフィル、健全性チェックを含む）。
  - DB 未取得時は曜日ベース（土日非営業）でフォールバックする堅牢な挙動を採用。
  - next_trading_day / prev_trading_day は探索上限を設けて無限ループを防止。

- リサーチ機能（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB の prices_daily / raw_financials から計算する関数を実装。
    - 公開 API: calc_momentum(conn, target_date), calc_volatility(conn, target_date), calc_value(conn, target_date)
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランキングユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - calc_forward_returns は可変ホライズン対応（デフォルト [1,5,21]）、ホライズン検証（1〜252）。
    - calc_ic はスピアマンのランク相関を実装し、少数レコードや等分散時の安全処理を含む。

- データユーティリティ
  - kabusys.data.etl で ETLResult を再エクスポート。
  - 各モジュールで DuckDB を使用する際の互換性考慮（例: executemany に空リストを渡さない等）を実装。

### Changed
- 新規リリースのため該当なし。

### Fixed
- 新規リリースのため該当なし。

### Security
- OpenAI / J-Quants / Kabu 関連の API キーは環境変数で管理する設計。Settings の必須プロパティは未設定時に ValueError を投げるため、運用時に適切な環境変数設定が必要。
- .env 自動読み込みはデフォルトで有効。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定。

### Notes / Migration
- 必須テーブル（DuckDB 側）:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等が各機能で参照される。初回使用前にスキーマ・初期データを準備してください。
- OpenAI の呼び出しは gpt-4o-mini を前提に JSON Mode（response_format={"type":"json_object"}）を使っています。API のレスポンス形式や SDK の挙動変更に注意してください。
- API エラーやパース失敗時は安全側のデフォルト（中立スコア 0.0、ma200 不足時は 1.0 等）で継続する設計になっているため、ログを監視して部分失敗を検出してください。
- テスト容易性:
  - news_nlp と regime_detector の内部的な OpenAI 呼び出しはモック可能に実装されています（_call_openai_api をパッチする等）。

その他の詳細は各モジュールの docstring を参照してください。