# Changelog

すべての重要な変更はここに記載します。  
フォーマットは「Keep a Changelog」に準拠します。  

※このファイルはコードベースから推測して作成した初回リリース向けの変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-31

Added
- パッケージ基盤
  - 初期パッケージ `kabusys` を追加。公開モジュールは `data`, `strategy`, `execution`, `monitoring`（`src/kabusys/__init__.py`）。
  - パッケージバージョンを `0.1.0` として定義。

- 設定・環境変数管理
  - `.env` / `.env.local` をプロジェクトルート（`.git` または `pyproject.toml` を探索）から自動読み込みする機能を実装（`kabusys.config`）。
  - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - `.env` パーサを実装し、以下に対応：
    - 空行・コメント行（`#`）の無視
    - `export KEY=val` 形式のサポート
    - シングル／ダブルクォートされた値のバックスラッシュエスケープ処理
    - クォートなし値におけるインラインコメント処理（直前がスペースまたはタブの場合にコメントとして処理）
  - 環境変数読み込み時の上書き制御（`override`）と既存 OS 環境変数の保護（`protected`）の実装。
  - アプリケーション設定用 `Settings` クラスを追加。必須環境変数取得用 `_require`、および次のプロパティを提供：
    - J-Quants / kabuステーション / Slack トークン関連（必須チェック）
    - DB パス (`duckdb_path`, `sqlite_path`)
    - `KABUSYS_ENV`（`development`/`paper_trading`/`live` の検証）
    - `LOG_LEVEL`（`DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL` の検証）
    - 利用しやすい `is_live` / `is_paper` / `is_dev` ブールプロパティ

- AI（NLP）機能
  - ニュースセンチメント集約・スコアリング機能を実装（`kabusys.ai.news_nlp.score_news`）。
    - 前日 15:00 JST ～ 当日 08:30 JST のニュースウィンドウを計算するユーティリティ `calc_news_window`。
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約し、OpenAI（`gpt-4o-mini`）にバッチ送信して銘柄単位のスコアを取得。
    - 1チャンクあたり最大 20 銘柄、1銘柄あたり最大 10 記事かつ 3000 文字でトリム。
    - OpenAI 呼び出しは JSON モードを利用し、レスポンスのバリデーション（`_validate_and_extract`）とスコアの ±1.0 クリップを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフでのリトライを実装（最大再試行数やベース待機時間は定数化）。
    - DuckDB への書き込みは部分失敗に配慮して、対象コードのみ DELETE → INSERT による置換を行う（`executemany` の空リスト注意も対処）。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（`_call_openai_api` を patch 可能）。
  - 市場レジーム判定機能を実装（`kabusys.ai.regime_detector.score_regime`）。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースからの LLM センチメント（重み 30%）を合成して日次でレジーム（`bull`/`neutral`/`bear`）を判定。
    - news_nlp の `calc_news_window` を利用してマクロ記事を抽出、OpenAI を用いたマクロセンチメントスコアリングを実装。
    - API エラー時はフェイルセーフとして macro_sentiment=0.0 を使用。
    - 結果は `market_regime` テーブルへ冪等に保存（BEGIN / DELETE / INSERT / COMMIT）。ロールバック処理とログを備える。
    - LLM 呼び出しは `news_nlp` とは独立した内部実装（モジュール結合を避ける形）。

- 研究（Research）機能
  - ファクター計算モジュール（`kabusys.research.factor_research`）を追加：
    - `calc_momentum`：1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None を返す）を計算。
    - `calc_volatility`：20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率等を計算。
    - `calc_value`：raw_financials から最新財務データを取得して PER/ROE を計算。
    - すべて DuckDB 上の SQL を中心に実装し、外部 API へアクセスしない設計。
  - 特徴量探索モジュール（`kabusys.research.feature_exploration`）を追加：
    - `calc_forward_returns`：複数ホライズンの将来リターンを一度のクエリで取得（ホライズン検証あり）。
    - `calc_ic`：ファクター値と将来リターンのスピアマンランク相関（IC）を計算。
    - `rank`：同順位は平均ランク扱いのランク付けユーティリティ。
    - `factor_summary`：各ファクター列の count/mean/std/min/max/median を計算。
    - パフォーマンスや数値安定性を考慮した実装（丸め・有限値チェックなど）。

- データプラットフォーム / ETL
  - カレンダー管理モジュール（`kabusys.data.calendar_management`）を追加：
    - JPX カレンダーを扱う `market_calendar` を前提とした営業日判定ロジックを提供：
      - `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day`
    - DB にデータが無い場合は曜日ベース（土日除外）でフォールバック。DB 登録値があればそれを優先する一貫性ある判断。
    - night-batch 用の `calendar_update_job` を実装：J-Quants から差分取得して `market_calendar` を冪等保存。バックフィルと健全性チェックを実装。
  - ETL パイプライン（`kabusys.data.pipeline`）を追加：
    - 差分更新、IDempotent 保存、品質チェックの設計に基づく ETL の結果を格納する `ETLResult` データクラスを公開。
    - DuckDB 上の最大日付取得やテーブル存在チェックなどのユーティリティを実装。
  - `kabusys.data.etl` で `ETLResult` を再エクスポート。

- ロギング・例外処理・設計上の配慮
  - 重大な外部依存（OpenAI / J-Quants）呼び出しに対してフェイルセーフを設ける（API 失敗時はスコア 0.0 へフォールバック、処理を継続）。
  - DB 書き込みは冪等性を保ち、失敗時に ROLLBACK を試行し、ROLLBACK 失敗時も警告ログを出す。
  - DuckDB 互換性のため `executemany` に空リストを渡さないチェックを追加（DuckDB 0.10 の制約に対応）。
  - 「ルックアヘッドバイアス防止」の方針を一貫して適用（datetime.today() / date.today() をスコアリング内部で参照しない、クエリは target_date を基準に過去データのみ参照）。

Changed
- 初回リリースのためなし（このバージョンでの初期導入・設計仕様を列挙）。

Fixed
- 初回リリースのためなし。

Security
- 外部 API キーは直接ハードコードせず `api_key` 引数または環境変数 `OPENAI_API_KEY` / 各種トークン経由で解決する方針を採用。

Notes / Implementation details
- OpenAI 呼び出しは JSON Mode（response_format={"type": "json_object"}）を利用し、レスポンスの厳密な JSON パースと復元ロジックを実装（前後余計なテキストの抽出などに対応）。
- ニュースウィンドウは JST を基準に UTC に変換して DB 内の UTC 保存値と照合する実装（`calc_news_window`）。
- マクロキーワードによる絞り込みや取得件数上限を設け、LLM への入力量・コストを制御。
- テスト容易性のため OpenAI 呼び出し部分はモジュールレベルで差し替え可能に設計。

-- end of changelog --