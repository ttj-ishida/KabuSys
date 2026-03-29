# Keep a Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog の仕様に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買／リサーチ用のコアライブラリを追加。

### Added
- パッケージエントリポイント
  - kabusys パッケージを公開（__version__ = 0.1.0）。主要サブパッケージとして data, research, ai, monitoring, strategy, execution を想定してエクスポート。
- 環境設定モジュール（kabusys.config）
  - .env/.env.local ファイルおよび OS 環境変数から設定を自動読込する機能を実装。
  - プロジェクトルート自動検出（.git / pyproject.toml を探索）によりカレントディレクトリに依存しない自動ロードを実現。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env のパースロジックを実装（コメント、export プレフィックス、クォート・エスケープ処理、インラインコメントの扱いなどに対応）。
  - 必須環境変数取得ヘルパー _require と Settings クラスを提供。J-Quants / kabu API / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベルの検証・デフォルト設定を含む。
- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を元に、指定タイムウィンドウ（前日15:00 JST 〜 当日08:30 JST）に該当する記事を銘柄ごとに集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントスコアを ai_scores テーブルに保存する機能を実装。
    - バッチサイズ、記事数・文字数トリム、JSON モードのレスポンス検証、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを組み込み。
    - レスポンス検証ロジック（JSON 抽出、results フォーマット検証、未知コード無視、数値チェック、スコアクリップ）を実装。
    - score_news(conn, target_date, api_key=None) を公開。ETL的に書き込み（DELETE → INSERT）する際の部分失敗保護（対象コードのみ置換）を考慮。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime(conn, target_date, api_key=None) を実装。
    - マクロ記事抽出、OpenAI 呼び出し（JSON 出力期待）、再試行・フェイルセーフ（API 失敗時 macro_sentiment=0.0）、スコア合成と market_regime への冪等書き込みをサポート。
    - ルックアヘッドバイアス対策として target_date 未満のデータのみ参照する実装方針を採用。
- Data モジュール（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを用いた営業日判定（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB 未取得時は曜日ベース（土日非営業）でのフォールバック、DB がまばらな場合でも一貫した判定を返すロジックを実装。
    - JPX カレンダーの夜間差分更新 job（calendar_update_job）を実装。J-Quants クライアント経由の取得と保存、バックフィル・健全性チェックを含む。
  - ETL パイプライン（kabusys.data.pipeline, etl）
    - ETLResult データクラスを提供（取得数・保存数・品質チェック・エラー概要を含む）。
    - 差分更新・バックフィル・品質チェックの方針を実装する基盤ロジック（テーブル存在チェック、最大日付取得、トレーディング日調整等）を追加。
    - kabusys.data.etl から ETLResult を再エクスポート。
- Research モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER/ROE）を計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB での SQL を用いた実装により、prices_daily / raw_financials テーブルのみを参照。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient、calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB で完結する実装。
  - zscore_normalize 等のユーティリティを data.stats から再エクスポートするエントリポイントを追加。
- DuckDB を中心とした DB 操作
  - 複数モジュールで DuckDBPyConnection を受け取る設計を採用。全体的に SQL を活用して集計・ウィンドウ関数を実行。
- OpenAI クライアント呼び出しの抽象化
  - テスト容易性のため各モジュールで _call_openai_api を分離（unittest.mock で差し替え可能）。
- ロギングとフェイルセーフ
  - 各処理において詳細なログ出力を追加。API 失敗時のフェイルセーフ動作（0.0 フォールバック、スキップして継続、部分書き換え保護など）を実装。

### Changed
- 初版のため該当なし。

### Fixed
- 初版のため該当なし。

### Deprecated
- 初版のため該当なし。

### Removed
- 初版のため該当なし。

### Security
- .env 読み込み時に OS 環境変数を保護する仕組み（protected set）を導入し、override=True でも OS 側の設定を上書きしないよう保護。
- 必須の外部 API キー（OPENAI_API_KEY 等）は明示的に要求し、未設定時は ValueError を投げることで秘密情報が未設定のまま処理されることを防止。

---

注:
- 本リリースは「データ取得・解析・AI によるスコアリング・市場レジーム判定・研究用ファクター計算」を中心とした基盤実装です。  
- 実際の発注・実行ロジック（execution/strategy/monitoring 等）はパッケージ構成に含める設計が示唆されていますが、本バージョンで提供されるのは主にデータ・研究・AI スコアリング・カレンダー・ETL 基盤です。