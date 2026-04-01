# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-01

初期公開リリース。日本株自動売買システムのコアライブラリ群を実装しました。主な機能、設計方針、運用上の注意点は以下の通りです。

### Added
- 基本パッケージ構成
  - kabusys パッケージとサブモジュール（data, research, ai, monitoring, execution, strategy 等の公開インターフェース）。
  - バージョン: 0.1.0（src/kabusys/__init__.py）。

- 環境設定管理（kabusys.config）
  - .env/.env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）。
  - export KEY=val 形式やクォート付き値、インラインコメント処理などを考慮した .env パーサーを実装。
  - OS 環境変数の上書き抑止（protected set）。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - Settings クラスを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等の必須チェック、各種パスや閾値の型変換とバリデーション）。
  - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）と is_live / is_paper / is_dev ユーティリティ。

- AI モジュール（kabusys.ai）
  - ニュースセンチメントスコアリング（news_nlp.score_news）
    - raw_news / news_symbols を集約し、銘柄ごとに記事をまとめて OpenAI（gpt-4o-mini）にバッチ送信してスコアを取得。
    - バッチサイズ、記事・文字数トリム、JSON Mode レスポンス検証、±1.0 クリッピング、429/ネットワーク/5xx に対する指数バックオフリトライを実装。
    - 部分成功時の DB 書き込み保護（該当コードのみ DELETE → INSERT を実行）。
    - テスト用に _call_openai_api を差し替え可能に設計。
    - calc_news_window ユーティリティ（JST の前日 15:00 ～ 当日 08:30 の UTC 変換）を提供。

  - 市場レジーム判定（ai.regime_detector.score_regime）
    - ETF 1321（225連動ETF）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）の合成で日次レジームを判定（'bull' / 'neutral' / 'bear'）。
    - マクロキーワードによる raw_news フィルタリング、OpenAI 呼び出し、合成スコアのクリップ、閾値に基づくラベリングを実装。
    - API エラー時はマクロ寄与を 0.0 とするフェイルセーフ、DB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - テスト時に差し替え可能な内部フックあり。

- データプラットフォーム関連（kabusys.data）
  - カレンダー管理（data.calendar_management）
    - market_calendar ベースの営業日判定、next/prev_trading_day、get_trading_days、is_sq_day を実装。
    - market_calendar が未取得/まばらな場合の曜日ベースのフォールバック。
    - J-Quants からの夜間カレンダー更新ジョブ（calendar_update_job）：バックフィル、健全性チェック、差分取得・保存処理。

  - ETL パイプライン基盤（data.pipeline / data.etl）
    - ETLResult データクラス（取得件数、保存件数、品質チェック結果、エラー一覧など）。
    - 差分更新、バックフィル、品質チェックの設計方針を反映。

- リサーチ／ファクター（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR / 相対 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER、ROE）を DuckDB 上で計算する関数を実装。
    - データ不足時の None 戻りや、ルックアヘッド防止のための範囲制限を実装。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic：Spearman ランク相関）、rank、factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等に依存せず標準ライブラリ＋DuckDB のみで実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / 運用上の重要事項
- OpenAI API
  - news_nlp と regime_detector は OpenAI（gpt-4o-mini）を使用します。呼び出しには OPENAI_API_KEY を設定するか、各関数に api_key 引数を渡してください。未設定時は ValueError を送出します。
  - API 呼び出しは JSON Mode を利用し、レスポンスパースや形式検証が行われます。失敗時は該当処理をスキップまたはデフォルト値（例: macro_sentiment=0.0）にフォールバックする設計です。

- .env 自動読み込み
  - 実行環境の OS 環境変数 > .env.local > .env の順で読み込みます。OS 環境変数はデフォルトで保護され、.env による上書きは発生しません。
  - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- DuckDB と DB 書き込み
  - 各種書き込みは冪等性を重視（DELETE→INSERT、ON CONFLICT 相当）しています。
  - DuckDB の executemany が空リストを受け付けない制約に配慮したガードが入っています。

- ルックアヘッドバイアスの排除
  - AI スコア生成やファクター計算は内部で datetime.today()/date.today() を参照せず、引数で与えられた target_date を基準に過去データのみを参照するよう設計されています。

- テスト容易性
  - OpenAI 呼び出し部分（_call_openai_api 等）はテスト時に差し替え可能（unittest.mock.patch を想定）に実装されています。

### Required / 推奨環境変数
- 必須（Settings が ValueError を投げる）
  - OPENAI_API_KEY（各 AI 機能使用時）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- 任意（デフォルトあり）: KABUSYS_ENV, LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, 各種閾値（CPU/MEM/DISK）

### Breaking Changes
- 初回リリースのため無し。

---

以上。本 CHANGELOG はコードベースの実装内容から推測して作成しています。実装上の細かい挙動や将来の変更はリリースノートで随時更新してください。