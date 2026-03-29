# Changelog

すべての注目すべき変更点をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

全般的な注意
- このリポジトリの初期リリースを記録しています。
- 日付・バージョンはパッケージ内の __version__ を基にしています。

## [0.1.0] - 2026-03-29

### Added
- パッケージ基盤
  - パッケージ初期化: `kabusys.__init__` を追加し、バージョン "0.1.0" 、公開モジュール一覧を定義（data, strategy, execution, monitoring）。
- 設定 / 環境変数管理 (`kabusys.config`)
  - .env ファイルと環境変数の自動読み込み機能を実装（プロジェクトルート検出: .git or pyproject.toml を基準）。
  - .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応、インラインコメント処理など）。
  - 自動ロードを無効化するフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト時に便利）。
  - Settings クラスを提供し、必要な設定値をプロパティ経由で取得。必須キーは未設定時に ValueError を送出。
  - デフォルト値: `KABUS_API_BASE_URL` のデフォルト、`DUCKDB_PATH` / `SQLITE_PATH` の既定パスを設定。
  - 環境値のバリデーション: `KABUSYS_ENV`（development/paper_trading/live）と `LOG_LEVEL` の検証実装。
- AI 関連 (`kabusys.ai`)
  - ニュース NLP スコアリング（`kabusys.ai.news_nlp`）
    - raw_news / news_symbols を集約して、OpenAI（gpt-4o-mini）に JSON モードでバッチ送信して銘柄ごとのセンチメント（ai_score）を計算。
    - タイムウィンドウ定義（JST 前日 15:00 ～ 当日 08:30、内部は UTC naive datetime で扱う）。
    - バッチ処理・チャンクサイズ（最大 20 銘柄）・1 銘柄あたりの最大記事数/文字数制限を実装。
    - API 呼び出しのリトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実装。
    - レスポンスの厳格なバリデーションと ±1.0 のクリップ、部分成功時の idempotent な DB 書き込み（DELETE → INSERT）。
    - テスト用の差し替えポイント（内部の _call_openai_api を patch 可能）。
  - 市場レジーム判定（`kabusys.ai.regime_detector`）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロ記事はキーワードフィルタで抽出（キーワード定義あり）。
    - OpenAI 呼び出しは JSON モードで実施、リトライとフェイルセーフ（失敗時 macro_sentiment=0.0）。
    - レジームスコアを計算し、`market_regime` テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - テスト用に内部 API 呼び出し関数の差し替えが可能。
- リサーチ機能 (`kabusys.research`)
  - ファクター計算（`factor_research.py`）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR）、Value（PER/ROE）などの定量ファクター計算を実装。
    - DuckDB 上の SQL ウィンドウ関数を活用し、(date, code) 単位で結果を返す。
    - データ不足時の None ハンドリングやログ出力。
  - 特徴量探索（`feature_exploration.py`）
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman ランク相関）計算、統計サマリー、ランク変換ユーティリティを実装。
    - 外部ライブラリ非依存（標準ライブラリのみ）。
  - 便宜上エクスポートを整理（`__all__` に主要関数を公開）。
- データプラットフォーム (`kabusys.data`)
  - カレンダー管理（`calendar_management.py`）
    - JPX カレンダー（market_calendar）を扱うユーティリティ: 営業日判定、前後の営業日取得、期間内営業日リスト取得、SQ 日判定。
    - カレンダー未取得時の曜日ベースフォールバック（週末除外）を実装し、DB 登録がある日を優先する一貫したロジック。
    - 夜間バッチ更新ジョブ（`calendar_update_job`）で J-Quants API から差分取得・バックフィル・健全性チェックを実行。
  - ETL パイプライン（`pipeline.py` / `etl.py`）
    - ETL 実行結果を表す `ETLResult` データクラスを追加（品質チェック結果やエラー一覧を保持）。
    - 差分取得・保存・品質チェックを想定したユーティリティの下地を実装（J-Quants クライアント連携想定）。
    - `etl.py` で `ETLResult` を再エクスポート。
  - jquants_client / quality 等の外部連携モジュールと連携する設計（IDempotent 保存、バックフィルなど）。
- テスト・開発補助
  - 各所にテスト用フック（例: OpenAI 呼び出し差し替え、KABUSYS_DISABLE_AUTO_ENV_LOAD）を用意し、単体テストの容易化を考慮。

### Security
- OpenAI API キーや各種トークンは必須環境変数として扱う箇所があります（未設定の場合 ValueError を送出）。
  - 必須環境変数（Settings で必須とされるもの）:
    - JQUANTS_REFRESH_TOKEN
    - KABU_API_PASSWORD
    - SLACK_BOT_TOKEN
    - SLACK_CHANNEL_ID
  - OpenAI の利用には環境変数 OPENAI_API_KEY（または各関数の api_key 引数）を指定する必要があります。
- 自動で .env を読み込む機能は便利ですが、運用環境では機密情報の取り扱いに注意してください。
- OpenAI 呼び出しは外部ネットワーク通信であり、API 使用に伴うコストとレイテンシ、情報漏洩リスクを考慮してください。

### Notes / Migration
- 日時の取り扱いはルックアヘッドバイアスを避ける設計（datetime.today()/date.today() を参照しない関数設計）になっています。ターゲット日を明示的に渡して利用してください。
- データベースは DuckDB を前提に SQL を組んでいます。API 実行時の部分失敗に備え、DB 書き込みは部分置換（必要なコードのみ DELETE → INSERT）で既存データ保護を行います。
- テスト時に .env の自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しの振る舞いをテストで置き換えるには、各モジュールの `_call_openai_api`（news_nlp / regime_detector）を mock/patch してください。

### Removed
- （初期リリースのため無し）

### Deprecated
- （初期リリースのため無し）

### Fixed
- （初期リリースのため無し）

もしリリースノートに追記してほしい詳細（例: 各関数の使用例、必須テーブルスキーマ、期待される DuckDB テーブル一覧など）があればお知らせください。必要に応じて CHANGELOG を分割して「Unreleased」セクションを追加することもできます。