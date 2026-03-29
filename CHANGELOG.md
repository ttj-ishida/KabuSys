CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従っています。  
詳細な設計メモ・実装上の注意点は各モジュールの docstring を参照してください。

Unreleased
----------

- 今のところなし。

0.1.0 - 2026-03-29
------------------

Added
- パッケージ初期リリース。
  - パッケージ名: kabusys、バージョン: 0.1.0
- 基本パッケージ構成を追加:
  - モジュール群: data, research, ai, monitoring（__all__ で公開）。
- 環境設定管理:
  - kabusys.config: .env / .env.local の自動読み込み（OS 環境変数優先）。
  - .env パーサの実装: export 形式、クォートやエスケープ、インラインコメント処理に対応。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須環境変数取得ヘルパー _require と Settings クラスを提供。
  - Settings が公開する主な設定:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/... の検証）
- AI（自然言語処理）:
  - kabusys.ai.news_nlp:
    - raw_news / news_symbols から記事を集約し、OpenAI (gpt-4o-mini) を用いて銘柄別センチメントを算出。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で正確に計算。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/回）、1 銘柄あたりの記事トリム制御（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
    - API リトライ（429・ネットワーク・タイムアウト・5xx に対する指数バックオフ）とフェイルセーフ（失敗時は該当チャンクをスキップ）。
    - レスポンス検証とスコアの ±1.0 クリップ。
    - ai_scores テーブルへの冪等的書き込み（該当コードのみ DELETE → INSERT）。
    - テスト容易性: OpenAI 呼び出し部を _call_openai_api で差し替え可能。
  - kabusys.ai.regime_detector:
    - ETF 1321（Nikkei225 連動）の 200 日移動平均乖離（重み70%）と、マクロニュースの LLM センチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を算出。
    - prices_daily / raw_news / market_regime を参照し、レジームを market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - マクロキーワードフィルタ、最大記事数制限、OpenAI 呼び出しのリトライとフォールバック（失敗時 macro_sentiment=0.0）。
    - 設計上、ルックアヘッドバイアスを避けるため datetime.today() を参照しない実装。
- Research（ファクター計算・特徴量解析）:
  - kabusys.research.factor_research:
    - Momentum（1M/3M/6M、ma200 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）を DuckDB 上で計算するユーティリティを追加。
    - prices_daily / raw_financials のみ参照し、返却は date, code キーの dict リスト。
    - データ不足時の挙動（None を返す等）を明文化。
  - kabusys.research.feature_exploration:
    - 将来リターン calc_forward_returns（任意ホライズン、バリデーションあり）。
    - IC（Information Coefficient）計算（スピアマンランク相関）とランク化ユーティリティ（同順位は平均ランク処理）。
    - factor_summary による統計サマリー（count, mean, std, min, max, median）。
  - 研究用ユーティリティ zscore_normalize を kabusys.data.stats から再エクスポート。
- Data（データプラットフォーム関連）:
  - kabusys.data.calendar_management:
    - JPX カレンダー管理（market_calendar）: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ロジック実装。
    - DB 登録値優先、未登録日は曜日フォールバックの一貫した挙動。
    - calendar_update_job: J-Quants API から差分取得・バックフィル・健全性チェック・冪等保存を行う夜間ジョブを実装（jq.fetch_market_calendar / jq.save_market_calendar を利用）。
  - kabusys.data.pipeline:
    - ETLResult dataclass を用いた ETL パイプライン用の結果集約。
    - 差分更新・バックフィルの方針、品質チェックとの連携（quality モジュール）を想定した実装。
    - DuckDB 上の最大日付取得等のユーティリティ。
  - kabusys.data.etl: ETLResult の再エクスポート。
- テスト・運用配慮:
  - OpenAI API 呼び出し部分はモジュール内 private 関数で分離されており、unittest.mock.patch により容易にモック可能。
  - API 失敗に対するフォールバック設計（例: macro_sentiment=0.0、チャンクスキップ）でフェイルセーフ性を確保。
  - DuckDB バインドの互換性考慮（executemany に空リストを渡さない等）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

注意事項（導入・移行メモ）
- 必須環境変数:
  - OPENAI_API_KEY（AI スコアリング機能を利用する場合）
  - JQUANTS_REFRESH_TOKEN（J-Quants 連携が必要な場合）
  - KABU_API_PASSWORD（kabu ステーション連携が必要な場合）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Slack 通知を使う場合）
- .env 自動読み込み:
  - パッケージはパッケージ内ファイル位置からプロジェクトルート（.git または pyproject.toml）を探索し .env / .env.local を読み込みます。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 依存・外部モジュール:
  - DuckDB と OpenAI の Python SDK を前提としています（コード内で import して利用）。
  - jquants_client / quality 等、data モジュールが期待する外部実装が別途必要です（本リリースでは参照箇所を利用することを想定）。
- ルックアヘッドバイアス防止:
  - AI / レジーム / リサーチ機能は内部で現在時刻を直接参照しない設計になっています。target_date を明示して呼び出してください。
- DB 書き込みは基本的に冪等性を考慮（DELETE → INSERT、ON CONFLICT を想定）していますが、実行環境の DuckDB バージョンや設定に依存するため事前にテストしてください。

今後の予定（アイデア）
- ai モジュールのモデル選択やプロンプトの外部設定化
- ETL の実行スケジューラ統合および監視用ダッシュボード
- 追加ファクター・ファインチューニングのためのユニットテスト充実

---  
もし CHANGELOG に追加してほしい点（例: リリース日を別にしたい、より詳細な機能区分、既知の問題リストなど）があれば教えてください。