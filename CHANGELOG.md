CHANGELOG
=========

すべての重要な変更をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

- （なし）


[0.1.0] - 2026-03-27
--------------------

Added
- 初回リリース。日本株自動売買プラットフォームの基礎機能を提供するパッケージを追加。
  - パッケージ公開: kabusys.__init__ により主要サブパッケージをエクスポート（data, strategy, execution, monitoring）。
- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml から検出）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーの強化:
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメントの扱い（クォートあり/なしでの差分処理）
  - Settings クラスを用意し、J-Quants / kabuステーション / Slack / DB パス / 実行環境 / ログレベル等のプロパティを提供。
    - 必須値未設定時に明確な ValueError を送出する _require を実装。
    - KABUSYS_ENV と LOG_LEVEL の値バリデーションを実装（有効値限定）。
    - デフォルト DuckDB / SQLite パスの設定（data/kabusys.duckdb, data/monitoring.db）。
- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）にバッチ送信して銘柄別センチメント（-1.0〜1.0）を算出。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリで使用）。
    - バッチ処理: 最大 _BATCH_SIZE（20）銘柄ごとに API 呼び出し。
    - 1銘柄あたり最大記事数・文字数でトリム（_MAX_ARTICLES_PER_STOCK=10, _MAX_CHARS_PER_STOCK=3000）。
    - API リトライ（RateLimit / ネットワーク / タイムアウト / 5xx）に対する指数バックオフを実装。
    - レスポンス検証ロジックを実装（JSON 抽出、構造チェック、コード照合、数値チェック、スコアのクリップ）。
    - スコアを書き込む際は部分失敗に備え、対象コードだけを DELETE → INSERT で置換（冪等性、既存スコア保護）。
    - テスト容易性: _call_openai_api をパッチ差し替え可能に設計。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み70%）とマクロ経済ニュースの LLM センチメント（重み30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは news_nlp.calc_news_window に基づくウィンドウで抽出し、OpenAI（gpt-4o-mini）で JSON レスポンスを要求してスコア化。
    - API 呼び出しのリトライ/バックオフ、5xx とそれ以外の扱い、JSON パース失敗時はフェイルセーフで macro_sentiment=0.0 にフォールバック。
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - ルックアヘッドバイアス対策: datetime.today() / date.today() を参照せず、与えられた target_date に対してのみ処理。
- データモジュール (kabusys.data)
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar を参照して営業日判定・前後営業日検索・期間内営業日取得・SQ 日判定を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - カレンダー未取得時は曜日ベース（平日を営業日）でフォールバックする一貫した挙動を実装。
    - calendar_update_job を実装し、J-Quants から差分取得 → 保存（バックフィルや健全性チェック付き）を行うバッチ処理を提供。
  - ETL パイプライン (kabusys.data.pipeline / kabusys.data.etl)
    - ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラーの集約、辞書化メソッドを含む）。
    - 差分更新、バックフィル、idempotent な保存、品質チェックの収集という設計方針を実装（jquants_client と quality モジュールを利用する前提）。
    - ユーティリティ関数（テーブル存在確認、最大日付取得、market_calendar 調整等）を提供。
    - kabusys.data.etl で ETLResult を再エクスポート。
- リサーチモジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - モメンタム: calc_momentum（1M/3M/6M リターン、200日MA乖離など）
    - ボラティリティ/流動性: calc_volatility（20日 ATR、平均売買代金、出来高比率など）
    - バリュー: calc_value（PER, ROE の計算、raw_financials の最新財務を使用）
    - すべて DuckDB の prices_daily / raw_financials のみ参照し、外部 API へはアクセスしない方針。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算: calc_forward_returns（任意ホライズンでのリターン）
    - IC（Information Coefficient）計算: calc_ic（ランク相関・Spearman）
    - ランキング補助: rank（同順位は平均ランク）
    - 統計サマリー: factor_summary（count/mean/std/min/max/median）
  - 研究向けユーティリティを kabusys.research.__init__ でまとめてエクスポート（zscore_normalize 等の既存ユーティリティと統合）。
- 実装上の注意点（横断）
  - DuckDB を主要な永続化・照会エンジンとして使用（関数は DuckDB 接続オブジェクトを受け取る）。
  - OpenAI 呼び出しは JSON Mode を利用し、厳密な JSON 出力を期待する設計だが、余計な前後テキストが混入した場合の復元ロジックを組み込む。
  - テスト容易性を意識し、API 呼び出し部分（_call_openai_api）をモック可能に設計。
  - ルックアヘッドバイアス回避のため、内部処理はすべて与えられた target_date に依存する（グローバルな現在日時参照を避ける）。

Changed
- 初回リリースにつき該当なし。

Fixed
- 初回リリースにつき該当なし。

Security
- 初回リリースにつき該当なし。

Upgrade / Migration Notes
- OpenAI API キー
  - news_nlp.score_news / regime_detector.score_regime は api_key を引数で受け取ります。引数を渡さない場合は環境変数 OPENAI_API_KEY を使用します。未設定時は ValueError が発生します。
- 環境変数 / .env
  - 自動でプロジェクトルートの .env を読み込みます。テスト時や明示的に無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings のプロパティ参照）。
- データベース
  - 多くの関数は DuckDB 内の以下のテーブルを前提とします: prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等。初回利用前に適切なスキーマとデータを用意してください。
- 部分失敗の挙動
  - API 呼び出しの失敗やレスポンスの不備があっても「フェイルセーフ」動作を優先します（該当箇所はログ出力のうえ、スコアは 0.0 にフォールバックまたは該当銘柄をスキップ）。ETL では品質チェックでの問題を収集して呼び出し元に委ねる設計です。

既知の制約 / 注意事項
- OpenAI モデルとして gpt-4o-mini を指定している（利用可否は要確認）。
- DuckDB のバージョン依存（executemany の空リスト扱いなど）を考慮した防御的実装が多数あるため、古い DuckDB での動作確認を推奨。
- calendar_update_job は J-Quants クライアント（kabusys.data.jquants_client）に依存。実行前にクライアント実装と認証情報を準備すること。

---

この CHANGELOG はコード内容から推測して作成しています。実際のリリースノートとして使用する際は、差分情報や実際の変更履歴に合わせて適宜修正してください。