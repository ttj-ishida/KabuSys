Keep a Changelog
すべての重要な変更点をここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

※ 本リリースノートはリポジトリ内のソースコードから推測して作成したものであり、実装意図・設計方針・主要機能を要約しています。

v0.1.0 - 2026-04-02
------------------

Added
- パッケージ基礎
  - パッケージ初期バージョンを追加。 __version__ = "0.1.0" を設定し、公開 API として data / strategy / execution / monitoring をエクスポート。

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml から検出）。
  - .env パーサーはコメント行、export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - 環境変数上書き挙動 (override/protected) をサポートし、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化が可能。
  - Settings クラスを実装し、J-Quants / kabu API / Slack / DB パス / 監視閾値 / 実行環境（development/paper_trading/live）等のプロパティを提供。値検証（KABUSYS_ENV, LOG_LEVEL）を実施。
  - Path 型プロパティ（duckdb_path, sqlite_path, pid_file_path）を返すユーティリティを提供。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - raw_news と news_symbols を集約し、銘柄ごとにニューステキストを結合して OpenAI（gpt-4o-mini）でセンチメントを評価。
    - バッチ処理（最大20銘柄/チャンク）、1銘柄あたりの記事数・文字数制限、JSON Mode 応答のバリデーション、スコアの ±1.0 クリップを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装し、API 失敗時はスキップして継続（フェイルセーフ）。
    - レスポンスの厳密な検証（results 配列・code/score 型チェック）と部分書き換え（対象コードのみ DELETE → INSERT）による冪等性・部分失敗耐性を確保。
    - calc_news_window 関数でニュース収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST の UTC 変換）を算出。

  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily からの ma200_ratio 計算（target_date 未満のデータのみ使用でルックアヘッドを防止）。データ不足時は中立値を採用。
    - raw_news をマクロキーワードでフィルタして LLM でセンチメント評価（gpt-4o-mini、JSON 出力を期待）。API エラー・パース失敗時は macro_sentiment=0.0 として継続。
    - レジームスコア算出後、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実施。
    - API 呼び出しはリトライ・バックオフを実装し、OpenAI の例外（RateLimitError 等）に対応。

- データプラットフォーム (kabusys.data)
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar を用いた営業日判定ロジックとユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データがあれば優先使用、未登録日は曜日（週末）ベースのフォールバックを採用。最大探索日数の制約や健全性チェック、バックフィル（直近再取得）を実装。
    - calendar_update_job を実装し、J-Quants API から差分取得して market_calendar を冪等更新／保存するフローを提供。

  - ETL パイプライン (pipeline, etl)
    - ETLResult dataclass を実装（取得件数・保存件数・品質問題・エラー等を集約）。to_dict によるシリアライズ対応。
    - pipeline モジュールは差分取得、保存（jquants_client の save_* を利用した冪等保存）、品質チェック（quality モジュール）を想定した設計をサポート。
    - デフォルトのバックフィル・カレンダー先読み日数・品質チェックに関する方針を盛り込んだ設計。

- 研究用ユーティリティ (kabusys.research)
  - ファクター計算 (research.factor_research)
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER、ROE）を DuckDB を用いた SQL／Python 組合せで実装。
    - データ不足時の None 返却、ルックアヘッド回避のためのクエリ設計を実施。

  - 特徴量探索 (research.feature_exploration)
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（デフォルト [1,5,21]）のリターンを一度のクエリで取得。
    - IC（Information Coefficient）計算（calc_ic）: コードで結合した上でスピアマンランク相関を算出、サンプル数不足時は None を返却。
    - ランク関数（rank）: 同順位は平均ランクで処理（丸めで ties の安定化）。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を実装。
    - 外部ライブラリ非依存（標準ライブラリ＋DuckDB）で実装。

Changed
- 設計上の注意点（初版実装ポリシーとして明示）
  - すべてのスコア計算・解析関数は内部で datetime.today()/date.today() を直接参照しない（ルックアヘッドバイアス回避）。
  - OpenAI 呼び出しは API キー注入可能にしてテストしやすくし、テスト時には関数差し替えが可能（unittest.mock.patch を想定）。
  - DB 書き込みは冪等性を重視（DELETE→INSERT の置き換え、部分書換による既存データ保護）。

Fixed
- フェイルセーフ・堅牢性
  - OpenAI API 呼び出しに対し 429 / 接続断 / タイムアウト / 5xx を考慮したリトライと指数バックオフを導入。リトライ失敗時は警告ログ出力のうえ、処理継続（値を中立にフォールバック）することで全体処理の停止を防止。
  - DuckDB の executemany における空リスト問題を考慮し、空時は実行をスキップする安全策を導入。

Security
- センシティブ情報（OpenAI API キー・各種トークン・パスワード等）は Settings 経由で環境変数から読み込む設計。自動ロードは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes / Known considerations
- JSON Mode を前提とする OpenAI 応答でも稀に前後に余計なテキストが混在するケースを考慮し、最外の {} を抽出してパースするフォールバック処理を実装。
- ai モジュール内の OpenAI 呼び出しラッパー関数はモジュール間で共有せず、それぞれ独立実装（テストやモジュール結合の観点から）。
- 一部モジュールは外部クライアント（jquants_client）や quality モジュールを利用する設計になっており、これらの実装・設定（API トークン等）は別途必要。

Migration / Upgrade notes
- 初期リリースのためアップグレード手順は特になし。DuckDB スキーマ（prices_daily, raw_news, ai_scores, market_calendar, raw_financials, news_symbols, market_regime など）を事前に準備することを推奨。

Contributing
- バグ報告・機能要望は ISSUE へ。テスト容易性のため、OpenAI 呼び出し周りは API キー注入および patch による差し替えを前提に実装されています。ユニットテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して環境読み込みを制御してください。