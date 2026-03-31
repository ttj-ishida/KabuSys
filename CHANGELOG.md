# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

現在のバージョン: 0.1.0

## [Unreleased]
- （現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-31
初期リリース。日本株自動売買 / データ基盤 / リサーチ向けのコアユーティリティ群を提供します。主な追加点は以下の通りです。

### Added
- パッケージ基礎
  - kabusys パッケージ初期化（__version__ = 0.1.0、公開モジュール定義）。
- 環境設定管理（kabusys.config）
  - .env/.env.local 自動読み込み機能をプロジェクトルート（.git または pyproject.toml を基準）から実装。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサを独自実装（export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、行末コメントの扱いなどに対応）。
  - 環境変数上書き制御（.env.local は .env を上書き、OS 環境変数は保護）。
  - Settings クラスを提供し、アプリで必要な設定値をプロパティとして安全に取得（必須キー未設定時は ValueError）。
  - 設定値検証: KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の許容値チェック。
  - データベースパス（duckdb, sqlite）を Path 型で取得するユーティリティ。

- データ関連（kabusys.data）
  - カレンダー管理（calendar_management）
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得→冪等保存。
    - 営業日判定・前後営業日取得・期間内営業日取得・SQ日判定のユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB にカレンダーがない場合は曜日ベース（平日）でフォールバックする堅牢設計。
    - 最大探索日数・バックフィル・健全性チェック等の安全パラメータを実装。
  - ETL パイプライン（pipeline, etl）
    - ETLResult データクラスを公開し、ETL の実行結果（取得件数、保存件数、品質問題、エラー）を集約。
    - 差分更新・バックフィル・品質チェックを想定した設計方針を用意。
    - DuckDB のテーブル存在チェック、最大日付取得ユーティリティ等を実装。
  - jquants_client のラッパー（想定、jq 呼び出しを使用）との統合点を用意（calendar 更新や ETL 処理で利用）。

- AI（kabusys.ai）
  - ニュース NLP（news_nlp）
    - raw_news / news_symbols を入力に OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出し ai_scores テーブルへ書き込むバッチ処理を実装。
    - 日時ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST に対応する UTC 範囲）を計算する calc_news_window。
    - 銘柄ごとに最新記事を集約しトリム（記事数・文字数上限）、最大バッチサイズ 20 銘柄で API 呼び出し。
    - API レスポンスの厳密な検証（JSON モードの復元処理、results フォーマット検査、未知コードの無視、数値変換・有限性チェック）。
    - スコアの ±1.0 クリッピング。
    - リトライ戦略（429・ネットワーク断・タイムアウト・5xx に対して指数バックオフ）を実装。その他エラーはスキップして継続するフェイルセーフ。
    - テスト用に _call_openai_api を patch 可能に設計。
    - DuckDB executemany の互換性対策（空パラメータリスト時の挙動を考慮）。
  - 市場レジーム判定（regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - MA 計算は target_date 未満のデータのみ利用しルックアヘッドを防止。
    - マクロニュースはキーワードでフィルタし最大記事数を制限、OpenAI でセンチメントを評価（記事なし時は LLM 呼び出しをスキップ）。
    - OpenAI 呼び出しと再試行の実装、API 失敗時は macro_sentiment=0.0 にフォールバック。
    - 計算結果を market_regime テーブルへ冪等に書き込む（BEGIN / DELETE / INSERT / COMMIT）。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。
- リサーチ（kabusys.research）
  - ファクター計算（factor_research）
    - モメンタム（1M/3M/6M リターン、ma200 偏差）、ボラティリティ（20日 ATR, atr_pct）、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）を計算する関数群を提供（calc_momentum / calc_volatility / calc_value）。
    - DuckDB 上の SQL を主体にして営業日ベースのホライズン計算を行う。データ不足時は None を返す扱い。
  - 特徴量探索（feature_exploration）
    - 将来リターン算出（calc_forward_returns）、IC（Spearman ランク相関）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリ（factor_summary）を実装。
    - pandas 等に依存せず、標準ライブラリ + DuckDB のみで動作する設計。
- 共通ユーティリティ
  - DuckDB を想定した日付変換・テーブル存在チェック等のヘルパー関数を提供。
  - ルックアヘッドバイアスを避けるため、主要な関数は内部で datetime.today()/date.today() を参照しない設計（target_date を明示的に受け取る）。

### Changed
- （初期リリースのため過去の変更はなし）

### Fixed
- DuckDB executemany の空リストバインド制約を考慮し、空リスト時に実行しないガードを追加（news_nlp / score_news の書込み処理等）。
- OpenAI API 呼び出し周りでのエラー処理強化（APIError の status_code の有無に依存しない安全な判定）。

### Security
- 環境変数取得は Settings を通して行うことを想定し、必須キー未設定時は明示的なエラーを通知。
- OS 環境変数の上書きを防ぐ protected セットを導入。

### Notes / Design decisions
- 各種処理は「ルックアヘッドバイアス防止」を重視して設計されており、すべてのスコア／レジーム判定／ETL は明示的な target_date に依存します。
- OpenAI（gpt-4o-mini）呼び出しは JSON Mode を使用することを想定しつつ、実務上のノイズに耐えるパーサを実装しています。
- 部分失敗時のデータ保護（例: ai_scores の置換時に成功したコードのみ差し替える等）を重視しています。
- テストフレンドリーな設計（外部 API 呼び出し点を patch 可能、api_key を引数注入）を意識しています。

---

（今後のリリースでは、発注/実行モジュール、モニタリング、Slack 通知などの統合機能やより細かな品質チェック/メトリクス追加が予定されます。）