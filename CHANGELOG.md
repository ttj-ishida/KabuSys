# Changelog

すべての重要な変更点を記録します。本ファイルは "Keep a Changelog" の形式に準拠します。  
リリースの方針: セマンティックバージョニングに従います。

リンク: （リポジトリの比較リンク等があればここに挿入してください）

## [Unreleased]

## [0.1.0] - 2026-03-31
初回公開リリース。

### Added
- パッケージのエントリポイント
  - パッケージ名: kabusys
  - バージョン: `0.1.0`
  - パッケージは public モジュール群を `__all__` で公開 (`data`, `strategy`, `execution`, `monitoring`)。

- 設定・環境変数管理 (`kabusys.config`)
  - プロジェクトルート探索ロジックを実装（`.git` または `pyproject.toml` を起点に探索）。
  - `.env` / `.env.local` の自動読み込み機能を提供（環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
  - `.env` のパーサ実装:
    - `export KEY=val` 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープを適切に処理
    - 非クォート値の行内コメント処理（`#` の直前がスペース/タブの場合にコメントと判定）
  - セーフティ機構:
    - ファイル読み込みエラー時に警告を出力して継続
    - OS 環境変数を保護する `protected` オプション
  - `Settings` クラスを提供し、主要設定をプロパティで公開:
    - J-Quants: `jquants_refresh_token`
    - kabuステーション: `kabu_api_password`, `kabu_api_base_url`（デフォルト: `http://localhost:18080/kabusapi`）
    - Slack: `slack_bot_token`, `slack_channel_id`
    - DB パス: `duckdb_path`（デフォルト `data/kabusys.duckdb`）, `sqlite_path`
    - 実行環境: `env`（検証済み値: `development`, `paper_trading`, `live`）
    - ログレベル: `log_level`（`DEBUG`,`INFO`,`WARNING`,`ERROR`,`CRITICAL`）
    - 利便性プロパティ: `is_live`, `is_paper`, `is_dev`
  - 必須変数未設定時は `ValueError` を送出する `_require` を実装。

- AI 関連モジュール (`kabusys.ai`)
  - news NLP スコアリング (`kabusys.ai.news_nlp`)
    - ニュース記事を銘柄ごとに集約し、OpenAI（`gpt-4o-mini`）でセンチメントを評価して `ai_scores` テーブルへ書き込み。
    - タイムウィンドウ（JST 基準）計算ユーティリティ `calc_news_window(target_date)` を提供（前日 15:00 JST 〜 当日 08:30 JST）。
    - バッチ処理（最大 20 銘柄/回）・1 銘柄あたりの記事数／文字数上限（過度なトークン肥大対策）。
    - レスポンスは JSON Mode を期待し、堅牢なバリデーション（JSON 抽出、`results` リスト、`code`/`score` 検証）を実装。無効レスポンスはスキップし例外を投げない（フェイルセーフ）。
    - リトライ/バックオフ: 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。
    - スコアは ±1.0 にクリップ。
    - DB 書き込みは冪等性を保つ（対象コードのみ DELETE → INSERT）。DuckDB の `executemany` の制約に対応した空チェックを実装。
    - 外部テストのため `kabusys.ai.news_nlp._call_openai_api` をモック可能に設計。
    - 公開 API: `score_news(conn, target_date, api_key=None)` — 成功時に書き込んだ銘柄数を返す。OpenAI API キー未指定の場合は `ValueError`。

  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（`bull` / `neutral` / `bear`）を判定して `market_regime` テーブルに書き込む。
    - MA 計算: target_date 未満のみを使用してルックアヘッドを防止。データ不足時は中立 (1.0) として扱う。
    - マクロニュース抽出はキーワードマッチ（定義済みキーワード群）に基づき最大件数で取得。記事がない場合は LLM 呼び出しをスキップして macro_sentiment=0.0。
    - OpenAI 呼び出しは専用関数で実装。リトライ/バックオフ、5xx の取り扱い、パース失敗時のフォールバック（macro_sentiment=0.0）を実装。
    - レジーム値はクリップされ閾値でラベル化。DB 書き込みはトランザクションで冪等性を確保（BEGIN / DELETE / INSERT / COMMIT、失敗時に ROLLBACK）。
    - 公開 API: `score_regime(conn, target_date, api_key=None)` — 成功時に 1 を返す。OpenAI API キー未指定は `ValueError`。

- Data / ETL / カレンダー関連 (`kabusys.data`)
  - ETL インターフェース
    - `kabusys.data.pipeline.ETLResult` を公開 (`kabusys.data.etl` 経由で再エクスポート)。
    - ETL の結果表現に品質チェック・エラー情報を含められるように設計。
  - パイプラインユーティリティ (`kabusys.data.pipeline`)
    - 差分取得 / 保存 / 品質チェックに関するユーティリティ実装（DuckDB ベース）。
    - 市場カレンダー・データ最終日取得ヘルパ `_get_max_date`、テーブル存在チェック等を実装。
    - 設計上、初回ロード等のための最小開始日定義やバックフィル日数等を定義。
  - カレンダー管理 (`kabusys.data.calendar_management`)
    - JPX カレンダーの夜間バッチ更新ジョブ `calendar_update_job(conn, lookahead_days=...)` を実装（J-Quants クライアント経由で取得・保存）。
    - market_calendar が未取得でも曜日によるフォールバックで営業日判定を行うロジックを提供:
      - is_trading_day(conn, d)
      - is_sq_day(conn, d)
      - next_trading_day(conn, d)
      - prev_trading_day(conn, d)
      - get_trading_days(conn, start, end)
    - 最大探索日数の上限を設定して無限ループを防止。
    - DB 登録ありの場合は DB 値優先、未登録日は曜日ベースのフォールバックで一貫して補完する実装。
    - カレンダー取得時のバックフィル・健全性チェックを実装（未来日が過大な場合はスキップ）。

- リサーチ / ファクター計算 (`kabusys.research`)
  - ファクター計算群を提供（DuckDB を用いた SQL 集約 + Python ロジック）:
    - `calc_momentum(conn, target_date)`:
      - mom_1m / mom_3m / mom_6m、ma200_dev（200日移動平均乖離）
      - データ不足時は None を返す挙動
    - `calc_volatility(conn, target_date)`:
      - 20日 ATR（atr_20）、相対 ATR（atr_pct）、avg_turnover、volume_ratio
      - true_range の NULL 伝播を制御して ATR のカウントを正確化
    - `calc_value(conn, target_date)`:
      - PER（EPS が 0/NULL の場合は None）、ROE（財務データから取得）
  - 特徴量探索・評価 (`kabusys.research.feature_exploration`)
    - `calc_forward_returns(conn, target_date, horizons=None)`:
      - 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で取得。
      - horizons に対する入力検証（正の整数、<=252）。
    - `calc_ic(factor_records, forward_records, factor_col, return_col)`:
      - スピアマンのランク相関（IC）を実装（同順位は平均ランク）。
      - 有効レコードが 3 未満の場合は None を返す。
    - `rank(values)`、`factor_summary(records, columns)` などの統計ユーティリティ。
  - 設計方針:
    - DuckDB 接続のみを参照し、本番の発注 API にはアクセスしない（安全性）。
    - pandas などの外部依存を使わず標準ライブラリで実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーや各種シークレットは環境変数から取得する設計。`.env` 自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
- 設定読み込み時にファイル読み込みエラーは警告で扱い、例外でプロセスを停止しない設計（安全側の挙動）。

---

注記:
- 各 AI モジュール・ETL・カレンダー等で外部 API 呼び出しや DB 書き込みを行います。実行にあたっては該当する環境変数（OpenAI, J-Quants, kabu API, Slack トークン等）と DuckDB/SQLite の設定が必要です。  
- テストしやすさを考慮して、OpenAI 呼び出し部分はモック差し替え可能に実装されています（ユニットテストでの差し替え推奨）。