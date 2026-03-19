CHANGELOG
=========
すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

[未リリース]
------------

- なし

[0.1.0] - 2026-03-19
--------------------

追加 (Added)
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
- 環境設定モジュール (src/kabusys/config.py)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込みする仕組みを実装。
  - 読み込み順序: OS環境 > .env.local > .env。テスト等で自動読み込みを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env のパース機能を実装（コメント処理、export プレフィックス、クォートとバックスラッシュエスケープ対応、インラインコメント処理など）。
  - Settings クラスを提供し、J-Quants トークン、kabu API 設定、Slack トークン/チャンネル、DB パス、環境（development/paper_trading/live）やログレベル検証等のプロパティを公開。
  - 環境変数必須チェックを行う _require() を実装。

- データ層 (src/kabusys/data/)
  - J-Quants クライアント (src/kabusys/data/jquants_client.py)
    - API 呼び出しのための汎用 HTTP ユーティリティと _request 実装（JSON パース、最大リトライ、指数バックオフ）。
    - レート制御: 固定間隔スロットリングによる 120 req/min の RateLimiter 実装。
    - 401 に対する自動トークンリフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュ。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
    - DuckDB への保存関数 save_daily_quotes / save_financial_statements / save_market_calendar を実装（冪等: ON CONFLICT DO UPDATE）。
    - 数値変換ユーティリティ _to_float / _to_int（安全な数値パースと不正値の扱い）。
  - ニュース収集モジュール (src/kabusys/data/news_collector.py)
    - RSS を取得して raw_news に保存するフローを実装（fetch_rss, save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
    - セキュリティ対策: defusedxml による XML パース、SSRF 対策のリダイレクト検査ハンドラ、プライベートアドレス判定（DNS 解決含む）、許可スキームは http/https のみ。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES）や gzip 解凍後の検査、Content-Length 事前チェックによる DoS 防止。
    - URL 正規化（トラッキングパラメータ除去、フラグメント削除、キーソート）と記事 ID 生成（URL 正規化後 SHA-256 の先頭 32 文字）による冪等性確保。
    - テキスト前処理（URL 除去、空白正規化）、銘柄コード抽出（4桁数字、known_codes によるフィルタ）を実装。
    - 複数件をチャンク分割して一括 INSERT、INSERT ... RETURNING により挿入された実行結果を正確に返す実装。
    - デフォルト RSS ソースを定義（例: Yahoo Finance のカテゴリ RSS）。
  - スキーマ定義 (src/kabusys/data/schema.py)
    - DuckDB 用の DDL を定義（raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義の骨子を実装）。
    - Raw / Processed / Feature / Execution 層を意識した設計方針をコメントで明記。

- リサーチ / ファクター計算 (src/kabusys/research/)
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、単一クエリで取得、営業日→カレンダー日バッファ処理）。
    - IC（Information Coefficient）計算 calc_ic（Spearman ρ をランク変換から算出、欠損・同一値ハンドリング）。
    - ランク関数 rank（同順位は平均ランク、浮動小数丸めで ties 検出の安定化）。
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median、None の除外）。
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - モメンタム calc_momentum（1M/3M/6M リターン、MA200 乖離率、データ不足時 None）。
    - ボラティリティ/流動性 calc_volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比率、true_range の NULL 伝播制御）。
    - バリュー calc_value（raw_financials の最新財務データと株価を組合せて PER/ROE を算出、EPS 不正時は None）。
    - 各関数は DuckDB 接続を受け取り prices_daily / raw_financials テーブルのみを参照する設計。

- リサーチパッケージ公開 (src/kabusys/research/__init__.py)
  - calc_momentum, calc_volatility, calc_value, zscore_normalize（外部ユーティリティ参照）, calc_forward_returns, calc_ic, factor_summary, rank を __all__ に追加して公開。

- 空のパッケージプレースホルダ
  - src/kabusys/execution/__init__.py と src/kabusys/strategy/__init__.py を設置（今後発注・戦略関連を拡張するためのプレースホルダ）。

改善 (Changed)
- 各種モジュールに詳細な docstring と設計方針コメントを追加し、外部アクセス・副作用の制限（DB / API 以外の外部リソースへの直接アクセス回避）を明示。

セキュリティ (Security)
- RSS パーサで defusedxml を使用して XML Bomb 等に対処。
- ニュース収集時の SSRF 対策（リダイレクト検査・最終 URL 再検査・プライベートアドレス拒否）。
- J-Quants クライアントでトークン管理とリフレッシュロジックを実装し、無限再帰を防止。

内部 (Internal)
- DuckDB への保存処理はできるだけ冪等化（ON CONFLICT DO UPDATE / DO NOTHING）し、fetched_at を記録して取得時刻を追跡可能に。
- API 呼び出しの再試行は 408/429/5xx を対象に指数バックオフを用いる。429 の場合は Retry-After ヘッダを優先。
- 単体関数は副作用を限定し、リサーチ用関数は本番の発注 API にアクセスしないことを明文化。

既知の制限 (Known limitations)
- strategy/ execution の本体は未実装（プレースホルダのみ）。
- 一部の DDL（raw_executions など）はファイルの断片で終了しており、完全なスキーマ定義は今後の追加実装が必要。
- 外部依存は最小化しているが、DuckDB 接続や実際の network 環境を必要とする箇所はテストでのモックが必要。

謝辞
- 初期実装のため、今後のフィードバックに基づいて API 形状・例外処理・テストカバレッジを強化予定です。