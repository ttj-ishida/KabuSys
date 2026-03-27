Keep a Changelog に準拠した形式で、このコードベースから推測される変更履歴を日本語で作成しました。
バージョンはパッケージ内の __version__ (0.1.0) に合わせています。

CHANGELOG.md
-------------

All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠しています。  

[0.1.0] - 2026-03-27
--------------------

Added
- パッケージの初期実装を追加
  - パッケージメタ情報
    - kabusys.__version__ = "0.1.0"
    - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に登録（将来的なモジュール構成を示唆）。
- 環境設定 / ロード機構（kabusys.config）
  - .env ファイルまたは環境変数から設定値を読み込む自動ローダを実装。
  - プロジェクトルートを .git または pyproject.toml で探索して .env / .env.local を読み込み（CWD に依存しない）。
  - .env パーサは export KEY=val 形式、クォート（シングル/ダブル）・バックスラッシュエスケープ・インラインコメント処理をサポート。
  - 読み込み優先順: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - Settings クラスを提供（必須環境変数取得を行う _require 関数を含む）。
    - 必須環境変数例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - デフォルト値を持つ項目: KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）、DUCKDB_PATH（data/kabusys.duckdb）、SQLITE_PATH（data/monitoring.db）
    - 環境／ログレベル検証（KABUSYS_ENV, LOG_LEVEL の許容値検査）
- AI 関連（kabusys.ai）
  - news_nlp モジュール（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI (gpt-4o-mini) に JSON モードで送信して銘柄別センチメント（ai_scores）を算出・保存する処理を実装。
    - バッチ処理（最大 BATCH_SIZE=20 銘柄ずつ）、1銘柄あたり最大記事数／文字数制限（MAX_ARTICLES_PER_STOCK, MAX_CHARS_PER_STOCK）。
    - リトライ（429、ネットワーク断、タイムアウト、5xx）を指数バックオフで実装。失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - レスポンス検証とパース回復処理（JSON 前後の余計なテキストが混ざる場合の切り出し）。
    - スコアの ±1.0 クリップ、DuckDB への冪等書き込み（DELETE → INSERT、部分失敗時に他銘柄を保護）。
    - 公開 API: calc_news_window(), score_news()
  - regime_detector モジュール（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定・保存。
    - マクロニュース抽出はキーワードベース（MACRO_KEYWORDS）で raw_news からタイトルを取得。
    - OpenAI 呼び出しは独立実装で _score_macro を提供。リトライ、5xx 判定、JSON パース失敗時は macro_sentiment=0.0 にフォールバック。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。公開 API: score_regime()
    - 設計上の注意点: ルックアヘッドバイアス防止のため datetime.today()/date.today() を参照しない実装。
- Data モジュール（kabusys.data）
  - calendar_management
    - JPX カレンダー管理と営業日判定ユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar テーブルが存在しない場合は曜日ベース（土日非営業日）でフォールバックする堅牢設計。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存。バックフィル（直近 BACKFILL_DAYS）と健全性チェック（SANITY_MAX_FUTURE_DAYS）を実装。
  - pipeline / etl
    - ETLResult データクラスを実装（ETL 実行結果の集約、品質問題やエラー一覧を保持）。
    - pipeline モジュールの ETLResult を data.etl で再エクスポート。
    - ETL パイプライン設計方針（差分更新、backfill、品質チェックの継続性、id_token 注入可能など）を実装に反映。
  - jquants_client（参照のみ: 一部関数を使用しているが実装は別モジュール想定）
- Research モジュール（kabusys.research）
  - factor_research
    - ファクター計算（momentum, value, volatility）を実装。
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。データ不足時は None を返す。
    - calc_value: raw_financials から最新財務データ（report_date <= target_date）を取得し PER（EPS が無効なら None）と ROE を算出。
  - feature_exploration
    - calc_forward_returns: target_date から所定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズンの妥当性チェックあり。
    - calc_ic: スピアマン（ランク）相関（IC）を実装。十分なサンプルがない場合は None を返す。
    - rank, factor_summary: ランク付け（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を提供。
  - research パッケージは zscore_normalize（kabusys.data.stats から）や各 calc 関数を再エクスポートしている。
- 汎用・運用設計
  - DuckDB をデータ処理の主なストレージとして利用する設計を反映（関数の引数に DuckDB 接続を要求）。
  - OpenAI クライアント（OpenAI SDK）を利用。モデルは gpt-4o-mini を指定。
  - 全体として「ルックアヘッドバイアス防止」「API 障害時のフェイルセーフ」「DB への冪等性」を優先した設計。
  - ロギング（logger）を各モジュールに導入し情報/警告/エラーを記録。

Changed
- 初リリースのため該当なし。

Fixed
- 初リリースのため該当なし。

Security
- 初リリースのため該当なし。

Notes / 実装上の重要ポイント（ユーザ向け）
- 環境変数の自動ロードはプロジェクトルートの検出に依存するため、配布パッケージやテスト環境で不要な自動ロードを避けるには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI API を使う機能（score_news, score_regime）は API キーが必要（引数で注入可能、未指定時は OPENAI_API_KEY 環境変数を使用）。未設定時は ValueError を送出します。
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）を前提とした実装です。実行前に適切なスキーマとデータの準備が必要です。
- ai モジュールは LLM レスポンスの堅牢な検証を行いますが、LLM の不安定な応答を考慮して「欠損チャンクはスキップ」する方針です（部分成功時に既存データを保護）。

Breaking Changes
- 初リリースのため該当なし。

参考（実装上の仕様・挙動の要約）
- .env のパースは export 句、クォート内のバックスラッシュエスケープ、インラインコメントの扱いをサポート。
- score_news はニュースの時間ウィンドウを JST ベースで計算（前日 15:00 JST 〜 当日 08:30 JST）し、DB は UTC で保存されている前提。
- News/NLP のバッチは最大 20 銘柄、1 銘柄あたり最大 10 記事・3000 文字にトリム。
- Regime 判定は ETF (1321) の ma200 乖離とマクロセンチメントを重み付けして総合スコアをクリップし閾値でラベル付け。
- ETLResult は品質チェックの結果を保持し、to_dict() で品質問題を (check_name, severity, message) 形式で出力可能。

--- End of CHANGELOG ---