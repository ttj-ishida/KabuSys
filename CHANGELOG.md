CHANGELOG
=========

すべての重要な変更点はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

注: このパッケージは初期リリースとして v0.1.0 を公開しています。

Unreleased
----------

（なし）

0.1.0 - 2026-03-28
------------------

Added
- パッケージ全体の初期実装を追加。
  - パッケージ名: kabusys、バージョン: 0.1.0
  - エクスポート済みモジュール: data, strategy, execution, monitoring（__all__ に登録）
- 環境変数・設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする機能を実装。
  - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサは以下の形式をサポート:
    - コメント行（# で始まる）や空行を無視
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のエスケープ処理を考慮した文字列抽出
    - クォートなし値ではインラインコメント（直前が空白／タブの場合）を無視
  - Settings クラスを提供し、主要設定プロパティを公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）、LOG_LEVEL（DEBUG/INFO/... の検証）
    - is_live / is_paper / is_dev のショートハンドプロパティ
  - 必須環境変数未設定時は ValueError を発生させる厳格な取得ヘルパーを提供。
- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理ロジック（market_calendar テーブルの利用、フォールバック、営業日判定）を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - calendar_update_job: J-Quants API からの差分取得 → 冪等保存（ON CONFLICT 相当）を実装。バックフィル、健全性チェックを含む。
    - DB 登録がない場合は曜日ベース（土日休）でフォールバック。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）で無限ループを防止。
  - pipeline / etl:
    - ETLResult データクラス（ETL 実行結果の記録）を実装し再エクスポート。
    - ETL パイプラインのユーティリティ（差分ロード、バックフィル、品質チェックの統合方針）を実装。
    - DuckDB の挙動（exectuemany の空リスト回避など）に配慮した実装。
  - jquants_client と quality モジュールを利用する設計。
- AI モジュール（kabusys.ai）
  - news_nlp.score_news:
    - raw_news と news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメント（-1.0～1.0）を算出。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC 変換して扱う）を対象。
    - バッチ/トリム戦略（最大記事数／最大文字数）、チャンク単位のリトライ（429・ネットワーク・5xx のエクスポネンシャルバックオフ）。
    - レスポンス検証とスコアのクリップ、部分成功時の DB 書き換え方針（DELETE → INSERT）を実装。
    - API キー注入（api_key 引数）対応。未設定の場合は環境変数 OPENAI_API_KEY を参照して ValueError を送出。
    - テスト用に _call_openai_api を patch して差し替え可能。
  - regime_detector.score_regime:
    - ETF 1321（Nikkei 225 連動 ETF）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - calc_news_window（news_nlp からインポート）でウィンドウ計算、raw_news からマクロキーワードでタイトル抽出、OpenAI 呼び出し（gpt-4o-mini）でマクロセンチメントを算出。
    - API 失敗時は macro_sentiment = 0.0 のフェイルセーフ。
    - DB に対する冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - OpenAI SDK のエラー型（APIError 等）に対する扱いとリトライロジックを実装。
- リサーチ機能（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（prices_daily を参照）。
    - calc_volatility: 20 日 ATR、ATR 比率、平均売買代金、出来高比などの計算。
    - calc_value: latest raw_financials を用いた PER / ROE の計算（EPS が不適切な場合は None）。
    - 計算は DuckDB の SQL ウィンドウ関数を活用し、データ不足時の None ハンドリングを行う。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズンでの将来リターン（LEAD を利用して一括取得）。
    - calc_ic: ファクターと将来リターンの Spearman（ランク相関）を実装（必要件数不足時は None）。
    - rank: 同順位は平均ランクを採るランク化ユーティリティ（浮動小数の丸め対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - zscore_normalize は kabusys.data.stats から再エクスポート。
- テスト・開発配慮
  - OpenAI 呼び出し箇所は内部関数を介しており unittest.mock で差し替え可能（テスト容易性を考慮）。
  - ルックアヘッドバイアス回避: 多くの関数で datetime.today()/date.today() を直接参照しない設計（target_date を明示的に受け取る）。

Security
- 環境変数読み込み時に OS 環境変数（process 環境）を保護する仕組み（protected set）を導入。.env の override 動作は protected を尊重する。

Changed
- 初版のため「変更」は該当なし。

Fixed
- 初版のため「修正」は該当なし。

Removed
- 初版のため「削除」は該当なし。

Compatibility / Requirements / Notes
- 依存:
  - duckdb（DuckDB 接続を利用）
  - openai（OpenAI Python SDK、v1 系の status_code 参照に配慮）
- DuckDB のバージョン差異に対する互換性配慮（executemany の空リスト回避など）を実装。
- OpenAI モデル: gpt-4o-mini を JSON mode で利用する想定。API レスポンスの不安定性を補うバリデーション・パース補正（最外の {} 抽出）を実装。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings で必須）
  - OpenAI API 利用には OPENAI_API_KEY が必要（score_news / score_regime は未指定時に ValueError を投げる）
- デフォルトパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- 実装上の設計方針や注意点は各モジュールの docstring に詳述（例: ルックアヘッドバイアスの回避、冪等書き込み、部分失敗時の DB 保護など）。

開発者向けメモ
- 自動 .env 読み込みはプロジェクトルート探索に __file__ を使用するため、CWD に依存せずパッケージ配布後も動作します。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化してください。
- OpenAI 呼び出しをモックする場合、kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api を patch してください。
- 必要な DB テーブル（例）:
  - prices_daily, raw_news, market_regime, market_calendar, ai_scores, news_symbols, raw_financials
  - ETL / calendar_update_job 等は jquants_client の fetch/save 関数に依存します。

今後の TODO（非網羅）
- strategy / execution / monitoring モジュールの実装（初期 __all__ に名前はあるが詳細実装は別途）。
- 追加の品質チェックルールと監視アラート。
- OpenAI レスポンスのより厳密なスキーマ検証やログ拡充。

-----