# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

注: この CHANGELOG は、ソースコード（src/kabusys）から推測して作成した初版リリースノートです。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-03-27

初回公開リリース。日本株自動売買プラットフォームのコア機能群を提供します。

### Added
- パッケージ全体
  - pakage: kabusys（バージョン 0.1.0）。
  - モジュール群を提供: data, research, ai, config, etl/pipeline, monitoring 等の基盤モジュールの雛形／実装。

- 環境設定とロード（kabusys.config）
  - .env / .env.local の自動ロード機能を実装（OS 環境変数を優先、.env.local は .env を上書き）。プロジェクトルート検出は .git または pyproject.toml を基準に行うため、CWD に依存しない。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env 行パーサを実装：`export KEY=val`、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
  - 環境変数必須取得ユーティリティ `_require` と Settings クラスを提供。主要設定プロパティ:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（有効値: development, paper_trading, live）
    - LOG_LEVEL（有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - is_live / is_paper / is_dev ヘルパー

- AI ニュース NLP（kabusys.ai.news_nlp）
  - score_news(conn, target_date, api_key=None)
    - 前日 15:00 JST ～ 当日 08:30 JST のニュースウィンドウ計算（UTC naive datetime を返却する calc_news_window を提供）。
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約（記事数・文字数上限あり）。
    - 最大 20 銘柄／チャンクで OpenAI（gpt-4o-mini, JSON Mode）へ送信し、レスポンスをバリデーションして ai_scores テーブルへ冪等的に書き込み（DELETE→INSERT の戦略）。
    - 再試行ロジック（429、ネットワーク断、タイムアウト、5xx を対象に指数バックオフ）を実装。
    - レスポンスの堅牢なパース（JSON mode の微妙な余分テキストに対する復元処理）とスコアの ±1.0 クリップ。
    - API キーは引数で注入可能。未指定時は環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を送出。

- AI 市場レジーム判定（kabusys.ai.regime_detector）
  - score_regime(conn, target_date, api_key=None)
    - ETF 1321 の 200 日移動平均乖離（MA200 比率）とマクロセンチメント（LLM）を合成して日次市場レジーム（bull/neutral/bear）を算出。
    - マクロニュースは news_nlp.calc_news_window で生成されるウィンドウから取得したタイトルを用いる。
    - LLM 呼び出しは独立実装。リトライやフェイルセーフ（API 失敗時は macro_sentiment=0.0）を備える。
    - 最終結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書き込み失敗時は ROLLBACK を試行して例外を伝播。

- データプラットフォーム（kabusys.data）
  - calendar_management
    - market_calendar テーブルを利用した営業日判定ユーティリティを実装: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - DB にカレンダーがない場合は曜日（土日）ベースでフォールバック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を更新（バックフィル・健全性チェックを実装）。
  - pipeline & ETL
    - ETLResult データクラスを公開（取得・保存レコード数、quality issues、errors 等を含む）。
    - 差分更新・バックフィル方針、品質チェックの結果収集方針（Fail-Fast ではなく呼び出し元へ報告）を実装方針として反映。

- リサーチ機能（kabusys.research）
  - factor_research
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、MA200 乖離等を計算。
    - calc_volatility(conn, target_date): 20日 ATR（atr_20）、相対 ATR、平均売買代金、出来高比等を計算。
    - calc_value(conn, target_date): raw_financials から最新財務データを取得して PER、ROE を計算。
    - DuckDB を用いたウィンドウ関数中心の実装。データ不足時は None を返す挙動。
  - feature_exploration
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（デフォルト [1,5,21]）を計算。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を計算、データ不足時は None。
    - rank(values): 同順位は平均ランクで処理（round で丸めて ties 対応）。
    - factor_summary(records, columns): count/mean/std/min/max/median の基本統計量を算出。

- DuckDB を第一級でサポート
  - 多くのモジュールが DuckDB 接続を受け取り、SQL と Python を組み合わせて処理を実行。

### Changed
- （初回リリースのため該当なし）

### Fixed
- .env パーサの堅牢化：クォート内のエスケープ処理やインラインコメント判定、export プレフィックス対応等を実装。
- OpenAI レスポンスパースの回復力向上（JSON 前後の余計なテキストから最外の {} を抽出して復元する処理を追加）。

### Security
- 自動 .env ロード時に既存 OS 環境変数を保護する仕組みを実装（.env の上書きを防ぐ protected set）。
- API キーや機密情報は Settings で必須化されており、未設定時は例外を投げて安全に停止。

### Notes / Important operational details
- OpenAI API を利用する各機能（score_news, score_regime）は OPENAI_API_KEY の提供が必須（関数引数で注入可能）。未設定時は ValueError。
- J-Quants 連携には JQUANTS_REFRESH_TOKEN が必要。
- kabuステーション連携には KABU_API_PASSWORD が必要。
- Slack 通知連携には SLACK_BOT_TOKEN / SLACK_CHANNEL_ID が必要。
- デフォルトの DB パス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
- ログレベル・環境の妥当性チェックを行う（KABUSYS_ENV / LOG_LEVEL の有効値検証）。
- 設計上、各 AI モジュールは「ルックアヘッドバイアス防止」のために date.today()/datetime.today() を直接参照しない実装方針を採用。すべて target_date を外部から与えて処理。

### Breaking Changes
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

---

今後の更新では、監視・実行（execution, monitoring）や J-Quants / kabu API クライアントの具体実装、品質チェックモジュールの詳細、CI テスト向けのモック対応やドキュメント拡充が想定されます。必要であればリリースノートの粒度を細かく分けて追記します。