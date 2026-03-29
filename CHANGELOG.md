# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

## [0.1.0] - 2026-03-29

### Added
- パッケージ初版リリース。KabuSys: 日本株自動売買およびリサーチ用ユーティリティ群を提供。
  - バージョン: `kabusys.__version__ = "0.1.0"`

- 環境設定管理モジュール (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートの検出は `.git` または `pyproject.toml` に基づく）。
  - 自動ロードを無効化するフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env の読み込み順序: OS 環境 > `.env.local` (上書き) > `.env`（保護された OS 環境変数は上書き除外）。
  - 柔軟な .env パーサ実装:
    - `export KEY=val` 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - クォートなしでのインラインコメント扱いの細かな取り扱い（直前が空白 / タブの場合に `#` をコメント扱い）。
  - 必須設定取得ヘルパ `_require()` と `Settings` クラスを公開（例: `settings.jquants_refresh_token`、`settings.kabu_api_password`、`settings.slack_bot_token`、`settings.duckdb_path`、`settings.env`、`settings.log_level` など）。
  - 環境変数の値検証（`KABUSYS_ENV` / `LOG_LEVEL` の許容値チェック）。

- AI 関連モジュール (kabusys.ai)
  - ニュースセンチメントスコアリング (kabusys.ai.news_nlp)
    - 関数: `score_news(conn, target_date, api_key=None)` を提供。raw_news / news_symbols / ai_scores を用いて銘柄別にニュースを集約し OpenAI（gpt-4o-mini、JSON mode）でセンチメント評価を実行。
    - 設計上の特徴:
      - JST ベースのニュース収集ウィンドウ計算: `calc_news_window(target_date)`（前日 15:00 JST 〜 当日 08:30 JST に対応する UTC naive 時刻を返す）。
      - 1銘柄あたりの記事数・文字数制限（デフォルト `_MAX_ARTICLES_PER_STOCK=10`, `_MAX_CHARS_PER_STOCK=3000`）。
      - バッチ処理（1回あたり最大 `_BATCH_SIZE=20` 銘柄）とチャンク単位の API 呼び出し。
      - エラー耐性: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ（`_MAX_RETRIES` / `_RETRY_BASE_SECONDS`）。
      - レスポンスバリデーションとスコアクリッピング（±1.0）。
      - DuckDB への冪等書き込み: 取得済みコードのみ DELETE → INSERT（部分失敗時に既存スコアを保護）。DuckDB 0.10 の executemany の注意点に対応。
      - テスト容易性: OpenAI 呼び出しを内部関数 `_call_openai_api` でラップしモック差替え可能。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - 関数: `score_regime(conn, target_date, api_key=None)` を提供。ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して market_regime テーブルに日次で書き込み。
    - 設計上の特徴:
      - ETF コード `_ETF_CODE = "1321"`、MA ウィンドウ 200 日など固定パラメータ。
      - macro_sentiment は OpenAI（gpt-4o-mini）へタイトルリストを渡して JSON で取得。記事が無ければ LLM 呼び出しは行わず 0.0 を採用。
      - OpenAI API のリトライ・エラー処理により、API 失敗時はフェイルセーフとして `macro_sentiment=0.0` を採用し続行。
      - レジームスコアは clip して閾値により "bull"/"neutral"/"bear" を決定。
      - DB 書き込みはトランザクションで冪等に実施（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

- データプラットフォーム関連 (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダー（market_calendar）に関するユーティリティを提供:
      - 営業日判定: `is_trading_day(conn, d)`（DB に登録があれば DB 優先、未登録は曜日フォールバック）。
      - SQ 判定: `is_sq_day(conn, d)`。
      - 前後営業日取得: `next_trading_day(conn, d)`, `prev_trading_day(conn, d)`（探索最大範囲 `_MAX_SEARCH_DAYS` を設定し無限ループ防止）。
      - 期間内営業日リスト: `get_trading_days(conn, start, end)`（DB 登録優先かつ曜日フォールバックで一貫性を維持）。
    - 夜間バッチ更新ジョブ: `calendar_update_job(conn, lookahead_days=_CALENDAR_LOOKAHEAD_DAYS)`。J-Quants クライアントを使った差分取得、バックフィル（直近 `_BACKFILL_DAYS`）と健全性チェック（将来日付の異常検出）を実装。
    - DB 未取得時のフォールバック動作や NULL 値検出時のログ出力に配慮。

  - ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETL の結果を表す `ETLResult` dataclass を導入（取得件数、保存件数、品質検査結果、エラー一覧などを含む）。
    - ETL の補助ユーティリティ:
      - テーブル存在チェックや最大日付取得のユーティリティ。
      - 差分更新、バックフィル、品質チェックの設計方針を踏まえた実装向けの下地（jquants_client / quality モジュールを呼び出す前提）。
    - `kabusys.data.etl` で `ETLResult` を再エクスポート。

- リサーチ / ファクター計算 (kabusys.research)
  - ファクター計算モジュール群を追加:
    - `calc_momentum(conn, target_date)`:
      - mom_1m / mom_3m / mom_6m（約1/3/6ヶ月リターン）、ma200_dev（200日 MA に対する乖離）を計算。
      - データ不足時は None を返す。
    - `calc_volatility(conn, target_date)`:
      - 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。
      - 必要行数未満は None を返す。
    - `calc_value(conn, target_date)`:
      - raw_financials と prices_daily を用いて PER（EPS が 0/欠損の場合は None）および ROE を算出。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - `calc_forward_returns(conn, target_date, horizons=None)`:
      - 指定ホライズン（営業日数）後の終値リターンを計算（デフォルト [1,5,21]）。
      - horizons の妥当性チェック（1〜252 日）を実装。
    - `calc_ic(factor_records, forward_records, factor_col, return_col)`:
      - スピアマンランク相関（IC）を計算。3 レコード未満で計算不能の場合は None。
    - `rank(values)`:
      - 同順位は平均ランクを返すランク化ユーティリティ（丸め誤差対策あり）。
    - `factor_summary(records, columns)`:
      - count/mean/std/min/max/median を計算する統計サマリー。
  - 研究ユーティリティのエクスポート:
    - `zscore_normalize`（kabusys.data.stats から再公開）や上記関数群を `kabusys.research` パッケージで公開。

### Changed
- （新規リリースのため該当なし）

### Fixed
- （新規リリースのため該当なし）

### Security
- OpenAI API キーやその他機密情報は環境変数経由で扱う設計。自動 .env ロードは明示的に無効化可能（テスト等の目的）。

### Notes / Implementation details
- OpenAI を利用する各箇所は JSON mode（厳密な JSON 出力を期待）で実装されているが、実運用で LLM の出力が完全な JSON でないケースに備えたパーシング復元ロジックを含む。
- 多くの処理で「ルックアヘッドバイアス」を避けるために内部で datetime.today()/date.today() を参照せず、呼び出し側から `target_date` を受け取る設計としている。
- DuckDB に対する互換性考慮（executemany の空リスト問題等）や、DB 書き込みは冪等化（DELETE→INSERT 等）している。
- テスト性を考慮して外部 API 呼び出し部分（OpenAI 呼び出し等）は内部ラッパー関数で切り出しておりモック差替えが容易。

---

初版のため今後はバグ修正・機能追加（例: strategy / execution / monitoring の実装拡張や CLI、ドキュメント整備）を予定しています。