# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に従います。  
未リリースの変更は "Unreleased" に記載し、リリースごとにバージョンを追加してください。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-31
初回リリース。日本株自動売買システム "KabuSys" の基礎機能群を公開します。

### 追加（Added）
- パッケージ構成
  - kabusys パッケージの初期公開（サブパッケージ: data, research, ai, research, ほか）。
  - バージョン情報: __version__ = "0.1.0" を設定。

- 環境設定 / 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - .env のパース実装（コメント行、export プレフィックス、クォートおよびエスケープ対応、インラインコメント処理など）。
  - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを追加し、J-Quants / kabuステーション / Slack / DB /監視 /システム設定等の設定プロパティを提供。
  - 設定値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と必須環境変数未設定時の明示的エラー (_require)。

- AI（kabusys.ai）
  - ニュースセンチメント分析モジュール（news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとのニューステキストを作成。
    - OpenAI（gpt-4o-mini、JSON mode）を用いたバッチセンチメント取得。
    - チャンク処理（最大 20 銘柄/チャンク）、トークン肥大対策（記事件数・文字数トリム）。
    - 再試行ロジック（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ）。
    - レスポンス検証ロジック（JSON 抽出、"results" 構造検証、スコア数値検証、既知銘柄コードのみ採用）。
    - ai_scores テーブルへの冪等的書き込み（該当コードだけ DELETE → INSERT）。
    - テスト容易性のため _call_openai_api を patch で差し替え可能に設計。

  - 市場レジーム判定モジュール（regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を算出。
    - prices_daily / raw_news / market_regime を参照し、計算結果を冪等的に market_regime テーブルへ書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API 呼び出しのリトライ（最大 3 回）とフェイルセーフ（API失敗時は macro_sentiment=0.0）。
    - マクロニュース抽出用のキーワード群を内包。
    - テスト容易性のため _call_openai_api を patch で差し替え可能に設計。

- データ基盤（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - market_calendar を用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DBにデータが無い場合は曜日ベースのフォールバック（週末を休場と判定）。
    - calendar_update_job: J-Quants からの差分取得・バックフィル・保存処理（fetch/save の呼び出しとエラーハンドリング）。
    - 探索上限や健全性チェック（最大探索日数、バックフィル日数、未来日付のサニティチェック）を実装。

  - ETL パイプライン（pipeline）
    - ETLResult dataclass を追加（実行結果の集約、品質問題の一覧化、エラー有無判定、辞書化ユーティリティ）。
    - ETL 実装方針に基づいたユーティリティ関数群の雛形（テーブル存在チェック、最大日付取得等）。

  - etl モジュールは pipeline.ETLResult を公開。

- リサーチ（kabusys.research）
  - ファクター計算（factor_research）
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）を計算する関数群を実装。
    - DuckDB による SQL ベースの計算を採用し、外部 API に依存しない設計。
    - データ不足時の None ハンドリングを実装。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns: 複数ホライズン対応、入力検証）。
    - IC（Information Coefficient）計算（calc_ic: スピアマンランク相関）。
    - ランキング変換ユーティリティ（rank: 同順位は平均ランク処理）。
    - ファクター統計サマリ（factor_summary: count/mean/std/min/max/median）。

### 変更（Changed）
- （初回リリースのため履歴なし）

### 修正（Fixed）
- （初回リリースのため履歴なし）

### 注意点 / 設計上の点（Notes）
- ルックアヘッドバイアス防止のため、内部実装は datetime.today() / date.today() を直接参照せず、すべて target_date 引数ベースで動作するよう設計されています。
- OpenAI API 呼び出しは外部依存のため、API キー（api_key 引数または環境変数 OPENAI_API_KEY）が必要です。未設定時は ValueError を発生させます。
- OpenAI 呼び出しは JSON Mode を前提としたレスポンスパースを行いますが、実運用では外部 API の挙動に応じた追加の堅牢化が必要になる場合があります。
- DuckDB を前提とした SQL クエリ設計（ウィンドウ関数等）になっています。DuckDB のバージョン差異に注意してください（ex. executemany の空パラメータ制約への対処あり）。
- テスト容易性のため、AI 呼び出し部分は patch による差し替えを想定した設計（private helper の明確化）になっています。
- 一部モジュールは jquants_client 等の外部モジュール（データ取得/保存）に依存します。実データ読み込み・保存にはその実装が必要です。

---

（補記）ソースコードの大部分は DuckDB 接続を受け取って動作する関数群で構成されており、本リリースは「計算・判定・ETL のコアロジック」を中心に実装されています。運用・発注（execution）、監視（monitoring）、ストラテジー（strategy）等のサブパッケージはパッケージ定義に含まれていますが、本 CHANGELOG は公開されたコードベースの実装内容に基づいて記載しています。