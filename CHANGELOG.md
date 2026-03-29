# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルではパッケージのリリースごとの追加・変更点・修正点を日本語でまとめています。

なお、本リポジトリのバージョンはパッケージルートの __version__ に合わせて 0.1.0 としています。

## [Unreleased]
- （特になし）

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買用のコアライブラリ群を初めて公開。

### Added
- パッケージのエントリポイント
  - `kabusys.__init__` を追加。バージョン情報と主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境設定管理
  - `kabusys.config.Settings` を追加。環境変数／.env ファイルからの設定読み込み、必須キー検証を行うプロパティを提供。
  - .env 自動読み込み機構を実装（優先順位: OS 環境変数 > .env.local > .env）。プロジェクトルート判定は .git または pyproject.toml を探索して行うため、CWD に依存しない設計。
  - .env パーサ実装: export 形式、クォート文字列、インラインコメント対応などを考慮した堅牢なパース処理。
  - 自動読み込みを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - 設定で参照される必須環境変数:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - DB パスのデフォルト: DuckDB `data/kabusys.duckdb`、SQLite `data/monitoring.db`
  - KABUSYS_ENV と LOG_LEVEL の検証（許容値でない場合は ValueError を送出）

- AI（自然言語処理）モジュール
  - `kabusys.ai.news_nlp.score_news` を追加。
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント評価を行い、結果を `ai_scores` テーブルへ書き込む。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB と比較）。
    - バッチ処理（最大 20 銘柄 / リクエスト）、1 銘柄あたりの記事数制限・文字数トリム等のトークン肥大化対策。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results フィールド、コード照合、数値チェック）を実装し、不正レスポンスやパース失敗はスキップしてフェイルセーフに継続。
    - DuckDB の executemany の制約（空リスト不可）への互換考慮を実装。
    - API キーは引数 api_key または環境変数 OPENAI_API_KEY から解決（未設定時は ValueError）。

  - `kabusys.ai.regime_detector.score_regime` を追加。
    - ETF (1321) の 200 日移動平均乖離（ウエイト 70%）とニュース由来のマクロセンチメント（ウエイト 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定し、`market_regime` テーブルへ冪等的に書き込む。
    - マクロセンチメントは `news_nlp.calc_news_window` で取得する記事タイトルを OpenAI へ送り JSON で受け取り解析。
    - API エラー時のフェイルセーフ: macro_sentiment = 0.0 を採用。
    - リトライ・バックオフや 5xx 判定の扱いを備えた堅牢な OpenAI 呼び出し実装。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の形で冪等性を確保し、失敗時は ROLLBACK 実行。

  - 共通事項:
    - AI モジュールの OpenAI 呼び出し部分は内部で差し替え可能（テスト容易性のため `_call_openai_api` を patch 可能に実装）。
    - スコアは定義された範囲（ニュース ±1.0、レジーム -1.0〜1.0）にクリップ。

- Data（データ基盤）モジュール
  - `kabusys.data.pipeline.ETLResult` を追加（ETL 実行結果の dataclass）。
  - `kabusys.data.etl` で ETLResult を再エクスポート。
  - `kabusys.data.calendar_management` を追加。
    - JPX マーケットカレンダーを扱うユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - market_calendar が未取得時は曜日ベース（平日）でフォールバックする一貫した動作。
    - calendar_update_job を実装。J-Quants からの差分フェッチ（lookahead / backfill / sanity check を考慮）と保存ロジックを備える。
    - 最大探索日数やバックフィル、健全性チェックのパラメータを定義。

  - `kabusys.data.pipeline`（ETL パイプライン）
    - 差分取得、idempotent 保存（jquants_client の save_* を想定）、品質チェック取得（quality モジュールを利用）までの ETL ワークフロー設計を反映。
    - DuckDB のテーブル最大日付取得等のヘルパー実装。
    - ETLResult に品質問題・エラーを収集して戻す設計。

- Research（リサーチ）モジュール
  - `kabusys.research.factor_research`
    - Momentum / Volatility / Value（per, roe）等の定量ファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB を用いたウィンドウ関数と SQL ベースの計算により、各銘柄のファクターを出力（date, code キー）。
    - 必要データ不足時に None を返す堅牢な取り扱い。

  - `kabusys.research.feature_exploration`
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク関数（rank）、統計サマリー（factor_summary）を実装。
    - 外部ライブラリに頼らず標準ライブラリのみで実装（テスト容易性・軽量化）。

  - `kabusys.research.__init__` で主要関数をエクスポート。

### Changed
- 初回リリースのため該当なし（新規追加が中心）。

### Fixed
- 初回リリースのため該当なし。

### Notes / 実装上の重要ポイント（ユーザ向け）
- OpenAI API の使用
  - AI 関連関数（score_news, score_regime）は api_key 引数を受け取り、未指定時は環境変数 OPENAI_API_KEY を参照します。どちらも未設定の場合は ValueError を送出します。
  - 使用モデルはデフォルトで gpt-4o-mini。レスポンスは JSON モードを期待します。
  - API の一時的失敗時はログを出力してリトライまたはスキップして処理を続行する設計（フェイルセーフ）。

- 環境変数の自動読み込み
  - プロジェクトルートが検出できる場合（.git または pyproject.toml の存在）、起動時に .env と .env.local を自動的に読み込みます。既存 OS 環境変数は保護されます。
  - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- DB（DuckDB）との互換性
  - DuckDB のバージョン差異を考慮した実装（例: executemany に空リストを渡せない問題、配列バインドの不安定性など）に対応しています。

- ルックアヘッドバイアス対策
  - AI モジュール・リサーチモジュールともに内部で datetime.today()/date.today() を直接参照しない設計です。target_date を明示的に渡して過去データだけに基づき計算・評価します。

- テストしやすさ
  - OpenAI 呼び出し箇所は内部関数をパッチ可能に実装しており、ユニットテストでモックを差し替えやすくしています。

### Breaking Changes
- 初回リリースのため該当なし。

### Security
- セキュリティ関連の既知の問題は無し（初回公開時点）。

---

今後のリリースでは、strategy / execution / monitoring サブパッケージの実装や CI テスト、ドキュメント追加、型アノテーション強化、より詳細な品質チェックロジックなどを予定しています。必要であれば CHANGELOG の項目をより詳細に分解して更新します。