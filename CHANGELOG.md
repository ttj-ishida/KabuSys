# Changelog

すべての注目すべき変更はこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。

## [0.1.0] - 2026-03-27

### Added
- 初期リリース: パッケージ kabusys (バージョン 0.1.0) を追加。
  - パッケージ公開インターフェース: kabusys.__all__ で data, strategy, execution, monitoring を公開（モジュール群のエントリポイントを提供）。
- 環境設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動ロードする機能を実装。
  - 自動ロード無効化のための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env のパースは export プレフィックス、シングル／ダブルクォートやバックスラッシュエスケープ、インラインコメントの取り扱いに対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DBパス / 環境種別（development/paper_trading/live） / ログレベル等の取得とバリデーションを実装。
  - 必須環境変数未設定時に ValueError を送出するヘルパー (_require) を実装。
- AI モジュール (kabusys.ai)
  - ニュース NLP (kabusys.ai.news_nlp)
    - raw_news と news_symbols を基に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメントスコアを算出する score_news を実装。
    - 時間ウィンドウの算出（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window として提供。
    - バッチ処理（最大 20 銘柄/リクエスト）、記事数/文字数のトリム、レスポンスの厳密バリデーション、スコア ±1.0 のクリップ、部分成功時の DB 書き換えロジック（DELETE → INSERT）を実装。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフのリトライを実装。テスト容易性のため _call_openai_api を差し替え可能。
  - 市場レジーム検出 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - prices_daily / raw_news を参照し、ma200_ratio、マクロニュース抽出、LLM 評価、レジームスコアの合成、market_regime テーブルへの冪等書き込みを行う。
    - API エラー時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ、リトライ／バックオフ処理を実装。
- Data モジュール (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダーの夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants クライアント経由で差分取得→保存）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定ユーティリティを提供。DB にデータがない場合は曜日ベースでフォールバック。
    - バックフィル・先読み・健全性チェックを備えた実装。
  - ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを公開。ETL 実行のメタ情報（取得件数・保存件数・品質問題・エラー等）を集約。
    - 差分取得 / 保存 / 品質チェックを想定したユーティリティ（テーブル存在チェック、最大日付取得、トレーディング日調整など）を実装。
    - kabusys.data.etl モジュールで ETLResult を再エクスポート。
- Research モジュール (kabusys.research)
  - factor_research: calc_momentum, calc_value, calc_volatility を実装（prices_daily / raw_financials 参照）。モメンタム・バリュー・ボラティリティ関連のファクターを計算。
  - feature_exploration: calc_forward_returns（複数ホライズン対応）, calc_ic（Spearman ランク相関）, factor_summary（基本統計量）, rank（同順位の平均ランク付け）を実装。
  - 研究用ユーティリティや正規化は kabusys.data.stats を参照して利用可能。
- DuckDB を主要なローカル分析 DB として想定し、SQL と Python の組合せで解析処理を実装。

### Changed
- （初回公開のため該当なし）

### Fixed
- （初回公開のため該当なし）

### Security
- OpenAI API キーは引数で注入可能。環境変数 OPENAI_API_KEY も利用可能。未設定時は明示的にエラーを出すことで誤使用を防止。

### Notes / 設計上の重要な点
- ルックアヘッドバイアス対策: 多くのスコアリング関数は内部で datetime.today() / date.today() を参照せず、必ず呼び出し側から target_date を受け取る設計です。
- トランザクションと冪等性: DB 書き込みは明示的に BEGIN/DELETE/INSERT/COMMIT を行い、失敗時には ROLLBACK を試みログを出力します（部分成功時に既存データを破壊しないよう配慮）。
- フォールバック動作: カレンダーデータや価格データが不足する場合は安全なデフォルト（例: ma200_ratio=1.0）や曜日ベースの推定で処理を継続します。
- テスト容易性: OpenAI 呼び出しや時間依存ロジックを差し替え可能／引数注入可能にしてユニットテストを容易にするフックを用意しています。
- 未実装／制限事項:
  - calc_value の PBR・配当利回りは未実装（ドキュメントに明記）。
  - 一部 DuckDB バインド挙動（executemany の空リスト扱い）への互換性対策が施されています。

※ 本リリースは初期実装です。今後、バグ修正・インターフェース改善・追加機能（strategy / execution / monitoring の具体実装等）を行っていきます。