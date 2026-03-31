# Changelog

すべての重要な変更点をここに記録します。本ファイルは「Keep a Changelog」仕様に準拠しています。

フォーマット: [バージョン] - YYYY-MM-DD

## [0.1.0] - 2026-03-31

初回リリース。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py）。
  - モジュールのエクスポート: data, strategy, execution, monitoring を公開。

- 環境設定/ロード機能（kabusys.config）
  - .env / .env.local ファイルと OS 環境変数からの設定読み込みを実装。
  - 自動ロード順序: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ等に対応）。
  - Settings クラスを提供し、主要な環境設定をプロパティで取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルトあり）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証あり）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証あり）
    - is_live / is_paper / is_dev ヘルパー

- AI モジュール（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を用いて銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出。
    - バッチサイズ、文字数・記事数トリム、JSON mode 応答パース、応答バリデーションを実装。
    - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - スコアは ±1.0 範囲にクリップし、ai_scores テーブルへ冪等的に置換（DELETE → INSERT）。
    - 時間ウィンドウ計算（JST基準の前日15:00〜当日08:30）を calc_news_window で提供。
    - テスト用に _call_openai_api を差し替え可能（unittest.mock.patch によるモック推奨）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - prices_daily / raw_news を参照し market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - OpenAI 呼び出しは内部で行い、エラー時は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - LLM 呼び出しに対するリトライ・タイムアウト制御を実装。

- リサーチ機能（kabusys.research）
  - factor_research モジュール
    - モメンタム: 1M / 3M / 6M リターン、200日 MA 乖離を計算する calc_momentum。
    - ボラティリティ / 流動性: 20日 ATR、相対 ATR、平均売買代金、出来高比率を計算する calc_volatility。
    - バリュー: PER / ROE を raw_financials と prices_daily を組み合わせて計算する calc_value。
    - DuckDB を利用した SQL ベースの実装。結果は (date, code) をキーとする dict のリストで返却。

  - feature_exploration モジュール
    - 将来リターン計算: calc_forward_returns（複数ホライズン対応、引数検証あり）。
    - IC（Information Coefficient）計算: calc_ic（Spearman のランク相関）。
    - ランク変換ユーティリティ: rank（同順位は平均ランク処理）。
    - ファクター統計サマリ: factor_summary（count/mean/std/min/max/median）。

  - research パッケージで zscore_normalize の再エクスポートを含む各種関数を __all__ で公開。

- データ基盤（kabusys.data）
  - calendar_management
    - JPX カレンダー管理: market_calendar を参照し営業日判定（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB 登録を優先、未登録日は曜日ベースでフォールバックする設計。
    - calendar_update_job: J-Quants API（jquants_client）から差分取得し market_calendar を IDempotent に更新。バックフィル・健全性チェックあり。

  - ETL パイプライン（pipeline）
    - ETLResult データクラスを定義し、取得・保存件数、品質チェック結果、エラー一覧を保持。
    - _get_max_date 等のユーティリティを提供。
    - data.etl で ETLResult を公開再エクスポート。

- 実装上の主要な設計方針（横断的）
  - ルックアヘッドバイアス回避: 各種処理で datetime.today() / date.today() を直接参照しないように実装（target_date を明示的に引数で受け取る設計）。
  - DuckDB をメインの分析用ローカル DB として使用（prices_daily, raw_news, ai_scores, market_regime, raw_financials, market_calendar などを想定）。
  - LLM/API 呼び出しはフェイルセーフ化し、API 問題時は処理をスキップまたはゼロ埋めして全体処理を継続。
  - DB 書き込みは可能な限り冪等（DELETE→INSERT、ON CONFLICT 相当）かつトランザクションで保護。
  - テスト容易性のため、内部の OpenAI 呼び出し関数を patch して差し替え可能。

### Changed
- （初版のため変更履歴はありません）

### Fixed
- （初版のため修正履歴はありません）

### Security
- 環境変数の取り扱いに注意:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings で _require により未設定時は ValueError を送出）。
  - OpenAI API キーは score_news / score_regime の引数経由または環境変数 OPENAI_API_KEY で供給。未設定時は ValueError を送出。
  - .env ロード時、既存 OS 環境変数は protected として上書きされない（.env.local は override=True だが OS キーは保護される）。

### Migration / Usage Notes
- 環境準備
  - プロジェクトルート探索は __file__ を基準に .git または pyproject.toml を探すため、配布後も .env 自動ロードは機能する想定。ただし自動ロードを無効化したいテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を設定。
- OpenAI
  - 本リリースは gpt-4o-mini を想定。API のレスポンス構造変更やモデル名の変更があった場合、パーサやエラーハンドリングを見直す必要あり。
- DuckDB スキーマ
  - 多数のモジュールが特定テーブル名（prices_daily, raw_news, ai_scores, market_regime, news_symbols, raw_financials, market_calendar 等）を前提としているため、ETL で該当テーブルを事前に準備すること。
- テスト
  - OpenAI 呼び出し関数は各モジュールでプライベート関数化しており、unit test 時には unittest.mock.patch により差し替え可能。

---

今後の予定（想定）
- strategy / execution / monitoring パッケージの追加実装（発注・モニタリング機能）。
- ai モデルの切り替えやレスポンス検証の強化。
- ETL の詳細な品質チェックルールの追加と警告/通知機能の統合。

ご要望や誤記・補足があればお知らせください。コードベースやドキュメントの追加情報に基づいて CHANGELOG を更新します。