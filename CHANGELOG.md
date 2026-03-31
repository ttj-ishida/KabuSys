# Changelog

すべての重要な変更点を Keep a Changelog 準拠で記載します。

フォーマット:
- すべての変更は日付付きリリース単位で記載しています。
- カテゴリは Added / Changed / Fixed / Security を使用しています。

## [0.1.0] - 2026-03-31

初回公開リリース。

### Added
- パッケージ基盤
  - パッケージ名: kabusys。トップレベルで data, strategy, execution, monitoring をエクスポート。
  - バージョン情報: __version__ = "0.1.0" を追加。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードの無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` でスキップ可能。
    - プロジェクトルートは __file__ を基点に `.git` または `pyproject.toml` で検出（CWD に依存しない）。
  - .env パーサ実装（クォート・エスケープ・インラインコメント対応、`export KEY=val` にも対応）。
  - 上書きポリシー: override / protected オプションで既存 OS 環境変数を保護。
  - Settings クラスを提供し、アプリ設定をプロパティで取得可能:
    - J-Quants / kabu API / Slack トークン・チャンネル / DB パス（DuckDB/SQLite）等。
    - KABUSYS_ENV 値チェック（development / paper_trading / live）。
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。
  - 必須値未設定時は明確な ValueError を発生させる `_require` 実装。

- AI（ニュース NLP / レジーム判定）
  - kabusys.ai.news_nlp
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを評価。
    - バッチ処理（1 API 呼び出しで最大 20 銘柄）、1 銘柄あたり記事数・文字数上限を設定（トークン肥大化対策）。
    - 429・接続断・タイムアウト・5xx に対する指数バックオフリトライ実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results リスト、code/score 検証）。
    - スコアは ±1.0 にクリップ。部分失敗に備えて対象コードのみ DELETE → INSERT を実行（冪等性確保、部分失敗で既存データ保護）。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（unittest.mock.patch でのモック想定）。
    - 公開関数: score_news(conn, target_date, api_key=None)（書き込み銘柄数を返す）。
    - タイムウィンドウ計算ユーティリティ: calc_news_window(target_date)。

  - kabusys.ai.regime_detector
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組み合わせて日次市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは kabusys.ai.news_nlp の window 計算を利用して取得し、OpenAI（gpt-4o-mini）で macro_sentiment を算出。
    - LLM 呼び出しは再試行・バックオフを備え、失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - レジームスコアはクリップ処理および閾値判定を実施し、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - 公開関数: score_regime(conn, target_date, api_key=None)。

- Data モジュール
  - kabusys.data.calendar_management
    - JPX マーケットカレンダーを扱うユーティリティを実装。
    - 営業日判定/is_sq_day/next_trading_day/prev_trading_day/get_trading_days を提供。
    - market_calendar が未取得または未登録日の扱いとして曜日ベースのフォールバック実装（週末を非営業日扱い）。
    - 最大探索日数上限（_MAX_SEARCH_DAYS）で無限ループを防止。
    - calendar_update_job(conn, lookahead_days=90)：J-Quants API から差分取得して market_calendar を冪等に更新。バックフィル・健全性チェック実装。

  - kabusys.data.pipeline / etl
    - ETL パイプラインの骨組みを実装。
    - ETLResult dataclass を導入（取得数・保存数・品質チェック・エラー情報を含む）。
    - 差分更新・バックフィル方針・品質チェックの収集設計（Fail-Fast ではなく全件収集）を反映。
    - DuckDB 互換性考慮（テーブル存在チェック、executemany の空リスト回避など）。

- Research モジュール（特徴量・ファクター）
  - kabusys.research.factor_research
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、ATR（20 日）、20 日平均売買代金、出来高比率、PER/ROE（raw_financials から）を計算する関数群を実装。
    - calc_momentum(conn, target_date)、calc_volatility(conn, target_date)、calc_value(conn, target_date) を提供。
    - データ不足時の None ハンドリング、DuckDB を用いたウィンドウ集計の実装。

  - kabusys.research.feature_exploration
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=None)（複数ホライズンに対応）。
    - IC（Information Coefficient）計算: calc_ic(factor_records, forward_records, factor_col, return_col)（Spearman の ρ、rank ユーティリティあり）。
    - ファクター統計サマリー: factor_summary(records, columns)（count/mean/std/min/max/median）。
    - 軽量実装: pandas 等外部依存を持たない純粋 Python 実装。

### Changed
- 設計ポリシー（全体）
  - すべての分析処理で datetime.today() / date.today() を参照しない方針を採用（ルックアヘッドバイアス防止）。呼び出し側が target_date を明示的に渡す設計。
  - OpenAI 呼出周りはニュースモジュール間でプライベート実装を共有しない（モジュール結合を避けるため _call_openai_api を各モジュールで独自実装）。
  - DB 書き込みは可能な限り冪等操作（DELETE→INSERT / ON CONFLICT 的扱い）を採用し、部分失敗時のデータ保護に配慮。

### Fixed
- N/A（初回リリースのため既知のバグ修正は無し。設計上の堅牢性措置（入力検証・例外処理・フォールバック）を充実させています）

### Security
- 機密情報の扱いに関する注意:
  - API キー・トークンは Settings 経由で環境変数から取得。必須パラメータ未設定時に明示的にエラーを出すことで誤動作を防止。
  - .env 自動読み込みは環境変数で無効化可能（テスト・CI 用に配慮）。

---

開発チームへ:
- 将来的に CHANGELOG を自動生成するため、コミットメッセージや PR テンプレートで「何が追加/変更/修正されたか」を明示的に記載してください。
- API の安定化（公開関数シグネチャや Settings のプロパティ）を図る際はメジャー/マイナーのポリシーに従ってバージョニングしてください。