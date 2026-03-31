# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
次のバージョン番号／日付は、コードベースから推測した初期リリースの内容に基づき作成しています。

お問い合わせや差分の修正が必要な場合はお知らせください。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-31
初期リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。主要な機能群は設定管理、データ ETL / カレンダー管理、リサーチ（ファクター計算・特徴量解析）、および AI ベースのニュースセンチメント / 市場レジーム判定です。設計上の方針として「ルックアヘッドバイアス防止」「冪等性」「外部 API のフェイルセーフ」「DuckDB を用いたローカル集計」を重視しています。

### Added
- パッケージ初期化
  - kabusys.__init__ にバージョン情報（0.1.0）と公開サブパッケージを定義。

- 設定管理（kabusys.config）
  - .env / .env.local ファイル自動読み込み機能（プロジェクトルートは .git または pyproject.toml で探索）。
  - export KEY=val 形式、クォート文字列（エスケープ対応）、コメントの取り扱いに対応した .env パーサ実装。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 環境変数取得ラッパー Settings クラスを追加。主要設定項目:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - PID_FILE_PATH, CPU/MEMORY/DISK 閾値
    - KABUSYS_ENV（development/paper_trading/live 検証）
    - LOG_LEVEL（DEBUG/INFO/... 検証）
  - 必須環境変数未設定時にわかりやすいエラーメッセージを投げる _require()。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini、JSON mode）でセンチメントを評価して ai_scores テーブルへ書き込み。
    - バッチ処理（最大 20 銘柄／チャンク）、記事トリム（最大記事数／最大文字数）実装。
    - API 呼び出しはリトライ（429, ネットワーク, タイムアウト, 5xx）＋指数バックオフ。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列検査、コード照合、数値検証）。
    - DuckDB の executemany の挙動（空リスト不可）を考慮した実装。
    - calc_news_window(target_date) による JST ベースのニュースウィンドウ計算（ルックアヘッド防止）。
    - score_news(conn, target_date, api_key=None) の公開 API。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出。
    - マクロキーワードフィルタリング、OpenAI 呼び出し（gpt-4o-mini）、リトライ、フェイルセーフ（API失敗時は macro_sentiment=0.0）。
    - レジームスコア合成と market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - score_regime(conn, target_date, api_key=None) の公開 API。
  - AI モジュール内部の OpenAI 呼び出し関数はテスト容易性のためモジュール単位で独立実装（モジュール間で private 関数を共有しない設計）。

- Research モジュール（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離の計算（データ不足時に None を返す）。
    - calc_volatility: 20 日 ATR、相対ATR、20日平均売買代金、出来高比率の計算（データ不足時は None）。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS 無効時は None）。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効データ < 3 件なら None）。
    - rank: 同順位は平均ランクとするランク関数（round(..., 12) による丸めで ties を安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - kabusys.research.__init__ で主要関数を再エクスポート。

- Data モジュール（kabusys.data）
  - calendar_management
    - market_calendar テーブルを元に営業日判定（is_trading_day）、next/prev_trading_day、get_trading_days、is_sq_day を実装。
    - DB にデータがない場合は「土日を非営業日」とする曜日ベースのフォールバックを提供。
    - calendar_update_job(conn, lookahead_days=90) で J-Quants から差分取得 → 冪等保存（J-Quants クライアント経由）。バックフィルと健全性チェックを実装。
  - pipeline / etl
    - ETLResult データクラス（取得件数・保存件数・品質問題・エラー集約、has_errors/has_quality_errors/properties、to_dict()）。
    - ETL 実装方針に関するコメントとユーティリティ（差分取得・バックフィル・品質チェック連携等）。
  - etl モジュールで ETLResult を再エクスポート。
  - データアクセスで DuckDB を前提とした SQL 実装を多数追加。

### Changed
- （初期リリースのため該当なし）ただし実装上の設計方針を README 等に明記することを推奨（特に「ルックアヘッドバイアス」回避の注意等）。

### Fixed
- （初期リリースのため該当なし）

### Security
- OpenAI API キー・その他機密情報は環境変数経由で注入する設計（Settings の _require を通じて必須チェック）。
- .env 自動ロード時に OS 環境変数は保護される（.env.local は既存 OS 環境変数を書き換えない保護挙動あり）。

### Notes / Migration / 運用メモ
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings にて必須判定）
  - OpenAI API は score_news / score_regime 実行時に api_key 引数を渡すか、環境変数 OPENAI_API_KEY を設定する必要あり。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。CI/テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- DuckDB スキーマ（想定テーブル）:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar などが利用されます。ETL / カレンダー更新 / AI スコア保存の前にスキーマ作成が必要です。
- 日時扱い:
  - ルックアヘッドバイアス対策として、内部ロジックは target_date 引数を明示的に受け取り、datetime.today()/date.today() を直接参照しない実装を多用しています（テストや再現性が容易）。
- DuckDB の executemany に関する注意:
  - 空リストを渡すとエラーになるバージョン（例: DuckDB 0.10）のため、空チェックを実装しています。
- テスト容易化:
  - OpenAI 呼び出し箇所（各モジュールの _call_openai_api）は unittest.mock.patch による差し替えを想定した分離実装になっています。

### Known issues / TODO
- ai モデル・API 使用量に依存するため、実運用時はレート制限・コストに対する監視と制御が必要です。
- 現状では PBR・配当利回りなど一部バリューファクターは未実装（calc_value の注記参照）。
- calendar_update_job は jquants_client の実装に依存。API のレスポンス仕様変更に備えた堅牢化テストを推奨。
- 例外ハンドリングはいくつかのケースで「警告ログ + スキップ」にしているため、上位での監視・アラート設計が必要。

---

参考: Keep a Changelog—https://keepachangelog.com/en/1.0.0/