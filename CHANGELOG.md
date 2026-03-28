# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

最新の開発状況はトップの Unreleased セクションに記載します。リリースごとに下へ移動してください。

## [Unreleased]
（直近の開発中の変更はここに記載します）

## [0.1.0] - 2026-03-28
初回公開リリース

### Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定モジュール（kabusys.config）
  - .env ファイル自動読み込み機能を実装
    - プロジェクトルートを .git または pyproject.toml を基準に探索（CWD に依存しない）
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
  - .env パーサ実装（クォート、エスケープ、`export` プレフィックス、インラインコメント処理対応）
  - protected 引数による OS 環境変数の上書き防止
  - Settings クラスを提供:
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティ（必要時は ValueError を送出）
    - env / log_level の値検証（許容値は定義済み）
    - is_live / is_paper / is_dev の簡易判定プロパティ
  - デフォルト DB パス (DUCKDB/SQLite) の設定

- データプラットフォーム関連（kabusys.data）
  - calendar_management: JPX カレンダー管理と営業日ロジック
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装
    - market_calendar がない場合の曜日ベースのフォールバック
    - calendar_update_job: J-Quants から差分取得して冪等に保存する夜間バッチ処理（バックフィル／健全性チェック付き）
  - pipeline / etl:
    - ETL パイプライン用の ETLResult データクラス（結果の集約とシリアライズ機能付き）
    - 差分取得、バックフィル、品質チェックを想定した設計（jquants_client / quality と連携）

- AI モジュール（kabusys.ai）
  - news_nlp:
    - raw_news と news_symbols から銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）でセンチメントを算出
    - バッチ（最大20銘柄）処理、1銘柄あたりの最大記事数・文字数トリム、JSON mode 応答バリデーション
    - 再試行（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実装
    - レスポンス整形・スコアクリップ（±1.0）、DuckDB 互換性（executemany の空チェック）を考慮した DB 書き込み（DELETE→INSERT、トランザクション）
    - calc_news_window: JST ベースのニュース収集ウィンドウ計算ユーティリティ
  - regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定
    - LLM 呼び出しは専用ラッパーで実装（news_nlp の内部関数とは独立）
    - API 呼び出しの再試行、フェイルセーフ（API 失敗時は macro_sentiment=0.0）、冪等な DB 書き込みを実装

- リサーチモジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離などの算出
    - calc_volatility: 20 日 ATR、相対 ATR、出来高・売買代金関連
    - calc_value: PER / ROE の計算（raw_financials と prices_daily の組み合わせ）
    - DuckDB を用いた SQL ベース実装（外部 API にはアクセスしない）
  - feature_exploration:
    - calc_forward_returns: 任意ホライズンの将来リターンを一括で取得
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算
    - rank, factor_summary: ランク変換と統計サマリー
  - kabusys.data.stats から zscore_normalize を re-export

- テストしやすさを意識した設計
  - OpenAI 呼び出し箇所は internal な _call_openai_api を経由し、ユニットテストでモック可能
  - API キーは関数引数で注入可能（引数未指定時は環境変数 OPENAI_API_KEY を参照）
  - DuckDB 周りの互換性問題（executemany の空チェックなど）に配慮

### Changed
- （初版のため過去変更なし）

### Fixed
- （初版のため過去修正なし）

### Security
- 環境変数の取り扱いについて保護機能を実装（読み込み時に OS 環境変数を protected として上書きを防止）
- OpenAI API キー未設定時は明示的に ValueError を送出して誤動作を防止

### Design / Implementation notes
- ルックアヘッドバイアス防止のため、内部実装で datetime.today()/date.today() を参照しない設計方針を採用（主要関数は target_date を明示的に受け取る）
- DB 書き込みは可能な限り冪等に（DELETE→INSERT、トランザクション）実装
- LLM レスポンスは厳密な JSON を想定しつつ、パース不良に対する復元処理も実装（最外側の {} を抽出する等）
- 失敗時はフェイルセーフとして「処理をスキップして継続」する挙動を基本とする（ログ出力で状況を通知）

### Known issues / Notes
- OpenAI API キー未設定の場合、news_nlp.score_news / regime_detector.score_regime は ValueError を送出する（利用前に環境変数 or 引数での設定が必要）
- calendar_update_job / ETL 周りは外部 J-Quants クライアント（jquants_client）に依存しており、API エラー時は 0 を返して処理継続する設計
- DuckDB バインドの互換性については注意（executemany の空リスト回避を実装済み）

---

（今後のリリースでは、API の安定化、追加の監視/実行モジュール、ドキュメント・サンプル・ユニットテストの追加を予定しています）