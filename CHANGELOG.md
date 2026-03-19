# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
このプロジェクトの最初の公開リリースを示すエントリを以下に記載します。

全般的なルール:
- バージョンはパッケージの __version__ に従っています（src/kabusys/__init__.py）。
- 日付は本ファイル生成日（2026-03-19）を使用しています。

## [0.1.0] - 2026-03-19

### Added
- パッケージの初期公開
  - パッケージ名: KabuSys（src/kabusys）
  - バージョン: 0.1.0

- 環境・設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動ロード（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env と .env.local の読み込み順序と上書きルール（OS 環境変数は保護）。
  - .env 行パーサの強化:
    - `export KEY=val` 形式対応
    - シングル／ダブルクォート内でのバックスラッシュエスケープ処理
    - インラインコメントの扱い（クォート有無での違い）
  - 必須変数チェック用ヘルパー _require と Settings クラスを提供（J-Quants トークンや Slack 設定、DB パス、実行環境フラグ等をプロパティで取得）。
  - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の値検証（許容値の制限とエラーメッセージ）。

- Data 層（DuckDB）スキーマ定義（src/kabusys/data/schema.py）
  - Raw Layer のテーブル定義（raw_prices, raw_financials, raw_news, raw_executions を含む。DDL 定義により初期化可能）。
  - スキーマは DataSchema.md に準拠する設計（Raw / Processed / Feature / Execution の層構造）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しラッパ（_request）:
    - 固定間隔のレートリミッタ実装（120 req/min を想定）。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx に対するリトライ）。
    - 401 受信時の自動トークンリフレッシュを1回だけ行い再試行（再帰防止フラグあり）。
    - ページネーション対応と id_token のモジュールレベルキャッシュ（ページ間で共有）。
  - 認証ヘルパ get_id_token（refresh token から idToken を取得）。
  - データ取得関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応、取得ログ出力）。
  - DuckDB への永続化ユーティリティ（冪等保存）:
    - save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を使用して重複を排除）。
  - データ変換ユーティリティ: _to_float, _to_int（堅牢なパース；不正値は None）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事収集と DuckDB 保存ワークフローを実装。
  - 安全性重視の設計:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - SSRF 対策: 初回ホスト検証、リダイレクト時のホスト/スキーム検査を行うカスタムリダイレクトハンドラ（_SSRFBlockRedirectHandler）。
    - URL スキームの検証（http/https のみ許可）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の追加検査（Gzip bomb 対策）。
    - トラッキングパラメータ（utm_*, fbclid など）を除去する URL 正規化。
  - 記事 ID の生成: 正規化 URL の SHA-256 の先頭32文字により冪等性を確保。
  - テキスト前処理: URL 除去・空白正規化（preprocess_text）。
  - RSS パースと記事生成（fetch_rss）: content:encoded 優先、pubDate の RFC パース（失敗時は警告と現在時刻で代替）。
  - DB 保存処理:
    - save_raw_news: バルク挿入（チャンク）＋トランザクション、INSERT ... RETURNING を用いて実際に挿入された記事IDを返す。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをバルク挿入（重複除去・チャンク・トランザクション）。
  - 銘柄コード抽出ユーティリティ: 日本株の4桁コード抽出と known_codes によるフィルタ（extract_stock_codes）。
  - 統合ジョブ run_news_collection: 複数ソースの独立処理、known_codes による紐付け処理、ソース単位のエラーハンドリングと集計結果返却。
  - デフォルト RSS ソース定義（Yahoo Finance のビジネスカテゴリ等）。

- 研究（Research）モジュール
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: DuckDB の prices_daily を参照して各銘柄の将来リターン（デフォルト horizons=[1,5,21]）を一クエリで取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（NaN/None の除外、最小有効サンプル数チェック）。
    - rank: 同順位は平均ランクとして扱うランク付け（丸めによる ties の過小検出対策あり）。
    - factor_summary: 各ファクター列に対する count/mean/std/min/max/median を算出（None を除外）。
    - 実装方針: DuckDB の prices_daily のみ参照、外部ライブラリに依存しない（標準ライブラリのみ）。
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均乖離）を計算。データ不足時は None を返す。ウィンドウは営業日ベースで計算。
    - calc_volatility: atr_20（20日 ATR の単純平均）、atr_pct（ATR/close）、avg_turnover（20日平均売買代金）、volume_ratio（当日出来高/20日平均）を計算。true_range の NULL 伝播制御やカウント条件を明示。
    - calc_value: raw_financials と prices_daily を組み合わせて per（株価/EPS）と roe を計算。target_date 以前の最新財務レコードを銘柄ごとに取得。
    - 各ファクター関数は DuckDB 接続を受け取り、(date, code) をキーとする辞書リストを返す。
  - research パッケージ __all__ を通じて主要ユーティリティを公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- パッケージ初期化（src/kabusys/__init__.py）
  - __version__ = "0.1.0"
  - __all__ に主要サブパッケージを列挙（data, strategy, execution, monitoring）

### Security
- RSS / HTTP 周りの堅牢化
  - defusedxml を用いた XML パース（XML に起因する脆弱性を低減）。
  - SSRF 対策: ホストのプライベートアドレス判定、リダイレクト時の事前検査、許可スキームの限定（http/https）。
  - レスポンスサイズ制限と gzip 解凍後の検査によりメモリ DoS / Gzip bomb を防止。
- J-Quants API クライアント側の堅牢化
  - 再試行ロジックおよびトークン自動リフレッシュにより認証エラーや一時的なサービスエラーの耐性を向上。

### Internal / Other
- ロギングを広く導入（各処理で info/warning/debug レベルのログを出力）。
- DuckDB 操作はトランザクションで保護（news_collector の挿入処理など）。
- 外部依存関係の明示:
  - duckdb（データベース操作）
  - defusedxml（XML パースの安全化）
  - その他標準ライブラリ（urllib, json, logging, datetime, hashlib, ipaddress 等）

### Known limitations / Notes
- Strategy / execution / monitoring の具象実装は本リリースでは空のパッケージプレースホルダのみ（src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py 等）。
- 一部スキーマファイルは Raw Layer の定義を主体としており、Processed/Feature/Execution 層の追加 DDL は今後の拡張対象。
- research モジュールは外部ライブラリ（pandas 等）に依存しない実装だが、実運用での大規模データ処理や高速化を目的とした最適化は今後の課題。

---

今後のリリース案内やバグ修正・機能追加については CHANGELOG に逐次追記していきます。