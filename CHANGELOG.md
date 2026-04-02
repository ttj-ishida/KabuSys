# Changelog

すべての重要な変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

注: この CHANGELOG はソースコード（src/ 以下）の内容から推測して作成しています。関数名や設計方針、ログ・例外ハンドリングの記述に基づき実装済み機能や仕様をまとめています。

## [Unreleased]

（現在差分なし）

## [0.1.0] - 2026-04-02

Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys、トップレベル __version__ = 0.1.0、公開サブパッケージ: data, research, ai, execution, strategy, monitoring（__all__ にて宣言）。
- 環境変数 / 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルートの検出は .git または pyproject.toml を基準としており、カレントワーキングディレクトリに依存しない。
  - .env のパースは export プレフィックス、クォート／エスケープ、インラインコメントを考慮した堅牢な実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB パス / 監視閾値 / 実行環境 (development/paper_trading/live) / ログレベル 等のプロパティを公開。未設定の必須値は ValueError を送出。
- データ基盤 (kabusys.data)
  - ETL パイプラインインターフェースを実装（ETLResult データクラスを公開）。
  - pipeline モジュール: 差分取得、バックフィル、品質チェックの設計を反映した ETLResult/ユーティリティを実装。
  - calendar_management: JPX 市場カレンダー管理（market_calendar）を実装。営業日判定（is_trading_day）、前/翌営業日取得(next_trading_day / prev_trading_day)、期間内営業日列挙(get_trading_days)、SQ判定(is_sq_day)、夜間バッチ更新(calendar_update_job) を提供。DB データがない場合は曜日ベースでフォールバックする動作を採用。
  - jquants_client（インターフェースを参照）との統合ポイントを想定。
- AI モジュール (kabusys.ai)
  - news_nlp.score_news: raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）で銘柄別センチメントを算出、ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウは JST 基準（前日 15:00 ～ 当日 08:30）を UTC に変換して利用（calc_news_window）。
    - バッチ処理（最大20銘柄/chunk）、記事・文字数トリム（_MAX_ARTICLES_PER_STOCK、_MAX_CHARS_PER_STOCK）を実装。
    - JSON Mode を利用した OpenAI 呼び出し、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、レスポンスの厳密な検証（results 配列、code/score の型チェック、スコアのクリップ）を実装。
    - API 呼び出し箇所はテスト容易性のため差し替え可能（内部 _call_openai_api を patch 可能）。
    - 部分失敗時の DB 書き換えは idempotent を意識して DELETE（対象 code のみ）→ INSERT を行う。
  - regime_detector.score_regime: ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して market_regime テーブルへ書き込む実装。
    - ma200_ratio の計算は DuckDB 上で直近200行（target_date 未満のデータのみ）を利用し、データ不足時は中立（1.0）でフォールバック。
    - マクロ記事はニュースタイトルをマクロキーワードでフィルタして取得し、LLM にて -1.0〜1.0 の macro_sentiment を取得（記事なし・API失敗時は 0.0 フェイルセーフ）。
    - OpenAI 呼び出しはリトライ／バックオフや 5xx 判定に対応。結果はクリップして閾値で bull/neutral/bear を判定。
    - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の順で冪等性を確保。例外時は ROLLBACK を試行。
- Research モジュール (kabusys.research)
  - factor_research: calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials を基にモメンタム・ボラティリティ・バリュー因子を算出（MA200乖離、ATR20、平均売買代金、PER、ROE 等）。欠損やデータ不足時は None を返す設計。
  - feature_exploration: calc_forward_returns（複数ホライズンの将来リターン）、calc_ic（スピアマンのランク相関による IC）、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を実装。外部ライブラリに依存せず標準ライブラリと DuckDB で実装。
  - research.__init__ で主要関数を再公開。
- DuckDB を中心とした DB 操作
  - 多くのモジュールで duckdb.DuckDBPyConnection を受け取り SQL クエリで処理。パフォーマンスや互換性（DuckDB の executemany の制約など）を考慮した実装。
- ログ・設計上のフェイルセーフ
  - API エラーやパース失敗時は警告ログを出力して処理を継続する（例外を無闇に投げないフェイルセーフ方針）。
  - テスト補助のため内部の API 呼び出し関数を patch して差し替え可能に実装。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で解決。必須未設定時は ValueError を送出して明示的に失敗させる設計。

Notes / 既知の制約
- research モジュール・factor 計算は prices_daily / raw_financials のみに依存し、本番発注ロジックへはアクセスしない。
- news_nlp/regime_detector の OpenAI 呼び出しは JSON Mode（厳密な JSON 出力想定）に依存しており、LLM の出力が期待通りでない場合はスキップ・フォールバックする。
- DuckDB のバージョン差異により executemany のリストバインド動作が不安定なため、個別 DELETE を行う実装を採用。
- calendar_update_job は J-Quants クライアント実装（jquants_client）に依存。API 呼び出し失敗時は 0 を返して安全に終了する。

---- 

参考: 各モジュールの主な公開 API
- kabusys.config.settings: jquants_refresh_token, kabu_api_password, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, pid_file_path, cpu_threshold_pct, memory_threshold_pct, disk_threshold_pct, env, log_level, is_live/paper/dev
- kabusys.ai.news_nlp: score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector: score_regime(conn, target_date, api_key=None)
- kabusys.data.pipeline: ETLResult
- kabusys.data.calendar_management: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day, calendar_update_job
- kabusys.research: calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize（data.stats 経由）

もし特定の変更点をより詳細に分けて記載したい、あるいは過去のリリース履歴（プレリリース等）を追加したい場合は、該当箇所のソース差分やコミットログを提示してください。