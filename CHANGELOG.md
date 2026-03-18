CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog の慣習に従います。
※日付はコードベースから推測して付与しています。

[Unreleased]
------------

なし

[0.1.0] - 2026-03-18
--------------------

Added
- 初回リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを実装。
- パッケージ初期化
  - src/kabusys/__init__.py: パッケージ名、バージョン（0.1.0）、公開モジュール一覧（data, strategy, execution, monitoring）を定義。
- 設定/環境変数管理
  - src/kabusys/config.py:
    - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装（OS 環境変数 > .env.local > .env の優先順位）。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）により CWD に依存しないロードを実現。
    - .env パーサーは export プレフィックス、クォート・エスケープ、行内コメント判定等に対応。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応（テスト用途）。
    - Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_*, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL 等のプロパティ）。
    - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）と環境判定ユーティリティ（is_live / is_paper / is_dev）。
- Data レイヤ
  - src/kabusys/data/schema.py:
    - DuckDB 用スキーマ（Raw Layer を中心に raw_prices / raw_financials / raw_news / raw_executions 等の DDL を定義・初期化する基盤）。
    - テーブル定義は主キー・チェック制約を含む（データ整合性を念頭に設計）。
  - src/kabusys/data/jquants_client.py:
    - J-Quants API クライアントを実装。
    - レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter を実装。
    - リトライ戦略（指数バックオフ、最大3回）および 408/429/5xx のリトライ対象判定。
    - 401 受信時に自動でリフレッシュトークンから id_token を取得して 1 回リトライするロジック。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB への冪等保存（save_daily_quotes / save_financial_statements / save_market_calendar）を実装（ON CONFLICT DO UPDATE）。
    - 型変換ユーティリティ（_to_float / _to_int）で入力データの堅牢な処理。
  - src/kabusys/data/news_collector.py:
    - RSS フィードからニュース記事を収集・保存する一連の機能を実装。
    - defusedxml による XML パースで安全性を確保。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）と記事ID（SHA-256 の先頭32文字）生成による冪等性。
    - SSRF 対策:
      - リダイレクト時にスキーム/ホストを検査するカスタムリダイレクトハンドラ。
      - ホストがプライベートアドレス/ループバック等であればアクセスを拒否。
      - 事前にホストを検証してプライベートアドレスへのアクセスをブロック。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - コンテンツ前処理（URL 除去・空白正規化）と記事の DB 保存（save_raw_news: INSERT ... RETURNING を使い実挿入IDを返す）。
    - 銘柄コード抽出（4 桁の数字パターン）と news_symbols への紐付け保存（バルク挿入・トランザクション処理）。
    - run_news_collection: 複数ソースを逐次処理し、ソース単位で例外を隔離して継続する処理フロー。
- Research / Feature 工学
  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算 calc_forward_returns（1/5/21 営業日などホライズン対応）、IC（calc_ic：Spearman の ρ の実装）、factor_summary（基本統計量）、rank（同順位平均ランクの実装）を追加。
    - DuckDB の prices_daily テーブル参照のみで動作するよう設計。外部ライブラリ（pandas 等）に依存しない実装。
  - src/kabusys/research/factor_research.py:
    - ファクター計算（calc_momentum, calc_volatility, calc_value）を実装。
    - モメンタム（1m/3m/6m、200 日移動平均乖離）、ボラティリティ（20 日 ATR、相対 ATR、出来高比率）、バリュー（PER, ROE）等を DuckDB の prices_daily / raw_financials を用いて算出。
    - データ不足時の None 処理やウィンドウサイズチェックを実装。
  - src/kabusys/research/__init__.py:
    - 主要関数をエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
    - zscore_normalize は kabusys.data.stats から利用（データ正規化ユーティリティ）。
- 研究・運用での安全策や疎結合化のため、テスト時に置換可能なフックを用意（例: news_collector._urlopen のモック差し替え）。

Security
- NewsCollector:
  - defusedxml を利用して XML 攻撃（XML bomb 等）を防止。
  - SSRF 対策を複数層で実装（事前ホストチェック + リダイレクトハンドラの検査）。
  - レスポンスサイズ制限および gzip 解凍後の再チェックを導入。
- J-Quants クライアント:
  - レートリミットを守る設計、リトライ対象の適切なハンドリング、401 時の自動トークンリフレッシュで不正な滑走を防止。

Performance
- API クライアントでページネーションをサポートし、ページ間で id_token をキャッシュして無駄な認証リクエストを削減。
- DuckDB へのバルク挿入やチャンク処理（news_collector の chunked INSERT）により大規模データ挿入時のオーバーヘッドを低減。
- research モジュールは SQL ウィンドウ関数で集約を行い、可能な限り DuckDB 側で計算してメモリ負荷を抑制。

Configuration / 環境変数
- 必須（Settings._require によるチェック対象）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- 任意 / デフォルトあり
  - KABUSYS_ENV (development / paper_trading / live; デフォルト: development)
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL; デフォルト: INFO)
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - KABUSYS_DISABLE_AUTO_ENV_LOAD (1 で自動 .env ロードを無効化)

Notes / Known limitations
- research の設計方針として pandas 等の外部ライブラリに依存していないため、多機能だが一部の高機能集計（例: グループごとの複雑な欠損補完）は今後の拡張余地あり。
- calc_value では現状 PER と ROE のみ実装。PBR・配当利回り等は未実装。
- ニュース中の銘柄抽出は 4 桁の数値パターンに限定（偽陽性/偽陰性の可能性あり）。known_codes セットを渡してフィルタする設計。
- DuckDB スキーマ定義は Raw Layer を中心に実装。Processed / Feature / Execution レイヤは今後の拡張で DDL・ETL を追加予定。
- 一部の SQL は DuckDB のウィンドウ関数や ROW_NUMBER を前提としているため、別の RDBMS への移植はそのままでは動作しない可能性あり。

Deprecated
- なし（初回リリース）

Removed
- なし（初回リリース）

Acknowledgements / Implementation choices
- Look-ahead bias 回避のため、外部データ取得時に fetched_at を UTC で記録する設計を採用。
- API/HTTP 関連は標準ライブラリ urllib を使用し、外部依存を最小化。
- セキュリティ重視の実装（SSRF・XML・サイズ制限等）を優先。

--- 

補足:
- 本 CHANGELOG は提供されたコードベースの実装から推測して作成しています。将来のリリースや実運用にあたっては、実際のコミット履歴やリリースノートに合わせて更新してください。