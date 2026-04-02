# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
このプロジェクトはセマンティックバージョニングを採用します。  

## [Unreleased]

- ドキュメント・テスト・CI 等のメンテナンス項目は今後追加予定。

## [0.1.0] - 2026-04-02

初回公開リリース。日本株自動売買システムのコアライブラリを提供します。主な追加点は以下の通りです。

### Added
- パッケージ初期化
  - kabusys パッケージの公開 API を定義（data, strategy, execution, monitoring）。
  - パッケージバージョン __version__ = "0.1.0" を設定。

- 設定 / 環境管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。プロジェクトルートの検出は .git または pyproject.toml を基準に行い、CWD に依存しない動作を実現。
  - .env/.env.local の読み込み順序（OS 環境変数 > .env.local > .env）。.env.local は上書き（override）される。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化フラグをサポート（テスト向け）。
  - export KEY=val 形式やシングル/ダブルクォート、バックスラッシュエスケープ、行末コメントの取り扱いなどを考慮した .env パーサ実装。
  - 必須設定取得ヘルパー（_require）と Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境種別・ログレベル等）。
  - 環境値のバリデーション（KABUSYS_ENV / LOG_LEVEL の許容値チェック）。

- AI ニュース解析（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ保存する機能を実装。
  - ニュース収集ウィンドウの定義（JST 基準）：前日 15:00 JST 〜 当日 08:30 JST を UTC に変換して検索（calc_news_window）。
  - バッチ処理（最大 20 銘柄 / チャンク）と、1 銘柄あたりの最大記事数（10 件）・最大文字数（3000 文字）でトリムするロジックを導入。
  - OpenAI 呼び出しに対するエクスポネンシャルバックオフとリトライ（429・ネットワーク断・タイムアウト・5xx を想定）。
  - レスポンスの厳密なバリデーション（JSON 抽出、"results" リスト、コード照合、数値チェック、±1.0 クリップ）。
  - 部分成功時に既存スコアを保護するため、取得できたコードのみ DELETE → INSERT により置換する冪等書き込み。
  - テスト容易性のため _call_openai_api を差し替え可能に設計（unittest.mock.patch を想定）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（LLM、重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定する機能を実装。
  - MA200 比率計算（ターゲット日未満のデータのみ使用し、ルックアヘッドを防止）。
  - マクロキーワードによる raw_news のフィルタリング（複数キーワードリストを定義）。
  - OpenAI（gpt-4o-mini）呼び出しのリトライ戦略とフェイルセーフ（API 失敗時は macro_sentiment = 0.0）。
  - スコア合成・閾値判定（BULL_THRESHOLD / BEAR_THRESHOLD）と market_regime テーブルへの冪等的な書き込み（BEGIN / DELETE / INSERT / COMMIT）。
  - テスト容易性のため API キーの注入をサポート（引数 or 環境変数 OPENAI_API_KEY）。

- 研究・因子計算（kabusys.research）
  - factor_research: モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER、ROE）計算を実装。DuckDB の SQL を活用し、prices_daily / raw_financials のみ参照。
  - feature_exploration: 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman の ρ）計算、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を実装。
  - 外部ライブラリに依存せず、標準ライブラリと DuckDB で完結する実装。

- データプラットフォーム（kabusys.data）
  - calendar_management: JPX カレンダー管理（market_calendar の読み書き、is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の判定ユーティリティ）。DB にデータがない場合は曜日ベースのフォールバックを使用。
  - calendar_update_job: J-Quants API からの差分取得および保存、バックフィル日数や健全性チェックの実装。
  - pipeline: ETLResult データクラスを実装し、ETL パイプラインの入出力情報（取得件数・保存件数・品質問題・エラー等）を集約。
  - ETL 実装方針: 差分更新、バックフィル、品質チェックの設計を反映（jquants_client, quality モジュールと連携想定）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （新規実装のため該当なし）

### Security
- OpenAI API キー等の機密情報は環境変数から取得する設計。誤って .env を公開しないよう注意。

---

注記（設計上の重要ポイント）
- ルックアヘッドバイアスの防止: date.today() / datetime.today() に依存せず、target_date を明示的に与える設計。DB クエリでも「date < target_date」や半開区間を使う等の注意が払われています。
- フェイルセーフ: 外部 API 失敗時はプロセス全体を止めずに安全側のデフォルト（例: macro_sentiment=0.0、スコア未取得はスキップ）で継続する方針を採用。
- テスト容易性: OpenAI 呼び出しポイントを差し替え可能にしてユニットテストを行いやすくしています。
- DuckDB 互換性: executemany に空リストを与えないガードや、日付型の取り扱いユーティリティなど互換性考慮が見られます。

もし特定の変更点（リリース日や追加してほしいカテゴリ）を反映したい場合はお知らせください。