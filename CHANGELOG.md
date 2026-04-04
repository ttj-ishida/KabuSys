# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

## [0.1.0] - 2026-04-04

### Added
- パッケージ初回リリース。
- 基本パッケージ公開情報
  - kabusys.__version__ = "0.1.0"
  - パッケージのトップレベル __all__ に data, strategy, execution, monitoring を公開。

- 環境変数・設定管理（kabusys.config）
  - .env ファイルと環境変数の自動読み込み機能を実装（読み込み優先順位: OS 環境変数 > .env.local > .env）。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサは export KEY=val 形式やシングル/ダブルクォート内のエスケープ、インラインコメントの扱い等に対応。
  - .env 読み込み時の上書き制御（override）と OS 環境変数を保護する protected キー群をサポート。
  - Settings クラスを提供し、アプリケーション設定をプロパティとして取得可能。
    - J-Quants / kabu API / LINE / DB パス / 監視閾値 等のプロパティを実装。
    - KABUSYS_ENV の許容値バリデーション（development, paper_trading, live）。
    - LOG_LEVEL の許容値バリデーション（DEBUG, INFO, WARNING, ERROR, CRITICAL）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- AI モジュール（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して、銘柄ごとのニューステキストを OpenAI（gpt-4o-mini）でセンチメント評価。
    - タイムウィンドウ計算（JST 基準: 前日 15:00 ～ 当日 08:30、内部は UTC naive datetime で扱う）。
    - バッチ送信（最大 20 銘柄 / バッチ）、1 銘柄あたりの記事トリム（最大件数/最大文字数）を実装。
    - API 呼び出しでのリトライ（429・ネットワーク断・タイムアウト・5xx に対して指数バックオフ）、レスポンスのバリデーションとスコアの ±1.0 クリップ。
    - DuckDB への書き込みは部分失敗を避けるため、取得済みコードのみ DELETE→INSERT で置換。executemany に空リストを渡さない安全処理を実装。
    - テスト用に _call_openai_api を patch できる設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio 計算、マクロキーワードによるニュース抽出、OpenAI（gpt-4o-mini）呼び出し、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API 失敗時はマクロセンチメントを 0.0 にフォールバックするフェイルセーフ。
    - OpenAI 呼び出しは専用関数化し、モジュール間で内部関数を共有しない設計（結合度低減）。
    - リトライロジックと 5xx 判定、JSON パースの安全処理を実装。

- データプラットフォーム関連（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを使った営業日判定ロジックを提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した振る舞いを実装。
    - カレンダー夜間バッチ更新 job（calendar_update_job）を実装。J-Quants クライアント経由で差分取得→冪等保存（ON CONFLICT 相当）し、バックフィルや健全性チェックを含む。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - 差分更新、バックフィル、品質チェックの設計方針を反映した基盤実装（定数: _MIN_DATA_DATE, _CALENDAR_LOOKAHEAD_DAYS, _DEFAULT_BACKFILL_DAYS 等）。
    - DuckDB テーブル存在チェックや最大日付取得などのユーティリティを実装。
    - 品質チェック（quality モジュール）との連携を想定したエラー/警告の集約設計。

- 研究/リサーチ機能（kabusys.research）
  - factor_research:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE の算出）等のファクター計算関数を実装。
    - DuckDB を使った SQL 主導の実装で、ルックアヘッドバイアスを避ける設計（target_date 未満/以下の扱い等）。
    - データ不足時の None 処理やロギングを実装。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient, スピアマン ρ）計算、rank 関数、factor_summary（統計サマリー）を実装。
    - rank は同順位の平均ランク処理を実装し、浮動小数丸めで ties 検出漏れを防止。

- ロギング / エラーハンドリング
  - 各モジュールで詳細な logger 呼び出しを追加（info/debug/warning/exception）。
  - DB 書き込み時は BEGIN/DELETE/INSERT/COMMIT と ROLLBACK で安全に処理し、ROLLBACK に失敗した場合も警告ログを出力して上位へ例外を伝播する実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数で注入可能（api_key 引数）かつ環境変数 OPENAI_API_KEY を参照。キー未設定時は ValueError を送出して明示的な扱いとする。

### Notes / 設計上の重要点
- ルックアヘッドバイアス抑制: ほぼ全ての処理で datetime.today() / date.today() を直接参照せず、外部から target_date を与える方式を採用。
- テスト容易性: OpenAI 呼び出し関数はモック差し替え可能な作りにしてある（ユニットテストでの差し替えを想定）。
- DuckDB の互換性配慮: executemany に空リストを渡さない等、DuckDB の既知制約への対応を各所に実装。

（今後のリリースでは変更点をカテゴリ別に追記します。）