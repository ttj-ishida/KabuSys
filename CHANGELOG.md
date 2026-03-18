# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
初回リリース v0.1.0 をコードベースから推測して作成しました。

全般な注意
- 本プロジェクトは日本株のデータ収集・特徴量生成・リサーチおよび実運用向け自動売買を念頭に設計されています。
- DuckDB を主要なストレージ層として想定し、外部発注 API など本番系操作と研究系処理を分離する設計方針が取られています。
- 可能な限り外部ライブラリへの依存を抑え（研究モジュールでは標準ライブラリのみを利用）、冪等性・セキュリティ・運用性を重視しています。

## [0.1.0] - 初回リリース（推定）
リリース日: 未設定

### 追加
- パッケージ基盤
  - パッケージ初期化を追加（kabusys.__init__.py）。公開モジュール: data, strategy, execution, monitoring。
  - バージョン情報を 0.1.0 として定義。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行うため、CWD に依存しない挙動を採用。
  - .env のパースは以下をサポート／安全対策を実装：
    - 空行・コメント行の無視、先頭に `export ` のある行のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしのインラインコメント扱いルール（直前がスペース/タブの場合は '#' をコメントとみなす）
  - .env の読み込み優先順位: OS 環境変数 > .env.local > .env（.env.local は上書き許可）
  - OS 環境変数を保護する protected セットの概念を導入（既存環境変数を上書きしない）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - Settings クラスを提供し、必須環境変数取得（_require）や型変換・検証を encapsulate：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須プロパティ
    - パス系設定（DUCKDB_PATH, SQLITE_PATH）は Path に変換して返却
    - KABUSYS_ENV の有効値検証（development / paper_trading / live）
    - LOG_LEVEL の有効値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - ヘルパー: is_live / is_paper / is_dev

- Data: J-Quants クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装（取得・保存用ユーティリティ群）。
  - レート制御: 固定間隔スロットリングに基づく _RateLimiter（120 req/min に対応）。
  - リトライ戦略: 指数バックオフ、最大 3 回、HTTP 状態コード 408/429/5xx を再試行対象に設定。429 の場合は Retry-After ヘッダを優先。
  - 認証トークン取得/管理:
    - get_id_token(refresh_token) を実装（POST /token/auth_refresh）。
    - モジュールレベルの ID トークンキャッシュを導入し、ページネーション間で共有。
    - リクエスト実行中に 401 を受けた場合はトークンを 1 回だけ自動リフレッシュして再試行。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（pagination_key を扱う）
  - DuckDB への保存関数（冪等性を考慮）:
    - save_daily_quotes -> raw_prices へ INSERT ... ON CONFLICT DO UPDATE
    - save_financial_statements -> raw_financials へ INSERT ... ON CONFLICT DO UPDATE
    - save_market_calendar -> market_calendar へ INSERT ... ON CONFLICT DO UPDATE
  - データ変換ユーティリティ: _to_float / _to_int（不正・空値を安全に None に変換、int 変換時の小数部チェック）

- Data: ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからニュースを安全に収集・正規化して DuckDB の raw_news / news_symbols に保存する機能を実装。
  - セキュリティ・堅牢性:
    - defusedxml を利用した XML パース（XML Bomb 対策）。
    - SSRF 対策: 初期 URL とリダイレクト先のスキーム検証（http/https のみ）とホストがプライベート/ループバック/リンクローカル/マルチキャストでないことをチェック（DNS 解決済み検査）。
    - リダイレクト検査用のカスタム HTTPRedirectHandler (_SSRFBlockRedirectHandler) を利用。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後のサイズ検証（Gzip bomb 対策）。
    - URL 正規化: トラッキングパラメータ（utm_*, fbclid, gclid 等）の除去、スキーム/ホスト小文字化、フラグメント削除、クエリパラメータソート。
    - 記事 ID は正規化 URL の SHA-256 の先頭32文字を使用（冪等性確保）。
  - フィードパース/前処理:
    - title / content の前処理（URL 除去、空白正規化）
    - pubDate の RFC 日時パース（UTC 変換、パース失敗時は現在時刻を代替し警告ログ）
    - content:encoded の名前空間処理をサポート
  - DB 保存:
    - save_raw_news: チャンク挿入（_INSERT_CHUNK_SIZE = 1000）＋トランザクションでまとめて挿入、INSERT ... ON CONFLICT DO NOTHING RETURNING id により実際に保存された ID を返す。
    - save_news_symbols / _save_news_symbols_bulk: (news_id, code) ペアの一括保存（重複除去、チャンク挿入、トランザクション、RETURNING による正確な挿入数取得）。
  - 銘柄抽出:
    - extract_stock_codes: 正規表現で 4 桁数字を抽出し、known_codes に含まれるもののみを返却（重複除去）。

- Data: スキーマ定義 (kabusys.data.schema)
  - DuckDB 用の DDL（Raw 層のテーブル定義）を追加:
    - raw_prices, raw_financials, raw_news, raw_executions（途中までコードあり）
  - Data 層の 3 層（Raw / Processed / Feature）構想に基づく設計コメントを含む。

- Research: ファクター・リサーチ (kabusys.research)
  - feature_exploration.py:
    - calc_forward_returns(conn, target_date, horizons=None): DuckDB の prices_daily を参照し、指定日から各ホライズン（日数）後の終値リターンを計算（複数ホライズンを一度に取得）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): Spearman の ρ（ランク相関）を計算。レコード結合、None/非有限値の除外、3 件未満は None を返す。
    - rank(values): 同順位は平均ランクで扱い、丸め誤差を避けるために round(v, 12) を用いて ties を正しく処理。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する軽量統計サマリー。
    - これらは pandas 等に依存せず標準ライブラリと duckdb のみで実装。
  - factor_research.py:
    - calc_momentum(conn, target_date): mom_1m / mom_3m / mom_6m / ma200_dev を計算。200日移動平均はウィンドウ内データが 200 件未満なら None。
    - calc_volatility(conn, target_date): atr_20（20 日 ATR）、atr_pct（ATR / close）、avg_turnover（20日平均売買代金）、volume_ratio（当日出来高 / 20日平均）を計算。true_range の NULL 伝播を正しく扱う実装。
    - calc_value(conn, target_date): raw_financials の target_date 以前の最新財務データと当日の株価を結合して PER（EPS が 0/欠損なら None）と ROE を計算。
    - 日数スキャン範囲やバッファ（週末・祝日吸収）の設計、営業日ベースのホライズン扱いなどを明記。
  - kabusys.research.__init__ で主要関数群をエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### 改善
- 安全性・運用性の向上
  - API クライアントでトークン自動リフレッシュ・リトライ・レート制御を実装し、外部サービス呼び出しの堅牢性を強化。
  - ニュース収集で SSRF 対策、XML パースの堅牢化、受信サイズ制限、gzip 対応等を実装。
  - DuckDB への保存を冪等に（ON CONFLICT）して上書き戦略を明確化。
  - news_collector の大量挿入はチャンク化して SQL 長やパラメータ数の上限に配慮。

### 仕様
- 研究モジュールは本番 API（発注等）には一切アクセスしない設計を明記（安全なリサーチ環境）。
- 主要な日数定数（モメンタム・ATR・MA200 等）はソースコード内に定義され、設計意図（営業日ベース / カレンダーバッファ）をコメントで記載。
- 外部依存（pandas 等）を使わずに動作する実装方針を明記（軽量・移植性重視）。

### 既知の未完事項（コードから推測）
- schema.py の raw_executions テーブル定義が途中で終わっており、Execution レイヤー（発注・約定・ポジション管理）の完全定義は未完と思われる。
- strategy / execution / monitoring パッケージは __init__ のみで中身が含まれていない（将来的な実装領域）。
- docs（使用例、API ドキュメント、運用手順書など）はコード内コメントはあるが別途ドキュメント整備が必要。

### セキュリティ修正 / 注意点
- ニュース収集での外部 URL 処理に関しては SSRF 対策や受信サイズ制限を導入済み。ただし DNS 解決失敗時に「安全側とみなす」箇所があるため、運用時はフィードソースの信頼性を確認することを推奨します。
- 環境変数の自動ロードはプロジェクトルート判定に依存するため、配布パッケージ等では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って制御可能。

---

今後のリリースでは以下を想定しています（提案）:
- Execution レイヤー（kabu ステーション連携、注文送信/約定処理）の実装
- Strategy モジュールの戦略モデル（ポジション管理・リスク制御）実装
- モニタリング（Slack 通知、DB ベースの監視）機能の追加
- スキーマの完成（Processed / Feature / Execution 層の DDL）
- 単体テスト・CI、例外・ログ出力の標準化ドキュメント整備

（以上）