Keep a Changelog
=================

すべての注目すべき変更点をこのファイルに記録します。  
このプロジェクトでは「Keep a Changelog」規約に準拠し、セマンティックバージョニングを採用しています。

Unreleased
---------

- なし（初期リリースのみ）

0.1.0 - 2026-03-28
-----------------

Added
- 基本パッケージを追加
  - パッケージ名: kabusys（version: 0.1.0）
  - パッケージ公開物: data, strategy, execution, monitoring（top-level __all__）

- 設定 / 環境変数管理（kabusys.config）
  - .env / .env.local 自動読み込み機能を実装（読み込み順序: OS 環境 > .env.local > .env）。
  - プロジェクトルート検出: __file__ から上位ディレクトリを探索し .git または pyproject.toml を基準に判定（CWD に依存しない）。
  - .env パース機能: export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - 自動読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供し、アプリ設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト値あり）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL の検証
    - is_live / is_paper / is_dev ヘルパー

- AI（自然言語処理）機能（kabusys.ai）
  - news_nlp モジュール（kabusys.ai.news_nlp）
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を使ってセンチメントを算出。
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST を UTC に変換して扱う（calc_news_window）。
    - バッチ処理（最大 _BATCH_SIZE 銘柄/回）、1 銘柄あたりの記事数・文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - 再試行ポリシー: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ。
    - レスポンスバリデーションとスコアの ±1.0 クリップ、部分成功時でも既存スコアを保護するため部分的に DELETE→INSERT（トランザクション）。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。APIキーが未設定の場合は ValueError。
    - テスト容易性: _call_openai_api をモック可能に実装。

  - regime_detector モジュール（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）200日移動平均乖離（重み70%）と、マクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - MA 計算は target_date 未満データのみを利用（ルックアヘッドバイアス対策）。
    - マクロニュース抽出: raw_news からマクロキーワードでフィルタ（上限 _MAX_MACRO_ARTICLES）。
    - OpenAI 呼び出し（gpt-4o-mini）で JSON を期待、リトライ・エラー時は macro_sentiment=0.0 としてフェイルセーフで継続。
    - 結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。公開 API: score_regime(conn, target_date, api_key=None) → 1（成功）。
    - テスト容易性: _call_openai_api をモック可能に実装。

- データプラットフォーム（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得・保存・品質チェックの流れを実装するための基盤。
    - ETLResult dataclass を公開（kabusys.data.etl は ETLResult を再エクスポート）。
    - DuckDB を用いた最大日付取得、テーブル存在チェックなどのユーティリティを実装。
    - backfill_days / lookahead の考慮・品質チェック結果の集約と to_dict 出力。

  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間更新ジョブ calendar_update_job を実装（J-Quants クライアント経由で差分取得 → 保存）。
    - 営業日判定と操作: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB にカレンダーがない/未登録の日は曜日ベースのフォールバック（週末非営業日）。
    - 最大探索範囲（_MAX_SEARCH_DAYS）やバックフィル日数、健全性チェック（_SANITY_MAX_FUTURE_DAYS）を導入。

- リサーチ（kabusys.research）
  - factor_research モジュール
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20日 ATR 等）、Value（PER, ROE）を計算する関数を実装。
    - DuckDB を用いた SQL ベース実装。関数: calc_momentum, calc_volatility, calc_value。結果は日付・銘柄単位の dict リストで返却。
    - 設計上、prices_daily / raw_financials のみ参照し、外部 API にはアクセスしない。

  - feature_exploration モジュール
    - 将来リターン計算: calc_forward_returns（任意ホライズン対応、入力検証あり）。
    - IC 計算（スピアマンのランク相関）: calc_ic（欠損排除、3 件未満で None を返す）。
    - ランク集合関数: rank（同順位は平均ランク）。
    - 統計サマリー: factor_summary（count/mean/std/min/max/median）。
    - すべて標準ライブラリのみで実装（pandas 等非依存）。

- パッケージ公開整理
  - kabusys.ai.__all__、kabusys.research.__all__ 等で API を明示的にエクスポート。

Security
- 特にセキュリティ脆弱性の修正は含まれません。外部 API キーは環境変数で管理し、必須キー未設定時は明示的にエラーを出す設計。

Changed
- なし（初期公開）

Fixed
- なし（初期公開）

Deprecated
- なし

Removed
- なし

Notes / 設計上の重要点
- ルックアヘッドバイアス回避: AI モジュール・リサーチモジュールは内部で datetime.today() / date.today() を参照せず、明示的な target_date 引数を必須もしくは使用している。
- OpenAI 連携: gpt-4o-mini を想定し JSON Mode を利用。レスポンス破損や API エラーに対して堅牢なフォールバックを実装。
- DuckDB 前提: 内部データストアは DuckDB を想定。SQL クエリ、トランザクション、executemany の互換性考慮（空パラメータを避ける等）。
- テストしやすさ: OpenAI 呼び出し部分はモックしやすいように内部関数で分離。
- 環境変数のデフォルトや必須キー:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（API 呼び出し時）
  - デフォルト: KABUSYS_ENV=development, LOG_LEVEL=INFO, KABU_API_BASE_URL=http://localhost:18080/kabusapi, DUCKDB_PATH=data/kabusys.duckdb, SQLITE_PATH=data/monitoring.db

将来の改善案（メモ）
- OpenAI クライアント抽象化: 現状は OpenAI SDK 直接利用。将来的に抽象化して SDK バージョン差分を吸収する余地あり。
- 並列化: news_nlp のチャンク処理や ETL の並列化による処理速度改善。
- モニタリング / メトリクス: API 呼び出し数・失敗率・処理時間を収集する仕組みを追加。

--- 

（以上がコードベースから推測して作成した CHANGELOG.md の内容です。追加の変更履歴やリリース日付の修正、あるいは過去の履歴を分割/詳細化したい場合はその旨を教えてください。）