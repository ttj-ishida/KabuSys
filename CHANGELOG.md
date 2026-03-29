# Changelog

すべての変更は https://keepachangelog.com/ja/ に準拠しています。

注: この CHANGELOG はリポジトリの現行コードベースから機能・設計方針を推測して作成した初期リリース向けの記録です。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-29

### Added
- パッケージ基本構成を追加
  - パッケージバージョンを設定: `kabusys.__version__ = "0.1.0"`
  - パッケージ公開 API の初期エクスポート: `__all__ = ["data", "strategy", "execution", "monitoring"]`

- 環境設定・ロード機能 (`kabusys.config`)
  - `.env` / `.env.local` ファイルまたは OS 環境変数から設定を読み込む自動ロードを実装。
  - 自動ロードはパッケージ内の `_find_project_root()` により `.git` または `pyproject.toml` を探索してプロジェクトルートを特定し、配布後も動作するよう設計。
  - `.env.local` が `.env` を上書きする優先順位を採用。OS 環境変数は保護（上書きされない）。
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
  - 強力な `.env` パーサ実装（`export` プレフィックス、シングル/ダブルクォート、エスケープ、行内コメントの扱いなどをサポート）。
  - 必須環境変数取得用ユーティリティ `_require()` と、アプリケーション設定をラップする `Settings` クラスを追加。
    - J-Quants / kabuステーション / Slack / DB パス等の設定プロパティを提供。
    - `KABUSYS_ENV` と `LOG_LEVEL` のバリデーションを実施し、`is_live` / `is_paper` / `is_dev` プロパティを提供。
    - デフォルトの DB パス: `DUCKDB_PATH="data/kabusys.duckdb"`, `SQLITE_PATH="data/monitoring.db"`

- ニュースNLP（AI）モジュール (`kabusys.ai.news_nlp`)
  - raw_news と news_symbols を入力に OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込む機能を実装。
  - タイムウィンドウ計算（JST基準、前日15:00〜当日08:30）用 `calc_news_window()` 実装。
  - 1銘柄あたり記事数・文字数制限（デバッグ・トークン肥大化対策）。
  - 1回あたり最大バッチ処理数やリトライ（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）を実装。
  - レスポンスの厳格なバリデーション（JSON抽出、results リスト、code と score の検証）、スコア ±1.0 クリップを実施。
  - DB 書込は部分失敗耐性を持たせるため、対象コードのみ DELETE → INSERT する冪等的アプローチを採用。
  - テスト容易性のため API 呼び出し部分は差し替え可能（`_call_openai_api` を patch 可能）。

- 市場レジーム判定モジュール (`kabusys.ai.regime_detector`)
  - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み70%）と、マクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（`bull` / `neutral` / `bear`）を判定する `score_regime()` を実装。
  - マクロキーワードによる raw_news フィルタ、OpenAI（gpt-4o-mini）による JSON 出力要求、API 再試行・フェイルセーフ（API失敗時は macro_sentiment=0.0）を実装。
  - レジームスコア算出ロジックと、`market_regime` テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT / ROLLBACK）を実装。
  - ルックアヘッドバイアス防止のため日付・クエリ条件に注意した設計。

- データプラットフォーム（Data）モジュール
  - カレンダー管理 (`kabusys.data.calendar_management`)
    - JPX カレンダー管理関数を実装: 営業日判定 `is_trading_day()`、翌営業日 `next_trading_day()`、前営業日 `prev_trading_day()`、期間内営業日 `get_trading_days()`、SQ判定 `is_sq_day()`。
    - market_calendar が未取得の場合は曜日ベースでフォールバック（週末を非営業日扱い）。
    - カレンダー夜間バッチ更新 `calendar_update_job()` を追加（J-Quants API から差分取得、バックフィル、健全性チェック）。
    - 最大探索日数 `_MAX_SEARCH_DAYS`、バックフィル日数、将来日健全性チェック等の保護を実装。
  - ETL パイプライン (`kabusys.data.pipeline`)
    - ETL 結果を表すデータクラス `ETLResult` を追加（取得数・保存数・品質問題・エラー一覧の保持、辞書変換ユーティリティ `to_dict()`）。
    - 差分更新、バックフィル、品質チェックとの連携を想定したユーティリティ群を実装（内部ユーティリティ `_table_exists`, `_get_max_date` 等）。
  - ETL 公開インターフェース (`kabusys.data.etl`)
    - `ETLResult` を再エクスポート。

- リサーチ（Research）モジュール (`kabusys.research`)
  - ファクター計算 (`kabusys.research.factor_research`)
    - Momentum / Volatility / Value 系のファクター計算関数を実装:
      - `calc_momentum(conn, target_date)` : 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None）
      - `calc_volatility(conn, target_date)` : 20日 ATR、相対 ATR、20日平均売買代金、出来高比率
      - `calc_value(conn, target_date)` : PER / ROE（raw_financials から最新財務データを利用）
    - DuckDB のウィンドウ関数等を利用した SQL ベース実装。外部 API にはアクセスしない設計。
  - 特徴量探索 (`kabusys.research.feature_exploration`)
    - 将来リターン計算 `calc_forward_returns()`（任意ホライズン、入力検証あり）。
    - IC（Information Coefficient）計算 `calc_ic()`（Spearman の ρ：ランク相関）。
    - ランク変換ユーティリティ `rank()`（同順位は平均ランク）。
    - 統計サマリー `factor_summary()`（count/mean/std/min/max/median）。
    - 外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装。

### Changed
- なし（初期リリース）

### Fixed
- なし（初期リリース）

### Security
- なし（初期リリース）

### Notes / 設計上の重要点
- ルックアヘッドバイアス防止
  - 多くの分析処理（ニュースウィンドウ、ファクター計算、レジーム判定等）は内部で `date.today()` を参照せず、呼び出し側が `target_date` を明示的に渡す設計によりルックアヘッドバイアスを回避している。
- テスト容易性
  - OpenAI 呼び出し部分は内部関数をパッチ可能に実装しており、ユニットテストで差し替えて検証可能。
  - API キーは関数引数で注入でき、環境依存を減らしている。
- フェイルセーフ
  - 外部 API（OpenAI、J-Quants等）で失敗した場合でも例外を投げずフォールバックするロジックを多用（例: マクロスコア0.0、スコア未取得はスキップ等）。
- DuckDB 互換性考慮
  - executemany に空リストを渡すことへの回避や、DATE 型の扱いに注意した実装など、DuckDB の既知制約に対する対策を含めている。

---

（この CHANGELOG はコードベースから推測して作成したため、実際のリリースノートとして利用する場合はプロジェクトの公式変更点と突き合わせてください。）