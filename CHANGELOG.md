# Changelog

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠し、重要な設計判断やフェイルセーフ動作も明記しています。

現在のバージョン: 0.1.0

## [Unreleased]
- （現時点で未リリースの変更はありません）

---

## [0.1.0] - 2026-03-28

### Added
- 基本パッケージ構成
  - パッケージ名: kabusys、バージョン: 0.1.0
  - パッケージ公開モジュール: data, strategy, execution, monitoring

- 環境・設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
  - 自動読み込みの探索はパッケージファイル位置から親ディレクトリを走査して .git または pyproject.toml をプロジェクトルートと特定（CWD 非依存）。
  - .env のパースは以下に対応:
    - 空行・コメント行（#）の無視
    - export KEY=val 形式
    - シングル/ダブルクォートとバックスラッシュエスケープ処理
    - インラインコメントの判定（クォートなしの場合は直前が空白・タブの '#' をコメントとして扱う）
  - 読み込み優先順位: OS環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能
  - 環境変数保護: OS 環境変数キーセットを保護して、override 時の上書きを制御
  - Settings クラスでプロパティ化した設定を提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（DEBUG/INFO/... の検証）
    - is_live / is_paper / is_dev のユーティリティ

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols テーブルを入力に、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む機能（score_news）。
  - ニュース収集ウィンドウ計算（calc_news_window）：前日 15:00 JST 〜 当日 08:30 JST に対応（UTC 変換済み）。
  - 1 銘柄につき最新の記事を最大 _MAX_ARTICLES_PER_STOCK 件・最大文字数でトリムしてプロンプト構築。
  - 最大 _BATCH_SIZE（デフォルト 20）銘柄ずつバッチ送信。
  - OpenAI（gpt-4o-mini）を JSON mode で利用。temperature=0、timeout=30。
  - エラー処理: 429/ネットワーク断/タイムアウト/5xx に対して指数バックオフでリトライ、その他はスキップ。API失敗時は該当チャンクをスキップして処理継続（フェイルセーフ）。
  - レスポンスバリデーション実装:
    - JSON パース（不正な前後テキストが混入する場合に{}ブロック抽出）
    - results キーの存在と型チェック
    - code と score の検証（score は数値かつ有限値、code は要求した銘柄集合に含まれること）
    - スコアは ±1.0 にクリップ
  - DuckDB 書き込みは冪等（DELETE where date/code → INSERT）、executemany の空リスト対策を考慮（DuckDB 0.10 互換性）
  - テスト容易性のため、内部の OpenAI 呼び出し関数をパッチ差し替え可能（unittest.mock.patch を想定）

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225 連動）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定（score_regime）。
  - prices_daily からの ma200_ratio 計算、raw_news からのマクロキーワードフィルタ（多数の日本語／英語キーワード）を用いた記事抽出。
  - OpenAI（gpt-4o-mini）でマクロセンチメントを JSON 出力として取得。API失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）。
  - LLM 呼び出しはリトライ・バックオフ、レスポンスパース失敗は警告ログを出して 0.0 にフォールバック。
  - 最終的な regime_score を閾値で判定し、market_regime テーブルへ冪等的にトランザクションで書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK を試行して例外伝播）。

- 研究用ファクター・特徴量モジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時は None を返す）
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算
    - calc_value: raw_financials から最新財務を取得して PER/ROE を計算
    - 設計方針: DuckDB 上で SQL＋Python による計算、外部 API にアクセスしない。結果は (date, code) をキーとする辞書リストで返す。
  - feature_exploration:
    - calc_forward_returns: 各ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算
    - rank: 平均ランクを返すランク関数（同順位は平均ランク、浮動小数の丸めで ties を扱う）
    - factor_summary: カウント・平均・標準偏差・最小・最大・中央値の統計サマリー
  - 依存を最小化（pandas 等外部ライブラリ未使用）、ルックアヘッドバイアス回避の設計を徹底

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - 市場カレンダー（market_calendar）を用いた is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装
    - market_calendar が存在しない場合は曜日ベース（土日を非営業日）でフォールバック
    - calendar_update_job: J-Quants API から差分取得し市場カレンダーを冪等更新、バックフィルと健全性チェックを実装（lookahead/backfill/sanity checks）
    - 最大探索範囲 _MAX_SEARCH_DAYS を用いて無限ループ防止
  - pipeline:
    - ETLResult データクラスを実装（取得・保存件数、品質チェック結果、エラー一覧などを保持）
    - 差分更新・バックフィル方針、品質チェックの扱い（致命的問題があっても ETL は継続し結果を集約して呼び出し元に委ねる）
    - _table_exists / _get_max_date 等の DB ヘルパー

- その他
  - DuckDB を主要なデータストアとして利用する設計を採用
  - OpenAI SDK（chat completions）を使用（gpt-4o-mini を想定）、API 呼び出しはテスト時に差替え可能な形で実装
  - トランザクション管理とロールバック処理（DB 書き込み失敗時の安全確保）
  - 詳細なログ出力と警告（データ不足、API パース失敗、ROLLBACK 失敗など）

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- 環境変数管理で OS 環境変数を保護する仕組み（protected set）を設け、.env による意図しない上書きを防止。
- OpenAI API キーは引数注入または環境変数 OPENAI_API_KEY のどちらかで指定する必要があり、未設定時は明示的に ValueError を投げる（安全な挙動）。

### Notes / 設計上の重要事項
- すべての AI／研究処理はルックアヘッドバイアスを避けるために datetime.today()/date.today() を直接参照せず、呼び出し元が target_date を指定する方式を採用。
- API 呼び出し失敗時は「フェイルセーフ」戦略を採用（スコアやセンチメントを 0.0 にフォールバック、処理は継続）。
- DuckDB のバージョン依存（executemany の空リスト制約など）を考慮した実装を行っているため、運用環境の DuckDB バージョンに留意してください。
- テスト容易性のため、OpenAI 呼び出しポイントはパッチ可能に実装しています（ユニットテストでモック化して API をエミュレート可能）。

---

（今後のリリースでは、実際の変更点にあわせて「Changed」「Fixed」「Deprecated」「Removed」などを積極的に追記してください。）