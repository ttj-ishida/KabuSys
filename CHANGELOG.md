# Changelog

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

現在のリリース履歴はコードベースから推測して作成しています（初期リリース相当）。

なお、日付はコード解析時点の想定リリース日を使用しています。

## [Unreleased]
- 今後の変更点をここに記載します。

## [0.1.0] - 2026-03-27
最初の公開リリース相当。コア機能群（データ取得・ETL・カレンダー管理・リサーチ・AI スコアリング・設定管理）を実装。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = "0.1.0"）。主要サブパッケージを公開: data, strategy, execution, monitoring。

- 設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml 基準）。
  - 読み込みの挙動:
    - OS 環境変数を保護する protected モード。
    - override フラグで .env.local による上書きが可能。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能（テスト等で利用）。
  - .env 行パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理）。
  - Settings クラスを提供し、環境変数から強い型（Path 等）や検証済み値（env / log_level）を取得可能。
  - 必須設定の判定とエラーメッセージ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID など）。

- データプラットフォーム / ETL (kabusys.data.pipeline, kabusys.data.etl)
  - ETL パイプラインの設計と ETLResult dataclass を実装。取得件数 / 保存件数 / 品質問題 / エラーの集約を行う。
  - 差分更新・バックフィル戦略（デフォルト backfill_days、calendar lookahead）をサポート。
  - DuckDB ベースの最大日付取得ユーティリティ等を実装。

- カレンダー管理 (kabusys.data.calendar_management)
  - JPX マーケットカレンダーの夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants クライアント経由で差分取得し冪等保存）。
  - 営業日判定と関連ユーティリティを実装:
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
  - カレンダー未取得時の曜日ベースフォールバック、最大探索日数制限（_MAX_SEARCH_DAYS）、バックフィル設定、健全性チェックを実装。

- 研究用モジュール (kabusys.research)
  - ファクター計算: calc_momentum, calc_value, calc_volatility（prices_daily / raw_financials を参照）。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
    - Volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率。
    - Value: PER（EPS が 0 か欠損時は None）、ROE（最新報告ベース）。
  - 特徴量探索: calc_forward_returns（複数ホライズン対応）、calc_ic（Spearman ランク相関）、factor_summary（基本統計量）、rank（平均ランク処理）。
  - kabusys.research パッケージで主要関数を公開し、zscore_normalize を kabusys.data.stats から再エクスポート。

- ニュース NLP / AI (kabusys.ai)
  - score_news: raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）を用いて銘柄毎のセンチメント（ai_score）を ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST、DB では UTC で比較）を calc_news_window で計算。
    - 1 銘柄あたり最大記事数・文字数でトリム（_MAX_ARTICLES_PER_STOCK、_MAX_CHARS_PER_STOCK）。
    - バッチ処理（_BATCH_SIZE=20）で複数銘柄をまとめて API に送信。
    - JSON Mode のレスポンス検証、未知コードの無視、スコアの ±1.0 クリップ。
    - リトライ戦略（429、ネットワーク断、タイムアウト、5xx を指数バックオフでリトライ）、フェイルセーフで失敗時は該当チャンクをスキップ。
    - DuckDB に対して部分置換（DELETE→INSERT）で冪等かつ部分失敗耐性を確保。
  - score_regime（kabusys.ai.regime_detector）: ETF (1321) の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ書込む処理を実装。
    - マクロ記事フィルタ（キーワード群）、最大記事数、OpenAI 呼び出し、リトライ、フォールバック（API 失敗時 macro_sentiment=0.0）。
    - レジームスコア合成と閾値判定、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）。
  - OpenAI 呼び出しは Chat Completions + JSON Mode を使用。テスト時に差し替え可能な内部ラッパーを提供。

- エラーハンドリング / 安全設計
  - ルックアヘッドバイアス防止のため、datetime.today() / date.today() を不透明に参照しない設計（各関数は target_date を引数で受ける）。
  - API 呼び出しのリトライとフォールバック（スコア 0.0、または対象チャンクスキップ）を徹底。
  - DuckDB の executemany に関する互換性考慮（空リストを送らないチェック等）。
  - DB 書き込みは冪等性を意識（DELETE → INSERT、ON CONFLICT 想定）し、ROLLBACK の保護ログを実装。

- 設定（Settings）における検証
  - KABUSYS_ENV の許容値（development / paper_trading / live）チェック。
  - LOG_LEVEL の許容値検証（DEBUG, INFO, ...）。
  - duckdb / sqlite のデフォルトパスを Settings で提供。

### Changed
- （初期リリース）コードベースの設計方針と注釈を多数付与。外部 API 依存箇所は最小化し、テスト用の差替えポイントを確保。

### Fixed
- （初期リリース）該当なし（リリース時点で既知の不具合修正は無しと推測）。

### Internal / Notes
- OpenAI SDK の例外（APIError 系）から status_code を安全に取得する実装を導入し、5xx のみリトライ対象とするなど将来の SDK 変更に配慮。
- JSON Mode でも余計な前後テキストが混入するケースを考慮して、最外の {} を抽出して復元する耐性を実装。
- 一部ユーティリティ（_to_date, _table_exists 等）は DuckDB の返却型差異に耐性を持たせている。
- モジュール間のプライベート関数共有を避ける設計（例: _call_openai_api は各モジュールで独自実装しテストで差し替え可能）。

---

開発・運用に関する補足（コードからの推測）
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- ローカルテスト・CI 用に KABUSYS_DISABLE_AUTO_ENV_LOAD を使用して .env 自動読み込みを抑制可能。
- AI モデルは gpt-4o-mini を想定（JSON Mode を使用）。API キーは引数注入または OPENAI_API_KEY 環境変数を想定。

もしリリース日やバージョン番号を別途指定したい場合や、より詳細なモジュール毎の変更ログ（関数レベルの追加/仕様）を追記したい場合は、対象のモジュールや範囲を教えてください。