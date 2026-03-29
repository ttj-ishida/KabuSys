# Changelog

すべての重要な変更を記録します。フォーマットは "Keep a Changelog" に準拠します。

## [Unreleased]

- ドキュメントやテスト追加、マイナー改善やバグ修正をここに記載してください。

---

## [0.1.0] - 2026-03-29

初回リリース。日本株自動売買・データ基盤・リサーチ支援のためのコア機能群を実装しました。主な追加点は以下のとおりです。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = "0.1.0"）。
  - パッケージトップで公開されるサブパッケージ: data, research, ai, monitoring, strategy, execution（__all__ 設定）。

- 設定管理 (.env / 環境変数)
  - kabusys.config:
    - プロジェクトルート自動検出機能（.git または pyproject.toml を探索）。
    - .env / .env.local 自動ロード（読み込み順: OS 環境 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
    - .env パーサの実装: コメント、export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントルールなどに対応。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境（development/paper_trading/live）やログレベルを環境変数から取得するヘルパーを実装。
    - 必須環境変数未設定時は ValueError を発生させる _require 実装。

- AI（ニュース NLP / レジーム判定）
  - kabusys.ai.news_nlp:
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を利用して銘柄ごとのセンチメント（ai_score）を算出。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST 相当）を calc_news_window で実装。
    - バッチ処理（1回あたり最大 20 銘柄）・記事・文字数トリム（最大記事数・最大文字数）によるトークン肥大対策。
    - リトライ（RateLimit / 接続断 / タイムアウト / 5xx）と指数バックオフ、レスポンスの厳密なバリデーション（JSON 抽出・results 構造・コード照合・数値検証）。
    - DuckDB への置換方式（DELETE → INSERT）により冪等性と部分失敗時の既存データ保護を実装。
  - kabusys.ai.regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の market_regime を算出・保存。
    - prices_daily を target_date 未満のデータのみ参照してルックアヘッドを排除。
    - OpenAI 呼び出しは独立した内部関数として実装し、API エラーや JSON パース失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフを採用。
    - 冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）で market_regime を更新。

- データプラットフォーム（ETL / カレンダー）
  - kabusys.data.pipeline:
    - ETL 用の ETLResult データクラスを導入（取得件数／保存件数／品質問題／エラーの集約）。
    - 差分更新／バックフィル／品質チェック設計に基づくユーティリティ関数（テーブル存在チェック／最大日付取得等）。
  - kabusys.data.calendar_management:
    - market_calendar を用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - calendar_update_job により J-Quants からカレンダーを差分取得して保存（バックフィル・健全性チェック含む）。

- リサーチ（ファクター計算・特徴量解析）
  - kabusys.research.factor_research:
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20 日 ATR 等）、Value（PER、ROE）等のファクター計算関数（calc_momentum / calc_volatility / calc_value）を追加。
    - DuckDB を用いた SQL ベースの計算で、欠損時は None を返す仕様。
  - kabusys.research.feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク付けユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - スピアマン（ランク相関）実装や ties の平均ランク処理を自前で提供。
  - kabusys.research.__init__.py で主要関数を再公開。

- 汎用 / 互換性
  - DuckDB を前提とした実装が中心（DuckDB のバージョン特性を考慮した実装、例: executemany の空リスト回避）。
  - OpenAI クライアント呼び出し箇所はテスト用に差し替え可能（内部呼び出し関数を意図的に分離）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし（実装時点で DuckDB の executemany に関する回避策を組み込む等、既知の互換性対応を行っています）。

### Security
- 初回リリースのため該当なし。
- 注意: OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY によって供給されます。必ず安全に管理してください。

### Notes / Migration
- 環境変数の自動読み込み:
  - デフォルトでパッケージインポート時にプロジェクトルートの .env / .env.local を読み込みます。テスト等で自動ロードを抑制したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - OS の既存環境変数は保護され、.env の値で上書きされない（ただし .env.local は override=True で上書き可能）。
- OpenAI 呼び出し:
  - news_nlp / regime_detector ともに gpt-4o-mini を利用する想定で実装されています。API のエラーはリトライ・フェイルセーフで扱われ、API 無効時は処理を続行（影響を受けたスコアは 0.0、あるいは該当銘柄はスキップ）。
- DuckDB の互換性:
  - 一部実装は DuckDB のバージョン依存挙動（例: executemany と空リスト）を回避するためのガード（空チェック）を実装しています。

もし追加で、リリース日付やリリースノートの細分化（バグ修正の詳細、既知の問題など）を反映したい場合は、対象のコミット履歴や issue 情報を提供してください。