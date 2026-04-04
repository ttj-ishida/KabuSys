# Changelog

すべての重要な変更点は Keep a Changelog 準拠で記録します。  
このファイルはコードベースから推測して自動生成しています — 実際のコミット履歴に基づくものではありません。

フォーマット:
- Unreleased: まだリリースしていない変更（空の場合なし）
- 各リリースは日付付きで記載（YYYY-MM-DD）

## [Unreleased]

## [0.1.0] — 2026-04-04
最初の公開リリース（推定）。日本株自動売買／データプラットフォームの基盤機能をまとめて提供します。

### Added
- パッケージ基礎
  - kabusys パッケージの初期バージョンを追加。__version__ = "0.1.0"。
  - サブパッケージ公開: data, research, ai, monitoring, strategy, execution（__all__ に含む）。

- 環境設定 / 設定管理
  - 環境変数の自動読み込み機能を実装（パッケージインポート時に実行、ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を探索、CWD に依存しない）。
  - .env / .env.local ファイルパーサを実装:
    - export KEY=val 形式対応、クォート文字列のエスケープ処理、行コメントの扱い等を考慮。
    - .env → .env.local の優先順位で読み込み。OS 環境変数は保護される（.env.local の上書き制御）。
  - Settings クラスを導入（settings インスタンスをエクスポート）:
    - J-Quants / kabuステーション / LINE / DB パス / 監視しきい値 / システム環境（development/paper_trading/live）等のプロパティを提供。
    - 必須環境変数未設定時の明確なエラー（ValueError）。

- AI（NLU）機能
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）:
    - raw_news / news_symbols を用いて、銘柄ごとのニュースを集約し OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出。
    - バッチ処理（最大20銘柄／チャンク）、記事数・文字数トリム、JSON Mode を想定したレスポンスバリデーションを実装。
    - リトライ戦略（429・ネットワーク断・タイムアウト・5xx）と指数バックオフ、API失敗時はフェイルセーフ（該当チャンクスキップ）。
    - テスト用に _call_openai_api を patch で差し替え可能。
    - ai_scores テーブルへの冪等書き込み（該当コードのみ DELETE → INSERT）で部分失敗に耐性。
    - calc_news_window 関数でニュース集計ウィンドウ（JST基準の前日15:00〜当日08:30）を算出。

  - 市場レジーム判定（kabusys.ai.regime_detector）:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロキーワードで raw_news のタイトルを抽出し LLM（gpt-4o-mini）で macro_sentiment を取得。
    - API リトライ・エラー時のフォールバック（macro_sentiment=0.0）とログ出力。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。

- データ基盤（data）
  - カレンダー管理（kabusys.data.calendar_management）:
    - market_calendar テーブルの存在チェック、営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB にデータがない場合は曜日ベース（土日除外）でフォールバックする一貫した振る舞い。
    - JPX カレンダーの夜間差分更新ジョブ（calendar_update_job）を実装。J-Quants client 経由で差分取得 → 保存（バックフィル・健全性チェックあり）。
  - ETL パイプライン（kabusys.data.pipeline / etl）:
    - 差分取得・保存・品質チェックフローを実装するための基盤。
    - ETLResult dataclass を追加：取得件数・保存件数・品質問題・エラーの集約と to_dict メソッドを提供。
    - デフォルトのバックフィルやカレンダールックアヘッド等の設定を備える。

- リサーチ機能（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）:
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Volatility（20日ATR 等）、Value（PER/ROE）を DuckDB の prices_daily / raw_financials から計算。
    - 欠損時の扱い（データ不足なら None）、結果は (date, code) をキーとする dict のリストで返す。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - 将来リターン calc_forward_returns（複数ホライズン対応、入力検証あり）。
    - IC（calc_ic）: Spearman ランク相関を実装（同順位は平均ランク処理）。
    - rank, factor_summary などの統計ユーティリティ（外部ライブラリに依存せず標準ライブラリのみで実装）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キー・機密情報は環境変数で管理。必須キー未設定時は ValueError を発生させることで明示的に扱う。

### Notes / 実装上の重要事項（運用・移行メモ）
- 必要な DB テーブル（推定）:
  - prices_daily, raw_news, raw_financials, market_regime, ai_scores, news_symbols, market_calendar 等。
- 環境変数（主なもの）:
  - OPENAI_API_KEY（必須 for AI 機能）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD（任意、1 で .env 自動ロードを無効化）
  - DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH など（デフォルトを提供）
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行うため、配布後やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して読み込みを制御可能。
- テスト容易性:
  - news_nlp と regime_detector 共に _call_openai_api を patch 可能。score_news / score_regime は api_key を引数で注入可能（環境変数に依存させないテストが可能）。
- フェイルセーフ設計:
  - AI API の失敗時は例外で止めずにフォールバック（ゼロスコアやチャンクスキップ）を採用し、部分失敗で全体が止まらない設計。
- 日付の扱い:
  - どのモジュールも内部で datetime.today() / date.today() を直接参照せず、target_date 引数によりルックアヘッドバイアスを防止する方針。

### Known limitations / 今後の改善余地（推定）
- PBR・配当利回り等のバリューファクターは未実装（calc_value に注記あり）。
- DuckDB バインドの互換性（executemany の空リスト扱い等）に配慮した実装が必要（すでに対策あり）。
- OpenAI の利用は JSON Mode 前提で実装しているが、API の将来的な仕様変更に対する追加適応が必要となる可能性あり。

---

履歴は今後の変更に応じて更新してください。必要であれば、各モジュールごとのより詳細な変更点（内部関数や SQL クエリの変更点など）を追記できます。