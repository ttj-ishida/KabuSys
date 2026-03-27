Keep a Changelog
すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の慣習に従っています。

フォーマット:
- すべての変更はセクション（Added, Changed, Fixed, Deprecated, Removed, Security）に分類しています。
- 日付はリリース日を示します。

Unreleased
- （現在なし）

[0.1.0] - 2026-03-27
Added
- 初回公開: KabuSys 0.1.0 — 日本株自動売買／データ分析プラットフォームの基礎機能を公開。
  - パッケージ情報
    - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。
    - パッケージ公開 API の __all__ に data, strategy, execution, monitoring を含める。
  - 設定管理 (src/kabusys/config.py)
    - Settings クラスを導入し、環境変数経由で設定を取得するプロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）。
    - .env 自動読み込み機構を実装:
      - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
      - export 形式、シングル／ダブルクォート、エスケープ、インラインコメント等に対応する堅牢なパーサを実装。
    - 環境値の検証ロジック（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）を実装。
    - デフォルトのデータベースパス（DuckDB / SQLite）プロパティを提供。
  - AI モジュール (src/kabusys/ai)
    - ニュース NLP (src/kabusys/ai/news_nlp.py)
      - score_news(conn, target_date, api_key=None): raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとのニュースセンチメントを算出し ai_scores テーブルへ保存。
      - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST）を calc_news_window で提供。
      - バッチ処理（最大 20 銘柄/回）、記事トリム（最大記事数・最大文字数）などトークン肥大化対策を実装。
      - API 呼び出しの再試行（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）およびレスポンス検証（JSON モードのフォールバック等）。
      - DuckDB に対する安全な書き込み（部分置換: 対象コードのみ DELETE → INSERT）を実装。
    - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
      - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ冪等書込。
      - prices_daily クエリはルックアヘッドを避けるため target_date 未満のデータのみを使用。
      - マクロ記事取得、LLM 呼び出し、リトライ、フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
  - データプラットフォーム (src/kabusys/data)
    - カレンダー管理 (src/kabusys/data/calendar_management.py)
      - market_calendar を用いた営業日判定APIを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
      - market_calendar が未取得のときは曜日ベース（土日非営業日）でフォールバック。
      - calendar_update_job(conn, lookahead_days=...) により J-Quants からの差分取得・保存（バックフィル、健全性チェック付き）を実装。
    - ETL パイプライン (src/kabusys/data/pipeline.py / etl.py)
      - ETLResult dataclass を公開（ETL 実行結果、品質問題、エラー情報の集約）。
      - 差分更新、バックフィル、品質チェックを意識した設計方針を実装（jquants_client, quality モジュールとの連携前提）。
    - ETLResult は to_dict() を持ち、品質問題をシリアライズ可能な形に変換。
    - data パッケージから ETLResult を再エクスポート。
  - 研究（Research）機能 (src/kabusys/research)
    - factor_research.py: calc_momentum, calc_value, calc_volatility を実装（prices_daily / raw_financials のみ参照）。
      - Momentum: mom_1m / mom_3m / mom_6m / ma200_dev（データ不足時は None を返却）。
      - Volatility: 20 日 ATR, 相対 ATR, 20 日平均売買代金, 出来高比率。
      - Value: PER, ROE（raw_financials の最新レコードを target_date 以前から取得）。
    - feature_exploration.py: calc_forward_returns（任意ホライズン）/ calc_ic（Spearman ランク相関）/ factor_summary（統計量）/ rank（平均ランク処理）を実装。
    - research パッケージの __init__ で主要関数を再エクスポート。
  - 汎用実装・設計上の配慮
    - DuckDB ベースの SQL と Python の混成処理でデータ処理を実現。
    - ルックアヘッドバイアス回避のため、内部で datetime.today() / date.today() を直接参照しない設計（関数は target_date を明示受け取り）。
    - OpenAI の出力が完全な JSON でない場合でも、{...} 部分を抽出してパースする復元処理を導入。
    - LLM が整数で銘柄コードを返すなどの不整合に対し耐性を持たせる（コードを str 正規化して照合）。
    - DuckDB 0.10 の executemany に空リストを与えると失敗する制約を回避するため、空チェックを明示的に行う。
    - ログ出力（info/warning/debug）を多用して運用時の可観測性を確保。

Fixed
- レスポンスパースの堅牢化:
  - LLM の JSON モードでも前後に余分なテキストが混入する場合に最外の {..} を抽出してパースすることでパース失敗を低減。
- news_nlp / regime_detector における API エラー処理の細分化とリトライロジックの実装（RateLimitError/APIConnectionError/APITimeoutError と APIError(5xx) を区別）。

Changed
- （初回リリースにつき該当なし）

Deprecated
- （初回リリースにつき該当なし）

Removed
- （初回リリースにつき該当なし）

Security
- OpenAI API キー等の機密情報は環境変数から取得する設計。設定取得に _require() を利用して未設定時は明示的にエラーを出すように実装。
- .env の自動ロードはデフォルトで有効。テスト時や特殊用途では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化可能。

互換性と既知の制約
- DuckDB を使用。ETL / データ処理は DuckDB のテーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）の存在を前提とする。
- news_nlp と regime_detector は OpenAI（gpt-4o-mini）へのアクセスを前提としており、API キーの提供が必須。
- LLM レスポンスの形式依存部分は存在するため、運用時はプロンプトとモデル挙動の監視が必要。
- DuckDB 0.10 の executemany の空リスト問題に対応済み。ただし、DuckDB の将来バージョンでの挙動変化に注意。
- calendar_update_job は jquants_client.fetch_market_calendar / save_market_calendar に依存し、これらの実装が必要。

必須環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- OPENAI_API_KEY（score_news / score_regime 実行時に必要）
- KABUSYS_ENV（development / paper_trading / live、未指定は development）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、未指定は INFO）

運用メモ（設計上の注意）
- AI スコアリング処理は外部 API の可用性に依存するため、API 失敗時は部分的にスコア取得が失敗することを想定した運用ロジックが必要（本実装はフェイルセーフでスキップ・部分書換を行う）。
- ルックアヘッドバイアス防止のため、すべてのバッチ関数は target_date を明示的に受け取り、DB クエリで date < target_date / date = target_date のように排他条件を採用している。
- LLM 呼び出しは応答の検証（JSON, codes の整合性, 数値チェックなど）を行い、検証失敗時はそのチャンクをスキップすることでデータ整合性を保護。

今後の予定（参考）
- モデルやプロンプトの微調整、OpenAI 呼び出しの抽象化（モックしやすいインタフェース化）。
- ETL の品質チェック（quality モジュール）とのより緊密な連携、監査ログの強化。
- strategy / execution / monitoring の実装・公開（現在はパッケージエクスポート名のみ存在）。

-----------------------------------------------------------------------------