# Changelog

すべての注目すべき変更はここに記録します。  
このファイルは Keep a Changelog 準拠で記載しています。

なお、本 CHANGELOG は提示されたソースコードから機能・設計方針を推測して作成した「初期リリース」向けの記録です。

## Unreleased

- なし

## [0.1.0] - 2026-03-26

初期リリース。日本株自動売買プラットフォームのコア機能群を実装しました。主要なコンポーネントは以下の通りです。

### 追加 (Added)

- 全体
  - パッケージ `kabusys` を初期実装。
  - バージョン番号を `0.1.0` に設定。

- 設定管理
  - `kabusys.config.Settings` を実装。環境変数/`.env` ファイルから設定を読み取るための高レベル API を提供。
  - 自動 `.env` ロード機能を実装（プロジェクトルートは `.git` / `pyproject.toml` を探索して判定）。`.env` → `.env.local` の優先度で読み込み。`KABUSYS_DISABLE_AUTO_ENV_LOAD` による無効化も可能。
  - `.env` 行パーサーを実装し、`export KEY=val` 形式、引用符中のエスケープ、インラインコメントの扱いなどに対応。
  - 必須キー取得用 `_require()` と、`KABUSYS_ENV` / `LOG_LEVEL` 等の値検証を実装。
  - DB パス用プロパティ（`duckdb_path`、`sqlite_path`）を実装。

- データプラットフォーム（Data）
  - `kabusys.data.calendar_management`:
    - JPX カレンダーの管理機能を実装。`market_calendar` テーブルを参照し、営業日判定・前後営業日の取得・期間内営業日取得を提供。
    - DB データがない場合の曜日ベースのフォールバックを実装（週末＝休業日）。
    - SQ 日判定、最大探索日数の上限、カレンダー更新バッチ `calendar_update_job` を実装。J-Quants クライアント経由で差分取得 → 冪等的保存（fetch/save 呼び出し）を行う。
    - バックフィル・健全性チェック（未来日チェック）などの運用ロジックを導入。
  - `kabusys.data.pipeline` / `kabusys.data.etl`:
    - ETL の結果を表す `ETLResult` データクラスを実装（取得数／保存数／品質問題／エラー等を含む）。品質チェックの集約や簡易の is-error 判定を提供。
    - DuckDB 上でのテーブル存在チェックや最大日取得等のユーティリティを実装。
    - ETL 設計方針（差分取得、バックフィル、品質チェックは Fail-Fast しない等）をコードに反映。
    - `kabusys.data.etl` から `ETLResult` を再エクスポート。

- AI / NLP
  - `kabusys.ai.news_nlp`:
    - ニュース記事（`raw_news` / `news_symbols`）を銘柄ごとに集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメントスコアを算出する `score_news` を実装。
    - タイムウィンドウ計算 (`calc_news_window`)（JST 基準で前日 15:00 ～ 当日 08:30）を実装し、DuckDB の UTC 保存前提で比較する仕様。
    - 銘柄ごとの記事トリム（記事数・文字数制限）、チャンク（デフォルト 20 銘柄）単位でのバッチ送信、リトライ（429/ネットワーク/5xx に対する指数バックオフ）を実装。
    - レスポンスのバリデーション関数を実装（JSON 抽出、results リストの検証、コード照合、数値検査、±1.0 クリップ）。
    - DuckDB への書き込みは「対象コードのみを置換（DELETE → INSERT）」して部分失敗時の既存データ保護を実施。
  - `kabusys.ai.regime_detector`:
    - 市場レジーム判定ロジック `score_regime` を実装。ETF 1321（日経225 連動）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成し、`market_regime` テーブルへ冪等書き込みを行う。
    - マクロ記事抽出（マクロキーワードでフィルタ）、OpenAI 呼び出し（gpt-4o-mini、JSON Mode）、リトライ、フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - lookahead バイアス防止のため日付の扱いを厳密化（内部で datetime.today() を参照しない等）。

- 研究（Research）
  - `kabusys.research.factor_research`:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER・ROE）を DuckDB クエリで計算する `calc_momentum` / `calc_volatility` / `calc_value` を実装。
    - データ不足時の None 扱いや、200 日未満での ma200_dev None 対応などを実装。
  - `kabusys.research.feature_exploration`:
    - 将来リターン計算 `calc_forward_returns`（horizons デフォルト [1,5,21]、入力検証あり）を実装。1 クエリで複数ホライズンを取得する設計。
    - IC（Information Coefficient）計算 `calc_ic`（Spearman ランク相関）実装、ランク変換ユーティリティ `rank`、ファクター統計要約 `factor_summary` を実装。
    - 外部ライブラリに依存せず標準ライブラリ + DuckDB で完結する実装。

- インフラ／ユーティリティ
  - OpenAI 呼び出し部分はモジュール毎に独立したヘルパー関数として実装（テスト時の差し替えを想定）。
  - 各モジュールで詳細なログ出力を追加（INFO/DEBUG/WARNING の適切な利用）。
  - 多数の定数（バッチサイズ、最大リトライ回数、モデル名、ウィンドウ時間、マクロキーワード等）を明示的に定義。

### 変更 (Changed)

- （初期リリースのため過去リリースからの変更はなし）

### 修正 (Fixed)

- （初期リリースのため修正履歴はなし）

### 制限事項 / 注意事項 (Notes)

- OpenAI API キーは `OPENAI_API_KEY` 環境変数か各関数の `api_key` 引数で提供する必要があります。未設定時は ValueError を送出します。
- DuckDB テーブルスキーマ（`prices_daily`, `raw_news`, `news_symbols`, `ai_scores`, `market_calendar`, `raw_financials` 等）が前提となっています。これらのテーブル作成・スキーマは別途用意する必要があります。
- `kabusys.data` 内で参照している `jquants_client` 等の外部クライアント実装は提示コードには含まれていません（実行時は実装/モックが必要）。
- 一部実装（ファイル断片の関係で続きがある関数等）は提示コードで途中までの実装となっている箇所があります。実運用前に完全実装とテストが必要です。
- 設計方針として「ルックアヘッドバイアス防止」「API障害時のフェイルセーフ」「部分書き込みで既存データを保護」等を優先しています。運用要件に応じてバッチ頻度・バックフィル日数・閾値等のチューニングが必要です。

### セキュリティ (Security)

- 本リリースでは特にセキュリティ修正はありません。環境変数に API キーを保持する設計のため、実運用では適切なシークレット管理（OS/コンテナ/クラウドのシークレットストア）を推奨します。

---

今後の予定（例）
- テストカバレッジの拡充（単体テスト、統合テスト、外部 API のモック）
- jquants / kabu ステーションクライアントの整備（提示コードでの参照実装の追加）
- モデルやバッチパラメータのパラメタライズ、運用モニタリング・アラートの実装

（この CHANGELOG はソースコードの内容から機能・設計を推測して作成しています。実際のリリースノート作成時はコミット履歴・Issue/Ticket 情報を反映してください。）