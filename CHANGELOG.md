CHANGELOG
=========

すべての注目すべき変更点を記載します。  
このファイルは「Keep a Changelog」のフォーマットに準拠しています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Removed: 削除
- Deprecated: 非推奨
- Security: セキュリティ関連の修正

Unreleased
----------

（現時点の未リリース変更はありません）

0.1.0 - 2026-03-18
------------------

Added
- 初回リリース。KabuSys の基本モジュール群を追加。
  - パッケージメタ情報
    - src/kabusys/__init__.py に __version__ = "0.1.0" と公開 API（data, strategy, execution, monitoring）を定義。
  - 設定・環境変数管理
    - src/kabusys/config.py
      - プロジェクトルート自動検出（.git または pyproject.toml を基準）による .env 自動読み込み機能を実装。
      - .env/.env.local の読み込み順（OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
      - 行パースの強化（export 形式、クォート内部のバックスラッシュエスケープ、インラインコメント処理等に対応）。
      - protected 引数による既存 OS 環境変数保護（override ロジック）。
      - settings オブジェクトを提供し、J-Quants / kabu API / Slack / DB パス / 環境種別・ログレベルなどをプロパティで取得。値検証（有効な env 値・ログレベル等）。
  - Data 層（J-Quants クライアント・ニュース収集・スキーマ）
    - src/kabusys/data/jquants_client.py
      - J-Quants API クライアントを実装。ページネーション対応（pagination_key）、fetch_* 系 API（daily_quotes, financial_statements, market_calendar）を提供。
      - レート制限（120 req/min）の固定間隔スロットリング実装（RateLimiter）。
      - 再試行（指数バックオフ、最大3回）と HTTP ステータスに応じた振る舞い（408/429/5xx のリトライ）。
      - 401 レスポンス時の自動トークンリフレッシュ（1回のみ）とモジュールレベルの ID トークンキャッシュ。
      - DuckDB への冪等保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT DO UPDATE による更新処理。
      - 型変換ユーティリティ (_to_float, _to_int) による入力整形。
    - src/kabusys/data/news_collector.py
      - RSS フィードからのニュース収集機能を実装（fetch_rss, save_raw_news, save_news_symbols 等）。
      - トラッキングパラメータ除去を含む URL 正規化、記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
      - defusedxml を用いた XML パース（XML Bomb 対策）、gzip 解凍対応、レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）によるメモリ DoS 対策。
      - SSRF 対策: URL スキーム検証（http/httpsのみ許可）、リダイレクト時のホスト検査（プライベートアドレス拒否）を導入。_SSRFBlockRedirectHandler / _urlopen を提供し、テスト時に差し替え可能。
      - DB への一括挿入をチャンク (INSERT_CHUNK_SIZE) ごとに実行し、トランザクションでまとめることで効率と整合性を確保。INSERT ... RETURNING を用いて実際に挿入された件数を正確に取得。
      - テキスト前処理（URL 除去・空白正規化）とテキストからの銘柄コード抽出機能（4桁数値、既知コード集合でフィルタリング）。
      - run_news_collection により複数ソースの独立エラーハンドリングと銘柄紐付けを一括処理。
    - src/kabusys/data/schema.py
      - DuckDB 向けスキーマ定義（Raw Layer を中心に raw_prices, raw_financials, raw_news, raw_executions 等の DDL を追加：CREATE TABLE IF NOT EXISTS）。
  - Research 層（特徴量・ファクター計算）
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算（calc_forward_returns）：DuckDB の prices_daily を参照し、任意のホライズン（デフォルト [1,5,21]）で fwd_* を一括取得。ホライズンの検証とパフォーマンス考慮（検索範囲の限定）を実装。
      - スピアマン IC 計算（calc_ic）：ファクターと将来リターンを code で結合しランク相関を計算。サンプル不足や定数分散時は None を返す。
      - ランク生成ユーティリティ（rank）：同順位は平均ランクを採用し、丸めで ties 検出を安定化。
      - factor_summary：各カラムの count/mean/std/min/max/median を計算する統計サマリー。
    - src/kabusys/research/factor_research.py
      - モメンタム（calc_momentum）：mom_1m/mom_3m/mom_6m および 200日移動平均乖離（ma200_dev）を計算（prices_daily を参照、データ不足時は None）。
      - ボラティリティ/流動性（calc_volatility）：20日 ATR、相対ATR（atr_pct）、20日平均売買代金、出来高比（volume_ratio）を計算。true_range の NULL 伝播制御により正確なカウントを実現。
      - バリュー（calc_value）：raw_financials から基準日以前の最新財務を取得し PER/ROE を計算。報告日以前の最新レコード抽出に ROW_NUMBER を使用。
    - src/kabusys/research/__init__.py
      - 主要ユーティリティを再エクスポート（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize）。
  - その他
    - 型注釈（typing）と詳細な docstring により API 使用方法と設計方針を明示。
    - pandas 等の外部データ処理ライブラリに依存しない実装（標準ライブラリと DuckDB / defusedxml を主に利用）。

Security
- RSS ニュース収集における SSRF 対策を実装（スキーム検証、リダイレクト先のプライベートアドレス拒否、取得前のホスト検証）。
- XML パースに defusedxml を使用し XML ベースの攻撃（XML Bomb など）を軽減。
- J-Quants API クライアントにおいてトークン自動リフレッシュと適切な再試行ロジックを実装し、不正な認証状態や一時的なネットワーク障害への耐性を向上。

Notes / Known behaviour
- 多くの解析関数はデータ不足時に None を返す（例: 移動平均が十分な行数を持たない場合など）。これは look-ahead bias を避けるための設計意図です。
- J-Quants データ取得はモジュール内でトークンキャッシュを共有するため、ページネーション間で ID トークンを再利用します。キャッシュ強制更新も可能。
- news_collector の URL 正規化は既知のトラッキングパラメータプレフィックスを除去しますが、未知のパラメータに関してはそのまま残る可能性があります。
- スキーマ定義は Raw Layer を中心に整備済み。プロダクション運用に当たっては追加テーブル（Processed / Feature / Execution layer）の DDL も今後拡張予定。

Acknowledgements / Dependencies
- DuckDB (duckdb) をデータ層に使用。
- defusedxml を RSS XML の安全な解析用に使用。
- 標準ライブラリで可能な限り実装（pandas などには依存しない方針）。

以上。今後のリリースでは、Strategy 実装、Execution（kabu ステーション連携）、モニタリング/Slack 通知、Processed/Feature レイヤの拡充、テストカバレッジ拡大を予定しています。