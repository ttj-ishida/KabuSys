# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記述しています。  
日付はリリース日です。

## [0.1.0] - 2026-04-03

初回公開リリース。日本株自動売買パイプラインのコアライブラリを実装しました。主に以下のサブパッケージ／機能を提供します。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0）。公開サブモジュール: data, research, ai, execution, monitoring, strategy（__all__ に一部記載）。
- 設定・環境変数管理 (`kabusys.config`)
  - .env ファイル自動ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml を探索）。
  - .env/.env.local の読み込み順と上書きルールを実装（OS 環境変数は保護）。自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ: export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理をサポート。
  - Settings クラスを追加。主なプロパティ:
    - jquants_refresh_token（必須）
    - kabu_api_password（必須）
    - kabu_api_base_url（デフォルト: http://localhost:18080/kabusapi）
    - line_channel_access_token, line_user_id
    - duckdb_path（デフォルト: data/kabusys.duckdb）
    - sqlite_path（デフォルト: data/monitoring.db）
    - pid_file_path / kill_flag_path / kill_flag_clear_on_start
    - cpu/memory/disk 閾値
    - env（KABUSYS_ENV、有効値: development, paper_trading, live）
    - log_level（LOG_LEVEL、有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - is_live / is_paper / is_dev 判定ユーティリティ
  - 未設定の必須環境変数は _require() により ValueError を送出。
- データプラットフォーム（DuckDB ベース）
  - calendar_management モジュール:
    - JPX カレンダー管理、market_calendar テーブルを用いた営業日判定 API:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - calendar_update_job: J-Quants API から差分取得して冪等的に保存（バックフィル・健全性チェックあり）。
    - DB にカレンダーがない場合は曜日（土日）ベースでフォールバック。
  - pipeline / etl:
    - ETLResult データクラスを実装（取得件数、保存件数、品質チェック、エラー一覧等を格納）。
    - ETL 実行のための基盤ロジック（差分取得、バックフィル、品質チェックの設計方針を反映）。
  - jquants_client との連携を想定（fetch/save 系関数の呼び出しポイントを実装）。
- AI（OpenAI 経由の NLP）
  - news_nlp モジュール:
    - score_news(conn, target_date, api_key=None):
      - 前日 15:00 JST 〜 当日 08:30 JST（JST基準。内部では UTC naive datetime で DB 比較）を対象に raw_news と news_symbols を参照し、銘柄ごとにニュースを集約して OpenAI (gpt-4o-mini) にバッチ送信してセンチメントを算出。
      - バッチサイズ、記事/文字数トリム、JSON mode を使用した応答検証、クリップ（±1.0）、429/ネットワーク/タイムアウト/5xx への指数バックオフリトライ、部分成功時に対象コード分のみ DELETE→INSERT で置換（冪等性・部分失敗耐性）などを実装。
      - API キーは引数で注入可能。未設定時は環境変数 OPENAI_API_KEY を参照し、未設定なら ValueError。
      - テスト時に _call_openai_api をモック可能。
      - スコアが得られなかった場合は 0 を返し、ログで可視化。
    - calc_news_window(target_date) を公開（news の集計ウィンドウ取得）。
  - regime_detector モジュール:
    - score_regime(conn, target_date, api_key=None):
      - ETF 1321（日経225連動ETF）の直近 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を算出。
      - MA 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを排除。
      - マクロニュースは news_nlp.calc_news_window と raw_news から抽出。記事がない場合は LLM を呼ばず macro_sentiment=0.0 を使用。
      - OpenAI 呼び出しはリトライ/フェイルセーフを備え、API エラー時は macro_sentiment=0.0 で継続。
      - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試行して例外を伝播。
- リサーチ（オフライン分析）
  - research パッケージ初期化と以下の実装:
    - factor_research:
      - calc_momentum(conn, target_date): 1M/3M/6M リターン、MA200乖離（MA200未満のデータは None）。
      - calc_volatility(conn, target_date): 20日 ATR, ATR/price, 20日平均売買代金, 出来高比率。
      - calc_value(conn, target_date): raw_financials から最新財務を取得し PER, ROE を計算（EPS が 0/欠損のときは None）。
      - すべて prices_daily / raw_financials のみ参照。実運用発注等は行わない。
    - feature_exploration:
      - calc_forward_returns(conn, target_date, horizons=None): デフォルト [1,5,21]。LEAD を用いた将来終値取得。
      - calc_ic(factor_records, forward_records, factor_col, return_col): Spearman（ランク）に基づく IC 計算。
      - rank(), factor_summary(): ランク付け、統計サマリーユーティリティ（依存は標準ライブラリのみ）。
- ロギング・デバッグ情報
  - 各モジュールで詳細な info/debug/warning ログを追加。多くのフェイルセーフ時は WARNING を出して処理を継続する設計。

### 変更点・設計上の注意 (Changed / Notes)
- ルックアヘッドバイアス回避:
  - 全ての AI スコアリング／レジーム判定／ファクター計算で date.today() を直接参照しない設計。必ず target_date を受け取る API を提供。
  - DB クエリは target_date 未満（排他）や date = ? など、未来データを参照しないよう注意。
- API 呼び出しはフェイルセーフ:
  - OpenAI 呼び出しや外部 API 呼び出しで失敗した場合でもシステム全体が停止しないよう、デフォルト値（0.0）やスキップ動作で継続する実装。
- 冪等性・部分失敗耐性:
  - ai_scores, market_regime, market_calendar 等の DB 書き込みは既存行の置換（DELETE→INSERT など）により冪等性を確保。部分失敗時に他コードの既存データを不用意に消さない設計。
- DuckDB 依存:
  - 内部クエリは DuckDB を想定しており、SQL のウィンドウ関数や executemany の挙動（空リスト不可等）に配慮した実装。
- タイムゾーン:
  - news ウィンドウは JST を基準に計算後、UTC naive datetime を DB 比較に使用（raw_news.datetime は UTC 前提）。
- テスト容易性:
  - OpenAI 呼び出し箇所は内部ヘルパー関数を通しており、unittest.mock.patch による差し替えが可能。
- 設定値の既定値・検証:
  - KABUSYS_ENV / LOG_LEVEL は許容値を検証し、不正値で ValueError を送出。

### 既知の制約・注意事項 (Known issues / Limitations)
- OpenAI API キー必須:
  - score_news / score_regime は OPENAI_API_KEY が必要（引数で上書き可）。未設定で呼ぶと ValueError。
- データテーブル前提:
  - 各機能は特定の DuckDB テーブル（例: prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）が存在することを前提に動作します。適切なスキーマとデータ投入が必要です。
- .env パースの互換性:
  - 一般的な .env 形式に対応していますが、非常に特殊なフォーマットや複雑なシェル展開はサポートしていません。
- executemany の空リスト取り扱い:
  - DuckDB 0.10 などでは executemany に空リストを渡せない制約に対処済み（空チェックを実施）。

### セキュリティ (Security)
- トークン・パスワード:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY 等は機密情報です。.env をバージョン管理に含めないよう注意してください。
- 自動ロード無効化:
  - テストや CI 環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを抑止できます。

---

このリリースはコア機能の実装を目的としており、以降のバージョンで以下を想定しています:
- モジュール単位のユニットテストと統合テストの追加
- execution / monitoring / strategy の実装拡張（発注ロジック・監視アラート等）
- jquants_client の実装例・ドキュメント強化
- パフォーマンス改善と追加の健全性チェック

必要であれば、本 CHANGELOG をもとにさらに詳細なリリースノート（環境変数一覧・DB スキーマ要件・使用例コードスニペット等）を作成します。希望があれば指示してください。