# Changelog

すべての注目すべき変更点はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]
### Added
- —（現時点では未リリースの変更はありません）—

---

## [0.1.0] - 2026-03-27
初期リリース。日本株自動売買システムのコアライブラリを提供します。主要なモジュールと実装方針は以下の通りです。

### Added
- パッケージ初期化
  - パッケージ名: kabusys
  - __version__ = "0.1.0"
  - main export: data, strategy, execution, monitoring を __all__ として公開。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダ実装。
    - プロジェクトルート検出は __file__ を基準に親ディレクトリを探索（.git または pyproject.toml を検出）。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env（.env.local は上書き）。
    - OS 環境変数は protected として上書きを回避。
  - .env 行パーサ: export プレフィックス、クォート、バックスラッシュエスケープ、インラインコメントの取り扱い等に対応。
  - Settings クラスを提供:
    - J-Quants / kabuステーション / Slack / DB パスなど多数のプロパティ（必須 env の検査を含む）。
    - KABUSYS_ENV / LOG_LEVEL の値検証 (許容値チェック)。
    - is_live / is_paper / is_dev のヘルパ。

- AI モジュール (kabusys.ai)
  - ニュース NLP (kabusys.ai.news_nlp)
    - score_news(conn, target_date, api_key=None)
      - 前日15:00 JST ～ 当日08:30 JST のニュースウィンドウを計算する calc_news_window を実装。
      - raw_news と news_symbols から銘柄ごとに記事を集約（最大記事数・文字数でトリム）。
      - 最大 _BATCH_SIZE（20）銘柄ずつ OpenAI (gpt-4o-mini) へバッチ送信し、JSON Mode レスポンスをパースして ai_scores テーブルへ idempotent に書き込み（DELETE→INSERT）。
      - 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ、その他エラーはスキップして継続するフェイルセーフ挙動。
      - レスポンスのバリデーションを厳密に実施（results リスト・code の検証・数値化・クリップ）。
      - テスト容易性のため _call_openai_api を patch で差し替え可能。
      - duckdb.executemany の空リスト制約に配慮して空チェックを行ってから実行。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - score_regime(conn, target_date, api_key=None)
      - ETF 1321 の直近200日データから ma200_ratio を計算（ルックアヘッド防止: date < target_date の排他条件）。
      - マクロ経済ニュースをキーワードで抽出し（_MACRO_KEYWORDS）、OpenAI によりマクロセンチメント（-1〜1）を評価（記事が無ければ LLM コールは行わず 0.0 を返す）。
      - レジームスコアを ma200 成分 (70%) + macro 成分 (30%) で合成しクリップ、閾値により bull/neutral/bear を決定。
      - DB への書き込みは冪等（BEGIN/DELETE/INSERT/COMMIT）かつ失敗時はROLLBACK の上例外を伝播。
      - API 呼び出しのリトライ・エラー処理、JSON パース耐性、フェイルセーフのデフォルトを実装。

- データ管理 (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダー管理ロジック（market_calendar テーブルを前提）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB にデータがない場合は曜日ベースのフォールバック（平日を営業日）を採用。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存。バックフィル、健全性チェックを実装。
  - ETL パイプライン (kabusys.data.pipeline / kabusys.data.etl)
    - ETLResult dataclass を定義して ETL の取得数・保存数・品質問題・エラーを集約可能に。
    - 差分更新（最終取得日算出）・backfill・品質チェックの設計方針を実装（jquants_client 経由での取得・保存を想定）。
    - 内部ユーティリティ: テーブル存在確認、日付最大値取得など。
  - pipeline の型を etl モジュールで再エクスポート（ETLResult）。

- 研究用モジュール (kabusys.research)
  - factor_research
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200日 MA 乖離 (ma200_dev)。
    - calc_volatility(conn, target_date): 20日 ATR、ATR 比率、20日平均売買代金、出来高比率。
    - calc_value(conn, target_date): PER（EPS が無効なら None）、ROE（raw_financials から最新の財務データを参照）。
    - DuckDB SQL を多用し、営業日ベースでの窓処理を実装。データ不足時は None を返す方針。
  - feature_exploration
    - calc_forward_returns(conn, target_date, horizons=None): 指定ホライズンに対する将来リターンを一括で取得（LEAD を利用）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）を実装（結合・除外・ties対策を含む）。
    - rank(values): 同順位は平均ランクを返すランク変換ユーティリティ（丸めによる ties 検出漏れ防止）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する統計サマリ。

### Changed
- （初期リリースのため過去バージョンからの変更は無し）

### Fixed
- （初期リリースのため過去バージョンからの修正は無し）

### Security
- OpenAI API キーは引数注入または環境変数 OPENAI_API_KEY で解決。未設定時は明示的な ValueError を発生させることにより誤使用を防止。

### Notes / 設計上の重要点
- ルックアヘッドバイアス回避:
  - 各モジュール（news_nlp, regime_detector, research 等）は datetime.today() / date.today() を直接参照しない設計。処理は明示的な target_date に依存。
- フェイルセーフ:
  - 外部 API エラー時は必要に応じて 0.0 やスキップで継続する設計（システム全体の停止を避ける）。
- テスト容易性:
  - OpenAI 呼び出し部分は内部関数として切り出してあり、unit test にて patch 可能。
  - api_key を引数で渡せるため環境依存を減らしてテスト可能。
- DuckDB 互換性:
  - executemany に空リストを渡せない制約を回避するチェックを実装。
  - DuckDB の日付型取り扱いや情報スキーマへのクエリに配慮。

---

今後のリリース案（例）
- strategy / execution / monitoring の具体実装（現在はパッケージ export が定義されているのみ）
- J-Quants / kabu API クライアントの詳細実装と統合テスト
- Slack 通知・モニタリング機能の追加
- 追加のファクター・モデル評価 (backtest 統合) 

（この CHANGELOG はコードベースの内容から推測して作成しています。実際の変更履歴やリリース日付はプロジェクト実情に合わせて調整してください。）