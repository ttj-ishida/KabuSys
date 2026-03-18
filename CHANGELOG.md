CHANGELOG
=========

すべての重要な変更を記載します。本ファイルは "Keep a Changelog" の書式に準拠しています。

フォーマット:
- 変更はバージョン別に整理し、カテゴリ（Added, Changed, Fixed, Security, etc.）ごとに記載します。

0.1.0 - 2026-03-18
-----------------

Initial release（初回リリース）

Added
- パッケージ構成を追加
  - トップレベルパッケージ kabusys を定義（src/kabusys/__init__.py）。公開モジュール: data, strategy, execution, monitoring。パッケージバージョン __version__ = "0.1.0" を設定。
- 環境変数 / 設定管理
  - 環境ロード機能を実装（src/kabusys/config.py）。
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索する _find_project_root() を実装し、CWD に依存しない自動 .env ロードを行う。
    - .env / .env.local の自動読み込み（優先順位: OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のパースは export KEY=val 形式、クォート/エスケープ、インラインコメント、空行/コメント行を適切に扱う _parse_env_line() を実装。
    - Settings クラスを導入し、J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベルの取得とバリデーション機能を提供。settings インスタンスを公開。
- Data モジュール（DuckDB ベース）
  - J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）。
    - 固定間隔スロットリングによるレート制御（120 req/min）を実装（_RateLimiter）。
    - 再試行（指数バックオフ）、Retry-After の考慮、最大リトライ回数の実装。HTTP 401 受信時は ID トークンを自動リフレッシュして 1 回のみリトライするロジック。
    - ページネーション対応の取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB への冪等保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE/DO NOTHING を利用して重複を排除）。
    - 型変換ユーティリティ: _to_float, _to_int（"1.0" 形式の扱いなどを厳密に処理）。
  - ニュース収集モジュールを実装（src/kabusys/data/news_collector.py）。
    - RSS フィード取得と記事整形（URL 正規化、トラッキングパラメータ除去、テキスト前処理）。
    - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保。
    - defusedxml を用いた安全な XML 解析、gzip 対応、最大受信バイト数制限（デフォルト 10MB）による DoS 対策、redirect 時のスキーム/プライベートアドレス検証（SSRF 対策）。
    - DB への保存はチャンク化・トランザクション化して効率・整合性を確保（save_raw_news は INSERT ... RETURNING により実際に挿入された ID を返す）。
    - テキスト中から銘柄コード（4桁）を抽出する extract_stock_codes と、収集ジョブの統合 run_news_collection を実装。
  - DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
    - DataSchema に基づく複数テーブル定義（Raw Layer の raw_prices, raw_financials, raw_news 等を含む DDL を定義）。（実装の一部はファイルの末尾で継続）
- Research モジュール（DuckDB を参照する分析ユーティリティ）
  - src/kabusys/research/factor_research.py
    - 定量ファクター計算を実装: calc_momentum (mom_1m/mom_3m/mom_6m, ma200_dev), calc_volatility (atr_20, atr_pct, avg_turnover, volume_ratio), calc_value (per, roe)。
    - DuckDB の prices_daily / raw_financials テーブルのみを参照する設計。欠損やデータ不足時は None を返す仕様。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算: calc_forward_returns（複数ホライズンを一度に取得する効率的なクエリ）。
    - IC（Information Coefficient）計算: calc_ic（スピアマンのランク相関を内部実装、データ不足時は None）。
    - rank（同順位は平均ランクで処理、丸め誤差対策の round を適用）、factor_summary（count/mean/std/min/max/median の算出）を提供。
  - パッケージ初期化で主要関数を再公開（src/kabusys/research/__init__.py）。
  - 設計方針として外部ライブラリ（pandas 等）に依存しない形で実装。
- Strategy / Execution / Monitoring
  - パッケージディレクトリ（src/kabusys/strategy, src/kabusys/execution）を用意（初期スタブ）。将来的な戦略・発注ロジックの配置を想定。

Security
- news_collector で SSRF 対策を実装
  - リダイレクト時にスキームとホストを検査するカスタムハンドラ _SSRFBlockRedirectHandler。
  - _is_private_host によるプライベート/ループバック/リンクローカル/マルチキャスト判定（DNS 解決済みの A/AAAA レコードも検査）。DNS 解決失敗時は安全側の扱いを採用。
- XML パースに defusedxml を使用して XML ボム等を低減。
- J-Quants クライアントにおいてトークンの安全な取り扱い（自動リフレッシュ、キャッシュ）とレート制御を実装。

Notes / Design decisions
- DuckDB を中心としたローカルデータレイヤ（raw / processed / feature / execution 層）を採用。研究・バックテストは DuckDB 接続を受け取り副作用なく完結する設計。
- Research モジュールは標準ライブラリのみで動作するように実装（pandas 等に依存しない）。
- calc_value は現時点で PER, ROE を実装。PBR や配当利回りは未実装（将来の拡張予定）。
- 多くの関数はデータ不足時に None を返すことで downstream の堅牢性を確保（IC 計算は有効レコード数 < 3 で None）。
- 設定周りは厳密なバリデーションを行う（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）。

Breaking Changes
- なし（初回リリースのため該当なし）。

Deprecated
- なし。

Fixed
- なし（初回リリースのため該当なし）。

今後の TODO / 既知の未実装点
- strategy / execution の具体的な発注ロジック、モニタリング機能は未実装（パッケージスタブのみ）。
- calc_value の PBR・配当利回り等の拡充。
- schema.py の Execution 層テーブル定義（raw_executions の続き以降）など、DDL の残り部分の整備。

貢献・フィードバック
- バグ報告や改善提案は Issue を立ててください。ドキュメントやテストの充実、機能追加の PR を歓迎します。