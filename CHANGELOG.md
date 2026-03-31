# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) 準拠で管理します。  
このプロジェクトのバージョンは semver を遵守します。

## [0.1.0] - 2026-03-31

初回公開リリース。

### 追加 (Added)
- パッケージ初期化
  - パッケージ名: kabusys。トップレベルで __version__ = "0.1.0" を設定し、主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機構を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env パーサを実装（コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、inline コメント処理に対応）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 環境変数保護機能（OS 環境変数を protected set として上書き保護）を追加。
  - Settings プロパティで主要設定値を取得可能に：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH（Path 型で expanduser 対応）
    - KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL 検証、is_live/is_paper/is_dev

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄単位のセンチメントスコアを算出する機能を実装（score_news）。
  - タイムウィンドウ計算（JST 前日 15:00 ～ 当日 08:30 を UTC に変換）を実装（calc_news_window）。
  - バッチ処理（最大 BATCH_SIZE=20 銘柄）と、1銘柄あたりの最大記事数/文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）を導入。
  - API リトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）とレスポンスの厳密なバリデーションを実装（_validate_and_extract）。
  - スコアは ±1.0 にクリップし、部分失敗時に既存スコアを保護するために書き込みは対象コードに対して DELETE → INSERT の置換方式を採用。
  - テスト容易性のため OpenAI 呼び出し関数をモジュール内で差し替え可能に（unittest.mock.patch により _call_openai_api をモック可能）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）の 200日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定する機能を実装（score_regime）。
  - MA200 比率計算（_calc_ma200_ratio）、マクロニュース抽出（_fetch_macro_news）、LLM でのマクロ評価（_score_macro）および最終スコア合成ロジックを実装。
  - LLM 呼び出し時に JSON パース失敗や API エラー発生時はフェイルセーフで macro_sentiment = 0.0 を採用。
  - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を採用。

- データ処理・ETL（kabusys.data.pipeline / kabusys.data.etl）
  - ETL 実行結果を表現する ETLResult dataclass を実装。取得件数、保存件数、品質チェック結果、エラー一覧などを格納。has_errors / has_quality_errors プロパティ、辞書変換メソッド to_dict を提供。
  - DuckDB を利用したテーブル存在チェック、最大日付取得ユーティリティを追加。
  - ETL 設計に沿った差分更新、バックフィル、品質チェックの方針をコード内に反映（実装の骨格）。

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - market_calendar テーブルを基に営業日判定・検索機能を実装：
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
  - DB にカレンダーデータがない/不完全な場合の曜日ベース（週末は非取引日）フォールバックを実装。
  - calendar_update_job を実装し、J-Quants API（jquants_client 経由）から差分取得して market_calendar を冪等更新（バックフィル、健全性チェックを含む）。
  - 探索上限（_MAX_SEARCH_DAYS）やバックフィル期間（_BACKFILL_DAYS）等の安全措置を導入。

- リサーチ（kabusys.research）
  - ファクター計算・特徴量探索モジュールを実装・公開：
    - calc_momentum（1/3/6ヶ月リターン、ma200乖離）
    - calc_volatility（20日 ATR、相対ATR、平均売買代金、出来高比）
    - calc_value（PER、ROE を raw_financials から結合して計算）
    - calc_forward_returns（任意ホライズンの将来リターンを一括取得）
    - calc_ic（Spearman ランク相関による IC 計算）
    - factor_summary（基本統計量算出）、rank（同順位は平均ランク）
  - DuckDB 上の SQL と Python 標準ライブラリのみで完結する実装（pandas 等に依存しない）。
  - 返り値は (date, code) を含む dict のリスト形式で一貫性を保持。

- モジュール再エクスポート
  - kabusys.data.etl で ETLResult を再エクスポート。
  - ai/__init__.py / research/__init__.py で主要関数を __all__ にて公開。

### 変更 (Changed)
- 実装上の設計判断・方針をドキュメント文字列（docstring）やログに明示化:
  - ルックアヘッドバイアス防止のため、datetime.today() / date.today() に依存しない設計（関数は target_date を入力で受け取る）。
  - DuckDB のバージョン互換性を考慮し、executemany の空リストバインドや配列バインドを避ける書き方を採用。
  - OpenAI の API エラー処理で status_code の有無に対応する安全実装。

### 修正 (Fixed)
- エラーや例外発生時のフォールバック処理を多数追加:
  - OpenAI 呼び出しに対するリトライ/バックオフと、最終的なフォールバック値（macro_sentiment=0.0、スコア未取得時は書き込みスキップ）を明確化。
  - DB 書き込み失敗時は ROLLBACK を試行し、ROLLBACK 自体の失敗もログ出力するように修正。

### 注意点 / 既知の制約 (Notes)
- OpenAI を利用する機能（news_nlp, regime_detector）は API キー（引数または環境変数 OPENAI_API_KEY）が必須。未設定時は ValueError を送出する。
- LLM で想定外のレスポンスが来た場合は安全側のデフォルトを採る設計（例: スコア 0.0、処理スキップ）。
- news_nlp と regime_detector は JSON Mode（response_format={"type": "json_object"}）を前提としているが、実際の SDK 実装差分やレスポンスノイズに備えた復元処理を含む（前後余計なテキストを { ... } 部分で抽出）。
- 一部の機能は jquants_client（外部モジュール）に依存する（カレンダー取得や保存など）。運用には J-Quants の認証情報が必要。

### セキュリティ (Security)
- 環境変数・.env の読み込みに際して、OS 環境変数を protected set として扱い、誤って上書きしない設計を採用。
- パスワード・トークン等は Settings 経由で必須チェックを行い、未設定時は明確なエラーメッセージを返す。

---

将来的なリリースでは、テストカバレッジの追加、OpenAI モデル切替の柔軟化、パフォーマンス改善（大量銘柄処理時の最適化）などを予定しています。不要/追加したい情報があればお知らせください。