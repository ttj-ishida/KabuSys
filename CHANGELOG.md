Keep a Changelog
=================

すべての重要な変更点をこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに準拠しています。

[Unreleased]: https://example.com/compare/v0.1.0...HEAD

0.1.0 - 2026-03-28
------------------

Added
- パッケージ初回リリース (kabusys 0.1.0)
  - パッケージメタ情報を src/kabusys/__init__.py に追加（__version__ = "0.1.0"、公開サブパッケージの __all__ を定義）。
- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルまたは OS 環境変数から設定を自動読み込みする機能を実装。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）。
      - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索。
    - 高度な .env パーサ実装 (.env 行の export KEY=val フォーマット、クォート内のエスケープ、インラインコメントの扱い等)。
    - Settings クラスを提供し、必要な環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID など）や既定値（KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL、KABUSYS_ENV）を取得可能。
    - env/log レベル入力検証と is_live/is_paper/is_dev の便宜プロパティを提供。
- AI ベースのニュース/レジーム分析
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols からニュースを銘柄別に集約し、OpenAI（gpt-4o-mini、JSON mode）へバッチ送信してセンチメント（ai_score）を算出。
    - タイムウィンドウは JST 基準（前日 15:00 JST ～ 当日 08:30 JST）を UTC に変換して使用。
    - 1チャンクあたり最大 20 銘柄（_BATCH_SIZE）で処理。1 銘柄あたり最大記事数・文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - 再試行戦略（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで実装。API 失敗時は該当チャンクをスキップして処理継続（フェイルセーフ）。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、code/score の検証、既知コードのみ採用、スコアを ±1.0 にクリップ）。
    - DuckDB への書き込みは冪等性を考慮（対象コードのみ DELETE → INSERT）し、部分失敗時に既存スコアを保護。
    - テスト容易性のため _call_openai_api を patch で差し替え可能。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロ記事は raw_news からキーワードで抽出（キーワードリスト _MACRO_KEYWORDS）。最大取得記事数制限あり。
    - OpenAI 呼び出しは gpt-4o-mini（JSON mode）を使用、最大リトライ・バックオフ戦略を実装。API 失敗時は macro_sentiment=0.0 にフォールバック。
    - レジームスコア合成ロジック（クリップ・閾値）と market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を提供。
    - テスト容易性のため news_nlp と内部の API 呼び出し関数は独立実装（モジュール結合を避ける）。
- 研究（Research）モジュール
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）等のファクター計算関数を提供（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上の prices_daily / raw_financials テーブルを用いた SQL ベース実装。データ不足時は None を返す設計。
    - 計算はルックアヘッドバイアス防止のため target_date 未満／以前のデータのみ参照。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns: 任意ホライズン、デフォルト [1,5,21]）、IC（Spearman の ρ）計算、ランク変換ユーティリティ、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリで実装。rank は同順位の平均ランク処理を行う。
  - src/kabusys/research/__init__.py で主要関数を再エクスポート。
- データプラットフォーム（Data）モジュール
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理：market_calendar を用いた営業日判定 (is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day) と夜間更新ジョブ（calendar_update_job）を提供。
    - DB 登録値を優先し、未登録日は曜日ベース（週末除外）でフォールバックする一貫したロジックを実装。探索上限を設け ValueError を防止。
    - J-Quants クライアント（jquants_client）から差分取得→保存のフローを実装し、バックフィルや健全性チェックを導入。
  - src/kabusys/data/pipeline.py
    - ETL の抽象化とユーティリティを実装（差分取得、保存、品質チェックの呼び出し）。
    - ETLResult dataclass を実装し、取得/保存件数・品質問題・エラー概要を集約。to_dict() で品質問題をシリアライズ可能。
    - 内部ユーティリティで DuckDB のテーブル存在や最大日付取得ロジックを提供。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult の再エクスポート。
- 汎用/設計上の注意点（各所に反映）
  - ルックアヘッドバイアス防止: datetime.today()/date.today() を参照しない設計（target_date を明示的に渡す方針）。
  - DB 書き込みでの冪等性を重視（DELETE→INSERT、ON CONFLICT 利用想定）。
  - API 呼び出し失敗時は全体停止ではなくフェイルセーフ動作（デフォルトスコア / スキップ）を採用。
  - テスト支援: auto .env ロード無効化、内部 API 呼び出しの差し替えポイントを用意。

Changed
- （該当なし - 初回リリース）

Fixed
- （該当なし - 初回リリース）

Deprecated
- （該当なし - 初回リリース）

Removed
- （該当なし - 初回リリース）

Security
- （該当なし - 初回リリース）

Notes / Known limitations
- OpenAI クライアント（OpenAI(api_key=...)）や jquants_client の外部依存があるため、実行時に該当 API キー・クライアント実装が必要。
- DuckDB のバージョン差異に起因するバインド挙動（リスト型バインド等）に配慮して実装しているため、古い/新しい DuckDB での互換性テスト推奨。
- ai モジュールは gpt-4o-mini（JSON mode）による出力形式と堅牢なパースを前提としているが、LLM の応答形式変化に対する監視が必要。
- 初期リリースのため、さらに細かなエラーハンドリングや性能チューニング、API クライアントの抽象化（DI）が今後の改善候補。

作者・貢献
- 本リリースは初版機能群の実装を含みます。今後の機能追加・改善要望は CHANGELOG の Unreleased に記録してください。