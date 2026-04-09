# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠し、セマンティックバージョニングを使用します。日付はパッケージの現行バージョン（__version__ = "0.1.0"）に合わせています。

## [Unreleased]

## [0.1.0] - 2026-04-09
初期リリース。以下の主要機能・モジュールを実装。

### Added
- パッケージ基盤
  - パッケージ初期化: kabusys パッケージの公開 API を定義（data, strategy, execution, monitoring）。
  - バージョン情報: __version__ = "0.1.0" を設定。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（読み込み優先順位: OS環境変数 > .env.local > .env）。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を探索して判定。CWD に依存しない）。
  - .env パーサーを実装（コメント、export 形式、クォート、エスケープ、インラインコメント扱いに対応）。
  - 環境変数上書き制御（override, protected）をサポートし、OS 環境変数の保護を提供。
  - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を導入（テストで利用可能）。
  - Settings クラスを実装し、J-Quants / kabuAPI / LINE / DB / 監視 / システム関連の設定プロパティを提供。
    - 必須変数取得用の _require()（未設定時は ValueError を送出）。
    - env, log_level 等の値検証（許容値チェックと不正値時の ValueError）。
    - PAPER_FILL_MODE 等の特定設定に対するバリデーションとデフォルト値設定。
    - ファイルパスは Path オブジェクトで返却（expanduser を適用）。

- AI（自然言語処理）モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode で一括評価して ai_scores テーブルへ書き込み。
    - タイムウィンドウ計算（JST 前日 15:00 ～ 当日 08:30 を UTC に変換）を提供 calc_news_window().
    - バッチ送信（最大 20 銘柄）とトークン肥大対策（1銘柄あたり最大記事数・文字数の制限）。
    - API 呼び出しのリトライ（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ）と一時エラーのログ出力。
    - レスポンスの厳格なバリデーション（JSON 抽出、results リスト、各要素の code/score チェック、未知コードは無視、スコアを ±1 にクリップ）。
    - 書き込み時は部分失敗を考慮し、取得したコードのみ DELETE→INSERT（DuckDB の executemany の空配列問題に対応）。
    - テスト用に _call_openai_api を patch 可能（ユニットテスト容易化）。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で regime を判定（bull/neutral/bear）。
    - マクロキーワードに基づく記事フィルタリング、OpenAI によるマクロセンチメント算出（JSON パース）、スコア合成ロジックを実装。
    - API リトライ方針（RateLimit / 接続失敗 / タイムアウト / 5xx）とフェイルセーフ（API エラー時は macro_sentiment=0.0）。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）と、失敗時の ROLLBACK/ログ処理。
    - テスト容易性のため _call_openai_api を patch 可能。

- データプラットフォーム (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを用いた営業日判定ユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得のときは曜日ベース（週末は非営業日）のフォールバックを提供。
    - next/prev/get_trading_days は DB の登録値優先・未登録日は曜日フォールバックで一貫した結果を返す。
    - 夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants API から差分取得、バックフィルや健全性チェックを含む）。J-Quants クライアント呼び出しは jquants_client 経由。
    - 最大探索日数やバックフィル・先読み日数等の安全パラメータを導入（_MAX_SEARCH_DAYS, _CALENDAR_LOOKAHEAD_DAYS, _BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS）。

  - ETL パイプライン (kabusys.data.pipeline)
    - ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラー等の集計と to_dict メソッド）。
    - 差分更新・バックフィル・品質チェック方針を明記した ETL パイプライン設計。
    - 外部に ETLResult を公開するための再エクスポート (kabusys.data.etl)。

- リサーチ（因子・特徴量探索） (kabusys.research)
  - factor_research モジュールを実装:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。データ不足は None。
    - calc_value: raw_financials から最新の財務データを取得し PER / ROE を計算（EPS が 0/欠損の場合は None）。
    - DuckDB を使った SQL + ウィンドウ関数で効率的に計算。
  - feature_exploration モジュールを実装:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを取得。horizons のバリデーションあり。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算。レコード不足時は None。
    - rank: 同順位は平均ランクを割り当てるランク関数（丸めで ties の検出誤差を抑制）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

### Changed
- 設計方針・安全対策の反映（全モジュール共通）
  - ルックアヘッドバイアス防止のため、datetime.today() / date.today() を直接参照しない設計を多数の関数で採用（target_date を引数で受ける方式）。
  - API 失敗時はフェイルセーフ（例: スコアは 0.0 を用いる、処理をスキップして継続）とし、単一障害が全体を停止しないように実装。
  - DuckDB の互換性考慮（executemany の空リスト非対応への対処）や日付型取り扱いのユーティリティ化(_to_date)。

### Fixed
- .env パーサーの細かな実装（クォート内のバックスラッシュエスケープ、export プレフィックス、インラインコメントの取り扱い）により現実的な .env フォーマットの互換性を確保。
- OpenAI API 周り:
  - JSON Mode のレスポンスに前後の余計なテキストが混ざるケースに対応するため、最外側の JSON オブジェクト { ... } を抽出してパースを試みる復元処理を追加。
  - APIError の status_code の有無に対して安全に扱う処理を追加（getattr を使用）。
- DB トランザクションの安全化:
  - 書き込み失敗時に ROLLBACK を試み、ROLLBACK 自体が失敗した場合に警告ログを出すことで障害調査を容易に。

### Security
- 環境変数の読み込みと保護（protected set）により OS 環境変数を意図せず上書きしない挙動を確保。
- API キー未設定時は明示的な ValueError を投げることで誤操作を防止。

---

注記:
- 本 CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノートに含めるべき追加情報（既知の制限、互換性、デプロイ手順、マイグレーション手順など）があれば追記してください。