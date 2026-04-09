CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（未リリースの変更はここに記載します）

[0.1.0] - 2026-04-09
-------------------

初回リリース。日本株自動売買プラットフォームのコアライブラリを実装しました。主要な機能群、設計方針、フェイルセーフ、外部サービスとの統合などを含みます。

Added
- パッケージ基盤
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。
  - トップレベルモジュールエクスポート: data, strategy, execution, monitoring。

- 環境変数 / 設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に検出）。
  - 読み込み順序: OS 環境 > .env.local（上書き）> .env（未設定時のみ）。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサーの堅牢化: export 形式、引用符内のエスケープ、インラインコメントの扱いに対応。
  - Settings クラスを提供し、主要設定プロパティを型付きで公開（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, DUCKDB_PATH, 各種閾値など）。
  - 環境値の検証: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等の有効値チェックを追加。
  - 用途に応じたパス設定（pid / kill flag / DB パス等）と paper trading 用設定の提供。

- ニュースNLP（自然言語処理） (kabusys.ai.news_nlp)
  - raw_news と news_symbols を元に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON mode でセンチメントを算出。
  - タイムウィンドウ定義（JST 前日15:00 〜 当日08:30、内部は UTC naive datetime で扱う）。
  - バッチ処理（最大 20 銘柄/リクエスト）、記事数・文字数上限でトリミング（上限: 10 件 / 3000 文字）。
  - 再試行ロジック: 429、ネットワーク断、タイムアウト、5xx に対する指数バックオフでのリトライ。
  - レスポンス検証: JSON 抽出、results 配列、code/score の型・既知コードチェック、スコアの有限性チェック、±1.0 でクリップ。
  - 部分成功に対応した DB 書き込み: 取得済みコードのみ DELETE → INSERT（DuckDB executemany の空リスト考慮）。
  - テスト可能性を考慮し、内部の OpenAI 呼び出し関数をパッチ可能に実装（unittest.mock による差し替えを想定）。

- 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321（日経225 連動）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull / neutral / bear）を算出。
  - マクロニュース抽出のためのキーワード群を定義し、raw_news からタイトルを取得。
  - OpenAI （gpt-4o-mini）を用いたマクロセンチメント算出。API エラー時は macro_sentiment = 0.0 にフォールバック。
  - レジーム値はクリップされ閾値によりラベル化、DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
  - ルックアヘッドバイアス対策: target_date 未満のデータのみ参照、datetime.today() を内部で参照しない設計。

- リサーチ / ファクター計算 (kabusys.research)
  - ファクター計算モジュール: モメンタム（1M/3M/6M リターン、ma200乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性（20日平均売買代金・出来高比）、バリュー（PER、ROE）を実装。
  - forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で計算。horizons の入力検証あり。
  - IC（Information Coefficient）計算: スピアマンランク相関（ランク化は同順位平均ランク処理を実装）。
  - 統計サマリー: count/mean/std/min/max/median を計算するユーティリティ。
  - zscore_normalize を data.stats から再エクスポート。
  - すべて DuckDB に対する SQL / 標準ライブラリのみで実装（外部依存を最小化）。

- データプラットフォーム (kabusys.data)
  - マーケットカレンダー管理: market_calendar を元に営業日判定ロジックを提供。
    - 関数: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB データが無い／未登録日の場合は曜日ベースのフォールバック（土日を非営業日扱い）。
    - 最大探索日数制限を設け、安全性確保。
    - calendar_update_job: J-Quants クライアントを用いた差分取得と保存処理（バックフィルや健全性チェックを実装）。
  - ETL パイプライン基盤:
    - ETLResult dataclass を定義し、取得件数・保存件数・品質問題リスト・エラーリスト等を保持。
    - 差分取得、バックフィル、品質チェック（quality モジュール連携）を想定した設計。
    - jquants_client 経由での保存は冪等化（ON CONFLICT / upsert）を想定。

- 外部 API 統合
  - OpenAI（gpt-4o-mini）を JSON mode で利用する実装を複数箇所で採用（news_nlp, regime_detector）。テスト用に呼び出し関数を差し替え可能。
  - DuckDB をデータストアとして標準的に利用。
  - J-Quants クライアントとの連携点（カレンダー・ETL）を用意。

- 運用 / 監視向け設定
  - PID ファイル、kill flag、CPU / メモリ / ディスク閾値など監視用設定を Settings で公開。
  - Paper Trading 用の設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）を提供。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- API キー取り扱い:
  - OpenAI API キーは関数引数で注入可能（テスト容易化）かつ、引数未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出し明示的に失敗する設計。
  - .env の自動読み込みはプロジェクトルート検出に基づき行われ、意図しないディレクトリでの読み込みを回避。必要に応じ自動読み込みを無効化可能。

公開された主なパブリック API（抜粋）
- kabusys.settings (Settings インスタンス)
- kabusys.ai.score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- kabusys.data.calendar_management:
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day, calendar_update_job
- kabusys.data.ETLResult（kabusys.data.pipeline からの再エクスポート）
- kabusys.research:
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize（再エクスポート）

Notes / 今後の課題（今後のリリースで対応予定）
- strategy / execution / monitoring の詳細実装（今回のコードベースではエクスポートされているが、該当モジュールの完全実装は継続作業）。
- OpenAI 呼び出しのコスト最適化・リクエスト並列化設計の改善。
- DuckDB スキーマ定義とマイグレーションツールの明示化。
- より詳細なテストカバレッジ（特に API フェイルオーバーと部分失敗時の DB 書き込み挙動）。

お問い合わせ / 貢献
- バグ報告や機能要望は issue を立ててください。パッチは Pull Request で歓迎します。