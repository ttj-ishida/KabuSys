# Changelog

すべての重要な変更点をここに記録します。  
このファイルは Keep a Changelog の慣習に従っています。  

## [Unreleased]

## [0.1.0] - 2026-04-04
初回公開リリース。

### Added
- パッケージ基盤
  - パッケージ名: `kabusys`。バージョン `0.1.0` を設定（src/kabusys/__init__.py）。
  - 公開モジュール一覧を __all__ で整理（data, strategy, execution, monitoring のエクスポート指示）。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む `Settings` クラスを追加。
  - 自動 .env ロード:
    - プロジェクトルートを `.git` または `pyproject.toml` から探索して `.env` / `.env.local` を自動ロード。
    - OS 環境変数を保護しつつ、`.env.local` は上書き可能。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサは `export KEY=val` 形式、シングル/ダブルクォート、エスケープ、コメント（インラインコメントの扱い）に対応。
  - 必須環境変数取得用 `_require()` を提供。未設定時は明示的に `ValueError` を発生。
  - 主要設定プロパティ:
    - J-Quants: `jquants_refresh_token`（必須）
    - kabuステーション: `kabu_api_password`（必須）、`kabu_api_base_url`（デフォルト `http://localhost:18080/kabusapi`）
    - LINE メッセージング: `line_channel_access_token`, `line_user_id`
    - DB パス: `duckdb_path`（デフォルト `data/kabusys.duckdb`）、`sqlite_path`（デフォルト `data/monitoring.db`）
    - 監視: `pid_file_path`, `kill_flag_path`, `kill_flag_clear_on_start`、`cpu_threshold_pct`、`memory_threshold_pct`、`disk_threshold_pct`
    - 実行環境: `env`（development / paper_trading / live を検証）、`log_level`（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - ヘルプメソッド: `is_live`, `is_paper`, `is_dev`（環境判定）

- AI モジュール（src/kabusys/ai/*）
  - ニュースセンチメント解析（src/kabusys/ai/news_nlp.py）
    - raw_news + news_symbols を集約して銘柄毎のニューステキストを作成し、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信してセンチメントを算出。
    - タイムウィンドウ定義（JST 前日 15:00 ～ 当日 08:30 を UTC に変換）を `calc_news_window()` で提供。
    - バッチサイズ、記事数上限、文字数上限、JSON レスポンス検証とスコアの ±1.0 クリップを実装。
    - 429・ネットワーク・タイムアウト・5xx に対する指数バックオフリトライを実装。失敗はフェイルセーフでスキップ。
    - DuckDB へ idempotent に書き込む（`ai_scores` の該当コードのみ DELETE → INSERT）。部分失敗時に既存データを保護する設計。
    - 公開関数: `score_news(conn, target_date, api_key=None)` — 書き込み銘柄数を返す。API キー未設定時は `ValueError`。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225 連動 ETF）の 200 日 MA 乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジームを判定（'bull' / 'neutral' / 'bear'）。
    - マクロニュースは `news_nlp.calc_news_window` を用いて抽出。OpenAI（gpt-4o-mini、JSON Mode）へ送信して -1.0～1.0 の `macro_sentiment` を取得。
    - LLM 呼び出しに対してリトライ（429/ネットワーク/タイムアウト/5xx）とフェイルセーフ（失敗時 macro_sentiment=0.0）を実装。
    - レジームスコアは clip され、`market_regime` テーブルへトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等に書き込み。DB 書き込み失敗時は ROLLBACK を試行して例外を再送出。
    - 公開関数: `score_regime(conn, target_date, api_key=None)` — 正常時 1 を返す。API キー未設定時は `ValueError`。

- 研究・ファクター群（src/kabusys/research/*）
  - factor_research.py:
    - Momentum: `calc_momentum(conn, target_date)` — 1M/3M/6M リターン、200 日 MA 乖離（不足時は None）を計算。
    - Volatility / Liquidity: `calc_volatility(conn, target_date)` — 20 日 ATR、ATR 比率、平均売買代金、出来高比率を計算。
    - Value: `calc_value(conn, target_date)` — raw_financials と prices_daily を組合せて PER/ROE を計算（EPS が 0/欠損時は None）。
    - すべて DuckDB 上の SQL ウィンドウ関数で実装。戻り値は (date, code) を含む dict のリスト。
  - feature_exploration.py:
    - 将来リターン計算: `calc_forward_returns(conn, target_date, horizons=None)`（デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算: `calc_ic(factor_records, forward_records, factor_col, return_col)` — スピアマンのランク相関を実装（有効レコード < 3 の場合は None）。
    - ランキングユーティリティ: `rank(values)` — 同順位は平均ランクで処理（丸めで ties の検出漏れを防止）。
    - 統計サマリー: `factor_summary(records, columns)` — count/mean/std/min/max/median を計算。
  - re-export: `kabusys.research` は主要関数をトップレベルで公開。

- データプラットフォーム（src/kabusys/data/*）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダーの夜間差分更新ジョブ `calendar_update_job(conn, lookahead_days=90)` を実装（J-Quants からの取得 + idempotent 保存）。
    - 営業日判定ユーティリティ:
      - `is_trading_day(conn, d)`, `next_trading_day(conn, d)`, `prev_trading_day(conn, d)`, `get_trading_days(conn, start, end)`, `is_sq_day(conn, d)`。
    - DB 登録がない場合は曜日ベースのフォールバックを使用。最大探索日数 `_MAX_SEARCH_DAYS` による安全防止。
    - 異常値（極端な未来日付など）に対する健全性チェックとログ出力。
  - ETL / パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETL 結果を表す dataclass `ETLResult` を提供（取得数・保存数・品質問題・エラー等を保持、to_dict メソッドあり）。
    - 差分更新、バックフィル（デフォルト 3 日）、品質チェックの設計方針を実装（jquants_client を利用して idempotent 保存）。
    - `etl` パッケージは pipeline の `ETLResult` を再エクスポート。

- その他
  - 例外ハンドリングとログ出力を重視（API 呼び出し失敗、DB トランザクション失敗時に適切にログ／フォールバック）。
  - 「ルックアヘッドバイアス防止」目的で、各種処理で datetime.today()/date.today() を直接参照しない設計が徹底されている（全関数は target_date 引数を受ける）。
  - OpenAI クライアントは `openai.OpenAI` を使用し、gpt-4o-mini モデルと JSON Mode を想定。
  - DuckDB を主要な分析 DB として想定（SQL を直接実行する設計）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数読み込み時に OS 環境変数を保護する仕組みを導入（`.env` の上書き制御）。
- OpenAI / 外部 API キーは引数で注入可能にしてテスト容易性と秘匿性を考慮（`api_key` 引数が優先、未設定は環境変数 `OPENAI_API_KEY` を参照）。

### Notes / Requirements / 観察事項
- 動作に必要な主な環境変数:
  - OPENAI_API_KEY（AI 機能: news_nlp / regime_detector）
  - JQUANTS_REFRESH_TOKEN（データ ETL）
  - KABU_API_PASSWORD（発注系）
- デフォルトではローカルの DuckDB ファイル（data/kabusys.duckdb）を使用する想定だが、`DUCKDB_PATH` 環境変数で上書き可能。
- OpenAI のレスポンスの妥当性チェック・パースに失敗した場合はログ出力の上でフェイルセーフとしてスキップまたは中立スコアを採用する。
- DuckDB バージョンや executemany の制約に配慮した実装（空リストバインド回避のためのガード）を行っている。

以上。