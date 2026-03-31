# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

## [0.1.0] - 2026-03-31

初回リリース。日本株自動売買システムのコアライブラリを実装しました。主な追加点は以下のとおりです。

### Added
- パッケージ基本情報
  - kabusys パッケージのバージョンを `0.1.0` として公開（src/kabusys/__init__.py）。
  - パッケージの公開 API として data, strategy, execution, monitoring を __all__ に設定。

- 環境設定/ローディング
  - 環境変数管理モジュールを追加（src/kabusys/config.py）。
    - .env/.env.local ファイル自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - export 形式やクォート、インラインコメントなどに対応した堅牢な .env パーサ実装。
    - 重要設定の取得用 Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。
    - env（development / paper_trading / live）と log_level のバリデーション、便利プロパティ（is_live 等）を実装。
    - データベースパスのデフォルト（DuckDB / SQLite）を設定。

- AI（ニュース NLP / レジーム判定）
  - ai モジュールを追加（src/kabusys/ai/）。
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を基に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）へバッチ送信。
    - JSON Mode を利用したレスポンス処理、最大バッチサイズ、トークン肥大化対策（記事数・文字数制限）を実装。
    - 429/ネットワーク断/タイムアウト/5xx などを対象に指数的バックオフでリトライ。
    - レスポンス検証とスコアの ±1.0 クリップ、部分成功時の安全な DB 書き換えロジック（DELETE→INSERT）を実装。
    - テストしやすいよう _call_openai_api を patch して差し替え可能。
    - calc_news_window(target_date) を提供（JST→UTC のウィンドウ計算）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース（重み 30%）を合成して日次レジーム判定（bull/neutral/bear）を実装。
    - prices_daily / raw_news / market_regime を用いた冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - OpenAI 呼び出しは独立実装（news_nlp と共有しない）で、API エラー時は安全に macro_sentiment=0 にフォールバック。
    - リトライ・バックオフ・JSON パース対策を実装。

- データ関連（Data Platform）
  - data パッケージと ETL 基盤（src/kabusys/data/）
    - pipeline モジュール（src/kabusys/data/pipeline.py）
      - ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラーを保持）。
      - 差分取得・バックフィル、品質チェックのためのユーティリティを実装（内部関数: _table_exists, _get_max_date など）。
      - J-Quants client（jquants_client）と quality モジュールを統合する設計。
    - etl の公開インターフェース（src/kabusys/data/etl.py）で ETLResult を再エクスポート。
    - カレンダー管理モジュール（src/kabusys/data/calendar_management.py）
      - market_calendar を使った営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
      - JPX カレンダーの夜間更新ジョブ calendar_update_job を実装（J-Quants API から差分取得して保存）。
      - DB にデータがない場合は曜日ベースのフォールバック（週末非営業）を採用。
      - 最大探索日数やバックフィル、健全性チェック等の安全策を実装。

- リサーチ（因子計算・特徴量解析）
  - research パッケージ（src/kabusys/research/）
    - factor_research.py
      - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER・ROE）を計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
      - DuckDB を用いた SQL ベースの実装。結果は (date, code) ベースの dict リストで返却。
      - データ不足時の None 扱い、ログ出力等の防御的実装。
    - feature_exploration.py
      - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
      - pandas 等に依存せず標準ライブラリのみで実装。
    - research/__init__.py で主要関数をエクスポート（zscore_normalize は data.stats から）。

### Changed
- N/A（初回リリースのため過去バージョンからの変更はありません）

### Fixed
- N/A（初回リリース）

### Security
- OpenAI API キーは引数経由または環境変数 OPENAI_API_KEY から安全に解決する実装。未設定時は明示的に ValueError を送出して誤使用を防止。

### Notes / 実装上の設計ポリシー・注意点
- ルックアヘッドバイアス回避のため、全てのバッチ/スコアリング関数は内部で datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計です。
- DuckDB を主要ストレージとして想定し、実行時には DuckDB 接続オブジェクト（DuckDBPyConnection）を引数に取る API を多用しています。
- 外部 API 呼び出し（OpenAI / J-Quants）はフェイルセーフを採用し、API エラー時も全体処理が停止しないように設計しています（必要箇所でログ出力・0フォールバック・部分失敗の局所化など）。
- テスト容易性を考慮して、OpenAI 呼び出し箇所は内部関数（_call_openai_api）を patch して差し替え可能にしています。
- DB 書き込みは冪等化（DELETE→INSERT、ON CONFLICT の利用想定）とトランザクション（BEGIN/COMMIT/ROLLBACK）を組み合わせて実装しています。

### Known issues / TODO
- strategy, execution, monitoring モジュールの実装は本リリース範囲外または最小限に留められており、実運用ロジック・オーダー発行部分は今後の実装・レビューが必要です。
- jquants_client および quality モジュール（参照箇所あり）は外部依存であり、環境に応じたモック／実実装の提供が必要です。
- DuckDB のバージョン差異による executemany の空リスト制約など、環境依存の挙動に対する注意（既に対策コードあり）。

---

今後のリリースでは、戦略実行（strategy/execution）や監視（monitoring）の具体的実装、テストケース整備、ドキュメントの充実を予定しています。上記内容で不明点や補足が必要であればお知らせください。