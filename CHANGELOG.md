CHANGELOG
=========

すべての重要な変更を時系列で記録します。フォーマットは "Keep a Changelog" に準拠しています。

なお、本CHANGELOGは提示されたコードベースの内容から推測して作成しています。バージョン番号はパッケージ定義（kabusys.__version__ = "0.1.0"）に基づいています。

[Unreleased]
------------

- （なし）

0.1.0 - 2026-03-18
------------------

Added
- 初回リリースとしてライブラリのコア機能を追加。
  - パッケージ初期化
    - src/kabusys/__init__.py に __version__ = "0.1.0" を定義。パブリック API として data, strategy, execution, monitoring をエクスポート。
  - 設定・環境変数管理
    - src/kabusys/config.py
      - .env ファイル（.env, .env.local）をプロジェクトルート（.git または pyproject.toml を基準）から自動ロードする仕組みを実装。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
      - .env 行パーサ（クォート対応、export プレフィックス対応、インラインコメント処理、無効行スキップ）を実装。
      - 読み込み時の override/protected オプションにより OS 環境変数を保護する挙動を提供。
      - Settings クラスでアプリ設定をプロパティとして提供（J-Quants トークン、kabu API 設定、Slack トークン/チャンネル、DuckDB/SQLite パス、環境種別およびログレベル検証、is_live/is_paper/is_dev フラグなど）。
  - データ収集クライアント（J‑Quants）
    - src/kabusys/data/jquants_client.py
      - J-Quants API クライアントを実装。urllib を用いた HTTP 呼び出し、JSON デコード、ページネーション対応の取得関数を提供（fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar）。
      - API レート制御: 固定間隔スロットリングによる 120 req/min 制限（RateLimiter）。
      - リトライロジック: 指数バックオフ、最大リトライ回数、408/429/5xx に対応。429 の場合は Retry-After を優先。
      - 401 応答時は refresh token から id token を自動取得して 1 回リトライする仕組み（トークンキャッシュをモジュールレベルで保持）。
      - DuckDB への冪等保存用関数（save_daily_quotes、save_financial_statements、save_market_calendar）を実装。ON CONFLICT DO UPDATE による上書き、PK 欠損行のスキップ、型安全処理（_to_float/_to_int）を含む。
  - ニュース収集（RSS）
    - src/kabusys/data/news_collector.py
      - RSS フィード取得・解析パイプラインを実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
      - セキュリティ対策: defusedxml による XML パース、安全なリダイレクトハンドラ（_SSRFBlockRedirectHandler）でリダイレクト先のスキーム/プライベートアドレスを検査、受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後サイズ検査、HTTP スキーム検証など。
      - URL 正規化（トラッキングパラメータ削除、スキーム/ホストの小文字化、フラグメント削除、クエリソート）で記事IDを SHA-256 の先頭32文字で生成し冪等性を確保。
      - テキスト前処理（URL 除去、空白正規化）、銘柄コード抽出ロジック（4桁数字マッチングと既知コードフィルタ）を実装。
      - DB 操作はチャンク化・トランザクション化され、INSERT ... RETURNING により実際に新規挿入された件数を正確に取得する。
      - SSRF 対策としてホスト名→IP 解析を行いプライベート/ループバック等を拒否（DNS 解決失敗時は安全側で通す設計）。
  - DuckDB スキーマ定義
    - src/kabusys/data/schema.py
      - Raw / Processed / Feature / Execution 層を想定したスキーマ定義を追加（raw_prices, raw_financials, raw_news, raw_executions 等の DDL を定義）。
      - テーブル列には型チェック制約（CHECK）や PRIMARY KEY を設定しデータ整合性を高める設計。
  - リサーチ／特徴量計算
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算（calc_forward_returns: 指定日から複数ホライズン分の将来リターンを一括SQLで取得）。
      - IC（Information Coefficient）計算（calc_ic: スピアマンの順位相関を独自実装し ties を平均ランク対応）。rank 関数は浮動小数点の丸めにより ties 検出を安定化。
      - factor_summary による基本統計量（count/mean/std/min/max/median）算出。
      - これらは標準ライブラリのみで実装（pandas 等非依存）することを意図。
    - src/kabusys/research/factor_research.py
      - momentum/value/volatility/流動性 などの定量ファクター計算関数を実装（calc_momentum, calc_value, calc_volatility）。
      - 各関数は DuckDB 接続を受け取り、prices_daily / raw_financials テーブルを参照してウィンドウ集計（移動平均、ATR 等）・LAG/AVG ウィンドウ関数で算出。データ不足時は None を返す安全設計。
    - src/kabusys/research/__init__.py
      - 主要API（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）を __all__ で公開。
  - 実行／ストラテジ／モニタリング用パッケージ構成
    - src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py（プレースホルダでパッケージ構造を確立）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- ニュース収集で複数の SSRF/DoS 対策を導入（URL スキーム制限、プライベートアドレス拒否、受信サイズ上限、gzip 解凍後検査、defusedxml 利用）。
- J-Quants クライアントは 401 時に安全にトークンリフレッシュを行い、リフレッシュ失敗時は適切に例外を上げる（無限再帰回避のため allow_refresh フラグを使用）。

Notes / Design decisions
- Research モジュールは運用時の再現性を重視し、外部 API や発注機能にはアクセスしない設計（DuckDB の prices_daily / raw_financials のみ参照）。
- NewsCollector の記事IDは URL 正規化＋SHA-256 の先頭32文字で生成し、トラッキングパラメータを削除することで冪等性を高める。
- J-Quants クライアントは urllib ベースで実装されており、rate limiter と再試行を組み合わせることで API 制限に配慮している。
- settings は環境変数のバリデーション（KABUSYS_ENV, LOG_LEVEL）を行い、不正値は ValueError を送出する。

既知の制約 / TODO（今後の改善候補）
- research モジュールはパフォーマンス上の理由から pandas 等を利用していないが、大量データ処理時に最適化余地あり。
- news_collector の DNS 解決失敗時の「安全側通過」は保守時に見直す可能性あり（可用性とセキュリティのトレードオフ）。
- raw_executions テーブル定義がコードスニペットで途中までのみ掲載されているため、実運用用の Execution 層 DDL の完成が必要。

参考
- パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
- 主なファイル一覧:
  - src/kabusys/config.py
  - src/kabusys/data/jquants_client.py
  - src/kabusys/data/news_collector.py
  - src/kabusys/data/schema.py
  - src/kabusys/research/feature_exploration.py
  - src/kabusys/research/factor_research.py
  - src/kabusys/research/__init__.py

もし CHANGELOG に追記したい差分（実際のコミット履歴や追加情報）があれば提供してください。より正確な日付・著者・詳細な分類で更新できます。