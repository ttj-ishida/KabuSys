Changelog
=========
すべての変更は Keep a Changelog の形式に準拠します。  
初期バージョンのリリースノートはコードベースから推測して作成しています。

Unreleased
----------
- （現在のところ未リリースの変更はありません）

[0.1.0] - 2026-03-27
-------------------
初期リリース。主要機能を実装し、以下のモジュール群を公開しました。

Added
- パッケージ基礎
  - パッケージ識別子を追加: kabusys.__version__ = "0.1.0"。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に追加。

- 設定・環境変数管理（kabusys.config）
  - .env/.env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロードの無効化をサポート（テスト用途）。
  - .env のパーサを実装（export KEY=val 形式、クォート内のバックスラッシュエスケープ、行末コメント処理に対応）。
  - 上書き制御（override）と OS 環境変数保護（protected set）を実装。
  - Settings クラスを提供してアプリケーション設定を型付きプロパティで取得可能に：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルトあり）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）および LOG_LEVEL の検証。
    - is_live / is_paper / is_dev ヘルパープロパティ。

- AI（自然言語処理）機能（kabusys.ai）
  - ニュースセンチメント（kabusys.ai.news_nlp）
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）にバッチ送信し、銘柄ごとの ai_scores を ai_scores テーブルへ書き込み。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST の変換ロジック）を提供（calc_news_window）。
    - 1回の API 呼び出しで最大 20 銘柄を処理、1 銘柄当たり最大 10 記事／3000 文字でトリム。
    - JSON Mode のレスポンスを検証・抽出するバリデーション実装（厳密な JSON / 前後ノイズの復元等）。
    - 429・接続断・タイムアウト・5xx に対する指数バックオフ/リトライの実装。
    - スコアは ±1.0 にクリップ。部分成功時は対象コードのみを DELETE → INSERT で置換して既存データを保護。
    - API キー未指定時は ValueError を送出（api_key 引数 または OPENAI_API_KEY 環境変数を期待）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - score_regime(conn, target_date, api_key=None): ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出はマクロキーワードでフィルタし、LLM（gpt-4o-mini）により -1.0〜1.0 の macro_sentiment を算出。
    - LLM 呼び出しに対するリトライ・フェイルセーフ実装（最終的に失敗した場合は macro_sentiment=0.0 を採用）。
    - レジームスコアに基づいて label を bull / neutral / bear に判定。
    - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等処理。失敗時は ROLLBACK を試行。

- リサーチ（kabusys.research）
  - factor_research: calc_momentum / calc_value / calc_volatility を実装。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None を返す設計）。
    - Value: PER（EPS が 0/NULL の場合は None）、ROE（raw_financials から取得）。
    - Volatility / Liquidity: 20 日 ATR、相対 ATR、平均売買代金、出来高比率等を計算。
    - DuckDB 上で SQL ウィンドウ関数を活用して計算（外部 API 不使用）。
  - feature_exploration: calc_forward_returns（任意ホライズンの将来リターン）、calc_ic（Spearman ランク相関）、factor_summary（基本統計量）、rank（同順位は平均ランク）を実装。
  - kabusys.research パッケージで必要なユーティリティを再エクスポート（zscore_normalize 等）。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - market_calendar が未取得の場合の曜日ベースフォールバック (土日休場) をサポート。
    - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等更新（バックフィルと健全性チェックを実装）。J-Quants クライアント呼び出しを jq モジュール経由で行う設計。
  - ETL（kabusys.data.pipeline）
    - ETLResult データクラスを提供（取得件数・保存件数・品質チェック結果・エラー要約等を格納）。
    - 差分取得、バックフィル、品質チェック、idempotent 保存（jquants_client の save_* を利用）を実装するためのユーティリティを整備。
    - _get_max_date / _table_exists 等の DB ヘルパーを用意。
  - エクスポート: kabusys.data.etl から ETLResult を再エクスポート。

- データベース・トランザクションと互換性対応
  - DuckDB を主なストレージとして利用。トランザクション管理（BEGIN/COMMIT/ROLLBACK）を多数のモジュールで使用。
  - DuckDB 互換性のため executemany に空リストを渡さない等の実装上の工夫を追加。

- ロギング・堅牢性
  - 各処理で詳細なログ出力（info/debug/warning/exception）を追加。
  - ルックアヘッドバイアス防止のため、内部で datetime.today()/date.today() をデータ基準処理に直接使わない設計を採用。
  - API レスポンスパース失敗や不完全データは例外で崩さずフェイルセーフにフォールバックする方針（例: macro_sentiment=0.0、スコア未取得はスキップ）。

Changed
- （初回リリースのため既存機能の変更はありません）

Fixed
- （初回リリースのため修正履歴はありません）

Security
- OpenAI API キーや各種トークン（J-Quants / Slack / Kabu API）を環境変数から取得する設計。キー未指定時は明示的な ValueError を発生させることで誤動作を抑止。

Notes / Migration / Upgrade
- 初回リリースのため移行手順は特にありません。環境変数（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）を正しく設定してください。
- .env の自動読み込みはプロジェクトルートの検出に依存します（.git または pyproject.toml）。CI/テスト環境等で自動ロードを抑止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のバージョン互換性に起因する executemany の扱いに注意（実装は互換性配慮済み）。

Acknowledgements / Implementation remarks
- OpenAI とのやり取りは gpt-4o-mini と JSON Mode を想定しており、レスポンスの堅牢な検証・復元処理を備えています。
- 各モジュールの docstring に設計方針・処理フロー・フォールバック動作の説明を含めているため、実運用時はそれらを参照してください。