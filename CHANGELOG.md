# CHANGELOG

すべての注目すべき変更点をここに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

※このファイルは与えられたコードベースの内容から推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]

- 特になし。

## [0.1.0] - 2026-04-01

### Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報: src/kabusys/__init__.py にて __version__="0.1.0" を定義。
  - パッケージ公開 API（__all__）に data, strategy, execution, monitoring を含む (一部はプレースホルダ)。

- 環境設定管理
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml に基づく）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env ファイルのパーサー実装（export プレフィックス対応、シングル/ダブルクォートとエスケープ処理、インラインコメントの扱い）。
  - 読み込みポリシー:
    - OS 環境変数 > .env.local > .env の優先順位。
    - .env.local は override=True（ただし既存 OS 環境変数は保護）。
  - Settings クラス（kabusys.config.Settings）を提供。J-Quants / kabuステーション / Slack / DB / 監視閾値などの設定プロパティを環境変数から取得・検証。
    - 必須キー取得用の _require() を提供 (未設定時は ValueError)。
    - KABUSYS_ENV と LOG_LEVEL の値検証を実装（有効値セットを定義）。
    - Path 型の設定プロパティ（duckdb_path, sqlite_path, pid_file_path）を提供。

- AI モジュール（kabusys.ai）
  - ニュースベースの銘柄スコアリング: news_nlp.score_news
    - 指定日（target_date）に対応するニュースウィンドウを計算（前日 15:00 JST 〜 当日 08:30 JST）。
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約し、OpenAI (gpt-4o-mini) の JSON Mode へバッチ送信してセンチメントスコアを取得。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/回）、1銘柄あたり記事数・文字数上限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）を実装。
    - API 呼び出しのリトライ（429・ネットワーク断・タイムアウト・5xx に対して指数バックオフ）とレスポンス検証を実装。
    - レスポンスのバリデーション（JSON 抽出、results の存在、コード一致、数値チェック）、スコアの ±1.0 クリップ、および DuckDB への冪等書き込み（DELETE → INSERT）を実装。
    - API キー未指定時は ValueError を送出。

  - 市場レジーム判定: regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定。
    - マクロキーワードによる raw_news フィルタリング、OpenAI への問い合わせ（独立実装）とスコア合成ロジックを提供。
    - API の冗長性対策: 失敗時は macro_sentiment=0.0 をフォールバックし続行。
    - 結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）する。
    - API キー未指定時は ValueError を送出。

  - テスト容易性: OpenAI 呼び出しを行う内部関数は差し替え（モック）できるように設計（unittest.mock.patch を想定）。

- Research モジュール（kabusys.research）
  - ファクター計算: calc_momentum, calc_value, calc_volatility（kabusys.research.factor_research）
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - Value: raw_financials と prices_daily を組み合わせて PER, ROE を計算（EPS 無効時は None）。
    - Volatility & Liquidity: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。必要行数未満は None。
    - DuckDB を用いた SQL 集約＋ウィンドウ関数で効率的に実装。
    - 外部 API へのアクセスは行わない（安全）。
  - 特徴量探索: calc_forward_returns, calc_ic, rank, factor_summary（kabusys.research.feature_exploration）
    - 将来リターン（任意ホライズン）を一括クエリで取得。
    - IC（Spearman の ρ）計算、ランク変換（同順位は平均ランク）、統計サマリー（count/mean/std/min/max/median）を実装。
    - 標準ライブラリのみで実装（pandas 等に依存しない）。
  - zscore_normalize を kabusys.data.stats から再エクスポート（kabusys.research.__init__）。

- Data モジュール（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等の営業日判定ユーティリティを提供。
    - market_calendar が存在しない場合は曜日ベース（平日）でフォールバック。
    - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等更新。バックフィル（直近 _BACKFILL_DAYS を再フェッチ）と健全性チェックを実装。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）により無限ループ防止。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを実装（取得数・保存数・品質チェック結果・エラー等を集約）。
    - 差分更新、バックフィル、品質チェック（kabusys.data.quality を使用）等の設計方針に沿った実装（J-Quants クライアント経由での取得・保存を想定）。
    - jquants_client を利用した取得/保存処理を統合。
  - etl モジュールは pipeline.ETLResult を再エクスポート（kabusys.data.etl）。

- 実装方針・設計上の特徴（全体）
  - DuckDB を主要な分析 DB として使用し、SQL + Python の組合せで計算処理を実装。
  - ルックアヘッドバイアス回避: datetime.today() / date.today() を直接参照せず、target_date 等を明示的に受け取る設計。
  - OpenAI など外部 API 呼び出しは可搬性・テスト容易性に配慮して冪等性・リトライ・フォールバック処理を整備。
  - DB 書き込みは冪等操作（DELETE→INSERT、ON CONFLICT など）やトランザクション（BEGIN/COMMIT/ROLLBACK）で保護。
  - ロギング（警告/情報/デバッグ）を各所に設置。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

## Known issues / Notes
- pipeline._get_max_date の末尾にコードの断片（return date.fro）が見られ、実装が途中で切れているように見受けられます。リポジトリ全体でこの関数が完全に実装されているか確認が必要です。
- 一部モジュール（strategy, execution, monitoring 等）は __all__ に含まれますが、本コードスニペットには実装ファイルが含まれておらずプレースホルダの可能性があります。これらは別途実装・確認が必要です。
- DuckDB のバージョン互換性に関する注意点がコード内に記載されています（例: executemany に空リストを渡せない制約への対応）。運用時は使用する DuckDB バージョンとの整合性を確認してください。
- OpenAI API 呼び出しには API キー（OPENAI_API_KEY）が必須。未設定時は ValueError が発生します。テストでは内部呼び出しをモックする設計になっています。

---

もし実際のリポジトリで履歴やリリース日を確定する場合は、コミット履歴やタグを参照して日付・変更内容を更新してください。必要であれば英語版の CHANGELOG や各機能ごとの詳細なリリースノートも作成します。