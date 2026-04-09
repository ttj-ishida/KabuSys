# Changelog

すべての重要な変更を記録します。本ファイルは Keep a Changelog のフォーマットに準拠しています。

## [Unreleased]

## [0.1.0] - 2026-04-09

初回リリース。本リリースでは日本株自動売買システムのコア機能群（設定管理、データ ETL / カレンダー管理、リサーチ / ファクター計算、ニュース NLP / レジーム検出、ETL パイプライン用ユーティリティ等）を実装しました。

### Added
- パッケージの初期化
  - kabusys パッケージを公開（__version__ = 0.1.0）。パッケージ API として data, strategy, execution, monitoring を __all__ で宣言。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動ロードする仕組みを実装。
    - プロジェクトルート検出: __file__ を起点に .git または pyproject.toml を探索してプロジェクトルートを決定（配布後の動作を考慮）。
    - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト等で利用可能）。
    - ロード順: OS 環境 > .env.local（上書き） > .env（未設定時にセット）。
    - .env パーサは export KEY=val、クォート、エスケープ、インラインコメントなどに対応。
    - 既存 OS 環境変数を保護する protected セットを導入。
  - Settings クラスを提供し、主要設定をプロパティとして安全に取得できるように実装。
    - J-Quants / kabu API / LINE / データベースパス / Paper Trading / 監視設定 / ログレベル / 環境種別などの設定をサポート。
    - 値検証（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）とヘルプメッセージを実装。
    - ファイルパス設定は Path.expanduser により ~ を展開。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集約し、OpenAI Chat（gpt-4o-mini の JSON Mode）で銘柄別センチメントを算出して ai_scores テーブルへ書き込む機能を実装。
  - 処理の特徴:
    - JST ベースのニュース収集ウィンドウ計算（前日 15:00 ～ 当日 08:30 JST を UTC に変換）を実装。
    - 1 銘柄あたりの最大記事数・最大文字数トリム（トークン肥大化対策）。
    - 最大 20 銘柄単位のバッチ送信（_BATCH_SIZE）。
    - 429 / ネットワーク断 / タイムアウト / 5xx を対象とした指数バックオフリトライ。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、code/score の検証、スコアのクリップ）。
    - 部分失敗時に既存スコアを消さないための置換ロジック（対象コードに対する DELETE → INSERT）。
  - テスト容易性のため、OpenAI 呼び出し関数（_call_openai_api）を patch で差し替え可能に実装。

- レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225 連動型）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を算出し、market_regime テーブルへ冪等書き込みする機能を実装。
  - 処理の特徴:
    - DuckDB を用いた ma200_ratio 計算（ルックアヘッド防止のため target_date 未満のデータのみ使用）。
    - マクロキーワードによる raw_news フィルタと最大件数制限。
    - OpenAI 呼び出し（gpt-4o-mini）を使ったセンチメント評価。API 失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - API リトライ（429・ネットワーク・タイムアウト・5xx）と指数バックオフ。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等パターン、失敗時は ROLLBACK（失敗ログ）して例外を伝播。

- データ（kabusys.data）
  - カレンダー管理（calendar_management）:
    - market_calendar テーブルを基に営業日判定・前後営業日取得・期間内営業日取得・SQ 日判定等の API を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未登録の場合は曜日ベースのフォールバック（週末は非営業日）。
    - 最大探索範囲で無限ループを防止する安全策（_MAX_SEARCH_DAYS）。
    - calendar_update_job: J-Quants クライアント経由で JPX カレンダーを差分取得し保存（バックフィル・健全性チェック含む）。
  - ETL パイプライン（pipeline）:
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - ETL の設計方針に基づく差分更新・バックフィル・品質チェック連携を想定した構造を実装。
    - ETLResult は品質問題やエラーの集約、辞書変換ユーティリティを提供。

- リサーチ（kabusys.research）
  - factor_research:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）等のファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB のウィンドウ関数を活用し、date, code ベースで結果を返す。
    - データ不足時の None ハンドリングを実装。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、rank（同順位は平均ランクの実装）、factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。
  - data.stats の zscore_normalize を再公開（research パッケージから利用可能）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーや機密情報は Settings 経由で取り扱い、.env の自動ロードは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）にしてテストや CI の誤送信リスクを低減。

### Notes / Design decisions
- ルックアヘッドバイアス対策: 全ての分析・スコアリング関数は date / target_date を明示的に受け取り、datetime.today()/date.today() を直接参照しない設計。
- DuckDB を主要なストレージ層として利用。SQL と Python の組合せで効率的に集計・ウィンドウ処理を行う。
- 外部 API 呼び出し（OpenAI / J-Quants）に対してはフェイルセーフ（失敗時はスキップまたはデフォルト値）を採用し、システム全体のロバスト性を優先。
- テスト容易性を考慮し、OpenAI 呼び出しや環境ロード部分は差し替え可能（patchable）に実装。

---

（今後のリリースではバージョン毎に変更を追記してください。）