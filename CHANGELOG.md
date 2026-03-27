Keep a Changelog
=================

すべての注目すべき変更点をこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」規約に従います。

[Unreleased]
------------

- なし（次のリリースに向けた未反映の変更がある場合に記載）

0.1.0 - 2026-03-27
-----------------

Added
- パッケージ初期リリース: kabusys v0.1.0 を追加。
  - パッケージメタ情報:
    - src/kabusys/__init__.py にてバージョンを設定（__version__ = "0.1.0"）。
    - パブリックモジュールとして data, strategy, execution, monitoring を公開。

- 環境設定 / 設定管理:
  - src/kabusys/config.py
    - .env ファイルおよび環境変数からの設定読み込みを実装（自動ロード。プロジェクトルートは .git または pyproject.toml を探索）。
    - .env のパースは export プレフィックス、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメントをサポート。
    - .env と .env.local の読み込み優先度（OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
    - 必須環境変数取得時の検証（_require）、多数の設定プロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL 等）。
    - 環境値の検証ロジック（有効な env / log level の集合チェック）とユーティリティプロパティ（is_live / is_paper / is_dev）。

- AI（ニュース NLP / レジーム判定）:
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）へバッチでセンチメント評価を行う ai スコアリング実装。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST の記事を対象）を calc_news_window として提供。
    - 1銘柄あたり最大記事数／最大文字数トリム、バッチサイズ制御、レスポンスバリデーション、スコアの ±1.0 クリップ、ai_scores テーブルへの冪等的書き込み（DELETE → INSERT）。
    - エラー耐性: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによる再試行、失敗時は部分的スキップして処理継続。
    - JSON モードのレスポンス復元（前後ノイズが混ざるケースで最外の {} を抽出）や数値検証等の堅牢化ロジック。
    - 単体テスト用に _call_openai_api をパッチ差替えできる設計。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロ経済ニュースの LLM センチメント（重み30%）を合成して、市場レジーム（bull/neutral/bear）を日次判定する機能。
    - MA200 乖離計算、マクロキーワードに基づく raw_news 抽出、OpenAI（gpt-4o-mini）呼び出し、レジームスコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API キー解決（引数優先、環境変数 OPENAI_API_KEY）、API 失敗時のフェイルセーフ（macro_sentiment=0.0）、リトライ／バックオフ、JSON パース耐性、ログ出力を備える。
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計（target_date を明示的に与える）。

- データプラットフォーム / ETL / カレンダー:
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar テーブル中心）のユーティリティを提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった営業日判定 API を実装。
    - market_calendar が未取得のときは曜日ベース（土日非営業）でフォールバックする一貫した設計。
    - calendar_update_job により J-Quants API からの差分取得、バックフィル、保存（ON CONFLICT DO UPDATE 相当）を行う夜間バッチ処理を実装。安全性のための健全性チェックやバックフィル期間の設定を備える。

  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETL 処理のインターフェースと結果データクラス ETLResult を追加。
    - 差分取得ロジック（最終取得日の検出、backfill の扱い）、DuckDB テーブル存在チェック、最大日付取得ヘルパー等を実装。
    - 品質チェックのため quality モジュールとの統合ポイントを想定（QualityIssue を保持する構造）。
    - etl の結果を辞書に変換するユーティリティ（to_dict）を提供。

- リサーチ / ファクター計算:
  - src/kabusys/research/factor_research.py, feature_exploration.py, __init__.py
    - モメンタム（1M/3M/6M）、ma200 乖離、ATR ベースのボラティリティ、流動性指標（20日平均売買代金、出来高比率）、バリュー（PER, ROE）等のファクター計算を実装（DuckDB クエリベース）。
    - 将来リターン calc_forward_returns、IC（Spearman ランク相関）calc_ic、ランク変換ユーティリティ rank、統計サマリー factor_summary を提供。
    - すべて DuckDB の prices_daily / raw_financials テーブルのみを参照し、本番口座・発注 API にアクセスしない設計。
    - zscore_normalize は data.stats から再エクスポート。

- 共通設計上の注意点（クロスモジュール）
  - ルックアヘッドバイアス回避: 多くのモジュールで date.today()/datetime.today() を直接参照せず、明示的な target_date を引数に取る設計。
  - DuckDB を主要な永続化手段として使用（関数は DuckDB 接続を引数に取る）。
  - DB 書き込みは可能な限り冪等性を保つ（DELETE → INSERT、ON CONFLICT 相当の保存等）。
  - OpenAI 呼び出しは JSON mode を利用し、レスポンスの堅牢な検証とエラー時のフォールバックを実装。
  - ロギングを多用して状態を記録し、異常時は例外の伝播または WARN/INFO ログで把握できるようにしている。
  - 単体テスト容易性のため、外部 API コール部分（_call_openai_api 等）をモンキーパッチ可能に設計。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Deprecated
- 初版のため該当なし。

Removed
- 初版のため該当なし。

Security
- 初版のため特記事項なし。

Known issues / Limitations
- jquants_client 等、外部クライアント実装（fetch/save 関数）はこの差分に依存しているが、本 changelog のコードスニペットに含まれていない。実運用時は該当クライアント実装・認証フローを整備する必要あり。
- OpenAI キーは環境変数から読み込む想定（OPENAI_API_KEY）。API 利用に伴うコスト制御やレート制御はアプリ側での運用管理が必要。
- 一部関数（データ保存処理、pipeline のトランザクション設計など）は DuckDB のバージョン依存挙動に注意（コメントで互換性対策を記載）。
- strategy / execution / monitoring モジュールは __all__ で公開されているが、この差分での実装は含まれていません（今後追加予定）。

作者ノート / 今後の予定
- strategy, execution, monitoring の具現化（自動売買ロジック・発注エンジン・監視通知）を追加予定。
- テストカバレッジ拡大（特に AI 呼び出し周りのモックテスト、ETL の回帰テスト）。
- API クライアント（J-Quants, kabu ステーション, Slack）との統合と運用監視の強化。

--- 

この CHANGELOG はコードベースから推測して作成しています。必要があれば、リリース日や対象範囲の修正、さらに詳細な変更点（ファイル単位の diff 等）を追記します。