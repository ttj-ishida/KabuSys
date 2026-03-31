# Changelog

すべての注目すべき変更をこのファイルに残します。本プロジェクトは Keep a Changelog に準拠しています。  
バージョン番号は SemVer に従います。

## [Unreleased]

---

## [0.1.0] - 2026-03-31

初回公開リリース。

### Added
- パッケージの基本構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - プロジェクトルート検出: .git または pyproject.toml を起点に探索
    - .env パーサは export 形式、クォート・エスケープ、インラインコメントなどに対応
    - .env 読み込み時に OS 環境変数を保護する機能（protected set）
  - Settings クラスを提供し、各種必須設定をプロパティで取得
    - J-Quants / kabuステーション / Slack / DB パス設定など
    - env（development/paper_trading/live）・log_level のバリデーション
    - duckdb/sqlite のパスは Path オブジェクトとして取得
    - is_live / is_paper / is_dev のユーティリティプロパティ

- AI モジュール（kabusys.ai）
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を用いて銘柄ごとのニュースを集約して OpenAI（gpt-4o-mini）に渡し、銘柄ごとのセンチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む。
    - バッチ処理（最大 20 銘柄/chunk）、記事数と文字数のトリム、JSON Mode レスポンスのバリデーション、スコアのクリッピングを実装。
    - リトライ戦略: 429/ネットワーク断/タイムアウト/5xx に対して指数バックオフでリトライ。
    - API 呼び出しはテスト容易性のため _call_openai_api を用意し、テストで差し替え可能。
    - DuckDB の executemany の互換性に配慮し、空リストバインドのハンドリングを実装。
    - 関数:
      - calc_news_window(target_date) — ニュース収集ウィンドウ計算（JST->UTC 変換を含む）
      - score_news(conn, target_date, api_key=None) — スコア生成メイン処理
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）判定。
    - OpenAI（gpt-4o-mini）を用いたマクロセンチメント評価（JSON 出力期待）。
    - API 呼び出しに対する堅牢なリトライ・フェイルセーフ（API 失敗時は macro_sentiment=0.0 で継続）。
    - DuckDB へ冪等的に書き込むトランザクション処理（BEGIN/DELETE/INSERT/COMMIT、エラー時は ROLLBACK を試行）。
    - 関数:
      - score_regime(conn, target_date, api_key=None) — レジームスコア計算と保存

- データプラットフォーム（kabusys.data）
  - ETL パイプライン (kabusys.data.pipeline)
    - 差分取得、保存（jquants_client の save_* を利用して冪等保存）、品質チェック呼び出しの土台を実装。
    - ETL 実行結果を格納するデータクラス ETLResult を提供（kabusys.data.etl で再エクスポート）。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを提供。
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった営業日判定 API を実装。
    - DB（market_calendar）にデータがある場合は DB を優先。未登録の日は曜日（土日）ベースのフォールバックを行うことで DB がまばらでも一貫した判定を提供。
    - calendar_update_job により J-Quants API から差分取得して market_calendar を冪等更新。バックフィルと健全性チェックを実装。
    - 最大探索範囲やバックフィル等の定数を定義して安全性を確保。
  - jquants_client 経由での外部 API との連携を想定（詳細実装は client モジュールに依存）。

- リサーチ／ファクター計算（kabusys.research）
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum(conn, target_date)
      - 1M/3M/6M リターンおよび 200 日 MA 乖離を計算。データ不足時は None を返す。
    - calc_volatility(conn, target_date)
      - 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比などを計算。データ不足時は None を返す。
    - calc_value(conn, target_date)
      - raw_financials から最新財務を取得して PER, ROE を計算（EPS が 0/欠損なら PER は None）。
    - すべて DuckDB と prices_daily/raw_financials テーブルのみを参照する設計（外部 API へはアクセスしない）。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns(conn, target_date, horizons=None) — 将来リターン計算（デフォルト: 1,5,21 営業日）
    - calc_ic(factor_records, forward_records, factor_col, return_col) — スピアマンランク相関による IC 計算（ランクは平均ランクを採用）
    - rank(values) — 同順位は平均ランクで扱うランク変換ユーティリティ（丸めによる ties 対策あり）
    - factor_summary(records, columns) — 基本統計量（count/mean/std/min/max/median）を計算
    - research パッケージは zscore_normalize（kabusys.data.stats）を re-export

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / 設計上の重要ポイント
- ルックアヘッドバイアス対策
  - AI スコアリングやレジーム判定、ファクター計算は内部で datetime.today() / date.today() を直接参照せず、必ず外部から与えられた target_date を基準に処理を行う設計になっています。
  - DB クエリにも「date < target_date」や半開区間を用いる等のルックアヘッド回避の工夫を実施しています。
- フェイルセーフ動作
  - 外部 API（OpenAI / J-Quants 等）呼び出しで問題が発生した場合、致命的に停止させずログ出力してフォールバック値（例: macro_sentiment=0.0）で継続する設計が多く採用されています。
- テスト容易性
  - OpenAI 呼び出し箇所は _call_openai_api のようなラッパーを用意しており、unittest.mock.patch による差し替えが可能です。
- DuckDB 互換性
  - executemany に空リストを渡せない古い DuckDB バージョンを考慮したガードを実装しています。
  - 日付値の取り扱いにおいては date オブジェクトで統一し、文字列からの変換処理を慎重に行っています。
- ロギングとトランザクション
  - DB 書き込みは冪等性を意識（DELETE → INSERT 等）しており、例外時は ROLLBACK を試行してログ出力します。

### Breaking Changes
- 初回リリースのため、過去の互換性に関する変更はありません。

---

今後のリリースでは、strategy / execution / monitoring 周りの実装公開、より詳細な品質チェックモジュール、テストカバレッジの強化、外部クライアントの抽象化などを予定しています。