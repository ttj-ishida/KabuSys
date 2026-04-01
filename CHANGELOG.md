CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" のガイドラインに従っています。

v0.1.0 - 2026-04-01
-------------------

Added
- パッケージ初期リリース。
- パッケージメタ情報:
  - kabusys.__version__ = 0.1.0
  - パッケージ公開 API: data, strategy, execution, monitoring（__all__）

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイル（.env, .env.local）または OS 環境変数から設定を自動読み込みする仕組みを提供。
  - プロジェクトルートの自動検出ロジック（.git または pyproject.toml を起点）を実装。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサーを実装（export プレフィックス、シングル/ダブルクォート、エスケープ処理、インラインコメントの扱いに対応）。
  - OS 環境変数を保護する protected オプションを実装（.env.local による上書きを制御）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB /監視 /システム関連の設定プロパティを取得可能に。
  - 環境値検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック、必須環境変数の未設定での明示的例外）。

- AI（自然言語処理）機能（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp.score_news）
    - raw_news と news_symbols を集約し、銘柄ごとに記事をまとめて OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - JST ベースのニュース収集ウィンドウ計算（前日15:00〜当日08:30 JST）のユーティリティ（calc_news_window）。
    - チャンク処理（最大 20 銘柄/リクエスト）、1 銘柄あたりの最大記事数・文字数のトリム実装。
    - OpenAI レスポンスの厳格なバリデーション（JSON 抽出、results 配列、code/score 検証、数値の有限性チェック）。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフでのリトライ実装。
    - フェイルセーフ設計: API 失敗時は該当チャンクをスキップし、部分成功の書き込みは既存スコアを保護（対象コードのみ DELETE → INSERT）。
    - スコアは ±1.0 にクリップ。
    - テスト容易性のため、OpenAI 呼び出し箇所を差し替え可能（内部 _call_openai_api をパッチ可能）。

  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
    - ETF 1321（Nikkei225 連動 ETF）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照して ma200_ratio を算出、マクロ記事はキーワードフィルタで抽出、OpenAI で macro_sentiment を評価。
    - LLM 呼び出しは独立実装でモジュール結合を避ける。
    - API エラー時は macro_sentiment=0.0 へフォールバックし処理継続。
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。

- データプラットフォーム機能（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー取得・保存のバッチ処理（calendar_update_job）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定 API。
    - market_calendar がない場合は土日ベースのフォールバックを採用し、DB 登録ありの場合は DB 値優先。未登録日は曜日ベースで一貫した補完。
    - 最大探索日数や健全性チェック、バックフィルの日数等を導入して安全性を確保。

  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを公開（取得/保存したレコード数、品質問題、エラーの集計）。
    - 差分更新、バックフィル、J-Quants クライアント経由の冪等保存（ON CONFLICT 相当）と品質チェックの統合が可能な骨組みを実装。
    - テスト容易性のため id_token 等の注入を想定した設計。

- 調査 / 研究ツール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン）、200 日 MA 乖離、ATR（20 日）、平均売買代金、出来高比率、などの計算関数（calc_momentum, calc_volatility, calc_value）。
    - raw_financials からの財務指標取得と PER / ROE 計算。
    - DuckDB を使った SQL ベースの実装で外部サービスにアクセスしない安全設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 指定ホライズンのリターンを一括取得可能。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関に基づく評価（ties 対応）。
    - ランク関数（rank）と統計サマリー（factor_summary）を提供。
    - pandas 等に依存せず標準ライブラリのみで実装。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Notes / 設計上の重要ポイント
- ルックアヘッドバイアス防止: 主要モジュール（news_nlp, regime_detector, research）は datetime.today()/date.today() を内部で参照せず、外部から target_date を与える設計。
- DB 書き込みは冪等性を意識（DELETE→INSERT や ON CONFLICT 相当）しており、部分失敗時に既存データが不必要に削除されないよう配慮。
- OpenAI 呼び出しでは JSON Mode を想定し厳密なパースとフォールバックを実装。API エラーは再試行・ログ記録・フェイルセーフ（安全なデフォルト値）へフォールバック。
- テスト容易性: OpenAI 呼び出し関数等をモック／パッチできるよう内部関数を分離。

Upgrade / Migration notes
- 既存の利用者は以下点に注意:
  - 環境変数の必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）を .env または OS 環境変数に設定してください。未設定時は Settings プロパティが ValueError を投げます。
  - 自動 .env ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Security
- 重要なシークレット（OpenAI API キー等）は環境変数から取得する想定です。ローカル .env を使用する場合は権限・配布に注意してください。

Acknowledgements
- 本リリースは J-Quants, OpenAI, DuckDB 等の外部サービス／ライブラリを前提とした機能群を含みます。