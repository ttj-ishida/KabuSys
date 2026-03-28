# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
現在のバージョンはパッケージメタ情報 (src/kabusys/__init__.py) に基づき 0.1.0 です。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-28
初期リリース。以下の主要機能・モジュールを追加しました。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を設定。
  - パッケージ公開 API を __all__ で整理（data, strategy, execution, monitoring を想定してエクスポート）。

- 環境設定 / 初期化
  - robust な .env ローダーを実装（src/kabusys/config.py）。
    - プロジェクトルート検出（.git または pyproject.toml を探索）により CWD 非依存で .env を自動読み込み。
    - export 形式やクォート／コメント処理に対応するパーサー実装。
    - 自動読み込み無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD のサポート。
    - 必須環境変数取得ヘルパー _require と Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）。
    - env 値検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）と便利プロパティ（is_live / is_paper / is_dev）。

- データプラットフォーム関連（DuckDB ベース）
  - calendar_management モジュール（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 未取得時の曜日ベースのフォールバック、最大探索日数や健全性チェックを実装。
    - 夜間バッチ calendar_update_job を実装（J-Quants API から差分取得→冪等保存）。
  - ETL パイプライン基盤（src/kabusys/data/pipeline.py）
    - ETLResult データクラスを公開（ETL 実行結果、品質問題・エラーの集約）。
    - 差分取得、バックフィル、品質チェックの方針に沿ったユーティリティ関数群（テーブル存在確認・最大日付取得など）。
  - etl モジュールの公開インターフェース（src/kabusys/data/etl.py）で ETLResult を再エクスポート。

- J-Quants / ニュース NLP / OpenAI 連携（AI モジュール）
  - ニュースセンチメント集計（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols テーブルから銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信してセンチメント（-1.0〜1.0）を算出。
    - チャンク処理（1 API 呼び出しで最大 20 銘柄）、1 銘柄あたりの記事最大数・文字数トリム、JSON レスポンスのバリデーションを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ処理。
    - スコアの ±1.0 クリッピング、部分成功時は既存スコアを保護するため対象コードのみ DELETE→INSERT の冪等書き込み。
    - テスト容易性のため API 呼び出しラッパーを分離し mock で差し替え可能。
    - 公開関数: score_news(conn, target_date, api_key=None) — 書き込み銘柄数を返す。
    - calc_news_window(target_date) による JST ベースのニュース集計ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）200 日移動平均乖離（重み 70%）とニュースベースのマクロセンチメント（重み 30%）を合成して日次でレジーム判定（bull / neutral / bear）。
    - OpenAI 呼び出しは gpt-4o-mini を用い JSON 出力を期待、API エラー時はフェイルセーフとして macro_sentiment=0.0 を採用。
    - レジームスコアの合成と market_regime テーブルへの冪等書き込みを実装。
    - 公開関数: score_regime(conn, target_date, api_key=None) — 成功時に 1 を返す。
    - ルックアヘッドバイアス対策（target_date 未満のみのデータ使用、date.today() を参照しない設計）。

- リサーチ / ファクター計算
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20日 ATR、相対 ATR）、Value（PER、ROE）などの計算関数を実装。
    - DuckDB 上の SQL とウィンドウ関数を併用して効率的に計算。
    - 公開関数: calc_momentum, calc_volatility, calc_value（それぞれ target_date を受け取る）。
  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - horizons のバリデーション、ランクに対する同順位処理（平均ランク）、Spearman 相当の計算を提供。
  - research パッケージの __init__ で主要関数を再エクスポート。

### Changed
- 初版のため過去変更なし。

### Deprecated
- なし

### Removed
- なし

### Fixed
- 初版のため過去修正なし。

### Security
- OpenAI API キーの取り扱いは api_key 引数経由または環境変数 OPENAI_API_KEY を使用。環境変数未設定時は明示的に例外を発生させる設計（誤った silent failure を避ける）。

---

注意事項 / 設計上のポイント（実装に明示されている重要点）
- ルックアヘッドバイアス対策が各 AI / 研究モジュールで徹底されている（target_date 未満のみ参照、datetime.today() を用いない）。
- DuckDB をデータストアとして利用し、クエリは SQL ウィンドウ関数で実装。部分書き換え（DELETE→INSERT）で冪等性を確保。
- OpenAI 呼び出しは JSON Mode を前提とし、レスポンスパースに対する耐性（余分なテキストの切り出し等）を持つ。
- テスト容易性を考慮して API 呼び出しのラッパー（_call_openai_api 等）をモジュール内で分離しているためモッキング可能。
- .env パーサーは export 表記やクォート内のエスケープ、インラインコメント等に対応し現実の .env 運用を想定。

（将来追記）
- 今後のリリースでは strategy / execution / monitoring 周りの自動売買ロジック・実行基盤・監視機能の実装や、J-Quants / kabu ステーションとの統合強化、テストカバレッジの追加などが想定されます。