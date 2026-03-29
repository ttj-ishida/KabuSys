# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは Keep a Changelog に準拠します。

注: この CHANGELOG はリポジトリ内の現行実装（src/kabusys 以下）から推測して作成しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-29

初回公開リリース。

### Added
- パッケージ基盤
  - 基本パッケージ `kabusys` を追加。バージョンは `0.1.0`。
  - パッケージ公開用に `__all__` を定義（data, strategy, execution, monitoring）。

- 設定・環境変数管理（kabusys.config）
  - .env および .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動ロードする仕組みを追加。
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` に対応。
  - 高度な .env パーサ実装を追加：
    - `export KEY=val` 形式対応、シングル/ダブルクォート対応、バックスラッシュエスケープ処理、コメント処理（クォート外での inline コメント除去）等。
    - ファイル読み込み失敗時に警告を出力。
    - `override` / `protected` オプションで OS 環境変数を保護して上書き制御。
  - Settings クラスを提供（プロパティで必要な環境変数を取得）：
    - J-Quants / kabuステーション / Slack / DB パス等の設定プロパティを定義。
    - `env` と `log_level` の値検証（許容値チェック）。
    - `is_live` / `is_paper` / `is_dev` のユーティリティプロパティ。

- AI モジュール（kabusys.ai）
  - ニュースセンチメント（kabusys.ai.news_nlp）:
    - ニュース取得ウィンドウ算出（JST 基準→UTC 変換）を提供する `calc_news_window`。
    - `score_news(conn, target_date, api_key=None)` により raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini、JSON モード）で銘柄ごとのセンチメントを一括取得して `ai_scores` テーブルへ書き込む機能を追加。
    - バッチ処理（1回最大 20 銘柄）、1銘柄あたりのトークン肥大化対策（記事数上限・文字数トリム）を実装。
    - API 呼び出し時は 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数的バックオフでリトライ。
    - レスポンスの厳密なバリデーション処理（JSON パース、results 配列、code/score の検証、未知コードの無視、数値型・有限値チェック）。
    - スコアは ±1.0 にクリップして保存。部分失敗時に既存スコアを消さないため、対象コードのみ DELETE→INSERT する冪等的書込みを実装。
    - DuckDB の executemany の空リスト制約に対応する保護処理を追加。
    - API キーが未設定の場合は ValueError を送出。

  - 市場レジーム判定（kabusys.ai.regime_detector）:
    - ETF 1321 の 200 日移動平均（MA200）乖離とマクロニュースの LLM センチメントを重み付きで合成し、日次の市場レジーム（bull/neutral/bear）を判定する `score_regime(conn, target_date, api_key=None)` を実装。
    - MA 算出は target_date 未満（排他）データを使用してルックアヘッドを防止。
    - マクロニュースは `news_nlp.calc_news_window` を用いて取得、LLM 呼び出しは独自のラッパーで行いモジュール結合を緩める設計。
    - LLM 失敗時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）し処理を継続。
    - レジーム合成: MA 重み 70%、マクロ重み 30%、スコアはクリッピングし閾値でラベリング。
    - 結果は `market_regime` テーブルに対して冪等な BEGIN/DELETE/INSERT/COMMIT 書き込みを行う。DB 書き込み失敗時は ROLLBACK を試行して例外を上位へ伝播。

  - 共通
    - 各モジュールにおいて OpenAI 呼び出しを差し替え可能に設計（テスト容易性のため _call_openai_api を patch 可能）。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）:
    - JPX 市場カレンダーを管理する `market_calendar` ベースの判定ユーティリティを実装：
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB にデータがない場合は曜日ベース（土日除外）でフォールバックする一貫した挙動。
    - 夜間バッチ用 `calendar_update_job(conn, lookahead_days=90)` を実装。J-Quants から差分取得→保存（バックフィル・健全性チェック含む）。
    - 最大探索レンジやバックフィル、異常時の健全性チェック（将来日が極端に大きい場合のスキップ）を実装。

  - ETL パイプライン（kabusys.data.pipeline / etl）:
    - ETL 処理のための `ETLResult` データクラスを提供（取得件数・保存件数・品質チェック結果・エラー情報などを含む）。
    - 差分更新ロジックに必要な内部ユーティリティ（テーブル存在確認、最大日付取得など）を実装。
    - jquants_client と quality モジュールを利用する設計方針を反映。

- 研究用モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）:
    - calc_momentum: mom_1m/3m/6m と ma200 乖離を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials から最新の財務データを取得して PER/ROE を計算。
    - DuckDB ベースの SQL を多用して高速に計算する設計。外部 API は使用しない。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得（複数ホライズン対応、入力検証あり）。
    - calc_ic: スピアマンのランク相関（IC）を実装。データ不足（有効レコード<3）時は None。
    - rank: 同順位は平均ランクにする実装（丸めで ties 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。

- 内部ユーティリティ・安全対策
  - ルックアヘッドバイアス防止のため、各日次処理で datetime.today()/date.today() に依存しない設計を採用（target_date を明示的に受け取る）。
  - DuckDB の仕様差異（executemany の空リスト等）へ対処する追加チェック。
  - DB 書込み時はトランザクションを使用し、例外時に ROLLBACK を試みる安全実装。
  - API 呼び出し失敗時に例外を無闇に投げず、安全にフェイルオーバーする（ログを残し続行する設計箇所多数）。

### Changed
- 初回リリースのため該当なし（すべて新規追加）。

### Fixed
- 初回リリースのため該当なし（実装時点で対策を組み込んでいる点を記載）:
  - DuckDB executemany の空パラメータ問題を回避するガードを追加。
  - OpenAI レスポンスの JSON パース失敗や予期しない構造に対する耐性を実装（部分スキップ・警告ログ出力）。

### Security
- 環境変数未設定時の保護:
  - OpenAI API キーが必要な API（score_news / score_regime）は、api_key 引数または環境変数 OPENAI_API_KEY が未設定の場合に ValueError を送出して処理を中断。
  - Settings にて重要なトークン（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）を必須プロパティとして定義。

### Notes / Compatibility
- DuckDB を利用するため、実行環境に DuckDB の Python バインディングが必要。
- OpenAI の Python SDK（chat completions をサポートするバージョン）が必要。
- 各種外部 API（J-Quants, kabuステーション, OpenAI）への接続が実行時に要求される。
- 研究用機能・ETL・データ管理は本番口座や発注 API へはアクセスしない設計（安全上の配慮）。

---

記載はソースコードの実装内容を基に推測して作成しています。実際の変更履歴やリリース日、その他運用詳細はプロジェクトの正式な運用ルールに合わせて修正してください。