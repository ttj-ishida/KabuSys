# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

注意: ここに記載した内容は、与えられたコードベースから推測してまとめた初期リリース向けの変更履歴です。

## [0.1.0] - 2026-03-31

### Added
- パッケージの初期公開
  - メインパッケージ: `kabusys`（__version__ = "0.1.0"）。
  - 主要サブパッケージ／モジュール群を提供: `data`, `research`, `ai`, `execution`, `strategy`, `monitoring`（__all__ に明示）。

- 環境設定管理
  - `kabusys.config.Settings` による一元的な環境変数アクセスを実装。
  - `.env` / `.env.local` 自動読み込み機能を実装（プロジェクトルートは `.git` または `pyproject.toml` から検出）。
  - 読み込み挙動:
    - OS 環境変数 > `.env.local` > `.env` の優先順位。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - 上書き時に OS 環境変数を保護する仕組み（protected set）。
  - 高度な .env パーサ実装:
    - `export KEY=val` 形式、シングル/ダブルクォート文字列、バックスラッシュエスケープ、インラインコメント処理に対応。
  - 必須環境変数取得ヘルパ `_require` を提供し、未設定時は明示的なエラーを発生させる。
  - 主要設定プロパティを定義:
    - J-Quants: `JQUANTS_REFRESH_TOKEN`
    - kabuステーション: `KABU_API_PASSWORD`, `KABU_API_BASE_URL`
    - Slack: `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`
    - データベースパス: `DUCKDB_PATH`, `SQLITE_PATH`
    - 監視関連: `PID_FILE_PATH`, `CPU_THRESHOLD_PCT`, `MEMORY_THRESHOLD_PCT`, `DISK_THRESHOLD_PCT`
    - 実行環境判定: `KABUSYS_ENV` (`development`/`paper_trading`/`live`) と `LOG_LEVEL` 検証

- AI / ニュース NLP
  - `kabusys.ai.news_nlp.score_news`:
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON モードを使って銘柄ごとのセンチメント（-1.0〜1.0）を算出し `ai_scores` テーブルへ書き込み。
    - 前日 15:00 JST 〜 当日 08:30 JST のニュースウィンドウ計算（UTC 変換）を実装（`calc_news_window`）。
    - バッチ処理（最大 20 銘柄/チャンク）、記事数／文字数トリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - 再試行ポリシー：429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ（最大リトライ回数の制御）。
    - レスポンス検証（JSON 抽出、results リスト・code と score の検証、未知コードの無視、数値検証、±1.0 クリップ）。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（`_call_openai_api` をモック可能）。
    - 部分成功時に既存データを保護する安全な DB 書き込み（DELETE → INSERT をコード単位で実行）。

  - `kabusys.ai.regime_detector.score_regime`:
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio 計算（ルックアヘッド防止のため target_date 未満のみ使用）。
    - マクロ記事フィルタリング（キーワードリスト）→ LLM 呼び出し（gpt-4o-mini）→ JSON パース。
    - フェイルセーフ: API 失敗やパース失敗時は macro_sentiment = 0.0 にフォールバック。
    - しきい値に基づくラベル付け（_BULL_THRESHOLD, _BEAR_THRESHOLD）。
    - 冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。

- リサーチ / ファクター計算
  - `kabusys.research.factor_research`:
    - `calc_momentum`: 1M/3M/6M リターン、200日 MA 乖離（データ不足時の扱いを明確化）。
    - `calc_volatility`: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率。
    - `calc_value`: raw_financials から最新財務を取得し PER / ROE を計算（EPS が 0/欠損時は None）。
    - すべて DuckDB の SQL と Python の組合せで実装。外部 API/発注系にはアクセスしない設計。

  - `kabusys.research.feature_exploration`:
    - `calc_forward_returns`: 任意ホライズン（デフォルト [1,5,21]）の将来リターン計算（LEAD を利用）。
    - `calc_ic`: スピアマンのランク相関（IC）計算（結合・None 除外・最小サンプル数チェック）。
    - `rank`: 同順位は平均ランクを割り当てる実装（丸めで ties の判定安定化）。
    - `factor_summary`: count/mean/std/min/max/median を標準ライブラリのみで計算。
    - 外部依存を避け、標準ライブラリと DuckDB のみで統計処理を実装。

- データプラットフォーム
  - `kabusys.data.calendar_management`:
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days の提供。
    - カレンダーデータが無い場合の曜日ベースフォールバック（土日非営業）。
    - calendar_update_job: J-Quants API から差分取得・バックフィル・保存（フェイルセーフと健全性チェック）。
    - 最大探索日数制限やバックフィル、直近データの再取得設計を導入。

  - `kabusys.data.pipeline`:
    - ETL 用の結果 dataclass `ETLResult` を提供（取得件数、保存件数、品質問題、エラーリスト等を含む）。
    - `kabusys.data.etl` から ETLResult を再エクスポート。
    - 差分更新設計、バックフィル、品質チェックとの連携方針を実装方針コメントに記載。

- ロギングとテスト支援
  - 各モジュールで詳細な info/debug/warning ログを出力する用意がある（処理状況や API エラー時の通知）。
  - OpenAI 呼び出し等をモック差替え可能にしてユニットテストを想定した設計。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- OpenAI API キーは引数で注入可能かつ環境変数 `OPENAI_API_KEY` を参照。必須未設定時は ValueError を送出して明示的に失敗する設計。
- 自動 .env ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` によって無効化可能（テスト/セキュリティ用途）。

---

補足:
- 多くの設計コメント・フェイルセーフ・テストフックがコード内部に明記されており、本 CHANGELOG はそれらの設計方針と機能を要約しています。
- 実装の一部（pipeline モジュールの末尾など）は与えられたスニペットで途切れているため、関連する細部は推測に基づく記載があります。具体的な改善やバグ修正は今後のバージョンで追記してください。