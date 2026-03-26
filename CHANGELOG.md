CHANGELOG
=========

すべての変更は Keep a Changelog の書式に従います。  
重大なバージョンは SemVer に準拠します。

Unreleased
----------

- （なし）

[0.1.0] - 2026-03-26
--------------------

Added
- 基本パッケージ初期リリース。パッケージメタ:
  - パッケージバージョン: 0.1.0
  - パッケージ名: kabusys
  - __all__ に data/strategy/execution/monitoring を公開
- 環境変数／設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動ロード（プロジェクトルート検出: .git または pyproject.toml）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env のパース機能を実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理等）。
  - .env と .env.local の優先順制御（.env.local が上書き）。OS 環境変数は保護（protected）される。
  - 必須設定取得ヘルパー _require() を実装し、未設定時は ValueError を送出。
  - 標準的な設定プロパティを提供: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルトあり）、SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH。
  - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証ロジック、および便利なブールプロパティ is_live/is_paper/is_dev を提供。
- AI モジュール (kabusys.ai)
  - ニュースセンチメントスコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を元に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）にバッチで送信してセンチメント（-1.0〜1.0）を生成。
    - バッチサイズ制限、1銘柄あたりの記事数・文字数トリム、最大リトライ（429/ネットワーク/タイムアウト/5xx）および指数バックオフを実装。
    - JSON Mode レスポンスのバリデーションとフォールバック処理（前後の余計なテキストから最外の {} を抽出）。
    - スコアは ±1.0 にクリップ。部分成功時に既存スコアを保護するため、対象コードのみ DELETE → INSERT の冪等書き込みを行う。
    - テスト容易性のため _call_openai_api を patch して差し替え可能。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す。APIキー未指定時は環境変数 OPENAI_API_KEY を参照。
    - ニュースウィンドウ計算 util: calc_news_window(target_date)（JST 基準で前日 15:00 ～ 当日 08:30 を UTC に変換して返す）。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定。
    - マクロニュースは raw_news からキーワードでフィルタ（複数キーワード定義）し、最大記事数を制限して LLM に送信。
    - OpenAI 呼び出しは独立実装で、リトライ（エクスポネンシャルバックオフ）とフェイルセーフ（失敗時 macro_sentiment=0.0）を備える。
    - MA200 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。データ不足時は中立扱い（ma200_ratio=1.0）。
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。
- Research モジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - モメンタム（1M/3M/6M）、200日MA乖離、ATR/相対ATR、20日平均売買代金・出来高比などを計算する関数を提供: calc_momentum, calc_volatility, calc_value。
    - DuckDB のウィンドウ関数を活用し、データ不足時は None を返す設計。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応、入力検証あり）。
    - IC 計算 calc_ic（Spearman の順位相関）、rank ユーティリティ、factor_summary（count/mean/std/min/max/median）。
  - これらは外部 API にアクセスせず、DuckDB の prices_daily / raw_financials テーブルのみを参照する方針。
- Data モジュール (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダーを管理するユーティリティを実装。is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar テーブルの有無による DB 優先・未登録日の曜日フォールバックロジックを備える。
    - calendar_update_job により J-Quants API から差分取得し冪等保存（バックフィル・健全性チェック含む）を実現。
  - ETL パイプライン (kabusys.data.pipeline)
    - ETLResult データクラスを実装（取得/保存件数、品質チェック結果、エラー一覧等を保持）。to_dict() で品質情報をシリアライズ可能。
    - 差分更新、バックフィル、品質チェックを想定した設計（jquants_client と quality モジュールに依存）。
  - etl サブパッケージは pipeline.ETLResult を再エクスポート。
- その他
  - duckdb をデータバックエンドとして使用する前提のクエリ群（全モジュールで DuckDB 接続オブジェクトを受け取る設計）。
  - ロギング（logger）を各モジュールに導入し、情報・警告・例外ログを適切に出力する方針。

Changed
- （初回リリースのため無し）

Fixed
- （初回リリースのため無し）

Removed
- （初回リリースのため無し）

Security
- 環境変数に依存する機密情報（OpenAI API キー、Slack トークン、Kabu API パスワード、J-Quants トークン等）については取得時に未設定であれば ValueError を送出して明示的な設定を要求。
- .env 自動ロードは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes / Migration
- 初回セットアップ:
  - .env.example を参照して .env を作成し、必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY 等）を設定してください。
  - Docker / CI 等で自動ロードを妨げたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB:
  - デフォルトの DuckDB パスは data/kabusys.duckdb、SQLite は data/monitoring.db。必要に応じて DUCKDB_PATH / SQLITE_PATH をオーバーライドしてください。
- OpenAI:
  - news_nlp と regime_detector は gpt-4o-mini の JSON Mode を前提とした実装になっています。テスト時は各モジュールの _call_openai_api を patch してモックできます。
- ルックアヘッドバイアス防止:
  - 日付関連処理は内部で datetime.today()/date.today() を参照しない設計（target_date 引数ベース）。バッチ運用時は target_date を明示的に渡してください。

開発メモ（内部設計上の重要点）
- DuckDB の executemany に空リストを渡せない点に対するガード（params が空でないことを確認してから executemany を実行）。
- API 呼び出しでの 5xx とネットワークエラーは再試行対象、非 5xx エラーは即時フェイル（あるいはスキップ）として堅牢化。
- market_regime / ai_scores 等への書き込みは冪等性を重視（DELETE → INSERT の形で置換）。
- モジュール間の結合を避けるため、OpenAI 呼び出しヘルパーはモジュールごとに独立実装。

今後の予定（例）
- strategy / execution / monitoring の具体実装（現行は __all__ に名前のみ公開）。
- 追加の品質チェックルールやデータ補正ロジックの強化。
- テストカバレッジ拡充（特に OpenAI 呼び出しのリトライ/フォールバック挙動）。