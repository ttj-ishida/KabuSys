Keep a Changelog
すべての変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  
https://keepachangelog.com/ja/1.0.0/

Unreleased
- （なし）

[0.1.0] - 2026-03-19
Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージエントリポイント (src/kabusys/__init__.py) とバージョン管理を追加。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - 行パーサーはコメント・export 形式・クォート・エスケープを考慮して安全に解析。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベルの取得とバリデーションを実装。
  - 必須環境変数未設定時は明示的な例外を発生させるヘルパーを提供。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - レート制限 (120 req/min) を守る固定間隔スロットリング実装（RateLimiter）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。429 の場合は Retry-After を尊重。
  - 401 受信時にリフレッシュトークンで自動的に id_token を再取得して 1 回リトライする仕組み。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes (株価日足)
    - fetch_financial_statements (財務データ)
    - fetch_market_calendar (JPX カレンダー)
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - ON CONFLICT DO UPDATE を用いた重複対策と fetched_at による取得時刻記録（UTC）。
  - 型変換ユーティリティ (_to_float / _to_int) を実装し、非数値や不正値を安全に扱う。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード取得 / パース / 前処理 / DuckDB への冪等保存を実装。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 等の対策）。
    - SSRF 対策: リダイレクト時にスキーム検証とプライベートアドレスチェックを行うカスタムリダイレクトハンドラを実装。
    - 初期 URL のプライベートホスト検査、最終 URL の再検証を実施。
    - 許可スキームは http/https のみ。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後の上限チェックを実装（Gzip Bomb 対策）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）と記事 ID の SHA-256 (先頭32文字) による冪等化。
  - テキスト前処理（URL 除去、空白正規化）。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された記事IDの一覧を返す。チャンク単位でトランザクション中に挿入。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols への銘柄紐付けをチャンク INSERT で冪等に保存。
  - 銘柄抽出: 本文から 4 桁の数字を抽出し、与えられた known_codes に存在するもののみを返す機能を実装。
  - デフォルト RSS ソースに Yahoo ファイナンスのカテゴリフィードを設定。

- データスキーマ (src/kabusys/data/schema.py)
  - DuckDB 用 DDL（Raw Layer）を追加:
    - raw_prices, raw_financials, raw_news テーブル定義を含む。
    - raw_executions テーブルの定義開始（ファイル内で一部まで定義）。
  - Raw / Processed / Feature / Execution の多層構造設計に基づく初期スキーマを整備。

- リサーチ・特徴量探索モジュール (src/kabusys/research/)
  - feature_exploration.py:
    - calc_forward_returns: 指定日から各ホライズン先（デフォルト 1,5,21 営業日）の将来リターンを一括クエリで計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（tie を平均ランクで扱い、レコード不足時は None を返す）。
    - factor_summary / rank: ファクター列の基本統計量（count/mean/std/min/max/median）とランク変換ユーティリティ。
    - 実装方針として duckdb 接続を受け取り prices_daily のみ参照、外部 API にアクセスしないことを保証。
  - factor_research.py:
    - calc_momentum: mom_1m/mom_3m/mom_6m と 200 日移動平均乖離率(ma200_dev) を計算。ウィンドウ不足時は None。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR(atr_pct)、20 日平均売買代金(avg_turnover)、出来高比(volume_ratio) を計算。
    - calc_value: raw_financials から最新の財務を取得して PER / ROE を計算（EPS が 0 または欠損のときは None）。
    - 全関数は prices_daily / raw_financials のみ参照し本番発注 API 等にアクセスしない設計。

- research パッケージ公開エントリ (src/kabusys/research/__init__.py)
  - 主要関数（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）を __all__ で公開。

Changed
- 初期リリースのため履歴なし。

Fixed
- 初期リリースのため該当なし。

Security
- ニュース収集における SSRF 対策、defusedxml による XML パース、受信サイズ上限、URL スキーム制限など多層的な防御を実装。

Notes / Implementation details
- 多くの処理は DuckDB に対する SQL ウィンドウ関数と Python の組み合わせで実装され、ローカル分析・バックテスト用途に配慮。
- Research モジュールは外部ライブラリ（pandas 等）に依存しない設計。これにより軽量でユニットテストがしやすくなっています。
- J-Quants クライアントは id_token のモジュールレベルキャッシュを持ち、ページネーション間で共有されます。トークン再取得は自動だが無限再帰防止のため制御しています。
- news_collector の保存処理はチャンク分割とトランザクション管理を行い、大量挿入時の安全性と正確な挿入数計測（RETURNING）を担保します。

今後の予定（例）
- schema の Processed / Feature / Execution 層の DDL 完全実装。
- strategy / execution / monitoring モジュールの実装・統合テスト。
- 単体テスト・CI の整備とドキュメント充実。