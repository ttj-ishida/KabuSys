# Changelog

すべての変更は "Keep a Changelog" の形式に従い記載しています。  
このプロジェクトの初期リリース（0.1.0）は、データ取得・ETL・カレンダー管理・研究用ファクター計算・AI（ニュースセンチメント / 市場レジーム判定）など日本株自動売買プラットフォームのコア機能を含みます。

The format is based on Keep a Changelog and this project adheres to Semantic Versioning.

## [Unreleased]

## [0.1.0] - Initial release
リリース日: (推定) 0.1.0 — 初期実装

### Added
- パッケージの基本公開インターフェース
  - kabusys.__init__ にて __version__ = "0.1.0" を設定し、主要サブパッケージを公開（data, strategy, execution, monitoring）。

- 環境変数 / 設定管理 (kabusys.config)
  - .env ファイル（.env と .env.local）の自動読み込み機能を実装。プロジェクトルート (.git または pyproject.toml) を基準に探索し、自動ロードを行う。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途）。
  - .env のパース実装（コメント・export プレフィックス・シングル/ダブルクォート・エスケープ対応）。
  - Settings クラスを導入し、J-Quants / kabuステーション / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベル等のプロパティを提供。
  - 必須変数取得時の明確なエラー（_require）を導入。

- AI: ニュースセンチメント (kabusys.ai.news_nlp)
  - raw_news / news_symbols を集約して銘柄ごとにニューステキストを結合し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを取得。
  - JSON Mode を利用した厳密なレスポンス処理とレスポンスバリデーションを実装（結果の検査、未知コードの無視、スコアのクリップ）。
  - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実装し、失敗時は該当チャンクをスキップするフォールバック動作。
  - テスト容易性のため _call_openai_api の差し替えを前提とした設計。
  - calc_news_window により JST ベースのニュース収集ウィンドウ（前日 15:00 ～ 当日 08:30）を正確に計算。
  - ai_scores テーブルへの冪等的書き込み（DELETE → INSERT）を行うことで部分失敗時に既存データを保護。

- AI: 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とニュース由来の LLM マクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出。
  - OpenAI 呼び出しのリトライ・フォールバックを実装（API の失敗やパース失敗時は macro_sentiment = 0.0 で継続）。
  - DuckDB 上の prices_daily / raw_news / market_regime を参照/更新する処理を提供。market_regime への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実施。
  - ルックアヘッドバイアス対策（内部で datetime.today() を参照しない・クエリは target_date 未満のみ使用）。

- データ: ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
  - ETLResult dataclass を導入し、ETL 実行の取得件数・保存件数・品質問題・エラーを集約するインターフェースを提供。
  - 差分更新、バックフィル、品質チェックの設計方針を実装（J-Quants クライアント経由で差分取得し、idempotent に保存）。
  - _get_max_date などのヘルパーによるテーブル存在/最大日付取得処理。

- データ: カレンダー管理 (kabusys.data.calendar_management)
  - market_calendar を使った営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
  - DB 登録値優先、未登録日は曜日ベースでのフォールバック（週末判定）という一貫したポリシーを採用。
  - calendar_update_job により J-Quants からの差分フェッチと冪等保存（ON CONFLICT 相当）を実装。バックフィルや健全性チェック（将来日付の異常検出）を含む。

- 研究用ツール群 (kabusys.research)
  - ファクター計算 (factor_research):
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率を計算。
    - calc_value: PER / ROE を raw_financials と prices_daily から計算。
    - DuckDB を用いた SQL 中心の実装で、外部 API にアクセスしない安全な設計。
  - 特徴量探索 (feature_exploration):
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得（LEAD を活用）。
    - calc_ic: スピアマン（ランク相関）による IC 計算（最小サンプル数チェック有）。
    - rank, factor_summary: ランク化・統計サマリー算出ユーティリティを提供。
  - すべて標準ライブラリと DuckDB のみで完結する設計（pandas 等に依存しない）。

- テスト性 / 安全設計
  - OpenAI 呼び出し部の差し替え容易性（関数を patch 可能）を確保。
  - ルックアヘッドバイアス回避のため target_date ベースの設計を徹底。
  - DB 書き込みは明示的なトランザクション（BEGIN / COMMIT / ROLLBACK）で実行し、部分失敗に備えたロールバック処理を実装。
  - ロギングを各処理に挿入（警告・情報・デバッグレベル）し、異常時の診断を容易に。

### Changed
- N/A（初期リリース）

### Fixed
- N/A（初期リリース）

### Removed
- N/A（初期リリース）

### Security
- OpenAI API キーは関数引数で注入可能（api_key 引数）または環境変数 OPENAI_API_KEY を参照。いずれも明示的なエラーを出すことで未設定による実行を防止。

---

## 注意 / マイグレーション / 運用メモ
- 環境変数（必須）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings により必須とされるプロパティがあるため、本番稼働時は設定を確認してください。
  - OpenAI を利用する機能（score_news / score_regime）は api_key 引数を直接渡すか、環境変数 OPENAI_API_KEY を設定してください。未設定時は ValueError を送出します。

- デフォルト DB パス
  - DuckDB: data/kabusys.duckdb
  - SQLite（モニタリング）: data/monitoring.db
  - 必要に応じて環境変数 DUCKDB_PATH / SQLITE_PATH で変更可能。

- テスト時
  - 自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 によって無効化できます。
  - OpenAI 呼び出しはモジュール内の _call_openai_api を patch してテスト可能（unittest.mock.patch を想定）。

- ロバストネス設計
  - AI API 呼び出しは多段リトライ / バックオフを実装し、最終的にフォールバック動作（ゼロスコアやチャンクスキップ）で処理を継続します。これにより API 側の一時障害がシステム全体を停止させるリスクを低減しています。
  - DuckDB の executemany に関する互換性に配慮した空リストチェックなどの互換性考慮が含まれます。

---

この CHANGELOG はコードベースの実装内容（モジュール、関数、設計コメント、ログ出力等）から推測して作成しています。実際のリリース日や追加のリリースノート情報があれば適宜更新してください。