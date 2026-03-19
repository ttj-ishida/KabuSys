CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。

フォーマットの意味:
- Added: 新規機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティ関連の改善

Unreleased
----------

（現時点では未リリースの変更はありません）

0.1.0 - 2026-03-19
-----------------

Added
- パッケージ初期リリース。
- パッケージメタ情報（kabusys.__version__ = 0.1.0、公開モジュール一覧）を追加。

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動ロード機能を実装。読み込み優先順位は OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用途）。
  - プロジェクトルートを .git または pyproject.toml から探索する実装（CWD 非依存）。
  - .env 行解析の堅牢化:
    - export プレフィックス対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメント・アンコメント処理の改善
  - 環境変数取得ユーティリティ _require と Settings クラスを提供（J-Quants トークン、kabu API パスワード、Slack トークン/チャネル、DB パス等）。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値のチェック）、および is_live / is_paper / is_dev のプロパティを提供。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - 固定間隔の RateLimiter によるレート制御（デフォルト 120 req/min）。
    - 冪等な DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）：ON CONFLICT DO UPDATE を使用。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - リトライ（指数バックオフ、最大 3 回）および 401 受信時の自動トークンリフレッシュ処理。
    - JSON デコード失敗や各種 HTTP エラーのハンドリング。
    - 取得日時（fetched_at）を UTC ISO8601 で記録し、Look-ahead バイアス対策を意識。
    - 安全な型変換ユーティリティ _to_float / _to_int（不正データに対して None を返す）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュースを取得・前処理・DuckDB へ保存する実装（デフォルトに Yahoo Finance のビジネス RSS を含む）。
  - セキュリティ・堅牢性を考慮した実装:
    - defusedxml を利用した XML パース（XML Bomb 対策）。
    - SSRF 対策: URL スキーム検証、リダイレクト時のスキーム/ホスト検査、ホストがプライベート/ループバック/リンクローカル/マルチキャストかの判定。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 対策、gzip 解凍後のサイズチェック。
    - トラッキングパラメータ（utm_*, fbclid 等）の除去と URL 正規化、正規化 URL の SHA-256（先頭32文字）を用いた記事ID生成。
    - URL のスキームが http/https 以外は拒否。
  - テキスト前処理ユーティリティ（URL 除去・空白正規化）。
  - 保存処理:
    - save_raw_news: チャンク分割して INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、新規挿入された記事IDのリストを返す。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの記事-銘柄紐付けをチャンク・トランザクションで保存（重複除去 / RETURNING による正確な件数取得）。
  - 銘柄抽出ロジック（4桁数値パターン）と既知銘柄フィルタリングを提供。
  - run_news_collection: 複数 RSS ソースの統合収集ジョブ（ソースごとに独立してエラーハンドリング）。

- リサーチ（kabusys.research）
  - feature_exploration モジュール:
    - calc_forward_returns: 指定日の終値から複数ホライズン（例: 1,5,21 営業日）での将来リターンを一度のクエリで取得。
    - calc_ic: スピアマンランク相関（Information Coefficient）計算。欠損や非有限値を除外し、有効レコードが少ない場合は None を返す。
    - rank: 同順位は平均ランクを付与するランク関数（丸めによる ties 検出漏れ対策として round を使用）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - すべて標準ライブラリのみで実装し、DuckDB の prices_daily テーブルを参照する設計（pandas 等に依存しない）。
  - factor_research モジュール:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を計算。必要な過去データがない場合は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を算出。true_range の NULL 伝播を正確に扱う。
    - calc_value: raw_financials から最新の財務（target_date 以前）を取得して PER（EPS が 0/NULL の場合は None）と ROE を計算。prices_daily と結合して出力。
    - 各関数は DuckDB の prices_daily / raw_financials テーブルのみ参照し、本番 API へはアクセスしないことを明記。

- DuckDB スキーマ定義（kabusys.data.schema）
  - DataSchema.md に基づくスキーマ定義（Raw / Processed / Feature / Execution 層の方向づけ）。
  - raw_prices, raw_financials, raw_news 等の DDL を定義。PRIMARY KEY・チェック制約を含むテーブル定義を追加。
  - スキーマ初期化向けの DDL 管理モジュール。

Security
- news_collector: defusedxml の採用、SSRF ブロック用のリダイレクトハンドラ、ホストのプライベート判定、レスポンスサイズ制限、URL スキーム検証など複数の対策を実装。
- jquants_client: API リクエストの再試行とトークン自動リフレッシュを実装し、不正応答や一時障害への耐性を高めた。

Notes / Known limitations
- research モジュールは外部ライブラリ（pandas, numpy 等）に依存しない設計だが、大規模データの集計・処理ではパフォーマンス面で追加最適化や外部ライブラリ導入の余地あり。
- schema モジュールの DDL は raw_executions の定義が途中まで（提供コードの切れ）になっているため、エグゼキューション周りの完全なテーブル定義は今後の更新で補完が必要。
- strategy および execution パッケージの __init__.py はプレースホルダ（空）であり、発注ロジックやストラテジ管理の具体実装はまだ含まれていない。
- data.stats の zscore_normalize は参照されているが、今回のスナップショットに該当実装が含まれていない（別ファイルに存在する想定）。

Backwards compatibility
- 初回リリースのため、過去互換性に関する注意点はなし。

作者
- KabuSys チーム

--- 

（補足）本CHANGELOGは提供されたソースコードの内容から機能・設計方針を推測して作成しました。実装の内部ドキュメントや将来的な変更に合わせて更新してください。