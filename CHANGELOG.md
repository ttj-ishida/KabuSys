# CHANGELOG

全体方針: このファイルは「Keep a Changelog」準拠で記載します。  
フォーマットの意味合いについては https://keepachangelog.com/ を参照してください。

すべての変更はセマンティックバージョニングに従います。  
- バージョンは src/kabusys/__init__.py の __version__ に合わせています。

## [Unreleased]
- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-04
初回リリース。日本株自動売買プラットフォームの基礎機能群を実装しました。主に以下のサブパッケージと機能を提供します。

### Added
- パッケージ基盤
  - パッケージ初期化と公開API: kabusys パッケージ（data, strategy, execution, monitoring を __all__ に公開）。
  - バージョン情報: __version__ = "0.1.0" を設定。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - プロジェクトルートは .git または pyproject.toml を起点に探索（CWD 非依存）。
    - .env のパースは export 形式、シングル/ダブルクォート、エスケープ、インラインコメントなどに対応。
  - Settings クラスで型安全に設定を取得可能（プロパティベース）。
    - 必須値取得のヘルパー _require を実装（未設定時は ValueError）。
    - サポートする設定例:
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - OPENAI 用の環境変数（機能ごとに参照）
      - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知用、空文字既定）
      - データベースパス（DUCKDB_PATH, SQLITE_PATH）および監視用ファイルパス（PID_FILE_PATH, KILL_FLAG_PATH）
      - 各種閾値（CPU/MEMORY/DISK）
      - KABUSYS_ENV のバリデーション（development / paper_trading / live）
      - LOG_LEVEL のバリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- AI（NLP）機能（kabusys.ai）
  - news_nlp モジュール（kabusys.ai.news_nlp）
    - raw_news + news_symbols を元に銘柄ごとのニューステキストを集約し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信して銘柄ごとのセンチメント ai_score を算出。
    - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB と比較）。
    - バッチサイズ、記事数と文字数のトリム、レスポンス検証、スコアの ±1.0 クリップ等を実装。
    - API の 429 / ネットワーク断 / タイムアウト / 5xx への指数バックオフリトライを実装。
    - レスポンスパースでの雑多なケース（周辺テキストの混入）の一部復元ロジックを実装。
    - テスト容易性のため _call_openai_api を外部でモック可能に設計。
    - DuckDB への書き込みは部分失敗時に他銘柄の既存スコアを保護する手順（DELETE for codes → INSERT）を採用。DuckDB の executemany の空リスト制約に対応したガード実装あり。
  - regime_detector モジュール（kabusys.ai.regime_detector）
    - 日次で市場レジーム（'bull' / 'neutral' / 'bear'）を判定。
    - 判定ロジック: ETF(1321) の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成。
    - マクロ記事の抽出はキーワードマッチ（英日混在キーワード群）。
    - OpenAI 呼び出しは独自実装でリトライ、API 失敗時は安全フォールバック macro_sentiment = 0.0。
    - DB への書き込みは冪等性を保つ（BEGIN → DELETE → INSERT → COMMIT、失敗時は ROLLBACK）。
    - テスト容易性のため _call_openai_api をモック可能に設計。
  - ai パッケージ公開 API: score_news を __all__ で公開（kabusys.ai.score_news 経由）。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research モジュール
    - Momentum: mom_1m, mom_3m, mom_6m、ma200_dev（200日MA乖離率）を DuckDB の SQL ベースで計算。データ不足（行数不足）時は None を返す。
    - Volatility & Liquidity: 20日 ATR（atr_20）、atr_pct、avg_turnover、volume_ratio を計算。true_range の NULL 伝播を適切に扱う。
    - Value: raw_financials から最新財務を取得し PER（EPS != 0 の場合）と ROE を計算。
    - 実装は外部 API に依存せず DuckDB の prices_daily / raw_financials のみ参照。
  - feature_exploration モジュール
    - 将来リターン calc_forward_returns（任意ホライズン、デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンのランク相関）。
    - rank, factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等に依存せず標準ライブラリおよび DuckDB で動作。
  - research パッケージ公開 API: 主要関数を __all__ で公開。

- データ基盤（kabusys.data）
  - calendar_management モジュール
    - JPX マーケットカレンダーの管理関数群（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar が未取得のときは曜日ベースのフォールバック（週末を休場）で一貫性のある結果を返す。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等的に更新するバッチジョブ。バックフィル・健全性チェックを実装。
    - jquants_client との連携を想定（fetch_market_calendar / save_market_calendar を使用）。
  - pipeline / etl モジュール
    - ETLResult dataclass を公開（kabusys.data.etl で再エクスポート）。
    - ETL パイプラインの骨子: 差分取得、保存（冪等）、品質チェック（quality モジュール）を想定した設計。
    - ETLResult は処理統計・品質問題・エラー概要を保持し、辞書化可能（監査ログ向け）。
    - 内部ユーティリティとしてテーブル存在チェックや最大取得日の取得ロジック等を実装（pipeline.py）。
  - jquants_client を想定したインタフェース呼び出し箇所を導入（外部クライアント実装に依存）。

- ロギングとエラーハンドリング
  - 各モジュールで詳細な info/debug/warning ログを追加。
  - API 呼び出しはネットワーク・レート制限・サーバエラーを考慮したリトライ戦略を採用し、失敗時はフェイルセーフ（例: スコア 0.0、処理スキップ）で継続する設計。
  - DB 書き込みは明示的なトランザクション（BEGIN/COMMIT/ROLLBACK）で保護。

### Changed
- 初リリースにつき既存コードの「変更」はありません（ベース実装）。

### Fixed
- 初リリースにつき「修正」はありません（ベース実装でエラー処理を多めに実装）。

### Security
- OpenAI API キーなどの機密情報は環境変数で扱う方針を採用。.env 自動読み込みはプロジェクトルート探索を行い、テスト時に無効化可能。

### Known issues / 注意点
- OpenAI API の応答は JSON Mode を利用する設計だが、実運用での多様な応答を完全に保証するものではありません。レスポンスパースに失敗した場合は該当チャンクをスキップする実装です。
- DuckDB の executemany が空リストを許容しないバージョン（例: 0.10）を考慮し、空リストガードを入れています。将来の DuckDB バージョンでは不要になる可能性があります。
- news_nlp / regime_detector は OpenAI（gpt-4o-mini）に依存します。API キー未設定時は関数が ValueError を投げます（呼び出し側でのハンドリングが必要です）。
- market_calendar が未取得の場合は曜日フォールバック（週末除外）を行います。カレンダーデータを必ず反映したい場合は calendar_update_job を定期実行してください。
- .env パーサは多くのケースに対応していますが、極端な複雑フォーマットの .env（複数行クォート等）では期待通りに動作しない可能性があります。

### Migration / マイグレーション手順（初回セットアップ）
- 必須環境変数を設定してください:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - OpenAI を利用する場合は OPENAI_API_KEY（または各関数の api_key 引数）
- 必要に応じて .env/.env.local をプロジェクトルートに配置してください。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- デフォルト DuckDB ファイル: data/kabusys.duckdb（環境変数 DUCKDB_PATH で上書き可）
- 監視用 SQLite（監視機能使用時）: data/monitoring.db（環境変数 SQLITE_PATH で上書き可）

---

今後の予定（短期）
- strategy / execution / monitoring の詳細実装と API 連携（発注ロジック、ポートフォリオ管理、監視エージェント）
- テストカバレッジ拡充（特に OpenAI 呼び出しの差し替え・DB 周り）
- J-Quants / kabu API クライアントの具体実装およびサンプル ETL 実行スクリプト公開

もし特定機能（例: ETL 実行例、AI モジュールのプロンプト調整、.env の取り扱いの詳細など）について CHANGELOG の追記や詳しい説明が必要であればお知らせください。