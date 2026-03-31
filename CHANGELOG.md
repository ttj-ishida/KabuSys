# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

現在のリリースバージョンはパッケージの __version__ と一致する 0.1.0 です。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-31

初回公開リリース。日本株自動売買システムの基盤機能群を提供します。

### Added
- パッケージ基盤
  - パッケージ名 kabusys とバージョン 0.1.0 を導入。
  - パッケージ公開 API（__all__）に data, strategy, execution, monitoring を想定して定義。

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出（.git または pyproject.toml）を行い、CWD に依存しない自動ロードを実現。
  - .env パーサーはコメント・export キーワード・シングル/ダブルクォート・バックスラッシュエスケープに対応。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、主要な設定値をプロパティ経由で取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev ヘルパー

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を基に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini、JSON Mode）でセンチメントを評価して ai_scores テーブルへ書き込み。
  - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window として提供。
  - バッチ処理（最大 20 銘柄 / リクエスト）、1 銘柄あたりの記事・文字数上限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）を実装。
  - API エラー（429 / ネットワーク断 / タイムアウト / 5xx）は指数バックオフでリトライし、失敗時は該当チャンクをスキップしてフェイルセーフに継続。
  - レスポンス検証およびスコアクリッピング（±1.0）。
  - DuckDB 向けの冪等テーブル更新（DELETE → INSERT、トランザクション制御）と、DuckDB 0.10 の executemany 空リスト制約に対する対策。
  - 公開 API: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
  - マクロニュースのフィルタリング（キーワードリスト）と OpenAI 呼び出しを実装（API レートリミット・ネットワーク対策、リトライ、フェイルセーフで macro_sentiment=0.0）。
  - ルックアヘッドバイアス防止のため target_date 未満のみ参照するクエリ設計。
  - 結果を market_regime テーブルへ冪等に書き込む（BEGIN / DELETE / INSERT / COMMIT）。
  - 公開 API: score_regime(conn, target_date, api_key=None) → 1（成功）を返す。

- データプラットフォーム関連（kabusys.data パッケージ）
  - ETL に関する公開インターフェース（ETLResult の再エクスポート）。
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得 / 保存 / 品質チェックのフレームワークを実装。
    - ETLResult データクラスを追加（品質問題・エラー集約・シリアライズ機能）。
    - DB の最大日付取得等のユーティリティを提供。
    - 市場カレンダーのヘルパー（トレーディングデイ調整）を実装予定の補助関数を含む。
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを用いた営業日判定ロジックを実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB にカレンダーがない場合のフォールバック（曜日ベース）と一貫した振る舞いを設計。
    - calendar_update_job による J-Quants からの差分取得と冪等保存（バックフィル、健全性チェックを実装）。
    - 最大探索日数の上限やバックフィルなどの安全策を導入。

- リサーチ機能（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、ATR（20 日）、出来高・売買代金指標、EPS/ROE に基づく Value 指標等を DuckDB 上で計算する関数を提供:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - 不足データに対する None 処理、ログ出力。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（Spearman）計算（calc_ic）、ランク付けユーティリティ（rank）、およびファクター統計サマリー（factor_summary）を実装。
    - pandas 等の外部依存を持たない純標準ライブラリ + DuckDB 実装。
  - zscore_normalize を含むデータ統計ユーティリティを data.stats から再エクスポート。

### Changed
- （初回リリースのため過去の変更なし）

### Fixed
- （初回リリースのため修正履歴なし）

### Security
- OpenAI API キーは関数引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を使用。未設定時は明示的に ValueError を送出して誤設定を防止。

### Notes / Migration / Requirements
- 必要な主な環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（任意: 関数引数で注入可）
  - KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
- DB スキーマ期待値（主に DuckDB テーブル）:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等のテーブル存在を前提とする処理あり。
- OpenAI 呼び出しは JSON Mode を利用するためレスポンスのパースとバリデーションに依存。外部 API の変化に注意。
- 多くの箇所で「ルックアヘッドバイアス防止」が設計方針として明記されているため、処理は target_date 未満／同日扱い等の境界に慎重に実装されています。
- DuckDB のバージョン互換性（executemany の空リスト等）に配慮した実装を行っています。

---

この CHANGELOG はコードの実装内容から推測して作成しています。実際のリリースノートとして使用する場合は、リリース作業や CHANGELOG の正式化時に差分や追加情報（既知の制限、既存バグ、設計上の注意点、依存パッケージのバージョンなど）を追記してください。