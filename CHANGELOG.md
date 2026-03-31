# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

なお、本 CHANGELOG は与えられたコードベースから推測して作成した初期リリース向けの変更履歴です。

## [0.1.0] - 2026-03-31

### Added
- パッケージ基盤
  - 初期パッケージ公開: `kabusys`（__version__ = "0.1.0"）。
  - パッケージ公開モジュール: data, strategy, execution, monitoring を __all__ に設定。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルと環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み優先度: OS 環境変数 > .env.local > .env
    - プロジェクトルート自動検出: `.git` または `pyproject.toml` を親ディレクトリから探索して特定。
    - 自動ロードの無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env パーサ実装:
    - コメント行、`export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメント処理に対応。
  - `.env` 読み込み時の上書き制御:
    - override と protected キー群で OS 環境変数の保護が可能。
  - 設定取得ラッパー `Settings` を提供（1つのインスタンス `settings` をエクスポート）。
    - J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / ログ・環境設定等のプロパティを提供。
    - 必須設定未指定時に ValueError を送出する `_require` 実装。
    - 有効値の検証（KABUSYS_ENV, LOG_LEVEL）。

- AI 関連 (`kabusys.ai`)
  - ニュース NLP (`kabusys.ai.news_nlp`)
    - raw_news と news_symbols を集約して銘柄ごとのニュースを OpenAI（gpt-4o-mini）に投げてセンチメントを算出し、`ai_scores` テーブルへ書き込む `score_news` を実装。
    - 時間ウィンドウ計算 `calc_news_window`（JST ベース → UTC 変換）を実装（前日 15:00 JST ～ 当日 08:30 JST）。
    - バッチ処理（1 API コールあたり最大 20 銘柄）、1銘柄あたり記事数・文字数制限（記事数上限 10、文字数上限 3000）。
    - JSON Mode を用いた出力パースと堅牢なバリデーション `_validate_and_extract`（余分な前後テキストから最外の {} を抽出するリカバリ含む）。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライと、失敗時は安全にスキップ（例外を上げず 0 個または部分書き込み）。
    - DuckDB 互換性対策として、空パラメータの executemany を避ける実装（部分失敗時に既存スコア保護のため delete→insert をコード単位で実行）。
    - 公開 API: `score_news(conn, target_date, api_key=None) -> int`。
  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（'bull' / 'neutral' / 'bear'）を判定する `score_regime` を実装。
    - マクロニュース抽出はキーワードベースで raw_news からタイトルを取得する `_fetch_macro_news`。
    - OpenAI 呼び出しは専用のラッパー `_call_openai_api` を持ち、JSON レスポンスをパースしてスコアを取得（フェイルセーフとして API 失敗時は macro_sentiment = 0.0）。
    - レジームスコア合成とクリップ、閾値によるラベリング、`market_regime` への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - 公開 API: `score_regime(conn, target_date, api_key=None) -> int`。

- データ関連 (`kabusys.data`)
  - マーケットカレンダー管理 (`calendar_management`)
    - JPX カレンダーの夜間バッチ更新ジョブ `calendar_update_job` を実装（J-Quants API 経由で差分取得→保存）。
    - 営業日判定ユーティリティ群を提供:
      - `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day`
    - DB にカレンダーがない/未登録日の場合は曜日ベースのフォールバック（週末は非営業日）を行い、一貫性を保つ設計。
    - 最大探索範囲 `_MAX_SEARCH_DAYS` による無限ループ防止、バックフィル日数 `_BACKFILL_DAYS`、健全性チェック `_SANITY_MAX_FUTURE_DAYS` を実装。
  - ETL パイプライン (`pipeline.py`)
    - ETL の結果を表すデータクラス `ETLResult` を実装（取得/保存件数、品質問題、エラーメッセージ等を保持）。
    - ETL の設計方針に則った関数群の基礎（差分更新・保存・品質チェックを行う想定）。（jquants_client / quality モジュールと連携）
  - ETL インターフェース再エクスポート (`etl.py`)
    - `ETLResult` を公開する薄いラッパーを実装。

- リサーチ（ファクター・特徴量探索） (`kabusys.research`)
  - ファクター計算 (`factor_research`)
    - Momentum, Volatility, Value, Liquidity などの計算関数を実装:
      - `calc_momentum(conn, target_date)`：1M/3M/6M リターン、ma200_dev（200日 MA 乖離）を計算。データ不足時は None を返す。
      - `calc_volatility(conn, target_date)`：20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
      - `calc_value(conn, target_date)`：raw_financials と prices_daily を組み合わせて PER（EPS が 0/欠損時は None）、ROE を計算。
    - DuckDB のウィンドウ関数を多用した実装と、データ不足時の安全処理。
  - 特徴量探索 (`feature_exploration`)
    - 将来リターン計算 `calc_forward_returns(conn, target_date, horizons=None)`（デフォルト horizons=[1,5,21]）。
    - IC（Information Coefficient）計算 `calc_ic(factor_records, forward_records, factor_col, return_col)`（Spearman ρ、有効レコード数 <3 の場合は None）。
    - ランク関数 `rank(values)`（同順位は平均ランクを返す、浮動小数点丸めで ties を安定化）。
    - 統計サマリー `factor_summary(records, columns)`（count/mean/std/min/max/median を計算）。
  - 便利関数の再エクスポート:
    - `zscore_normalize` を `kabusys.data.stats` から再エクスポート。

- 汎用設計方針・実装上の注意点（ドキュメント化）
  - ルックアヘッドバイアス防止のため、日付計算で datetime.today()/date.today() を直接参照しない設計（関数に target_date を渡す方式）。
  - DuckDB を主要なローカル分析 DB として利用。
  - OpenAI（gpt-4o-mini）の JSON Mode を活用し、厳密な JSON 出力を期待するが、実装側で前後ノイズのリカバリも行う。
  - API 呼び出し失敗時はフェイルセーフとしてスコアに中立値を使うか部分スキップし、例外でプロセス全体を壊さない方針。
  - DB 書き込みは冪等（DELETE→INSERT）または ON CONFLICT 相当の扱いを想定し、トランザクションで安全に行う（ROLLBACK 処理あり）。

### Changed
- （初回リリースのためなし）

### Fixed
- （初回リリースのためなし）

### Deprecated
- （初回リリースのためなし）

### Removed
- （初回リリースのためなし）

### Security
- OpenAI API キーや各種トークン（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等）は環境変数にて管理する設計。必須設定が未指定の場合は起動時に明示的にエラーを投げる実装。
- .env 読み込み時に OS 環境変数を保護する仕組みあり（protected set）。

---

注:
- 本 CHANGELOG はファイルの実装内容を元に推測して作成しています。将来の変更はこのファイルを更新してください。