# Changelog

すべての注目すべき変更履歴を記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-03-27

### Added
- 基本パッケージ初期リリースを追加
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）

- 環境設定・.env ローダー（kabusys.config）
  - プロジェクトルートを .git または pyproject.toml から自動検出して .env/.env.local を読み込む自動ロード機能を実装
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
  - .env パーサーは export KEY=val、シングル/ダブルクオート、バックスラッシュエスケープ、インラインコメントルールを考慮
  - 既存 OS 環境変数を保護する protected オプションを実装
  - 必須環境変数取得用 helpers（_require）と Settings クラスを公開
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等のプロパティを提供
    - DUCKDB_PATH / SQLITE_PATH のデフォルトパス設定
    - KABUSYS_ENV の値検証（development / paper_trading / live）
    - LOG_LEVEL の値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev ヘルパーを提供

- AI: ニュース NLP スコアリング（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集約して銘柄ごとの記事を作成し、OpenAI（gpt-4o-mini）でセンチメントを取得
  - バッチ処理（デフォルト1回あたり最大20銘柄）および各銘柄毎のトリミング（最大記事数/文字数）を実装
  - JSON Mode を使ったレスポンス検証とパース復元（前後余計テキストが混入した場合に {} を抽出）
  - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ（デフォルト最大試行数設定）
  - スコアは ±1.0 にクリップ。失敗時はスキップして継続（フェイルセーフ）
  - DuckDB への書き込みは部分失敗時に既存スコアを守るため、取得済みコードのみ DELETE → INSERT の置換を実施
  - calc_news_window(target_date) によるニュースウィンドウ計算（JST を基準に UTC 換算）
  - score_news(conn, target_date, api_key=None) を公開（api_key は引数または OPENAI_API_KEY 環境変数）

- AI: 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で市場レジームを判定（bull/neutral/bear）
  - ma200_ratio 計算（target_date 未満のデータのみ使用、ルックアヘッド防止）
  - マクロニュースはマクロキーワードでフィルタ（最大 20 記事）
  - OpenAI 呼び出しは専用関数で行い、リトライ・エラー時は macro_sentiment=0.0 でフォールバック
  - レジームスコア合成と閾値判定、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装
  - score_regime(conn, target_date, api_key=None) を公開

- Data: データ ETL / パイプライン関連（kabusys.data.pipeline / kabusys.data.etl）
  - ETLResult データクラスを導入（取得件数、保存件数、品質チェック結果、エラー概要などを保持）
  - 差分更新、バックフィル、品質チェックの設計方針とユーティリティを実装（モジュール内部）
  - DuckDB 存在チェック・最大日付取得ユーティリティを提供

- Data: マーケットカレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装
  - market_calendar がない・未登録日の場合は曜日ベースのフォールバック（週末を非営業日扱い）
  - calendar_update_job により J-Quants API から差分取得して market_calendar を冪等保存（バックフィル・健全性チェックを含む）
  - 最大探索日数や先読み日数等の安全策を実装

- Research: ファクター計算・特徴量探索（kabusys.research）
  - factor_research: calc_momentum, calc_volatility, calc_value を実装
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離
    - Volatility / Liquidity: 20 日 ATR、相対 ATR、平均売買代金、出来高比率
    - Value: PER、ROE（raw_financials を参照）
    - DuckDB を使った SQL ベース実装。データ不足時の None 処理
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank を実装
    - 将来リターン計算は複数ホライズン対応、horizons の検証
    - IC（Spearman のρ）計算、統計サマリー算出
  - research パッケージで必要な関数を公開、データ統計ユーティリティ（zscore_normalize）は kabusys.data.stats から再エクスポート

### Changed
- 初回リリースのため変更履歴なし

### Fixed
- 初回リリースのため修正履歴なし

### Notes / 設計上の重要点（ドキュメント的記載）
- ルックアヘッドバイアス対策: 各モジュールは内部で datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取る設計。
- フェイルセーフ方針: 外部 API（OpenAI / J-Quants 等）呼び出しでのエラーは基本的にロギングしてフォールバック動作（例: 中立スコアやスキップ）とし、ETL や AI スコア処理全体が中断しないようにしている。
- DuckDB に関する互換性・安全策:
  - executemany に空リストを渡さないガード（DuckDB 0.10 互換問題回避）
  - テーブル存在チェックや日付変換ユーティリティを提供
- OpenAI 呼び出しはテスト容易性を考慮して _call_openai_api を内部で定義しており、unittest.mock.patch による差し替えが可能

---

開発中の機能や既知の制約、互換性については各モジュールの docstring に詳細を記載しています。バージョン 0.1.0 は「最小限のデータプラットフォーム + 研究用ファクター計算 + AI ベースのニュース分析とレジーム判定」を提供する初期実装です。今後のリリースで監視・実行（execution / monitoring）などのランタイム部分、テストカバレッジ拡充、外部 API クライアントの実装（jquants_client 等）の安定化を予定しています。