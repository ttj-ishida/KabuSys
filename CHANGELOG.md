# CHANGELOG

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠します。

なお、本リポジトリの初回公開バージョンは v0.1.0 です（パッケージ内の __version__ に基づく）。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-28
初回リリース。以下の主要機能・モジュールを実装しました。

### Added
- パッケージ基盤
  - kabusys パッケージを初期実装（__version__ = 0.1.0）。
  - パッケージの主要サブモジュールを公開: data, research, ai, execution（実行関連は名前空間として準備）、monitoring（名前空間として準備）など。

- 環境・設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装。
  - プロジェクトルートの自動検出: `.git` または `pyproject.toml` を基準に探索（CWD非依存）。
  - .env パーサー実装:
    - 空行・コメント行・export プレフィックス対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - クォートなしでのインラインコメント処理（直前が空白/タブの場合）。
  - 自動読み込みの優先順位: OS環境変数 > .env.local > .env。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / システム設定（env, log_level）等をプロパティとして取得可能。デフォルト値やバリデーション（許容値チェック）を実装。
  - デフォルト DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。

- ニュース NLP（AI）モジュール (kabusys.ai.news_nlp)
  - raw_news, news_symbols テーブルを用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）を使ってセンチメントを算出して ai_scores テーブルへ書き込む機能を実装。
  - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive datetime）で記事取得。
  - バッチ処理: 最大 _BATCH_SIZE=20 銘柄単位での API 呼び出し。1銘柄当たりの記事は最新 _MAX_ARTICLES_PER_STOCK=10 件、かつ最大文字数 _MAX_CHARS_PER_STOCK=3000 にトリム。
  - OpenAI 呼び出しは JSON Mode を利用し、レスポンスのバリデーション（results リスト・code/score 検証・数値チェック等）を実装。
  - リトライ/バックオフ: 429・接続断・タイムアウト・5xx に対して指数的バックオフでリトライ（最大回数 _MAX_RETRIES）。
  - フェイルセーフ: API 失敗やバリデーション失敗時は該当チャンクをスキップして処理を継続。部分成功時は成功した銘柄のみ ai_scores を置換（DELETE → INSERT）し、既存データの保護を実現。
  - テスト容易性: 内部の OpenAI 呼び出しを差し替え可能に設計（unittest.mock.patch 対応ポイントあり）。

- 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321（Nikkei225 連動）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を評価し market_regime テーブルへ冪等的に書き込む処理を実装。
  - マクロニュースは news_nlp の calc_news_window で定義したウィンドウからマクロキーワードでフィルタして取得し、OpenAI（gpt-4o-mini）で JSON 出力を期待してセンチメントを取得。
  - リトライ・バックオフ戦略、API エラー時のフェイルセーフ（macro_sentiment=0.0）を実装。
  - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等操作を行い、失敗時は ROLLBACK を試みる。

- データ（DataPlatform）モジュール
  - calendar_management:
    - market_calendar を基にした営業日判定ユーティリティを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - カレンダー未取得時は曜日（平日）ベースのフォールバックを採用し、DB がまばらでも一貫した判定を行う設計。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存する夜間バッチ処理を実装。バックフィルと健全性チェックを含む。
  - pipeline:
    - ETLResult データクラスを実装し、ETL 実行結果・品質問題・エラー一覧などを表現。kabusys.data.etl で ETLResult を再エクスポート。

- リサーチ（Research）モジュール
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（prices_daily を参照）。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（EPS が 0 または欠損のとき PER は None）。
    - SQL（DuckDB）ベースの実装で、外部 API へのアクセスは行わないことを保証。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD を使用）。horizons の検証を実装。
    - calc_ic: ファクター値と将来リターンのランク相関（Spearman ρ）を計算。レコード不足や分散が 0 の場合は None を返す。
    - rank: 同順位は平均ランクを返すランク変換ユーティリティを実装（丸め処理で ties の安定化）。
    - factor_summary: 指定カラム群の count/mean/std/min/max/median を計算。

### Changed
- なし（初回リリースのため変更履歴なし）

### Fixed
- なし（初回リリースのため修正履歴なし）

### Security
- なし

### Notes / Limitations
- OpenAI API の利用には OPENAI_API_KEY が必要。各 AI 関数は api_key 引数で上書き可能。
- AI レスポンスは JSON モードを期待するが、余計な前後文字列が混入するケースに備えた復元ロジックを含む。完全な保証は無い点に注意。
- DuckDB 利用時の互換性を考慮し、executemany に空リストを渡さない等のワークアラウンドを実装。
- 時刻は可能な限り timezone-less（UTC naive）で扱う方針。news ウィンドウ等は説明どおり JST→UTC 変換を内部で行う設計を採用。

---

本 CHANGELOG はコードベースの実装内容から推測して作成したものです。実際のリリースノートや変更ポリシーと差異がある場合は適宜調整してください。