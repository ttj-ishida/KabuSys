Keep a Changelog に準拠した CHANGELOG.md

注: 以下は提供されたコード内容から推測して作成した変更履歴です。実際のコミット履歴ではなく、実装された主要機能・設計上の注記をリリース向けに要約しています。

All notable changes to this project will be documented in this file.

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
---------
- （なし）

[0.1.0] - 2026-03-31
--------------------
Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージルート: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

- 環境設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする機能を実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env ファイルパーサ実装:
    - コメント行・export プレフィックス対応、シングル/ダブルクォート内のエスケープを考慮した値パース。
    - インラインコメントの取り扱い（クォートあり/なしでの扱い差分）。
  - Settings クラスを提供（settings インスタンス経由）:
    - J-Quants / kabu ステーション / Slack / データベースパス / 監視閾値 / システム設定などをプロパティとして取得。
    - 必須環境変数については _require() により未設定時は ValueError を投げる。
    - KABUSYS_ENV と LOG_LEVEL の入力検証を実施（許容値チェック）。
    - デフォルト値: KABUS_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH 等を用意。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - raw_news と news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメントスコアを取得。
    - バッチサイズ、最大記事数・文字数トリム、指数バックオフによるリトライ（429・接続エラー・タイムアウト・5xx 対応）。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、型チェック、未知コード無視、スコアの ±1.0 クリップ）。
    - スコア書き込みは部分置換方式（該当 code の DELETE → INSERT）で冪等性を確保し、部分失敗時に他コードの既存スコアを保護。
    - テスト容易性のため OpenAI 呼び出し箇所は差し替え可能な private 関数設計（unittest.mock.patch が想定可能）。
    - ルックアヘッドバイアス対策: datetime.today()/date.today() を直接参照しない設計（target_date を引数で受け取る）。
    - デフォルトのニュース収集ウィンドウ（JST ベース）を calc_news_window 関数で提供（前日 15:00 ～ 当日 08:30 JST を UTC に変換して扱う）。

  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（日経225 連動）に対する 200 日移動平均乖離（重み 70%）と、マクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム（bull / neutral / bear）を決定。
    - LLM には gpt-4o-mini を使用（JSON 出力指定）。APIエラー時は macro_sentiment=0.0 としてフォールバック。
    - DuckDB を用いた ma200_ratio の計算（target_date 未満データのみ使用）と、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。書き込み失敗時は ROLLBACK を試行。
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。
    - ログ出力、リトライ・バックオフ、500 系の扱いなど堅牢な実装。

- データプラットフォーム (kabusys.data)
  - カレンダー管理 (calendar_management)
    - market_calendar テーブルを基に営業日判定のユーティリティを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にデータがない場合は曜日ベースでフォールバック（週末は非営業日）。DB が部分的にしかない場合でも一貫した結果を返す工夫あり。
    - JPX カレンダーを J-Quants から差分取得して market_calendar を更新する夜間バッチ job (calendar_update_job) を実装。バックフィル／健全性チェック（未来日異常検出）あり。
    - 探索の上限 (_MAX_SEARCH_DAYS) を設け無限ループを防止。

  - ETL パイプライン (pipeline.ETLResult / etl)
    - ETL 実行結果を格納する dataclass ETLResult を提供（取得数・保存数・品質チェック結果・エラー一覧を保持）。
    - ETL 実装方針: 差分更新、idempotent な保存、品質チェックは収集して呼び出し元に委ねる（Fail-Fast ではない）、id_token 注入でテスト容易性。
    - etl モジュール経由で ETLResult を再エクスポート。

- Research 用ユーティリティ (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、ma200_dev）、ボラティリティ（20日 ATR、相対ATR、平均売買代金、出来高比）、Value（PER、ROE）を DuckDB を用いた SQL/Python ハイブリッドで計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 扱いや、計算窓のバッファリングを実装。
  - feature_exploration:
    - 将来リターン計算 calc_forward_returns（任意ホライズン、ホライズン検証）、IC（Spearman ランク相関）計算 calc_ic、ランク関数 rank、統計サマリー factor_summary を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。
  - 研究ユーティリティ群を __init__ でまとめて公開。

Changed
- 初回リリースのため変更履歴はなし。

Fixed
- 初回リリースのため修正履歴はなし。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーは引数注入または環境変数 OPENAI_API_KEY を使用。キーの取り扱いは呼び出し元で安全に管理すること（本コードはキー管理機構を提供しない）。

Notes / 実装上の重要な設計事項（使用者向け）
- ルックアヘッドバイアス対策:
  - 主要なスコアリング/判定関数は target_date を引数で受け取り、内部で date.today()/datetime.today() を参照しない設計。
- フェイルセーフ:
  - OpenAI 呼び出し失敗時は例外で停止させず、スコアを 0.0 にフォールバックしたり処理をスキップして継続する方針（ログで警告しつつ安全側に倒す）。
- テスト容易性:
  - OpenAI 呼び出しをラップする private 関数を用意しており、ユニットテスト時は patch による差し替えが可能。
- DuckDB 互換性:
  - executemany に空リストを渡せない等の挙動を考慮して実装（空チェックを明示）。
- 環境設定:
  - .env と .env.local の読込順は OS 環境変数 > .env.local > .env（.env.local は既存の OS 環境変数を保護する設計）。
  - 保護された OS 環境変数は自動上書きされない（protected set を導入）。

既知の制約 / 今後の改善候補
- ニュース/マクロ判定では gpt-4o-mini（JSON mode）を想定しているため、将来的なモデル変更や SDK 仕様変更に対応するための抽象化が改善候補。
- jquants_client 周りは本コードでは外部モジュール（kabusys.data.jquants_client）を利用する前提。実行環境側で実装/認証が必要。
- DuckDB スキーマ（テーブル定義）や外部依存（OpenAI, J-Quants, kabu API）に関するドキュメントは別途必要。

Contact
- 実装に関する質問や修正提案はリポジトリの issue にお願いします。