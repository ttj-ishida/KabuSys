# Changelog

すべての注目すべき変更はここに記録します。これは Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

なお、この CHANGELOG はリポジトリ内のコードから推測して作成した初期リリースの概要です。

## [Unreleased]
- （今後の変更やマイナー修正をここに記載）

## [0.1.0] - 2026-03-18
初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを導入。トップレベルで data, strategy, execution, monitoring を公開。
  - バージョンを `0.1.0` に設定（src/kabusys/__init__.py）。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数の自動読み込み実装（プロジェクトルートの自動検出: .git または pyproject.toml を基準）。
  - robust な .env パーサを実装（export 形式、クォート・エスケープ、インラインコメント処理に対応）。
  - 自動ロードを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを導入し、J-Quants/Slack/DB/システム設定を環境変数から提供。必須キー未設定時は ValueError を送出。
  - KABUSYS_ENV と LOG_LEVEL の値検証を追加（有効値の検証）。

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - レート制限（120 req/min）を守る固定間隔 RateLimiter を導入。
  - 再試行（指数バックオフ、最大 3 回）とステータスに応じたリトライ制御を実装。429 の Retry-After を尊重。
  - 401 受信時はリフレッシュトークンで自動的に id_token を更新して 1 回リトライ。
  - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
  - DuckDB に対する冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT によるアップサート処理を行う。
  - 型変換ユーティリティ（_to_float, _to_int）を実装し、不正値の扱いを明確化。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからニュースを収集し raw_news へ保存するモジュールを追加。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、スキーム/ホスト小文字化、フラグメント除去）と記事ID（正規化 URL の SHA-256 先頭32文字）生成を実装。
  - defusedxml を用いた安全な XML パースを実装し XML Bomb 等への対策を行う。
  - SSRF 対策: リダイレクト時にスキーム/ホストの検証を行うカスタム RedirectHandler、ホストのプライベート判定（IPv4/IPv6 と DNS 解決でチェック）を導入。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）や gzip の解凍後サイズ検査を実装（圧縮攻撃対策）。
  - テキスト前処理ユーティリティ（URL 除去、空白正規化）と RSS pubDate の堅牢なパース関数を追加。
  - DB 保存ロジックはチャンク化してトランザクション内で行い、INSERT ... RETURNING を使用して実際に挿入された記事 ID を返す（save_raw_news）。
  - 銘柄コード抽出（4桁数字）と news_symbols への紐付けバルク保存機能を実装（重複除去、チャンク挿入）。

- スキーマ定義 (kabusys.data.schema)
  - DuckDB 用のスキーマ定義モジュールを追加（Raw / Processed / Feature / Execution 層の方針をコメントで記載）。
  - raw_prices, raw_financials, raw_news, raw_executions 等のテーブル DDL を定義（各テーブルのカラム、型、制約、主キーを明記）。

- リサーチ / ファクター計算 (kabusys.research)
  - ファクター計算モジュールを追加（kabusys.research.factor_research）。
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（MA200）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（true range ベース）、ATR の相対値（atr_pct）、20日平均売買代金、出来高比（volume_ratio）を計算。
    - calc_value: raw_financials と prices_daily を組み合わせ、PER（EPS が 0 または欠損の場合は None）と ROE を計算。
  - 特徴量探索モジュールを追加（kabusys.research.feature_exploration）。
    - calc_forward_returns: 指定日から各ホライズン（デフォルト 1,5,21営業日）先の将来リターンを一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコードが 3 未満なら None）。
    - rank: 同順位は平均ランクを返すランク化ユーティリティ（丸めによる ties 検出対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - kabusys.research.__init__ で主要関数を再エクスポート（zscore_normalize は kabusys.data.stats から）。

- API 設計上の考慮
  - Research / Data モジュールは prices_daily / raw_financials / raw_prices / raw_news 等の DB テーブルのみを参照し、本番発注 API や実口座へのアクセスは行わない設計を明記。
  - Look-ahead bias 防止のため、取得時刻（fetched_at）を UTC で記録する仕様。

### セキュリティ (Security)
- news_collector: defusedxml を使った XML パース、SSRF 対策（リダイレクト検査・プライベート IP チェック）、最大レスポンスサイズ制限、gzip 解凍後のサイズ検査を実装。
- jquants_client: ネットワーク / HTTP エラーに対する堅牢な再試行ロジック、トークンリフレッシュ時の無限再帰回避（allow_refresh フラグ）を実装。

### パフォーマンス (Performance)
- J-Quants の取得はページネーションをサポートし、モジュールレベルのトークンキャッシュを共有して複数ページ間の再認証を抑制。
- DuckDB への保存は executemany / チャンク化 / トランザクションを利用し、挿入オーバーヘッドを低減。
- calc_forward_returns 等の分析は必要範囲を限定して 1 クエリで複数ホライズンを取得することでクエリ回数を削減。

### その他 / ドキュメント
- 各モジュールに設計方針・注意点を docstring とコメントで明記（Look-ahead 防止、外部 API 不使用の方針等）。
- 多くの関数で入力検証（パラメータの型/範囲チェック）、エラーハンドリング、ログ出力を整備。

---

今後のリリースでは、strategy / execution / monitoring の具象実装（発注ロジック・モニタリング・バックテスト等）や、
追加のデータソース・テーブル拡張・ユニットテスト・CI/CD 設定などを追記する予定です。