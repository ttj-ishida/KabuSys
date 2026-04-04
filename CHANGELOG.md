# Changelog

すべての重要な変更履歴を記録します。本ファイルは「Keep a Changelog」の慣習に準拠しています。日付はリリース日（YYYY-MM-DD）です。

なお、本リポジトリの初期バージョンは package の __version__ に合わせて 0.1.0 として公開しています。

## [Unreleased]

（未リリースの変更をここに記載してください）

---

## [0.1.0] - 2026-04-04

初期リリース。日本株のデータ処理・リサーチ・AI によるニュース解析・市場レジーム判定・ETL・カレンダー管理など、取引アルゴリズム基盤に必要なコア機能をまとめて提供します。主な追加点は以下のとおりです。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。主要サブパッケージを __all__ で公開: data, strategy, execution, monitoring。
- 設定・環境変数管理（kabusys.config）
  - .env ファイル（.env, .env.local）と OS 環境変数を統合して読み込む自動ロード機構を実装。読み込み優先度は OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト等で使用可能）。
  - .env パーサの強化:
    - export プレフィックス対応
    - シングル/ダブルクォート、バックスラッシュエスケープ処理
    - 行末コメント（スペース前の # をコメントと扱う）への対応
  - 環境値取得ユーティリティ Settings を提供（例: settings.jquants_refresh_token, settings.duckdb_path 等）。必須変数未設定時は明示的に ValueError を発生させる _require を実装。
  - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）のバリデーションを実装。
- AI（自然言語処理）
  - kabusys.ai.news_nlp
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini を想定）へバッチ送信して銘柄ごとのセンチメント ai_score を生成・ai_scores テーブルへ書き込む機能を実装（score_news）。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を提供。
    - バッチ処理、1チャンク最大20銘柄、1銘柄あたり記事数上限・文字数トリムによりトークン肥大対策を実装。
    - JSON Mode を利用した厳密なレスポンス検証。レスポンスのバリデーション（構造・型・既知コード・数値性）を実装。
    - エラー耐性: 429・ネットワークエラー・タイムアウト・5xx に対する指数バックオフリトライを実装。失敗時は部分スキップし、他銘柄データを保護して継続。
    - テスト容易性を考慮し、OpenAI 呼び出し（_call_openai_api）を patch できる設計。
  - kabusys.ai.regime_detector
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定・market_regime テーブルへ冪等的に書き込む機能を実装（score_regime）。
    - マクロキーワードリスト、最大記事数、LLM モデル（gpt-4o-mini）やリトライ戦略を定義。
    - API 失敗時は macro_sentiment を 0.0 にフォールバックするフェイルセーフを実装。
    - レジームスコア合成ロジック、閾値（BULL_THRESHOLD/BEAR_THRESHOLD）を含む。
- リサーチ / ファクター計算（kabusys.research）
  - factor_research モジュール
    - calc_momentum: mom_1m/3m/6m、ma200 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務データを取得して PER、ROE を計算（EPS=0/欠損は None）。
  - feature_exploration モジュール
    - calc_forward_returns: 任意ホライズンの将来リターン（デフォルト [1,5,21]）を計算。ホライズンの妥当性チェックあり。
    - calc_ic: スピアマン（ランク相関）による IC を計算。データ不足（有効レコード < 3）時は None を返す。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量サマリーを実装。
  - これらは DuckDB 接続を受け取り prices_daily / raw_financials 等のみを参照し、本番口座や発注 API へアクセスしない設計。
- データプラットフォーム（kabusys.data）
  - calendar_management
    - JPX カレンダーの更新バッチ（calendar_update_job）、営業日判定 (is_trading_day)、翌/前 営業日 (next_trading_day / prev_trading_day)、期間内営業日列挙 (get_trading_days)、SQ 判定 (is_sq_day) を実装。
    - market_calendar 未取得時は曜日ベース（土日休）でフォールバックする堅牢な設計。DB 登録値を優先し未登録日は一貫した曜日フォールバックを適用。
    - 異常検知（将来日付の健全性チェック）、バックフィルロジックを実装。
  - pipeline / ETL
    - ETLResult データクラスを公開（kabusys.data.etl から再エクスポート）。ETL の取得件数・保存件数・品質問題・エラー一覧などを集約。
    - ETL 処理設計（差分更新、backfill、idempotent 保存、品質チェックの集約）に沿った基盤ロジック（pipeline モジュール）を実装。
  - 一部ユーティリティは DuckDB の互換性（executemany の空リスト制約など）を考慮して実装。
- ロギング・保護
  - 各モジュールにて情報 / 警告 / 例外時のログ出力を適切に実装。
  - DB 書き込みは可能な限り冪等（DELETE して INSERT、BEGIN/COMMIT/ROLLBACK）を意識。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- OpenAI API キーは引数注入と環境変数（OPENAI_API_KEY）両方に対応。未設定時は明示的に ValueError を返すことで誤操作を防止。

### Notes / Implementation details
- 「ルックアヘッドバイアス防止」の方針として、すべての分析関数は内部で datetime.today() / date.today() を直接参照せず、必ず外部から target_date を受け取る設計になっています。
- OpenAI 呼び出し箇所はテスト容易性のため差し替え（mock/patch）が可能。news_nlp と regime_detector の両方で各モジュール独自の _call_openai_api を持ち、モジュール間で private 関数を共有しない設計にしています。
- DuckDB に対する互換性（executemany の空リスト問題や日付型の扱い）を考慮した実装が各所に反映されています。
- .env 読み込みはプロジェクトルート判定を __file__ を基点に行うため、CWD に依存せずパッケージ配布後も正しく動作するよう配慮されています。

---

貢献・報告
- バグ報告や機能要望は issue を立ててください。README / ドキュメントに追記するべき使用例や注意点があれば、Pull Request を歓迎します。