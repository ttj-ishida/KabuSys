# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従っています。  

- 形式: YYYY-MM-DD
- 節: Added / Changed / Deprecated / Removed / Fixed / Security

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-31
初回リリース。日本株自動売買システムのコアライブラリを実装しました。主な追加点をモジュール別にまとめます。

### Added
- パッケージ基盤
  - パッケージのメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - 公開サブパッケージ: data, strategy, execution, monitoring（__all__ に登録）。

- 環境設定 / config
  - .env ファイルと OS 環境変数の自動読み込み機能を実装。
    - プロジェクトルートは .git または pyproject.toml を起点に探索し決定（CWD 非依存）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 優先順位: OS 環境変数 > .env.local > .env。.env.local は既存値を上書き。
  - .env パース実装を強化:
    - export KEY=val 形式に対応、シングル／ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い改善。
  - 環境値取得ユーティリティ Settings を追加:
    - J-Quants / kabuステーション / Slack / DB / 監視設定 / システム設定など主要プロパティを提供。
    - 必須キー未設定時は明示的な ValueError を投げる _require を実装。
    - KABUSYS_ENV や LOG_LEVEL の値検証、is_live / is_paper / is_dev の便宜プロパティを提供。
    - Path や float 変換等のデフォルト値と展開を実装（例: DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH）。

- AI モジュール（kabusys.ai）
  - ニュース NLP（news_nlp.py）
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols から記事を集約し、OpenAI（gpt-4o-mini, JSON mode）で銘柄ごとのセンチメント ai_score を算出して ai_scores テーブルへ書き込み。
    - タイムウィンドウ計算 calc_news_window（JST ベースで前日 15:00 ～ 当日 08:30 の UTC 変換）を提供。
    - バッチ処理: 最大 _BATCH_SIZE=20 銘柄単位で API コール。
    - テキスト長トリム、1 銘柄あたり _MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK による肥大化対策。
    - 再試行（429, ネットワーク断, タイムアウト, 5xx）→ 指数バックオフ実装。
    - レスポンスの堅牢なバリデーションと JSON 抽出、スコアの ±1.0 クリップ。
    - DuckDB 互換性考慮: executemany に空リストを与えない等の防御コード。
    - API キーは引数または環境変数 OPENAI_API_KEY で指定。未指定時は ValueError。
    - フェイルセーフ: API 失敗時は該当チャンクをスキップし、全体処理を継続（例外を抑制してログ出力）。
  - マーケットレジーム判定（regime_detector.py）
    - score_regime(conn, target_date, api_key=None): ETF 1321（日経225連動）の 200 日移動平均乖離とマクロニュースセンチメント（LLM）を合成して market_regime テーブルへ冪等書き込み。
    - ma200_ratio 計算（_calc_ma200_ratio）は target_date 未満のデータのみを使用してルックアヘッドを防止。
    - マクロニュース抽出（_fetch_macro_news）はキーワードマッチで最大記事数を取得。
    - LLM 呼び出し（_score_macro）は再試行/バックオフ、API の 5xx の扱い、JSON パースエラーに対するフォールバック（macro_sentiment=0.0）を実装。
    - レジームスコア合成重み: MA (70%) / マクロ (30%)、閾値で bull/neutral/bear を決定。
    - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等パターン、失敗時は ROLLBACK を試行して例外を伝播。

- Research モジュール（kabusys.research）
  - factor_research.py
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200 日 MA 乖離(ma200_dev) を計算。
    - calc_volatility(conn, target_date): 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value(conn, target_date): raw_financials から最新財務を取得して PER, ROE を計算（EPS が 0/NULL の場合は None）。
    - SQL ベースの実装で DuckDB ウィンドウ関数等を活用。データ不足時は None を返す仕様。
  - feature_exploration.py
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（任意ホライズン）をまとめて取得。horizons の妥当性チェックあり。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を計算。データ不足（有効レコード数 < 3）では None を返す。
    - rank(values): 同順位は平均ランクとするランク化ユーティリティ（浮動小数の丸め対策あり）。
    - factor_summary(records, columns): count/mean/std/min/max/median を標準ライブラリで計算。
    - すべての関数は DB 読み取りに限定し、発注系等の副作用なし。

- Data モジュール（kabusys.data）
  - calendar_management.py
    - 市場カレンダー管理機能を実装:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
      - market_calendar テーブルが存在する場合は DB 優先、未登録日は曜日ベースでフォールバック。
      - next/prev は最大探索日数制限を導入して無限ループ回避。
    - calendar_update_job(conn, lookahead_days): J-Quants API から差分取得し market_calendar を冪等更新。バックフィル・健全性チェックを実装。
  - ETL / pipeline（etl.py, pipeline.py）
    - ETLResult データクラスを実装して ETL 実行結果を収集・シリアライズ可能に（品質問題やエラーの一覧を保持）。
    - pipeline モジュールの ETLResult をデータ公開インターフェースとして再エクスポート。
    - pipeline モジュール内で差分更新・保存（idempotent）、品質チェックの基本設計を実装（モジュール全体の設計方針を明記）。
    - DuckDB のテーブル存在チェックや最大日付取得等のユーティリティを実装（互換性と堅牢性を重視）。

- 共通設計上の注意点（ドキュメント・コード内コメント）
  - ルックアヘッドバイアス防止のため、各処理は datetime.today()/date.today() への直接依存を避け、引数で基準日を受け取る設計。
  - API 呼び出しはフェイルセーフ（失敗時はゼロやスキップして継続）とし、重要な DB 書き込みはトランザクションで保護。
  - OpenAI 呼び出しは JSON Mode を利用、レスポンスパースの堅牢化（余分な前後テキストの復元処理等）を実装。
  - DuckDB 互換性に配慮した実装（executemany の空配列回避など）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- 初版では機密情報（API キー等）は環境変数経由で取得する設計。自動 .env ロードは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

注:
- ここに記載した変更点は、ソースコード内の docstring・コメント・実装から推測してまとめたものです。実際のリリースノートとして使用する場合は、必要に応じて日付やバージョン、影響範囲を正確に補完してください。