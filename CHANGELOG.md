Keep a Changelog
=================

すべての重大な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-03
--------------------

Added
- 初回リリース。
- パッケージエントリポイント:
  - `kabusys` パッケージを公開。`__version__ = "0.1.0"`。モジュール公開: `data`, `strategy`, `execution`, `monitoring`（`monitoring` 実装は省略）。
- 環境設定 / ロード機能（`kabusys.config`）:
  - プロジェクトルートを `.git` または `pyproject.toml` から探索して自動で `.env` / `.env.local` を読み込む自動ロード機能を実装。（環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）
  - `.env` パーサーは以下をサポート:
    - 空行・コメント行（`#`）を無視
    - `export KEY=val` 形式に対応
    - シングル/ダブルクォートされた値をバックスラッシュエスケープを考慮して正しく解析
    - クォートなし値でのインラインコメント処理（`#` の直前が空白またはタブの場合のみコメントとみなす）
  - 読み込み時の `override` と `protected`（OS 環境変数保護）機構を提供
  - 必須環境変数取得ヘルパー `_require` と、`Settings` クラス経由の型付きプロパティ群を提供:
    - J-Quants / kabuステーション / LINE / DB パス / 監視しきい値 / システム設定（`env`, `log_level`, `is_live` 等）
    - `env` / `log_level` の値検証を行い不正値時は `ValueError` を送出
- AI モジュール（`kabusys.ai`）:
  - `news_nlp`（`score_news`）:
    - ニュース記事を OpenAI（`gpt-4o-mini`）でセンチメント評価して `ai_scores` テーブルへ書き込む機能。
    - タイムウィンドウは JST 基準で「前日 15:00 ～ 当日 08:30」を UTC に変換して取得（`calc_news_window`）。
    - 銘柄毎に最新記事を集約し（最大記事数・文字数でトリム）、最大 20 銘柄ずつバッチ送信（チャンクサイズ `_BATCH_SIZE = 20`）。
    - API 呼び出しは JSON Mode を利用し、レスポンスのバリデーションとスコア ±1.0 クリップを実施。
    - リトライ戦略: 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ。失敗時は部分的にスキップしてフェイルセーフ（例外を上げず継続）。
    - DB 書き込みは idempotent に実施（対象コードのみ `DELETE` → `INSERT`）し、部分失敗時に既存データを不必要に削除しない設計。
  - `regime_detector`（`score_regime`）:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次の市場レジーム（`bull` / `neutral` / `bear`）を判定し `market_regime` テーブルへ冪等的に書き込む。
    - マクロセンチメントは `news_nlp.calc_news_window` で得たウィンドウのマクロキーワード一致タイトルを OpenAI に渡して評価。
    - OpenAI 呼び出しはリトライとフェイルセーフ（API 失敗時に `macro_sentiment = 0.0`）を備える。
    - ルックアヘッドバイアス対策として日付比較は全て排他的・明示的に行う（`date < target_date` 等）。また `datetime.today()` 等を直接参照しない実装方針。
- Research モジュール（`kabusys.research`）:
  - ファクター計算（`factor_research`）:
    - `calc_momentum`: 1M/3M/6M リターン、200 日 MA 乖離（`ma200_dev`）を計算。データ不足時は None を返す。
    - `calc_volatility`: 20 日 ATR、相対 ATR（`atr_pct`）、20 日平均売買代金、出来高比率を計算。欠損管理を考慮。
    - `calc_value`: `raw_financials` から最新財務データを取得し PER / ROE を計算（EPS が 0/欠損 の場合 PER は None）。
    - 設計上、DuckDB の `prices_daily` / `raw_financials` のみ参照し外部発注は行わない。
  - 特徴量探索（`feature_exploration`）:
    - `calc_forward_returns`: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズン検証あり（1..252）。
    - `calc_ic`: スピアマンランク相関（IC）を計算し、データ不足（<3件）時は `None` を返す。
    - `factor_summary`: count/mean/std/min/max/median 等の基本統計量を算出。
    - `rank`: 同順位を平均ランクで扱うランク関数（丸めで ties の検出漏れを抑制）。
  - `zscore_normalize` を `kabusys.data.stats` から再公開。
- Data モジュール（`kabusys.data`）:
  - カレンダー管理（`calendar_management`）:
    - JPX カレンダー（`market_calendar`）の夜間差分更新ジョブ `calendar_update_job` を実装。J-Quants クライアント経由で差分取得し idempotent に保存。
    - 営業日判定 API: `is_trading_day`, `is_sq_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days` を提供。DB にデータがない場合は曜日ベースのフォールバック（週末は非営業日）。
    - 検索最大範囲 `_MAX_SEARCH_DAYS` により無限ループを回避。backfill / sanity check を実装。
  - ETL パイプライン（`pipeline`）:
    - 差分更新・保存・品質チェック（`quality`）のワークフローを実装するためのユーティリティ群。
    - `ETLResult` データクラスを定義（取得数/保存数/quality_issues/errors を含む）。`to_dict()` で品質情報を辞書化可能。
    - デフォルトのバックフィル日数等の定数、テーブル存在/最大日付取得ユーティリティを提供。
  - `data.etl` は `ETLResult` を再エクスポート。
- DuckDB を主要なストレージとして利用する設計（SQL を多用）。
- ロギングと防御的設計:
  - 各処理で詳細なログ出力（`logger.debug/info/warning/exception`）を行う。
  - DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等性を確保し、失敗時は ROLLBACK を試行して例外を上位へ伝播。
  - 外部 API 呼び出しはリトライ・バックオフ・タイムアウトを導入し、致命的な例外を避ける（フェイルセーフ）。

Changed
- （初回リリースのため変更履歴はなし）

Fixed
- （初回リリースのため修正履歴はなし）

Removed
- （初回リリースのため削除履歴はなし）

Security
- 外部 API キー（OpenAI）は `api_key` 引数または環境変数 `OPENAI_API_KEY` から供給。未設定時は関数が `ValueError` を送出して明示的にエラーを返す（不注意な無条件呼び出しを防止）。

Notes / Known limitations
- OpenAI を利用する AI 部分は API コスト・レイテンシ・利用規約に依存するため、本ライブラリ単体ではそれらを抽象化しているが、運用時のキー管理・コスト管理は利用者側で行う必要があります。
- `monitoring` や一部実行/監視周りの具体実装はこのリリースのコードセットでは省略またはモジュール参照のみ（将来追加予定）。
- DuckDB バインドの挙動（`executemany` の空リスト制約等）はバージョン差異に注意。コード内に互換性対策あり。

作者
- KabuSys 開発チーム