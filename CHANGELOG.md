# Changelog

すべての変更は「Keep a Changelog」形式に従い、セマンティックバージョニングを採用しています。  

- 既存の変更点はコードベースから推測して記載しています。  
- 日付は現時点（このCHANGELOG生成時）の日付を使用しています。  

## [Unreleased]

## [0.1.0] - 2026-03-28
初回公開リリース。日本株自動売買プラットフォーム「KabuSys」のコア機能群を実装・追加。

### Added
- パッケージ基盤
  - パッケージ初期化: kabusys パッケージ（__version__ = 0.1.0）。
  - パブリックサブパッケージ一覧を __all__ に定義: data, strategy, execution, monitoring（将来の拡張を想定）。

- 環境設定・設定管理（kabusys.config）
  - .env/.env.local 自動ロード機能を実装（プロジェクトルートの検出は .git または pyproject.toml に依存）。
  - .env パーサを実装:
    - export KEY=val 形式対応、シングル/ダブルクォートのサポート、バックスラッシュエスケープ処理。
    - インラインコメント処理（クォートあり/なしのケースに対応）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト用途）。
  - Settings クラスを実装し、環境変数からの設定読み取りを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルトあり）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）、LOG_LEVEL（検証済み）
    - ヘルパープロパティ: is_live / is_paper / is_dev
  - 必須変数未設定時は ValueError を発生させる _require() を実装。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（calendar_management）:
    - JPX マーケットカレンダーの取り扱い（market_calendar テーブル参照／フォールバック：曜日ベース）。
    - 営業日判定ユーティリティ: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等的に更新（バックフィル・健全性チェックを含む）。
    - テーブル存在チェック・NULL ハンドリング・検索範囲上限（_MAX_SEARCH_DAYS）など堅牢性対策。
  - ETL パイプライン（pipeline, etl）:
    - ETLResult データクラスを公開（ETL 実行結果の集約、品質問題／エラーの記録）。
    - ETL 設計に合わせた差分取得、バックフィル、品質チェックのためのユーティリティを実装。
    - jquants_client を想定した fetch/save フローを記述（差分取得 → save_* の冪等保存）。
    - DuckDB のテーブル最大日付取得やテーブル存在チェックなどの内部ユーティリティを実装。
  - data.etl で pipeline.ETLResult を再エクスポート。

- ニュース NLP・AI（kabusys.ai）
  - ニュースセンチメント（news_nlp）:
    - score_news(conn, target_date, api_key=None) を実装。
    - 前日 15:00 JST 〜 当日 08:30 JST のウィンドウ計算（calc_news_window）。
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約（最大記事数・文字数トリム）。
    - OpenAI（gpt-4o-mini）へのバッチ送信（チャンクサイズ 20 銘柄）。
    - リトライ（429・ネットワーク・タイムアウト・5xx）を指数バックオフで実装。
    - レスポンス検証（JSON 抽出、results 配列・code・score の妥当性チェック）、スコアを ±1.0 にクリップ。
    - DuckDB への書き込みは部分的置換（該当 code の DELETE → INSERT）で部分失敗時の保護を実現。
    - テスト用フック: _call_openai_api を patch して差し替え可能。
  - 市場レジーム判定（regime_detector）:
    - score_regime(conn, target_date, api_key=None) を実装。
    - ETF 1321 の 200 日移動平均乖離を計算（_calc_ma200_ratio）。
    - マクロキーワードに基づくニュース抽出（_fetch_macro_news）。
    - LLM（gpt-4o-mini）によるマクロセンチメントスコア算出（_score_macro、リトライ・フェイルセーフで macro_sentiment=0.0 を採用）。
    - MA 重み 70% / マクロ重み 30% の合成ロジックで regime_score を算出し "bull"/"neutral"/"bear" をラベル付け。
    - market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
    - news_nlp と意図的に内部関数を共有しない設計（モジュール結合を低減）。
  - いずれの AI モジュールも以下を重視:
    - ルックアヘッドバイアス防止（datetime.today() を直接参照しない、ウィンドウは target_date に基づく）。
    - API 失敗時のフォールバック（例外を上げずに安全なデフォルト値を使用する設計）。
    - レスポンスパース失敗や未知コードに対する耐性。

- リサーチ（kabusys.research）
  - ファクター計算（research.factor_research）:
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。
    - calc_volatility(conn, target_date): 20日 ATR、相対 ATR、20日平均売買代金、出来高変化率（volume_ratio）を計算。
    - calc_value(conn, target_date): PER（EPS がある場合）、ROE を raw_financials と prices_daily から計算。
    - SQL ベースで DuckDB による高速計算、データ不足時は None を返す設計。
  - 特徴量探索（research.feature_exploration）:
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（デフォルト [1,5,21]）を計算。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）を計算。3 レコード未満で None。
    - rank(values): 同順位は平均ランクで扱うランク化ユーティリティ（丸め処理で ties の安定化）。
    - factor_summary(records, columns): count/mean/std/min/max/median を算出する統計サマリー。
  - research パッケージ __all__ で主要関数を公開（calc_momentum, calc_value, calc_volatility, zscore_normalize 等）。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- DuckDB 実装上の互換性考慮:
  - executemany に空リストを渡すと失敗する問題を回避するため、条件付きで executemany を実行。
  - テーブル存在チェックや NULL 値の扱いを明示的に実装し、予期せぬ NULL に対するログ出力とフォールバックを行う。

### Security
- 環境変数による API キー取得を採用。必須キー未設定時に明確なエラーを出すことで誤設定による誤動作を防止。

### Breaking Changes
- 初回リリースのため該当なし。ただし実行に必須な環境変数（OPENAI_API_KEY 等）が存在しない場合は ValueError が発生します。デプロイ前に必要な環境変数の設定を確認してください。

### Notes / Migration
- 必要な環境変数（主なもの）:
  - OPENAI_API_KEY (AI モジュール実行時必須)
  - JQUANTS_REFRESH_TOKEN (J-Quants API)
  - KABU_API_PASSWORD, KABU_API_BASE_URL (kabuステーション接続)
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (通知)
  - DUCKDB_PATH, SQLITE_PATH はデフォルト値あり（必要に応じて上書き可能）
- テスト:
  - OpenAI 呼び出し部分は内部の _call_openai_api を patch してモック可能。ユニットテスト容易性を考慮した設計。

---

参照: この CHANGELOG はソースコードの内容から自動的に推測して作成しています。実際のリリースノートや公開時のドキュメントと照合のうえ必要に応じて修正してください。