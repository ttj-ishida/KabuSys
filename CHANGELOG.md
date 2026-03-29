# Changelog

全ての重大な変更はこのファイルに記録します。

フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]


## [0.1.0] - 初期リリース (initial release)
リリース日: 2026-03-29

### Added
- パッケージ基盤
  - pakage: `kabusys` の初期公開。__version__ = 0.1.0。
  - モジュールの公開インターフェースを定義（data, strategy, execution, monitoring）。

- 設定 / 環境変数管理 (`kabusys.config`)
  - .env および環境変数から設定値を読み込む自動ロード機能を実装。
    - 読み込み順: OS環境変数 > .env.local > .env
    - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
    - プロジェクトルート検出はこのファイル位置から .git または pyproject.toml を探索（CWD 非依存）。
  - .env パーサ実装の強化:
    - 空行・コメント行の無視、`export KEY=val` 形式のサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - クォートなし値のインラインコメント扱いルール（直前が空白／タブのみ）。
  - 上書き制御（override）と OS 環境変数保護（protected）を実装。
  - Settings クラスを導入し、アプリケーション設定をプロパティ経由で取得可能に。
    - J-Quants、kabuステーション、Slack、DBパス、実行環境（development/paper_trading/live）、ログレベル等のプロパティを提供。
    - 必須環境変数未設定時は明示的に ValueError を投げる。

- データ/ETL (`kabusys.data`)
  - ETL 結果表現用データクラス `ETLResult` を公開（`kabusys.data.etl` 経由で再エクスポート）。
  - ETL パイプラインユーティリティ（`kabusys.data.pipeline`）:
    - 差分取得、バックフィル、品質チェック、idempotent 保存のための補助実装。
    - DuckDB 相互運用性を考慮したユーティリティ関数（テーブル存在確認、最大日付取得）。
  - 市場カレンダー管理（`kabusys.data.calendar_management`）:
    - market_calendar テーブルを利用した営業日判定ロジックを実装。
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB 未取得時は曜日（土日）ベースのフォールバックを使用。
    - 夜間バッチ job `calendar_update_job` を実装（J-Quants API から差分取得、バックフィル、健全性チェック）。

- リサーチ（`kabusys.research`）
  - ファクター計算（`kabusys.research.factor_research`）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER/ROE）等の計算関数を実装。
    - DuckDB 上の SQL/ウィンドウ関数を活用し、データ不足時の挙動（None を返す等）を明確化。
  - 特徴量探索（`kabusys.research.feature_exploration`）
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン対応（デフォルト [1,5,21]）、ホライズン入力検証。
    - IC（Information Coefficient）計算（Spearman）: 欠損/同一値処理、必要レコード数チェック。
    - rank、factor_summary（count/mean/std/min/max/median）などのユーティリティ。
  - いずれも外部ライブラリに依存せず標準ライブラリ + DuckDB のみで実装。

- AI / NLP (`kabusys.ai`)
  - ニュースセンチメントスコアリング（`kabusys.ai.news_nlp`）
    - raw_news & news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いてバッチ評価。
    - チャンク処理（最大 20 銘柄/コール）、記事数・文字数トリム、スコアの ±1.0 クリップ。
    - リトライ（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで実装。失敗時は当該チャンクをスキップして継続（フェイルセーフ）。
    - レスポンスバリデーション（JSON 抽出、results 配列、型チェック、未知コードの無視）。
    - DuckDB へは部分置換（該当 code の DELETE → INSERT）で冪等性を確保。DuckDB executemany の空パラメータ問題を考慮。
    - テスト向けのフック: OpenAI 呼び出しを差し替え可能（内部 _call_openai_api を patch 可）。
    - ニュース収集ウィンドウ計算（calc_news_window）を提供。タイムゾーンの混入を避けるため UTC naive datetime を返す。

  - 市場レジーム判定（`kabusys.ai.regime_detector`）
    - ETF 1321（日経225 連動 ETF）の 200 日 MA 乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム判定（bull/neutral/bear）。
    - マクロニュース抽出（キーワードベース）と OpenAI 呼び出し（gpt-4o-mini, JSON Mode）。
    - API エラー時のフォールバック（macro_sentiment=0.0）、リトライ/バックオフ、JSON パース失敗耐性。
    - 計算結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）し、DB 書き込み失敗時は ROLLBACK と例外伝播を行う。
    - 設計方針としてルックアヘッドバイアス防止（内部で datetime.today()/date.today() を参照しない）を厳守。

### Changed
- 初期リリースのため、主に「追加（Added）」が中心。設計・実装において以下を明確化:
  - 全体的に「ルックアヘッドバイアス防止」の設計原則を徹底（関数は target_date を明示的に受け取り、グローバルな現在時刻参照を避ける）。
  - DuckDB の互換性問題（executemany に空リストを渡せない等）に対応するためのガード実装を追加。

### Fixed
- OpenAI / API 関連での堅牢性改善（初期実装として）
  - 429/ネットワーク断/タイムアウト/5xx に対するリトライとログ出力を実装。
  - JSON レスポンスが前後に余計なテキストを含むケースを想定し、中身の {} を抽出してパースするフォールバックを実装。
  - API エラーの status_code 存在有無を安全に扱うため getattr を使用。

### Security
- 環境変数読み込み周りで OS 環境変数を上書きしない安全なデフォルト（.env は既存の OS 環境変数を上書きしない）。必要に応じて .env.local で上書き可能。

### Notes / 開発者向けメモ
- OpenAI キーは各関数で引数注入可能（api_key）か環境変数 OPENAI_API_KEY を参照する。未設定時は ValueError を送出して明示的に失敗する設計。
- テスト容易性のため、AI モジュール内のネットワーク呼び出しは patch 可能な内部関数を経由している。
- 一部の外部連携（例: jquants_client）やテーブル定義は本差分に含まれないため、実行環境では該当クライアント・テーブル準備が必要。
- 一部ファイル（kabusys.data.etl の続き等）は切り出し途中である可能性があるため、実行前に未実装箇所がないか確認してください。

---

今後の予定 (例)
- strategy / execution / monitoring モジュールの実装完了と統合テスト。
- J-Quants / kabu ステーション接続の実運用検証。
- モデルのプロンプト改善とレスポンス整合性のさらなる堅牢化。