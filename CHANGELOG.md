# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

現在のバージョン: 0.1.0

## [Unreleased]
- ドキュメント・テスト・インフラ等の追加予定事項をここに記載してください。

## [0.1.0] - 2026-03-27
初回公開リリース。以下の主要機能・モジュールを実装しています。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開。
  - __version__ を "0.1.0" として定義。
  - パッケージ公開インターフェースとして data, strategy, execution, monitoring をエクスポート。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出は __file__ を起点に `.git` または `pyproject.toml` を探索して行うため、CWDに依存しない動作をサポート。
  - .env パーサーはコメント・export プレフィックス・シングル/ダブルクォート・バックスラッシュエスケープに対応。
  - 自動ロードの優先順位: OS環境変数 > .env.local > .env。  
    環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - Settings クラスを提供し、アプリで必要な設定をプロパティ経由で取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須キー検証。
    - KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL の検証ロジック。
    - データベースパスのデフォルト値: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。

- データ (kabusys.data)
  - ETL パイプライン基盤（kabusys.data.pipeline）を実装。
    - 差分取得、バックフィル、品質チェック（quality モジュール経由）の流れを設計。
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - DuckDB を前提にした最終日付取得ユーティリティ等を実装。
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー管理ロジック（market_calendar）を実装。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB登録値を優先し、未登録日は曜日（週末）ベースのフォールバックを行う設計。
    - calendar_update_job: J-Quants から差分取得して冪等保存。バックフィル・健全性チェックを実装。
  - jquants_client との連携インターフェースを想定（fetch/save 関数を呼び出す設計）。

- AI（自然言語処理）モジュール（kabusys.ai）
  - ニュースNLP スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols テーブルから記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとにセンチメントを算出。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリを実行）。
    - バッチ処理（最大 20 銘柄/コール）、トークン肥大化対策（記事数上限・文字数トリム）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対するエクスポネンシャルバックオフのリトライ実装。
    - レスポンスの厳格なバリデーション（JSON 抽出、results フィールド、コード整合性、数値検証）。
    - ai_scores テーブルへ部分更新（対象コードのみ DELETE → INSERT）して部分失敗時の既存データ保護。
    - API キー注入可能（引数 api_key または環境変数 OPENAI_API_KEY）。
  - マーケットレジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で 'bull'/'neutral'/'bear' を判定。
    - prices_daily / raw_news / market_regime テーブルを参照し、冪等的に market_regime テーブルへ書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - LLM 呼び出しは個別実装でモジュール結合を避け、失敗時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ設計。
    - API リトライと指数バックオフを実装。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Value（PER、ROE）、Volatility（20日 ATR）、Liquidity（20日平均売買代金、出来高変化率）を実装。
    - DuckDB 内の prices_daily / raw_financials のみ参照する安全設計。
    - データ不足時の None 処理・ログ出力の一貫実装。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（複数ホライズン対応、デフォルト [1,5,21]）。
    - IC（Spearman の ρ）計算、ランク関数、ファクターの統計サマリー（count/mean/std/min/max/median）。
    - pandas 等に依存せず標準ライブラリと DuckDB で実装。

- 共通ユーティリティ
  - OpenAI 呼び出しラッパー（各モジュール内で独立実装）によりテスト時の差し替えを想定。
  - DuckDB を前提とした SQL と Python の組合せによる実装。トランザクション管理（BEGIN/COMMIT/ROLLBACK）を明示的に使用。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キー・各種機密は環境変数で扱うことを想定。Settings による必須検証を実装。

### Notes / Migration
- AI 機能（score_news, score_regime）を利用するには OPENAI_API_KEY を設定してください。関数呼び出し時に api_key を渡すことも可能です。
- 自動 .env ロードはデフォルトで有効です。テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- DuckDB / SQLite のデフォルトパスは Settings で定義されます。必要に応じて DUCKDB_PATH / SQLITE_PATH を環境変数で上書きしてください。
- カレンダーや ETL の更新は外部 API（J-Quants 等）呼び出しを伴うため、API クライアント実装（jquants_client）の提供・設定が必要です。
- 日付処理に関して、LLM やスコア計算関数は lookahead バイアスを避けるため date.today()/datetime.today() を直接参照しない設計です。target_date を明示的に渡して使用してください。

### Known limitations
- PBR・配当利回り等一部バリューファクターは未実装（calc_value に注記あり）。
- DuckDB executemany の空リスト取り扱いなどバージョン差異への互換処理を行っているが、古い/新しい DuckDB バージョンで追加検証が必要になる可能性があります。
- OpenAI の JSON mode に依存するため、将来の API 仕様変更があれば影響を受ける可能性があります。

---

貢献や不具合報告、機能提案は issue を通じてお願いします。