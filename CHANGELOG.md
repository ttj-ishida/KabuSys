# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。詳しくは https://keepachangelog.com/ja/ を参照してください。

※この CHANGELOG はリポジトリ内のコード内容から推測して作成した初期リリース向けの要約です。

## [Unreleased]

- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-04-01

Added
- 基本情報
  - パッケージメタ情報を追加: kabusys.__version__ = "0.1.0"、パブリック API として data / strategy / execution / monitoring をエクスポート。

- 設定管理 (kabusys.config)
  - .env ファイルと環境変数から設定を読み込む自動ローダーを実装（プロジェクトルートは .git または pyproject.toml により検出）。
  - .env / .env.local の読み込み優先順位を実装（OS 環境変数を保護する protected 機構、.env.local は上書きを許可）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env 行パーサーは以下に対応:
    - 空行・コメント行（#）の無視
    - export KEY=val 形式
    - シングル/ダブルクォートされた値（バックスラッシュエスケープ対応）
    - クォートなしの値内のインラインコメント扱い（直前が空白/タブの場合のみ）
  - Settings クラスを提供（プロパティ経由で取得）:
    - J-Quants / kabuステーション / Slack / データベースパス（duckdb/sqlite）/ 監視しきい値（CPU/Memory/Disk）/ PID ファイルパス
    - KABUSYS_ENV（development/paper_trading/live）の検証、LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev のヘルパー

- AI モジュール (kabusys.ai)
  - ニュース NLP (kabusys.ai.news_nlp)
    - ニュースのスコアリング機能 score_news を実装。
    - タイムウィンドウ計算 (calc_news_window)。JST ベースの前日 15:00 〜 当日 08:30 を UTC に変換して扱う。
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約（最大記事数・最大文字数でトリム）。
    - OpenAI（gpt-4o-mini）へチャンク単位（デフォルト 20 銘柄/チャンク）で JSON Mode による API 呼び出し。
    - エラー耐性: 429 / ネットワーク断 / タイムアウト / 5xx は指数的バックオフでリトライ、非リトライ系エラーはスキップして継続。
    - レスポンスの堅牢なバリデーションと JSON 復元（前後に余計なテキストが混入するケースを考慮）。
    - スコアは ±1.0 にクリップ。取得済みコードのみを対象に ai_scores テーブルへ置換（DELETE → INSERT）して部分失敗時の保護を実現。
    - テスト容易性: _call_openai_api を patch で差し替え可能に設計。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出する score_regime を実装。
    - ma200_ratio 計算（target_date 未満のデータのみ使用し、データ不足時は中立（1.0）にフォールバック）。
    - マクロニュース抽出（マクロキーワード群によるフィルタ、最大記事数制限）および LLM 呼び出し（gpt-4o-mini）で macro_sentiment を取得。API 失敗時は macro_sentiment=0.0 で継続。
    - レジームスコアの合成ロジック、閾値判定、idempotent な market_regime テーブルへの書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - OpenAI 呼び出しは news_nlp とは独立した実装でモジュール結合を低減。

- データプラットフォーム (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar に基づく営業日判定関数を実装:
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
    - market_calendar が未取得の場合の曜日ベースフォールバック（週末除外）を用意し、DB 登録ありの場合は DB 値を優先する一貫性ある挙動を提供。
    - next/prev_trading_day は最大探索範囲を設定し無限ループを防止（デフォルト _MAX_SEARCH_DAYS）。
    - calendar_update_job により J-Quants API から差分取得して market_calendar を冪等に保存（バックフィル・健全性チェック・例外ハンドリング付き）。
    - jquants_client との連携を想定（fetch_market_calendar / save_market_calendar）。
  - ETL パイプライン (kabusys.data.pipeline / kabusys.data.etl)
    - ETLResult dataclass を導入（target_date, fetched/saved 件数, quality_issues, errors 等を保持）。
    - ETL の設計方針として差分更新、バックフィル、品質チェック（quality モジュール）を想定。
    - DuckDB のテーブル存在チェックや最大日付取得などのユーティリティを実装（DuckDB 互換性考慮）。
    - data.etl モジュールで ETLResult を再エクスポート。
  - jquants_client / quality など外部モジュールとの連携を想定した API を提供（実装は別モジュール）。

- リサーチ / ファクター分析 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン・200日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す設計。
    - calc_volatility: 20日 ATR（true_range の扱いに注意）・相対 ATR（atr_pct）・20日平均売買代金・出来高比率を計算。
    - calc_value: raw_financials から最新財務を取得して PER（EPS が 0/欠損なら None）・ROE を計算。
    - DuckDB 上の SQL ウィンドウ関数を活用し、営業日ベースの窓幅やスキャン範囲バッファを設定。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得（LEAD を使用）。horizons のバリデーションあり。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。要件に応じて None を返却する境界条件を定義。
    - rank: 同順位は平均ランクを採るランク変換を実装（丸めで ties 検出漏れを防止）。
    - factor_summary: 各ファクター列の基本統計量（count, mean, std, min, max, median）を計算。
  - research.__init__ で主要関数をエクスポート。

- 設計上の共通方針（ドキュメント化され実装に反映）
  - ルックアヘッドバイアス防止: 各処理は datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計。
  - フェイルセーフ: 外部 API 失敗時は処理を停止せず、安全なデフォルト（例: macro_sentiment=0.0）または該当銘柄のスキップで継続する戦略。
  - DB 書き込みは冪等性を重視（DELETE→INSERT, ON CONFLICT 等）して部分失敗時のデータ保護を実現。
  - テスト容易性: OpenAI 呼び出しなど外部依存部分は patch / モックで差し替え可能に設計。
  - DuckDB の互換性や制約（executemany の空リスト禁止等）への対処を実装。

Changed
- 初回公開のため特になし（初期実装）。

Fixed
- 初回公開のため特になし。

Deprecated
- なし。

Removed
- なし。

Security
- なし。

---

備考:
- OpenAI モデルはデフォルトで gpt-4o-mini を想定しており、API 呼び出しで JSON Mode（response_format={"type":"json_object"}）を利用しています。API キーは引数経由または環境変数 OPENAI_API_KEY から解決されます。
- いくつかの jquants_client / quality / monitoring 等は本 CHANGELOG とコードの文脈で参照されていますが、実装ファイルは別モジュールに分かれている可能性があります。
- この CHANGELOG は与えられたコードベースの記述と docstring から推定して作成しています。実際のリリースノートとして利用する際は差分・履歴の確認を推奨します。