# CHANGELOG

All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

## [0.1.0] - 2026-03-31

### Added
- 基本パッケージ情報
  - パッケージ初期バージョンを定義: `kabusys.__version__ = "0.1.0"`。
  - パッケージ公開モジュールを `__all__ = ["data", "strategy", "execution", "monitoring"]` で定義。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数を読み込む自動ローダーを実装。プロジェクトルート検出ロジックは `.git` または `pyproject.toml` を探索して判定（カレントワーキングディレクトリに依存しない）。
  - .env パース実装: `export KEY=val` 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い（クォートの有無で異なる処理）。
  - `.env` / `.env.local` を順次読み込み（OS 環境変数を保護する protected 機能、`.env.local` は override=True）。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - 必須設定を取得する `Settings` クラスを提供（プロパティ経由で取得）。主なキー:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルトあり）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH
    - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
    - KABUSYS_ENV（development/paper_trading/live、検証あり）
    - LOG_LEVEL（DEBUG/INFO/...、検証あり）
  - settings インスタンスをエクスポートして簡単に利用可能。

- AI モジュール (`kabusys.ai`)
  - ニュースセンチメントスコアリング: `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)`
    - raw_news / news_symbols を集約して銘柄ごとの記事テキストを作成。
    - 1銘柄あたり最大記事数・文字数でトリム（デフォルト: 10記事, 3000文字）。
    - 最大20銘柄ずつのバッチ送信（`gpt-4o-mini` / JSON Mode）。
    - 429・ネットワーク断・タイムアウト・5xx で指数バックオフリトライ、その他はスキップ（フェイルセーフ）。
    - レスポンスの厳密なバリデーションとスコアのクリップ（±1.0）。
    - 成功した銘柄のみ `ai_scores` テーブルへ DELETE → INSERT（部分失敗時に他銘柄の既存スコアを保護）。
    - タイムウィンドウは JST ベースで前日 15:00 ～ 当日 08:30（内部は UTC naive datetime で扱う）。
  - 市場レジーム判定: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`
    - ETF 1321 の 200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - マクロニュースは `news_nlp.calc_news_window` と `raw_news` を用いて抽出、LLM は JSON 出力を期待。
    - LLM 呼び出しは失敗時に macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
    - 計算結果は冪等に `market_regime` テーブルへ書き込み（BEGIN/DELETE/INSERT/COMMIT、エラー発生時は ROLLBACK を試行）。

- ETL / Data モジュール (`kabusys.data`)
  - ETL 結果を表現する `ETLResult` データクラスを `kabusys.data.pipeline` で追加（`kabusys.data.etl` から再エクスポート）。
    - 取得件数、保存件数、品質チェック結果、エラー一覧などを含む。辞書化ユーティリティ `to_dict()` を提供。
  - ETL パイプライン設計（差分取得、backfill、品質チェックのフレームワーク）を実装。J-Quants クライアント（`jquants_client`）を介して取得・保存を行う想定。
  - マーケットカレンダー管理 (`kabusys.data.calendar_management`)
    - `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day` を提供。
    - market_calendar テーブルがない場合は曜日ベース（土日を非営業日）でフォールバック。
    - `calendar_update_job(conn, lookahead_days=90)` により J-Quants からカレンダーを差分取得・保存（バックフィルと健全性チェックあり）。
    - 最大探索日数などの安全制約を持ち、DB 値優先の一貫した判定ロジックを実装。

- Research（因子・特徴量探索）モジュール (`kabusys.research`)
  - ファクター計算 (`kabusys.research.factor_research`)
    - `calc_momentum(conn, target_date)` : 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None）。
    - `calc_volatility(conn, target_date)` : 20日 ATR、ATR 比率、20日平均売買代金、出来高比率。
    - `calc_value(conn, target_date)` : PER（EPS が 0/欠損のとき None）、ROE（raw_financials から最新）。
    - DuckDB SQL とウィンドウ関数を活用した実装。
  - 特徴量探索 (`kabusys.research.feature_exploration`)
    - `calc_forward_returns(conn, target_date, horizons=None)` : 将来リターン（デフォルト: [1,5,21]）。
    - `calc_ic(factor_records, forward_records, factor_col, return_col)` : スピアマンのランク相関（IC）計算（有効レコード < 3 の場合 None）。
    - `rank(values)` : 平均ランク（同順位は平均）を返すユーティリティ。
    - `factor_summary(records, columns)` : count/mean/std/min/max/median を計算する要約関数。

- 共通設計方針／実装注意点（ドキュメント化）
  - 全 AI / 研究ロジックは内部で datetime.today()/date.today() を直接参照しない（ルックアヘッドバイアス防止）。すべて target_date を明示的に渡す設計。
  - OpenAI 呼び出しは JSON Mode を利用し、レスポンスのパースとバリデーションを厳格化（パース失敗時の復元ロジックも実装）。
  - DuckDB に対するトランザクション処理（BEGIN/COMMIT/ROLLBACK）を用いた冪等書き込みパターンを採用。
  - API 呼び出し失敗時は基本的にフェイルセーフ（デフォルト中立値の使用、処理スキップ）で継続できるように設計。
  - `executemany` に空リストを渡すと失敗する DuckDB の挙動を考慮し、空チェックを追加。
  - ロギング・警告を広く配置し異常検出とデバッグを容易化。
  - テストのために OpenAI 呼び出し箇所を差し替え可能に（内部関数に注入や patch を想定）。

### Fixed
- 初版リリースのため該当なし。

### Changed
- 初版リリースのため該当なし。

### Removed
- 初版リリースのため該当なし。

---

補足（利用・移行メモ）
- 必須または想定される環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると自動 .env ロードが無効化される。
- OpenAI を用いる機能（news_nlp, regime_detector）は API キーが必要。関数呼び出し時に `api_key` を渡すか、環境変数 `OPENAI_API_KEY` を設定してください。
- DuckDB によるテーブルスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）が想定されています。初期化・スキーマ準備は呼び出し側で行ってください。

もし CHANGELOG に追加したい細かい実装や bugfix、日付の修正などがあれば指示ください。