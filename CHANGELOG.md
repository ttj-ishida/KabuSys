# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
このファイルは、リポジトリ内のソースコードから推測できる実装内容に基づいて作成した初期リリース向けの変更履歴です。

最新の変更
[Unreleased]

リリース
[0.1.0] - 2026-04-04
--------------------

Added
- 初期リリースとして kabusys パッケージを追加。
  - バージョンは src/kabusys/__init__.py の __version__ = "0.1.0" に従う。
- 環境設定・自動 .env ロード機能（src/kabusys/config.py）
  - プロジェクトルートを .git または pyproject.toml から検出して .env / .env.local を自動読み込み。
  - export 形式やクォート・インラインコメント・エスケープを考慮した .env パーサーを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - Settings クラスでアプリ設定を型付きプロパティとして提供（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / OPENAI 関連 / データベースパス / 監視閾値 / 環境モード等）。
  - 環境変数未設定時に _require() が ValueError を投げることで必須設定の早期検出を実現。
  - KABUSYS_ENV と LOG_LEVEL の妥当性チェック（許容値の列挙）。
- AI モジュール（src/kabusys/ai）
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini、JSON mode）へバッチ送信し、銘柄ごとにセンチメント ai_score を ai_scores テーブルへ書き込む score_news 関数を提供。
    - バッチサイズ・1銘柄あたりの記事数・文字数上限、タイムウィンドウ（JST→UTCで計算）などの制御を実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ、レスポンスの厳密なバリデーションとフォールバック（失敗時はスキップして継続）を実装。
    - DuckDB 互換性（executemany の空リスト回避）を考慮した書き込み実装。
    - テスト容易性のため OpenAI 呼び出し部分は差し替え可能（内部関数 _call_openai_api をモック可能）。
  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - ma200_ratio の計算、マクロニュース抽出、OpenAI 呼び出し、リトライ、JSON パース、スコア合成、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API 失敗時は macro_sentiment=0.0 のフェイルセーフ。
- Research（解析）モジュール（src/kabusys/research）
  - factor_research（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（EPS が 0/欠損の場合は None）。
    - 各関数は DuckDB 上で SQL と Python の組合せで処理し、(date, code) をキーとする dict のリストを返す設計。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定基準日から複数ホライズン（デフォルト: 1,5,21 営業日）の将来リターンを計算。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算。
    - rank: 同順位は平均ランクとするランク化関数を提供（丸め処理で ties の扱いを安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を標準ライブラリのみで計算。
  - research パッケージで主要関数を __all__ にて再エクスポート。
- Data / ETL（src/kabusys/data）
  - calendar_management（src/kabusys/data/calendar_management.py）
    - JPX カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日ロジックを実装。
    - market_calendar が無ければ曜日ベースのフォールバックを行う設計。
    - calendar_update_job により J-Quants から差分取得→冪等保存を実行（バックフィル・健全性チェック含む）。
  - pipeline / etl（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを実装し public インターフェースで再エクスポート（data.etl）。
    - ETL の設計方針（差分更新、backfill、品質チェックの取り扱い、jquants_client 呼び出し）を反映。
    - DuckDB のテーブル存在チェック等のユーティリティを実装。
  - jquants_client（参照のみ）を想定した保存/取得フローに対応（実装は外部モジュールに委譲）。
- パッケージ公開インターフェース
  - 各サブパッケージで主要関数・ユーティリティを __all__ により明示的に再エクスポート。

Changed
- 新規初期リリースのため、互換性を壊す変更はなし。

Fixed
- （初期リリースにつき該当なし）

Security
- 外部 API キー（OpenAI 等）を必要とする機能があるため、API キーの管理には環境変数を利用する設計。必須キー未設定時は早期例外を発生させることで誤動作を防止。

Notes / Design decisions（重要な設計注記）
- ルックアヘッドバイアス回避: 各 AI / 研究処理は datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計。
- 冪等性: DB 書き込みは idempotent に行う（DELETE → INSERT など）ことで再実行可能。
- フェイルセーフ: OpenAI API 失敗時は適切にデフォルト値（0.0 等）にフォールバックして処理継続する場面がある。部分失敗時でも既存スコアを不用意に削除しない設計。
- DuckDB 互換性: executemany の空リスト問題や日付型の取り扱い等、DuckDB のバージョン差分を考慮した実装（_to_date 等）。
- テスト容易性: OpenAI 呼び出し箇所は内部関数をモックしやすい構造になっている（_call_openai_api を patch して差し替え可能）。
- 必要な DB スキーマ（想定）: prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials などが前提。

Migration / Requirements（運用上の注意）
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN（Settings.jquants_refresh_token）
  - KABU_API_PASSWORD（Settings.kabu_api_password）
  - OPENAI_API_KEY（score_news / score_regime の呼び出し時に必要。引数経由でも指定可能）
- デフォルトファイルパス:
  - DUCKDB_PATH: data/kabusys.duckdb（Settings.duckdb_path のデフォルト）
  - SQLITE_PATH: data/monitoring.db（Settings.sqlite_path のデフォルト）
  - PID / KILL フラグ等の監視ファイルパスにデフォルトを設定
- KABUSYS_ENV は development / paper_trading / live のいずれかを指定。LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL。

既知の制約 / 今後の改善候補
- OpenAI への依存を抽象化してモックしやすくしているが、API モデルやレスポンス仕様が将来変わるとパースやバリデーションを更新する必要がある。
- データベーススキーマの作成・マイグレーション機構はこのコードに含まれていないため、運用前に必要なテーブル定義を用意する必要がある。
- news_nlp/regime_detector の JSON mode の扱いは厳密パースを行うが、LLM 出力のばらつき対策（より頑健な抽出）を強化する余地あり。

署名
- この CHANGELOG はリポジトリ内のソースコードから推測して作成したものであり、実際のソース管理履歴（コミットメッセージ等）と完全に一致するとは限りません。必要があれば差分や追加情報に基づいて修正します。