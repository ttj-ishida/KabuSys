# Changelog

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」形式に準拠しています。

フォーマット:
- すべての変更はカテゴリ別（Added / Changed / Fixed / Removed / Security）に記載します。
- バージョンごとにリリース日を付与します。

## [Unreleased]

## [0.1.0] - 2026-03-26
初回リリース。日本株自動売買プラットフォームのコアライブラリを提供します。主な追加点は以下の通りです。

### Added
- パッケージ初期化
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - __all__ に data / strategy / execution / monitoring を公開。

- 環境変数・設定管理（kabusys.config）
  - Settings クラスを導入し、各種設定値（J-Quants, kabu API, Slack, DB パス, 環境名, ログレベル）をプロパティ経由で取得可能に。
  - 必須環境変数未設定時は ValueError を送出する _require を実装。
  - 環境値の検証:
    - KABUSYS_ENV（development / paper_trading / live のみ許容）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許容）
  - .env 自動ロード機能:
    - プロジェクトルート（.git または pyproject.toml を探索）から .env/.env.local を読み込み。
    - OS 環境変数を保護する protected 機構を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）。
  - .env 解析の柔軟性:
    - export KEY=val 形式に対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理（クォート有無に応じた扱い）を実装。

- AI モジュール（kabusys.ai）
  - news_nlp モジュール
    - raw_news / news_symbols テーブルから記事を集約し、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄別センチメント（-1.0〜1.0）を算出。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/リクエスト）、1銘柄あたり記事数/文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - 再試行ロジック（429/ネットワーク/タイムアウト/5xx を指数バックオフでリトライ）。
    - レスポンス検証（JSON 抽出、results 配列、code/score 検証、スコアを ±1.0 にクリップ）。
    - 書き込みは部分置換（対象コードのみ DELETE → INSERT）で部分失敗時に既存データを保護。
    - テスト容易性のため _call_openai_api を patch 可能に。
    - 公開関数: score_news(conn, target_date, api_key=None)

  - regime_detector モジュール
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロセンチメントは raw_news からマクロキーワードでフィルタしたタイトルを OpenAI（gpt-4o-mini）に投げて評価。
    - 失敗時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
    - レジームスコアの計算と閾値（_BULL_THRESHOLD/_BEAR_THRESHOLD）判定、market_regime への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - テスト容易性のため _call_openai_api を patch 可能に。
    - 公開関数: score_regime(conn, target_date, api_key=None)

- データ基盤（kabusys.data）
  - calendar_management
    - JPX カレンダー管理（market_calendar）。はじめと夜間バッチ calendar_update_job を実装。
    - 営業日判定 API:
      - is_trading_day(conn, d)
      - is_sq_day(conn, d)
      - next_trading_day(conn, d)
      - prev_trading_day(conn, d)
      - get_trading_days(conn, start, end)
    - DB に情報がない場合は曜日ベース（土日休み）でフォールバックする設計により堅牢性を確保。
    - 最大探索範囲、バックフィル、健全性チェックなどの保護ロジックを実装。

  - ETL / パイプライン（pipeline, etl）
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - pipeline モジュールは差分取得、保存、品質チェックのワークフローを想定した設計。
    - ETL 実行結果を集約する構造（取得数・保存数・品質問題・エラー一覧、エラー有無判定ヘルパー）を提供。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得、トレード日調整ロジック等を実装。

- リサーチ（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M）、200日MA乖離、20日ATR、流動性（20日平均売買代金、出来高比）などの計算関数を実装。
    - DuckDB の SQL を駆使して効率的に計算。データ不足時は None を返す扱い。
    - 公開関数: calc_momentum, calc_volatility, calc_value
  - feature_exploration
    - 将来リターン計算（複数ホライズン LEAD を用いた一括取得）、IC（Spearman ランク相関）計算、ファクター要約統計量、ランク変換ユーティリティを実装。
    - 外部依存なしで標準ライブラリのみで実装。
    - 公開関数: calc_forward_returns, calc_ic, factor_summary, rank
  - research パッケージはデータ統計ユーティリティ（zscore_normalize）を data.stats から再利用するようエクスポートをまとめた。

### Design / Reliability / Testability
- ルックアヘッドバイアス対策:
  - 各処理（news/regs/research 等）は内部で datetime.today() / date.today() を直接参照せず、target_date を引数に受ける設計。
  - DB クエリでも date < target_date / date = target_date のようにルックアヘッドを防止。

- API 呼び出し周りの堅牢化:
  - OpenAI 呼び出しはリトライ（指数バックオフ）や 5xx と 4xx の扱い分離、最終フェイルセーフ（0.0 やスキップ）を実装。
  - JSON レスポンスのパースや形式検証を厳密に行い、不正レスポンスは無害化して続行。

- DB 操作の冪等性およびトランザクション管理:
  - market_regime / ai_scores 等への書き込みは削除→挿入の方式で部分置換を行い、部分失敗時に既存データを保護。
  - BEGIN / COMMIT / ROLLBACK を組み、ROLLBACK に失敗した場合は警告ログを出力して上位へ伝播。

- テスト支援:
  - OpenAI への実際の API 呼び出しを差し替えられるよう _call_openai_api 関数（各モジュール）を定義し、unittest.mock.patch で置換可能。

### Dependency / Implementation notes
- データストア: DuckDB を利用する前提で SQL を記述。
- OpenAI モデル: gpt-4o-mini を想定して JSON mode を利用。
- 環境変数（主なもの）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - OPENAI_API_KEY（news/regime のデフォルト API キー）
  - KABUSYS_ENV, LOG_LEVEL

### Security
- なし（初版）。API キー等は環境変数管理を前提。

### Breaking Changes
- 初回リリースのため該当なし。

---

今後の予定（参考）
- strategy / execution / monitoring パッケージの具現化（現在は __all__ で公開予定のまま）。
- ai モジュールの追加評価指標やモデル切り替えサポートの拡充。
- ETL のスケジューリング・監視機能の追加。

（以上）