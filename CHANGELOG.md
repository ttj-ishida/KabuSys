CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （なし）

0.1.0 - 2026-03-29
------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
- パッケージ公開情報
  - src/kabusys/__init__.py に __version__ = "0.1.0"、および主要サブパッケージを __all__ で公開。
- 環境設定管理
  - src/kabusys/config.py
    - .env/.env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。
    - export 付き行、クォート／エスケープ、インラインコメントの扱いに対応するパーサ実装。
    - OS 環境変数を保護する protected 上書き制御、override フラグ対応。
    - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / ログレベル 等の設定プロパティを型付きに取得。入力値検証（env 値・ログレベル・KABUSYS_ENV の検証）を実装。
    - デフォルト値（KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL 等）を設定。
- AI（ニュース・レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を集約して銘柄ごとのテキストを作成し、OpenAI（gpt-4o-mini）にバッチ送信してセンチメント（ai_score）を算出。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を行う calc_news_window を提供。
    - バッチサイズ、記事・文字数の上限、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスの堅牢なバリデーション（JSON 抽出・スキーマチェック・スコアの数値検査）を実装。
    - DuckDB への冪等書き込みロジック（DELETE → INSERT、トランザクション、ROLLBACK 保護）を実装。
    - テスト容易性を考慮し、内部の OpenAI 呼び出しを差し替え可能（unittest.mock.patch 対応）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - prices_daily / raw_news / market_regime を参照し、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を行う。
    - LLM 呼び出しのリトライ・フォールバック（API 失敗時は macro_sentiment=0.0）や JSON パース失敗時の安全化を実装。
    - API キー注入（引数または OPENAI_API_KEY 環境変数）に対応。
- データプラットフォーム（ETL / カレンダー）
  - src/kabusys/data/pipeline.py
    - ETLResult データクラスを提供（取得件数・保存件数・品質問題・エラーを保持）。
    - 差分更新・バックフィル・品質チェック・idempotent 保存の方針に基づく ETL ユーティリティの基盤を実装（jquants_client / quality と連携する設計）。
    - DuckDB のテーブル存在チェックや最大日付取得などのユーティリティを実装。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult を公開。
  - src/kabusys/data/calendar_management.py
    - market_calendar を用いた営業日判定ロジック（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）を実装。
    - DB 登録値優先、未登録日は曜日フォールバック（週末判定）という一貫したルールを採用。
    - calendar_update_job による J-Quants からの差分取得・バックフィル・保存処理を実装（健全性チェック、API エラー時の安全処理）。
- Research（ファクター計算・特徴量解析）
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M, ma200 乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性（20日平均売買代金・出来高比）、バリュー（PER/ROE）を DuckDB の prices_daily / raw_financials から計算する関数を実装。
    - データ不足時の None 扱い、返却形式は date, code を含む dict リスト。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリで計算。
  - src/kabusys/research/__init__.py
    - 主要関数をエクスポート (calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank)。
- パッケージ公開整理
  - ai/__init__.py に score_news をエクスポート。

Changed
- N/A（初回リリース）

Fixed
- N/A（初回リリース）

Security
- OpenAI API キーは引数または環境変数で注入する設計。環境変数未設定時は ValueError を発生させることで誤ったデフォルト送信を防止。

Notes / Implementation details / 制約
- 多くの処理でルックアヘッドバイアスを避けるため datetime.today() / date.today() を直接参照しない設計（score_news / score_regime 等は target_date を明示的に受け取る）。
- DuckDB のバージョン差異や制約（executemany の空リスト等）に配慮した実装。
- LLM 呼び出しは gpt-4o-mini を前提とし、JSON mode を期待したレスポンス処理を行う。API の挙動次第で部分的に前後テキストが混入する場合の復元処理を実装。
- データ不足時（MA200 の行数不足、記事ゼロ件など）は中立（1.0 や 0.0）にフォールバックし、例外を発生させないフォールトトレラントな振る舞いを選択。
- 一部外部モジュール（jquants_client, quality）は参照するがこのコミット内には実装が含まれない（外部依存）。
- monitoring は __all__ に含まれているが（パッケージ公開対象）実装ファイルはこのリリース内に含まれていない。

Known issues / TODO
- ai/regime_detector と ai/news_nlp の内部で OpenAI 呼び出しの実装を重複している（意図的に別実装としモジュール結合を避けているが、共通化の検討余地あり）。
- 一部 API エラーハンドリング（非5xx の詳細な分類など）は今後の改善候補。
- monitoring サブパッケージの実装（監視・アラート連携）は未提供。

-------------- 

ライセンスや変更管理ポリシーに従って、今後の変更は Unreleased セクションに記録してください。必要であれば各関数・モジュールごとの細かな変更履歴（コミット単位）も作成できます。どの粒度で記載するか指示をください。