# Changelog

すべての重要な変更を Keep a Changelog の形式で記録します。  
このファイルはリリースノートの要約であり、コード内の設計方針や主要な挙動も補足しています。

フォーマット:
- 変更はセクション（Added, Changed, Fixed, etc.）に分類しています。
- 日付はリリース日です。

## [Unreleased]
（現時点では未リリースの作業はありません）

## [0.1.0] - 2026-03-31
初期リリース。日本株自動売買システムの基盤となるモジュール群を導入しました。  
設計方針として、DuckDB をデータ基盤に利用し、外部 API 呼び出しは最小化・堅牢化（リトライ、フォールバック、フェイルセーフ）しています。LU（look-ahead）バイアス防止のため、日付取得に datetime.today()/date.today() の直接参照を避ける実装方針を各モジュールに適用しています。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。パッケージ公開時に data, strategy, execution, monitoring を __all__ に含む構成。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルと環境変数からの設定読み込み機能を実装。プロジェクトルート（.git または pyproject.toml）を基準に自動で .env/.env.local を読み込む。
  - 自動ロードの無効化オプション: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサは export 形式、シングル/ダブルクォート、エスケープ、インラインコメントなど多様なケースに対応。
  - Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY 等の必須項目取得メソッド、デフォルトパスや閾値の取得、環境値バリデーションを含む）。
  - 環境値検証: KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）の検証。

- AI モジュール (kabusys.ai)
  - news_nlp モジュール
    - raw_news と news_symbols をもとにニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini, JSON mode）で銘柄別センチメント（-1.0〜1.0）を取得。
    - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄あたりの記事数・文字数制限、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、レスポンス検証ロジックを実装。
    - レスポンス検証は JSON 抽出、results キー・型チェック・未知コード無視・数値検証を含み、不正レスポンスはスキップ（フェイルセーフ）。
    - ai_scores テーブルへの冪等書き込み（DELETE → INSERT）を実装。部分失敗時に既存スコアを保護する設計。
    - ニュース加工の時間ウィンドウ（JST 前日15:00 ～ 当日08:30、内部は UTC naive で扱う）を calc_news_window で計算。
  - regime_detector モジュール
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み70%）と、ニュースベースのマクロセンチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - OpenAI の呼び出しは専用関数経由で行い、APIの失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - レジーム判定結果を market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試行して例外を伝播。
    - ルックアヘッドバイアス回避のため、prices_daily クエリは target_date 未満のデータのみを使用。

- データ基盤モジュール (kabusys.data)
  - calendar_management
    - JPX カレンダー管理機能（market_calendar）と、営業日判定ユーティリティ群を提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB にカレンダーがない場合は曜日（土日）ベースのフォールバックを使用。DB に一部データがある場合は DB 値優先・未登録日は曜日フォールバックで一貫性を保持。
    - 夜間バッチ calendar_update_job を実装（J-Quants API から差分取得し冪等保存）。バックフィル、健全性チェックを実装。
  - pipeline / etl / ETLResult
    - ETLResult dataclass を公開（ETL の取得/保存数、品質チェック結果、エラー情報を保持）。
    - ETL パイプライン設計を実装（差分更新、idempotent 保存、品質チェックフック、backfill の導入、テスト容易性のため id_token 注入可能）。

- 研究系モジュール (kabusys.research)
  - factor_research
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、ATR ベースのボラティリティ、流動性（20日平均売買代金・出来高比）やバリュー（PER, ROE）等のファクター計算を実装。
    - DuckDB ベースの SQL と Python を組み合わせた高速処理。データ不足時は None を返す設計。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns：任意ホライズン、デフォルト [1,5,21]）、IC（calc_ic：Spearman）、rank・factor_summary（基礎統計量算出）を実装。
    - pandas 等に依存せず、標準ライブラリのみで実装。

- その他ユーティリティ
  - data/etl で ETLResult を再エクスポート。
  - すべての日付は date オブジェクトで扱い、タイムゾーン混入を避ける設計。
  - DuckDB を前提とした SQL 実行時の互換性配慮（executemany の空リスト回避等）。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Security
- OpenAI API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を発生させることで誤使用を抑止。

### Notes / 実装上の重要点（ユーザー向け）
- 環境変数必須項目（例）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings から取得可能で、未設定時は ValueError。
- デフォルトファイルパス
  - DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH で上書き可）
  - SQLite（監視用）: data/monitoring.db（SQLITE_PATH）
  - PID ファイル: data/execution.pid（PID_FILE_PATH）
- 自動 .env ロードの挙動
  - プロジェクトルート検出（.git または pyproject.toml が起点）に成功した場合、.env を先にロード（既存 OS 環境優先）、.env.local を上書きロード。OS 環境（既存のキー）は保護される。
- OpenAI 呼び出し
  - gpt-4o-mini を想定（JSON mode）。レスポンスは厳密な JSON を期待するが、現実的なノイズ（前後テキスト等）に対して復元ロジックを入れている。
  - 主要 API エラーには指数バックオフリトライを実装し、5xx とネットワーク系は再試行、非再試行系はスキップして処理継続（フェイルセーフ設計）。
- ルックアヘッドバイアス対策
  - score_news / score_regime / factor計算等、すべて target_date を明示的に受け取り、内部で date.today() を参照しない設計になっています。過去データのみ参照することでモデル評価のバイアスを低減します。

---

今後の予定（TODO）
- strategy / execution / monitoring の具体実装（現行の __all__ には宣言済み）
- テストカバレッジ拡充（特に OpenAI 呼び出しのモック検証、DuckDB クエリの整合性）
- Docs（StrategyModel.md, DataPlatform.md に基づくユーザ向けドキュメント整備）

---

発行: kabusys チーム（生成日: 2026-03-31）