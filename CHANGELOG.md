# Changelog

すべての注目すべき変更を記録します。This project は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-28
初期リリース。日本株自動売買システムのコアライブラリを公開します。主にデータ取得／ETL、マーケットカレンダー管理、ファクター計算、ニュース NLP / LLM 連携、マーケットレジーム判定、環境設定管理などの機能を含みます。

### Added
- パッケージ初期化
  - kabusys パッケージの基本エクスポートを追加（data, strategy, execution, monitoring を __all__ に設定）。
  - バージョン情報 __version__ = "0.1.0" を定義。

- 環境設定 / .env ローダー（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする機能を追加。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーは以下をサポート：
    - 空行・コメント行・`export KEY=val` 形式
    - シングル／ダブルクォート値のエスケープ処理
    - クォートなし値でのインラインコメント（直前がスペース/タブの場合のみ）
  - 既存 OS 環境変数を保護する protected set を用いた上書き制御（.env.local は上書き可能だが OS 環境変数は保護）。
  - Settings クラスを公開し、主要設定プロパティを提供：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト localhost）
    - Slack 設定（SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）
    - データベースパス（duckdb, sqlite）の Path 化とデフォルト値
    - KABUSYS_ENV の検証（development / paper_trading / live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live/is_paper/is_dev ヘルパー

- ニュース NLP & LLM スコアリング（kabusys.ai.news_nlp）
  - raw_news / news_symbols を元に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを評価して ai_scores に書き込む機能を実装（score_news）。
  - バッチ処理（1回あたり最大 20 銘柄）、トークン肥大化対策（記事数・文字数上限）、JSON レスポンスの堅牢なバリデーションを実装。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライを実装。その他のエラーはスキップして継続するフェイルセーフ設計。
  - calc_news_window（JST 基準のニュース集計ウィンドウ計算）を実装。
  - テスト容易性のため _call_openai_api を patch で差し替え可能に設計。

- マーケットレジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する機能（score_regime）を追加。
  - LLM 呼び出しは gpt-4o-mini を想定、API エラーに対するリトライ/フォールバック（macro_sentiment=0.0）を実装。
  - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とエラー時の ROLLBACK の保護処理を実装。
  - ルックアヘッドバイアス防止のため、日付は引数 target_date に基づき DB の target_date 未満のデータのみ参照する設計。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research: calc_momentum, calc_volatility, calc_value を実装
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）
    - ボラティリティ（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比）
    - バリュー（PER, ROE。raw_financials から最新の財務データを組合せ）
  - feature_exploration: calc_forward_returns（任意ホライズンの将来リターン）、calc_ic（Spearman ランク相関による IC）、rank（平均ランク処理）、factor_summary（基本統計量）を実装。
  - 全て DuckDB を直接クエリして計算（pandas 等への依存なし）。関数は (date, code) ベースのリストを返す。

- データプラットフォーム（kabusys.data）
  - calendar_management: JPX カレンダー管理、営業日判定 API（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）と夜間バッチ更新 job（calendar_update_job）を実装。
    - market_calendar 未取得時は曜日ベースのフォールバック（週末は非営業日）。
    - カレンダー更新は J-Quants クライアント経由で差分取得し保存（バックフィル、健全性チェックを含む）。
  - pipeline / etl: ETLResult dataclass と ETL 用ユーティリティを実装（差分取得、保存、品質チェックの枠組み）。
  - ETLResult.to_dict() は品質問題をシリアライズ可能な形に変換。

- DuckDB 互換性に配慮した実装
  - executemany の空リスト回避、ANY(?) のリストバインド問題回避など DuckDB 実装差異に対応する SQL パターンを採用。

- 設計方針・品質面の追加記述（コード内ドキュメント）
  - ルックアヘッドバイアス回避を明確化（datetime.today() 等を直接参照しない）。
  - テスト容易性（API 呼び出しの差し替え可能化、sleep の注入など）を配慮。
  - ロギングにより各処理の状況・警告を詳細に出力。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- OpenAI API キー等の必須シークレットは Settings で環境変数から取得し、未設定時は明示的に ValueError を送出する設計。自動 .env 読み込みは明示的に無効化可能。

### Known issues / Notes / Future work
- Value ファクターの PBR・配当利回り等は現バージョンでは未実装（ファイル内注記あり）。
- OpenAI SDK / API のバージョンやエラーモデルの変化により例外クラスや status_code の取り扱いが変わる可能性があるため、継続的な監視が必要。
- DuckDB バージョン依存の挙動（リストバインド等）に注意。将来的に互換性テストを CI に導入することが望ましい。
- 時刻は基本的に naive UTC / date を用いる設計。タイムゾーン要件が増えた場合は拡張検討。

---

著者注:
- 各モジュール内部に詳細な設計注釈（フェイルセーフ戦略、リトライ仕様、ルックアヘッド回避等）が含まれており、実運用やテスト時のふるまいを確認できます。