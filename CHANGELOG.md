# Changelog

すべての注目すべき変更履歴を記載します。  
このファイルは Keep a Changelog の形式に準拠します。

フォーマット:
- 変更はカテゴリ別（Added / Changed / Fixed / Security / Deprecated / Removed / その他）に記載しています。
- バージョンはパッケージの __version__ に合わせています。

---

## [Unreleased]

（次リリースへ向けた変更はここに記載してください）

---

## [0.1.0] - 2026-03-18

初回リリース（ベース実装）。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。__version__ = "0.1.0"。
  - サブパッケージ想定: data, strategy, execution, monitoring（__all__ に公開）。

- 環境設定 / 起動時自動読み込み
  - kabusys.config: Settings クラスを追加し、環境変数からアプリケーション設定を取得する API を提供（settings インスタンス）。
  - プロジェクトルート検出: .git または pyproject.toml を基準に探索する `_find_project_root()` を実装し、CWD に依存しない自動 .env 読み込みを実現。
  - 自動 .env 読み込み: 起動時にプロジェクトルートが見つかれば `.env` → `.env.local` の順で読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサー: export 形式やシングル/ダブルクォートのエスケープ、行末コメント処理に対応する堅牢なパーサ `_parse_env_line()` を実装。
  - 環境値バリデーション: KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL（DEBUG/INFO/...）の検証を行い、不正値は ValueError で通知。
  - 必須環境変数取得ヘルパ `_require()` を提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_* 等のプロパティによって参照）。

- Data レイヤー（duckdb を想定）
  - kabusys.data.schema: DuckDB 用スキーマ定義（Raw レイヤーの DDL: raw_prices, raw_financials, raw_news, raw_executions 等）を提供。各テーブルに適切な型チェック・主キー制約を付与。
  - kabusys.data.jquants_client:
    - J-Quants API クライアント実装。認証（リフレッシュトークン→id_token）とデータ取得機能を追加。
    - レート制御: 固定間隔スロットリングで 120 req/min を守る `_RateLimiter`。
    - リトライ & 指数バックオフ実装（最大3回、408/429/5xx 等に対応）。429 の場合は Retry-After を優先。
    - 401 レスポンス時の id_token 自動リフレッシュ（1回のみ）と再試行ロジック。
    - ページネーション対応のフェッチ関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB への冪等保存（ON CONFLICT DO UPDATE）関数: save_daily_quotes, save_financial_statements, save_market_calendar。fetched_at を UTC で記録して look-ahead bias を防止。
    - モジュールレベルの id_token キャッシュとユーティリティ関数（_to_float, _to_int）。

- ニュース収集
  - kabusys.data.news_collector:
    - RSS フィード取得と前処理機能を実装（fetch_rss, preprocess_text）。
    - セキュリティ対策: defusedxml による XML パース、SSRF 防止のリダイレクトハンドラ（_SSRFBlockRedirectHandler）、ホストのプライベートアドレス検査。
    - レスポンスサイズの上限チェック（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍時の追加チェック（Gzip bomb 対策）。
    - URL 正規化とトラッキングパラメータ削除（_normalize_url）および SHA-256 による記事 ID 生成（先頭32文字）。
    - DB 保存（DuckDB）用関数: save_raw_news（チャンク挿入 + INSERT ... RETURNING による新規挿入ID返却）、save_news_symbols、_save_news_symbols_bulk。トランザクションを使用し失敗時にロールバック。
    - 銘柄抽出: テキスト中の4桁コード抽出（extract_stock_codes）および run_news_collection による統合収集ジョブ。

- Research（特徴量・ファクター）
  - kabusys.research.factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev の計算（DuckDB 上の window 関数を利用）。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率などを計算。
    - calc_value: raw_financials から最新財務を結合して PER / ROE を計算（target_date 以前の最新レコードを取得）。
  - kabusys.research.feature_exploration:
    - calc_forward_returns: target_date を基準に複数ホライズンの将来リターンを一括取得。
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）計算。
    - factor_summary: カラムごとの count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクとなるランク付けユーティリティ。浮動小数点丸め（round(v,12)）で ties の誤検出を防止。
  - kabusys.research.__init__: 主要関数群を再エクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize 等）。

- 設計・実装ノート
  - Research モジュールは外部 API（発注等）へアクセスしない設計。DuckDB の prices_daily / raw_financials のみを参照。
  - NewsCollector は SSRF や大容量レスポンス対策、防御的 XML パースなどセキュリティに配慮した実装。

### Changed
- 初版のため該当なし。

### Fixed
- 初版のため該当なし。

### Security
- RSS/XML: defusedxml を使用して XML ベース攻撃を抑止。
- RSS フェッチ: リダイレクト時にスキーム検証とプライベートアドレス判定を行うことで SSRF を対策（_SSRFBlockRedirectHandler, _is_private_host）。
- 外部 HTTP 呼び出しでのレスポンスサイズ制限（MAX_RESPONSE_BYTES）と gzip 解凍後の検査によりメモリ DoS / Gzip bomb を軽減。
- J-Quants クライアントは 401 時の自動トークンリフレッシュ処理を限定的に実行し、無限再帰を防止（allow_refresh フラグ）。

### Deprecated
- なし

### Removed
- なし

### Notes / Known limitations
- research モジュールは標準ライブラリのみで実装されている箇所があり（feature_exploration の注記など）、大規模データ処理の際は pandas 等の導入を検討して性能改善を行う余地がある。
- strategy, execution, monitoring パッケージは初期化ファイルのみ（空）で、各種発注ロジック・モニタリング機能は今後実装予定。
- schema.py の DDL は Raw レイヤー中心で記載されているが、ファイル末尾の raw_executions 定義はソース内で途中までの断片が含まれている（以降のカラム定義は今後継続実装の可能性あり）。必要に応じて追加のテーブル定義（Processed / Feature / Execution レイヤー）を整備してください。

---

作者・貢献者: コードベースから推測した初期実装のまとめ（自動生成ドキュメント）。README / DataSchema.md / StrategyModel.md 等の設計ドキュメント参照が想定されています。