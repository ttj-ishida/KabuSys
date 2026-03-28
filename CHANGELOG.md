CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

- （なし）

0.1.0 - 2026-03-28
------------------

初回リリース。以下の主要機能と実装方針を含みます。

Added
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys.__version__ = 0.1.0、__all__ に主要サブパッケージを公開）。
- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダ実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - .env のパースロジックを実装（export プレフィックス対応、シングル/ダブルクォート、エスケープ、インラインコメント処理）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - 環境変数検証（必須項目は _require() で ValueError を投げる）。Settings クラスで以下などの設定を公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（AI モジュールで利用）
    - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（DEBUG/INFO/...）の検証
- データプラットフォーム機能（kabusys.data）
  - カレンダー管理（calendar_management.py）
    - market_calendar テーブルを使った営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 未取得時は曜日ベースのフォールバック。最大探索日数上限で無限ループ防止。
    - JPX カレンダー夜間更新ジョブ（calendar_update_job）を実装（J-Quants クライアント呼び出しによる差分取得、バックフィル、健全性チェック、保存処理）。
  - ETL パイプライン（pipeline.py / etl.py）
    - ETLResult データクラスを公開（取得件数、保存件数、品質問題、エラー情報を保持）。
    - 差分取得・バックフィル・品質チェックの設計に準拠したユーティリティ実装。
    - DuckDB の制約（executemany の空リストなど）を考慮した実装。
  - jquants_client との連携を想定した設計（fetch/save 系関数経由での保存、ON CONFLICT ベースの冪等処理）。
- 研究（research モジュール）
  - ファクター計算（research.factor_research）
    - モメンタム（1M/3M/6M のリターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER、ROE）の計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB を用いた SQL ベースの計算。結果は日付・銘柄キーの dict リストで返却。
  - 特徴量探索（research.feature_exploration）
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応、入力検証あり）。
    - IC（Information Coefficient）計算（calc_ic、Spearman のランク相関）、ランク付けユーティリティ（rank）。
    - ファクター統計サマリー（factor_summary）。
  - research パッケージ __all__ で主要関数を再エクスポート（zscore_normalize を data.stats から再利用）。
- AI（kabusys.ai）
  - ニュース NLP（news_nlp.py）
    - raw_news / news_symbols からニュースを銘柄別に集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとの sentiment/ai_score を算出。
    - バッチサイズ、1 銘柄あたり記事数・文字数制限、JSON Mode 応答の検証・復元ルールを実装。
    - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフリトライ。失敗時は該当チャンクをスキップしてフェイルセーフに継続。
    - レスポンス検証で未知コードの無視、スコアの ±1.0 クリップ。ai_scores テーブルへ冪等的に（DELETE→INSERT）書き込み。
    - calc_news_window（ニュース収集ウィンドウ計算）を提供（JST ベースの時間窓、UTC naive datetime を返却）。
    - 公開 API: score_news(conn, target_date, api_key=None) — 書き込み銘柄数を返す。
  - レジーム判定（regime_detector.py）
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジームを判定（'bull' / 'neutral' / 'bear'）。
    - マクロニュース抽出、OpenAI 呼び出し、再試行・フェイルセーフ、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - 設計方針としてルックアヘッドバイアス防止（datetime.today() を直接参照しない）を採用。
  - ai パッケージ __all__ に score_news を公開。news_nlp と regime_detector は独立した OpenAI 呼び出し実装を持ち、モジュール結合を避ける設計。
- 実装上の堅牢性・運用面の配慮
  - DB トランザクションでの BEGIN / DELETE / INSERT / COMMIT と ROLLBACK ハンドリング（例外時のロールバック試行と警告ログ）。
  - OpenAI 応答パース失敗や API 障害時はスコアを中立（0.0）にフォールバックする等、フェイルセーフを多数導入。
  - 各モジュールで詳細なログ（logger）を出力し、処理状況・警告・エラーを記録。
  - DuckDB 型や日付取り扱いに関するユーティリティ（_to_date など）を用意。

Changed
- 初公開版のため該当なし。

Fixed
- 初公開版のため該当なし。

Deprecated
- 初公開版のため該当なし。

Removed
- 初公開版のため該当なし。

Security
- 初公開版のため特記なし。ただし OpenAI API キー等の秘密情報は環境変数で管理する想定。

Notes / Requirements
- DuckDB を主要なローカル分析 DB として想定。ai モジュールは OpenAI API（gpt-4o-mini）を利用。
- 外部 API クライアント（J-Quants, OpenAI）は実行環境で利用可能であることが前提。テスト時のモック注入を容易にする設計（_call_openai_api の差し替え等）。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（その他 Settings 参照）
  - OPENAI_API_KEY は AI 関数（score_news, score_regime）の呼び出し時に必要（引数で注入可能）。
- デフォルトのデータパス:
  - DUCKDB_PATH = data/kabusys.duckdb
  - SQLITE_PATH = data/monitoring.db

Acknowledgements
- 実装では「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ」「DuckDB 周りの互換性配慮（executemany の空リスト等）」といった設計方針を重視しています。必要に応じて次版で API の追加・ユニットテスト・ドキュメント整備を進めてください。