Keep a Changelog 準拠 — 変更履歴 (日本語)
このファイルは Keep a Changelog の形式に沿っており、常にバージョン、日付、変更内容を記録します。

フォーマット:
- 変更種別: Added / Changed / Fixed / Removed / Security / Deprecated / Unreleased
- 各項目は該当するモジュールや機能、設計上の重要事項を簡潔に記載

注意: 以下の CHANGELOG はリポジトリ内のソースコードから機能・設計を推測して作成した初期リリース向けの記録です。

Unreleased
- 作業中・今後の予定
  - strategy / execution / monitoring パッケージの実装（パッケージ公開用の __all__ には含まれているが、本リリースには詳細実装が未着手）
  - 追加の品質チェック、ETL の細かい観測ログ、単体テストの拡充
  - news_nlp と regime_detector の LLM モデル運用に関するランタイム監視 / コスト制御

[0.1.0] - 2026-03-29
Added
- パッケージ基盤の初期実装（kabusys v0.1.0）
  - src/kabusys/__init__.py にてバージョン定義と公開モジュール一覧を設定。

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local 自動読み込み機能をプロジェクトルート（.git または pyproject.toml）から行う実装を追加。
  - .env パーサを独自実装（export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント取り扱いに対応）。
  - OS 環境変数を保護する protected モード、override フラグを実装。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）。
  - Settings クラスを提供し、必須環境変数取得（_require）や各種設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）、パス（DUCKDB_PATH, SQLITE_PATH）、環境検証（KABUSYS_ENV の制約）、ログレベル検証を実装。

- ニュースNLP / AI (src/kabusys/ai/*.py)
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント ai_score を算出。
    - JST ベースのニュース収集ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）。
    - バッチ処理（最大 20 銘柄／回）、各銘柄のトークン肥大化対策（記事数・文字数制限）。
    - JSON Mode を使った厳密レスポンス期待、レスポンスのバリデーションとスコアクリップ（±1.0）。
    - リトライ（429/ネットワーク/タイムアウト/5xx）で指数バックオフを実装し、失敗時はフェイルセーフでスキップ。
    - ai_scores テーブルへの冪等的書き込み（DELETE→INSERT、部分失敗で他銘柄スコアを保護）。
    - 単体テスト用に _call_openai_api を差し替え可能（patch の想定）。

  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードで raw_news タイトルをフィルタリングして LLM に投げる。記事が無い場合は LLM コールをスキップし macro_sentiment=0.0 を採用。
    - OpenAI 呼び出しに対するリトライ/バックオフ、API エラー時のフォールバックを実装。
    - レジームスコアを market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）し、失敗時は ROLLBACK を試行。
    - LLM 呼び出しはテスト差し替えやモジュール結合を避ける目的で独立実装。

  - ai パッケージ初期公開 (src/kabusys/ai/__init__.py)
    - score_news を公開、news_nlp.score_news を外部から利用可能に。

- データ基盤 (src/kabusys/data/*.py)
  - calendar_management（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを用いた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。
    - DB に登録のない日については曜日ベース（土日を非営業日）でフォールバックする一貫した振る舞いを実装。
    - カレンダー夜間バッチ（calendar_update_job）を実装：J-Quants API からの差分取得、バックフィル（直近 _BACKFILL_DAYS 日）、健全性チェック（過剰未来日付はスキップ）、jquants_client 経由での保存呼び出しを支援。

  - ETL パイプライン（src/kabusys/data/pipeline.py / etl.py）
    - ETLResult dataclass を導入（取得数、保存数、品質問題、エラーの集約）。
    - 差分取得、バックフィル、品質チェックの設計方針に基づくユーティリティ（_get_max_date, _table_exists 等）を実装。
    - モジュールは jquants_client（外部モジュール）と quality モジュールを利用する想定。
    - src/kabusys/data/etl.py で ETLResult を再エクスポート。

  - data パッケージの基礎（__init__.py 空の初期プレースホルダを含む）。

- 研究・ファクター分析モジュール (src/kabusys/research/*.py)
  - factor_research.py
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対 ATR）、Value（PER、ROE）、Liquidity（20日平均売買代金、出来高変化率）を DuckDB 上の SQL と Python の組合せで算出。
    - データ不足時は None を返す、結果は (date, code) をキーとする dict のリストで返却。
    - DuckDB のウィンドウ関数等を活用し、ルックアヘッドバイアス回避を考慮。

  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic: Spearman の ρ）、ランク変換（rank）、ファクター統計サマリ（factor_summary）を実装。
    - pandas 等の外部依存を使用せず、標準ライブラリと DuckDB のみで実装。

  - research パッケージ初期公開（src/kabusys/research/__init__.py）
    - 主要関数をエクスポート（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

Changed
- 設計・基本方針の明文化（各モジュールの docstring に設計方針、ルックアヘッドバイアス回避、フェイルセーフの扱いを明示）
- OpenAI 呼び出し箇所での冗長な例外処理とリトライ挙動を統一的に実装（news_nlp と regime_detector で類似ロジックを独立実装し、テスト差替えを容易に）

Fixed
- （初期リリース）ロールバック処理失敗時のログ出力を追加（DB 書き込み失敗時に ROLLBACK を試行し、それが失敗した場合に警告ログを残す）

Security
- 環境変数（API キーやトークン）は必須チェックを行い、未設定時は ValueError を発生させる（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY を参照する機能）。
- .env 自動読み込みはデフォルトで有効だが、テスト等のため KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- 注意項目: .env に機密情報を平文で置くことのリスクは変わらず、適切な秘匿（OS 環境変数やシークレットマネージャの利用）を推奨。

Known issues / Notes / TODO
- strategy / execution / monitoring の詳細実装は未提供。パッケージ公開用の枠組みはあるが、売買ロジック・注文実行・監視ツールは今後の実装予定。
- Value ファクターの一部（PBR、配当利回り）は未実装（docstring に明示）。
- news_nlp における sentiment_score と ai_score は現フェーズで同値として保存される（将来的に差分化の可能性あり）。
- DuckDB バインドの互換性を考慮し、executemany へ空リスト渡しを回避する保護コードを追加している（環境依存の挙動に注意）。
- OpenAI への投げ方・モデルは将来的な API 変更に依存するため、API ラッパーの保守が必要。

Migration / Usage notes
- 環境変数の準備:
  - 必須（例）: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY
  - デフォルトの DB パス: DUCKDB_PATH=data/kabusys.duckdb, SQLITE_PATH=data/monitoring.db
  - 環境を明示する: KABUSYS_ENV ∈ {development, paper_trading, live}
  - ログレベル: LOG_LEVEL ∈ {DEBUG, INFO, WARNING, ERROR, CRITICAL}
- 自動 .env 読み込みはプロジェクトルートの .env/.env.local を読み込む（.env.local は .env を上書き）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- OpenAI API を利用する機能（score_news, score_regime）は API キーの注入（引数 api_key）をサポート。テスト時は引数経由で差し替え可能。

作者メモ（推測）
- 設計方針として「ルックアヘッドバイアスの排除」「DB の冪等書き込み」「外部 API への堅牢なリトライ」「テスト容易性の確保（差し替え可能な internal call）」が重視されている。
- DuckDB を解析基盤に採用し、ETL→データ品質→研究→AI→（将来的に）取引実行へとつなげるデータ基盤構成を目指した初期実装。

参照
- ソース: src/kabusys 以下の各モジュール（config.py, ai/*.py, data/*.py, research/*.py）に実装および各 docstring の設計記述に基づく要約

（この CHANGELOG はコードベースの内容から推測して作成しています。実際の変更履歴やリリースノートとして公開する場合は、コミット履歴やリリースタグと照合してください。）