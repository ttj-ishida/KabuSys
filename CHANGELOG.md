# Changelog

すべての重要な変更点をここに記録します。これは Keep a Changelog のフォーマットに準拠しています。

リリースノートは安定した API やユーザー向けの重要な変更を中心に記載しています。内部実装の詳細や設計方針は各モジュールの docstring を参照してください。

## [0.1.0] - 2026-03-29

### Added
- パッケージ基本情報
  - パッケージ初期バージョンを追加（__version__ = "0.1.0"）。
  - パッケージ公開モジュール群を __all__ で定義（data, strategy, execution, monitoring）。

- 環境変数・設定管理 (kabusys.config)
  - .env ファイルおよび OS 環境変数から設定値を自動読み込みする仕組みを実装。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）によりカレントワーキングディレクトリに依存せず自動ロード。
    - 読込優先度: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応、インラインコメント処理）。
  - 保護された OS 環境変数（override フラグと protected セットによる上書き制御）をサポート。
  - Settings クラスを提供し、アプリケーション設定への型付きアクセスを実現（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH など）。
  - 環境値の検証を実装（KABUSYS_ENV の許容値、LOG_LEVEL の許容値、必須キー未設定時の明示的なエラー）。

- データプラットフォーム関連 (kabusys.data)
  - カレンダー管理モジュールを追加（calendar_management）。
    - market_calendar テーブルを用いた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録あり → DB 値優先、未登録日は曜日ベースのフォールバックを行う一貫した挙動。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等的に更新。バックフィル、健全性チェック（過度の未来日付検出）を実装。
  - ETL / パイプライン基盤を追加（pipeline, etl）。
    - ETLResult データクラスを追加（ETL 実行結果、品質チェック結果、エラー等の集約）。
    - 差分更新・backfill の考慮、品質チェックの収集方針、DuckDB を想定したテーブル存在チェックなどのユーティリティを実装。
  - etl から ETLResult を再エクスポートする短縮インターフェースを追加。

- AI / NLP 機能 (kabusys.ai)
  - ニュース NLP スコアリングモジュールを追加（news_nlp.score_news）。
    - raw_news / news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini, JSON mode）へバッチリクエストして銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - 処理はチャンク単位（デフォルト 20 銘柄/チャンク）、最大記事数・最大文字数でトリムしてトークン肥大化に対処。
    - 429（レート制限）・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ。その他エラーはスキップして継続（フェイルセーフ）。
    - レスポンスのバリデーション（JSON 抽出、results リスト、code/score の検証、スコアのクリップ）を実装。
    - テスト容易性のため _call_openai_api をモック差し替え可能。
    - スコアは ai_scores テーブルへ冪等的に置換（対象コードのみ DELETE → INSERT）して部分失敗時に既存データを保護。
  - 市場レジーム判定モジュールを追加（regime_detector.score_regime）。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュースベースのマクロセンチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定し market_regime テーブルへ保存。
    - prices_daily からの MA 計算、raw_news からマクロキーワードでフィルタしたタイトルを抽出、OpenAI を用いたマクロセンチメント評価、スコア合成、冪等的 DB 書き込みを実装。
    - LLM 呼び出し失敗時は macro_sentiment=0.0 で継続するフェイルセーフ設計。
    - テスト容易性のため _call_openai_api をモック差し替え可能。OpenAI クライアント生成に api_key 注入をサポート。

- リサーチ / ファクターフレームワーク (kabusys.research)
  - ファクター計算モジュールを追加（factor_research）。
    - モメンタム指標（約1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER、ROE）などの算出関数を実装。
    - DuckDB 上の prices_daily / raw_financials を参照し、結果を dict のリストとして返却。
    - データ不足に対する None ハンドリングやログ出力を整備。
  - 特徴量探索モジュールを追加（feature_exploration）。
    - 将来リターン計算（calc_forward_returns: 任意ホライズンの fwd リターンを一括取得、入力検証あり）。
    - IC（Information Coefficient）計算（スピアマンの順位相関ベース）、rank（同順位は平均ランク）実装。
    - factor_summary による基本統計量（count/mean/std/min/max/median）を算出。
  - 研究用ユーティリティ（zscore_normalize は kabusys.data.stats から再エクスポート）を __all__ で公開。

- 汎用的な実装・設計方針
  - すべての「日付基準」処理で datetime.today()/date.today() 等に依存しない設計（ルックアヘッドバイアス防止）。target_date を明示的に受け取る API を採用。
  - DuckDB を主要なデータストアとして想定した SQL / executemany に関する互換性対策（空リストの executemany 回避など）。
  - DB 書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）と例外発生時の ROLLBACK ログ出力で冪等性と堅牢性を確保。
  - OpenAI 呼び出しのリトライや 5xx ハンドリング、JSON モードのレスポンス復元ロジック、スコアのクリップなどフェイルセーフ実装を多数導入。
  - モジュール間の結合を弱める設計（例えば regime_detector は news_nlp の private 関数を直接使わない）。

### Changed
- 新規リリースのため該当なし。

### Fixed
- 新規リリースのため該当なし。

### Security
- OpenAI API キーなどの機密情報は Settings 経由の取得を想定し、.env 自動ロードは環境変数により無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。  
- .env パーサはクォートとエスケープを扱い、意図しないコメント切断による漏洩を低減。

### Notes / For developers
- OpenAI 統合は gpt-4o-mini と JSON Mode を想定しているため、実運用時は API usage とコストに留意してください。
- J-Quants 関連クライアント（jquants_client）は data モジュールから呼び出されますが、外部 API の認証や ID トークン注入の方法は実装依存です。テスト時は ID トークン注入や _call_openai_api のモックを利用してください。
- DuckDB のバージョン互換性（executemany の空引数など）を考慮した実装になっています。環境の DuckDB バージョンによっては動作確認を行ってください。

もしリリースノートに追加してほしい詳細（例えば各関数の入出力例、テーブルスキーマ、互換性注意点など）があれば教えてください。必要に応じて追記・分割して詳述します。