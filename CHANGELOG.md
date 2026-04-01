# Changelog

すべての変更は Keep a Changelog の規約に準拠しています。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]
（今後の変更履歴をここに記載）

---

## [0.1.0] - 初回リリース
初回の公開リリース。日本株自動売買プラットフォームの基盤的なモジュール群を実装しました。主にデータ取得/整備、リサーチ用ファクター計算、ニュース/NLP を用いた AI スコアリング、および環境設定ユーティリティを含みます。

### Added
- パッケージ基本情報
  - kabusys パッケージを追加。バージョンは 0.1.0。

- 環境設定 / ロード機能（kabusys.config）
  - .env/.env.local ファイル自動読み込み（プロジェクトルートの検出は .git または pyproject.toml を基準）。
  - 自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサーの強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - インラインコメントの取り扱い改善（クォート外での '#' をコメントと認識する条件を調整）。
  - .env 読み込み時に OS 環境変数を保護（既存キーは protected として扱い、.env.local の override 振る舞いを制御）。
  - Settings クラスを追加し、主要な設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID などの必須チェック。
    - KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、PID_FILE_PATH 等のデフォルト値。
    - CPU/MEMORY/DISK の閾値取得、環境（development/paper_trading/live）とログレベルのバリデーション（ホワイトリスト）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- ニュース NLP と AI スコアリング（kabusys.ai.news_nlp）
  - raw_news / news_symbols を元に銘柄ごとのニュース集約を行い、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込み。
  - ニュース対象ウィンドウの計算（前日 15:00 JST ～ 当日 08:30 JST 相当の UTC 範囲）を calc_news_window として提供。
  - バッチ処理（最大 20 銘柄/chunk）と、1 銘柄あたりの最大記事数・最大文字数でトリムする仕組みを実装（_BATCH_SIZE、_MAX_ARTICLES_PER_STOCK、_MAX_CHARS_PER_STOCK）。
  - OpenAI 呼び出しのリトライ（429・ネットワーク断・タイムアウト・5xx）と指数バックオフを実装。
  - レスポンスの厳密なバリデーションとスコアの ±1.0 でのクリップ。
  - 部分失敗に備え、書き込みは対象コードのみ DELETE→INSERT する冪等性の高い処理。
  - テスト容易性のため _call_openai_api を差し替え可能（unittest.mock.patch を想定）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、market_regime テーブルへ書き込み。
  - MA 計算は target_date 未満のデータのみ参照し、ルックアヘッドバイアスを防止。
  - API 呼び出し用のリトライ・エラーハンドリングを実装。LLM エラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
  - 結果は -1.0 ～ 1.0 にクリップし閾値で bull/neutral/bear を判定。
  - DB への書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等操作。失敗時は ROLLBACK を試行し例外を上位へ伝播。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research モジュールを実装し、以下のファクターを提供:
    - Momentum: mom_1m / mom_3m / mom_6m、ma200_dev（200 日 MA 乖離）。
    - Volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率。
    - Value: PER（株価 / EPS）、ROE（raw_financials を参照）。EPS が 0 または欠損の場合は None を返す。
  - 計算は DuckDB の SQL ウィンドウ関数を用い、データ不足時は None・ログ出力を行う。
  - research パッケージとして zscore_normalize（data.stats 由来）や feature_exploration のユーティリティを公開。
  - feature_exploration では:
    - 将来リターン計算（calc_forward_returns、horizons のバリデーションあり）。
    - IC（Information Coefficient）計算（スピアマンの順位相関）と rank ユーティリティ。
    - factor_summary による基本統計量（count/mean/std/min/max/median）計算。

- データプラットフォーム（kabusys.data）
  - calendar_management: market_calendar ベースでの営業日判定ロジックを実装:
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days。
    - market_calendar データがない場合は曜日ベースのフォールバック（週末は非営業日）。
    - calendar_update_job により J-Quants API からの差分取得と保存（バックフィル・健全性チェック含む）。
  - pipeline / etl:
    - ETLResult データクラスを実装（取得件数、保存件数、品質問題、エラー一覧を保持）。
    - pipeline モジュールの ETLResult を再エクスポートするインターフェース。
    - ETL の設計方針注記（差分更新、バックフィル、品質チェックの扱い、id_token 注入可など）。

- DuckDB と OpenAI SDK を用いる設計
  - データストアには DuckDB を想定し SQL を多用した実装。
  - OpenAI（gpt-4o-mini）を JSON モードで利用するための呼び出しとパース処理を組み込む。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- .env の読み込みで OS 環境変数を保護する機構を導入（.env による意図しない上書きを防止）。
- 必須トークン（OpenAI / J-Quants / Slack / kabu API）の未設定時に明確な ValueError を出すことで、安全に運用者へ設定不足を通知。

### Notes / Migration
- OpenAI API キーは api_key 引数に渡すか環境変数 OPENAI_API_KEY を設定する必要があります。未設定だと ValueError を送出します。
- DuckDB の executemany は空リストを受け付けない制約を考慮した実装（空の場合は実行をスキップ）を行っています。
- 一部の処理（ニュースウィンドウ、MA 計算など）はルックアヘッドバイアスを避けるため date.today()／datetime.today() を参照しない設計です。ETL やバッチ実行時は必ず target_date を明示してください。

---

作者: kabusys 開発チーム  
（実装内容はソースコードから推測して記載しています。実際の利用時は README / ドキュメントと併せて確認してください。）