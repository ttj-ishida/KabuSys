Keep a Changelog
=================

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog の形式に準拠します。

フォーマット: [Unreleased], 各バージョンは日付付きで記載します。

[Unreleased]
------------

（現在なし）

[0.1.0] - 2026-03-18
--------------------

初期公開リリース — KabuSys: 日本株自動売買支援ライブラリの基礎機能を追加。

Added
- パッケージ基盤
  - kabusys パッケージを導入。__version__ = "0.1.0"。
  - サブパッケージのスケルトン: data, strategy, execution, monitoring を公開。

- 設定管理 (kabusys.config)
  - .env / .env.local ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルートの検出ロジック（.git または pyproject.toml を基準）によりカレントワーキングディレクトリに依存しない自動読み込みを実現。
  - .env パース機能を強化（コメント行、export プレフィックス、クォート・エスケープ、インラインコメントの扱いをサポート）。
  - 環境変数の保護機能（既存 OS 環境変数は .env による上書きを防止する protected 機能）。
  - Settings クラスを実装し、J-Quants トークン、kabu API パスワード、Slack 設定、DB パス（DuckDB/SQLite）、実行環境（development/paper_trading/live）、ログレベル等の取得とバリデーションを提供。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。

- データ層 (kabusys.data)
  - J-Quants API クライアント (kabusys.data.jquants_client)
    - 固定間隔の RateLimiter によるレート制御（120 req/min を想定）。
    - 冪等性のため DuckDB への保存関数は ON CONFLICT DO UPDATE を使用。
    - リトライ機構（指数バックオフ、最大試行回数、408/429/5xx の対象）と 401 受信時のトークン自動リフレッシュ対応。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を提供。
    - DuckDB 保存用 save_daily_quotes / save_financial_statements / save_market_calendar を実装（PK 欠損行スキップ・fetched_at 記録）。
    - 型変換ユーティリティ _to_float / _to_int を提供（堅牢な変換ルール）。

  - ニュース収集 (kabusys.data.news_collector)
    - RSS フィード取得・パース機能（fetch_rss）を実装。
    - defusedxml による安全な XML パースを採用。
    - SSRF 対策: リダイレクト時のスキーム検証・プライベートホスト検出（_SSRFBlockRedirectHandler, _is_private_host）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES）、gzip 解凍後のサイズチェック、Content-Length の事前チェックによる DoS 対策。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）、記事ID は正規化URL の SHA-256（先頭32文字）で生成。
    - テキスト前処理（URL 除去・空白正規化）。
    - raw_news へ冪等保存（INSERT ... ON CONFLICT DO NOTHING）をチャンク化してトランザクションで実行し、実際に挿入された記事IDを返す save_raw_news。
    - 銘柄コード抽出（4桁数字パターン）と news_symbols への紐付け処理（_save_news_symbols_bulk, save_news_symbols）。
    - run_news_collection による複数 RSS ソース一括収集ジョブを提供（ソース単位でのエラーハンドリング）。

  - スキーマ定義 (kabusys.data.schema)
    - DuckDB 用の DDL 定義を追加（Raw Layer を中心に raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義を含む）。
    - DataSchema.md の設計に沿った 3 層構造（Raw / Processed / Feature）を想定した初期化用モジュールを用意。

- リサーチ（特徴量・ファクター計算） (kabusys.research)
  - Feature exploration (kabusys.research.feature_exploration)
    - calc_forward_returns: DuckDB の prices_daily を参照して複数ホライズンの将来リターンを一括取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。欠損/有限値チェック、有効レコード数判定を実装。
    - rank: 同順位は平均ランクとする堅牢なランク化アルゴリズム（浮動小数点丸めで ties 対応）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

  - Factor research (kabusys.research.factor_research)
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算（200日移動平均の行数チェック含む）。
    - calc_volatility: 20日 ATR（avg true range）・相対 ATR・20日平均売買代金・出来高比率を算出。true_range の NULL 伝播を考慮。
    - calc_value: raw_financials から最新財務データを取得して PER/ROE を計算（報告日の最新レコード取得ロジック含む）。
    - いずれの関数も DuckDB の prices_daily / raw_financials のみを参照し、本番発注 API にはアクセスしない設計を採用。
    - 研究用途のため外部ライブラリに依存せず標準ライブラリ + duckdb で動作するように実装。

  - research パッケージ __init__ に主要ユーティリティを公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

Changed
- （初期リリースのため該当なし）

Fixed
- 環境変数パーサーの堅牢化: クォート内のバックスラッシュエスケープ、コメント判定ルールの改善、不正行のスキップ等を実装。
- ニュース収集: 不正な link スキームや guid の扱い、XML パース失敗時のフォールバック処理を追加して取得の安定性を向上。

Security
- RSS パーサで defusedxml を使用し XML 関連攻撃を緩和。
- RSS フェッチでリダイレクト先のスキーム検証とプライベートホストチェックを導入し SSRF を防止。
- HTTP レスポンスサイズ上限・gzip 解凍後サイズチェックによりメモリ DoS を防御。

Performance
- J-Quants API クライアントで固定間隔スロットリングを導入し API レートを安定して守る設計。
- ニュース/銘柄紐付け・raw 保存をチャンク化して一括 INSERT を行い DB オーバーヘッドを低減。
- DuckDB 側は OVER ウィンドウ関数を使用して一括集計（historical スキャン範囲を限定することで不要なスキャンを削減）。

Notes
- research モジュールは「研究（Research）環境向け」に設計されており、本番の発注・実行 API を呼び出すコードは含まれていません。
- strategy / execution / monitoring パッケージは公開されているが、このバージョンでは実装がスケルトン（今後拡張予定）。
- DuckDB スキーマの一部（raw_executions の定義途中など）は将来的な拡張を想定している。

Authors
- 開発チーム

ライセンス
- （ソースにライセンス表記がないため、配布時に適切なライセンスを明記してください）

--- 

補足: 本 CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のリリースノート作成時には、コミット履歴やリリース管理ポリシーに基づく詳細な差分確認を推奨します。