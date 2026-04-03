# Changelog

すべての変更は Keep a Changelog の形式に従います。  
新機能追加・設計方針・互換性やフェイルセーフの説明を中心に、コードベースから推測できる変更点を日本語でまとめています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-03
初期リリース。以下の主要機能と設計方針を実装。

### Added
- パッケージ基本構成を追加
  - kabusys パッケージ（data, research, ai, execution, strategy, monitoring 等を想定）を公開。バージョンは `0.1.0`。

- 環境設定 / 設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を自動で読み込む仕組みを実装。
  - プロジェクトルートの自動検出: `.git` または `pyproject.toml` を基準に検索し、CWD に依存しない自動ロードを実現。
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト用等に利用可能）。
  - .env パーサ（`_parse_env_line`）:
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープに対応。
    - クォートなし値のインラインコメント処理（前にスペース/タブがある `#` をコメントとみなす）を実装。
  - .env 読み込みの上書き制御:
    - `.env` を既存 OS 環境変数を保護しつつ読み込み（override=False）。
    - `.env.local` を OS 環境変数を保護しつつ上書き（override=True）。  
  - 必須キー取得ヘルパ（`_require`）を実装し、未設定時は分かりやすいエラーメッセージを投げる。
  - 設定オブジェクト `Settings` を提供し、以下をプロパティで取得可能:
    - J-Quants: `jquants_refresh_token`（必須）
    - kabuステーション: `kabu_api_password`（必須）、`kabu_api_base_url`（デフォルト設定）
    - LINE: `line_channel_access_token`, `line_user_id`
    - データベースパス: `duckdb_path`, `sqlite_path`
    - 監視関連: `pid_file_path`, `kill_flag_path`, `kill_flag_clear_on_start`, `cpu_threshold_pct`, `memory_threshold_pct`, `disk_threshold_pct`
    - システム: `env`（`development`, `paper_trading`, `live` のバリデーション）、`log_level`（許容値を検証）、`is_live` / `is_paper` / `is_dev` の便利プロパティ

- AI モジュール
  - ニュース NLP (`kabusys.ai.news_nlp`)
    - 関数 `score_news(conn, target_date, api_key=None)` を実装。
    - 前日 15:00 JST 〜 当日 08:30 JST に相当する UTC ナイーブなウィンドウ計算（`calc_news_window`）を実装。
    - `raw_news` と `news_symbols` を結合して銘柄ごとに記事を集約。1 銘柄あたり上限記事数・文字数トリムを適用（トークン肥大化対策）。
    - OpenAI（gpt-4o-mini, JSON Mode）に対するバッチ呼び出し（最大 20 銘柄／コール）とレスポンスバリデーションを実装。
    - リトライ（429・ネットワーク切断・タイムアウト・5xx）を指数バックオフで実行。
    - レスポンス検証: JSON 抽出、`results` キー存在チェック、`code` の正規化、`score` の数値検査、±1.0 にクリップ。
    - DuckDB への書き込みは部分失敗時に既存データを守るため「対象コードのみ DELETE → INSERT」方式で冪等性を確保（トランザクション・ROLLBACK を使用）。
    - テスト容易性のため、内部 OpenAI 呼び出し関数 `_call_openai_api` はモックで差し替え可能に設計。
    - API キーは引数で注入可能（`api_key`）か環境変数 `OPENAI_API_KEY` を利用。未指定時に ValueError を送出。
    - 対象記事なしや API 失敗時は安全にスキップして継続（フェイルセーフ）。ログを詳細に記録。

  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - 関数 `score_regime(conn, target_date, api_key=None)` を実装。
    - ETF コード 1321（日経225 連動型）を用い、200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成してレジーム（`bull`/`neutral`/`bear`）を日次判定。
    - マクロ記事抽出はキーワードベース（日本・米国などのマクロ語）でフィルタリングし、最新上位 N 件を LLM に送付。
    - OpenAI 呼び出しは `_call_openai_api`（news_nlp とは独立）を使用、リトライ/バックオフを実装し、API 失敗時は `macro_sentiment = 0.0` にフォールバック。
    - レジームスコアの合成、ラベリング、`market_regime` テーブルへの冪等書き込み（DELETE/INSERT を含むトランザクション）を実装。
    - ここでも API キー注入が可能で、未設定時は明確な例外を出す。

- Research モジュール (`kabusys.research`)
  - ファクター計算 (`factor_research`)
    - `calc_momentum(conn, target_date)`:
      - mom_1m / mom_3m / mom_6m、ma200_dev（200 日 MA 乖離率）を計算。データ不足時は None を返す。
      - DuckDB 内のウィンドウ関数を活用した実装。
    - `calc_volatility(conn, target_date)`:
      - 20 日 ATR（平均 true range）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。欠測処理あり。
    - `calc_value(conn, target_date)`:
      - raw_financials（直近レポート）と当日の株価を使って PER（EPS が 0/欠損なら None）・ROE を計算。
    - すべて DB 読み取り専用で外部注文や取引 API へはアクセスしない設計。
  - 特徴量探索 (`feature_exploration`)
    - `calc_forward_returns(conn, target_date, horizons=None)`:
      - 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括で計算。horizons の検証（正の整数かつ <= 252）。
    - `calc_ic(factor_records, forward_records, factor_col, return_col)`:
      - スピアマンランク相関（IC）を実装。データ不足（有効レコード < 3）時は None。
    - `rank(values)`:
      - 同順位は平均ランクで処理。丸め（round(v,12)）で浮動小数点の tie 検出漏れを防止。
    - `factor_summary(records, columns)`:
      - count/mean/std/min/max/median を計算する統計サマリー。

- Data モジュール
  - マーケットカレンダー管理 (`kabusys.data.calendar_management`)
    - `is_trading_day`, `is_sq_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days` を実装。
    - market_calendar テーブルが存在しない/未登録の日は曜日ベース（週末除外）でフォールバックする一貫したロジック。
    - 探索範囲の上限（_MAX_SEARCH_DAYS）を設け無限ループを防止。
    - 夜間バッチ更新ジョブ `calendar_update_job(conn, lookahead_days=...)`:
      - J-Quants クライアント経由で差分取得し、冪等保存（ON CONFLICT / upsert想定）を実行。
      - バックフィル期間を設け API 側の訂正を吸収、健全性チェック（未来日付過大時はスキップ）を実装。
  - ETL / パイプライン (`kabusys.data.pipeline` / `kabusys.data.etl`)
    - ETL 処理方針に基づいた設計。差分取得・保存・品質チェックのフローを実装するための基盤を提供。
    - `ETLResult` データクラスを追加（取得数・保存数・品質問題・エラー集約・to_dict() を実装）。
    - テーブル存在チェックや最大日付取得等のユーティリティを実装。
    - `kabusys.data.etl` で `ETLResult` を再エクスポート。

- ロギング・フェイルセーフ・テスト性向上
  - 多くの関数で詳細なログ（info/warning/debug/exception）を追加。
  - API 呼び出しや DB 書き込み失敗に対するフェイルセーフ（例: API 失敗時はスコアを 0.0 にする、部分失敗で既存データを保護する等）を導入。
  - テストで差し替えやすい設計（OpenAI 呼び出し関数等をパッチ可能にしてユニットテスト容易化）。

### Changed
- （初版のため過去変更はなし。設計上の決定事項を明確化）
  - ルックアヘッドバイアス対策: ほとんどのスコアリング / ETL / レジーム判定関数は内部で datetime.today() / date.today() を参照せず、呼び出し側から `target_date` を受け取る形式に統一。

### Fixed
- DB 書き込み互換性の対処
  - DuckDB の `executemany` に空リストを渡せない問題に対応し、空チェックを入れてから `executemany` を実行するようにした（部分書き込み処理での互換性確保）。

### Security
- 環境変数の管理を明確化
  - 必須トークンを `_require` で明確に扱い、誤設定時に早期失敗することで運用上の誤りを検出しやすくした。

### Notes / Design decisions
- 外部 API（OpenAI / J-Quants）呼び出しは `api_key` 引数で注入可能にしており、CI/テスト環境でのモックや分離が可能。
- OpenAI へのプロンプトや JSON Mode の利用、JSON の前後テキスト混入時の復元など、LLM の不確実性を考慮した堅牢化を行っている。
- DB 書き込みは可能な限り冪等化（DELETE→INSERT、ON CONFLICT）し、トランザクションを用いて途中失敗時にロールバックを試みる。
- カレンダー系の関数は DB にデータがない場合にも安全に動作するため、初期導入フェーズでも利用しやすい設計。

### Breaking Changes
- なし（初回リリース）

---

この CHANGELOG はソースコードの実装内容および docstring / ログメッセージから推測して作成しています。実際のリリースノート作成時には、コミット履歴やリリースノートポリシーに基づく調整を推奨します。