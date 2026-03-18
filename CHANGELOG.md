Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」仕様に概ね準拠しています。

フォーマット
- 各バージョンは日付付きで記載しています。
- セクションは Added / Changed / Fixed / Security / Deprecated / Removed を使用します。

Unreleased
----------

（現在なし）

0.1.0 - 2026-03-18
------------------

Added
- パッケージ初期リリース。
  - パッケージ名: kabusys、バージョン 0.1.0。

- 環境設定・読み込み機能（kabusys.config）
  - .env / .env.local ファイルまたは OS 環境変数から設定を自動ロード。
  - プロジェクトルート検出は __file__ から親ディレクトリを検索し、.git または pyproject.toml を基準に判定（配布後の動作を考慮）。
  - .env パーサ実装:
    - 空行・コメント・export 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理を考慮。
    - クォートなしのコメント認識は直前が空白またはタブの場合のみ。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 環境変数保護機能（読み込み時に既存 OS 環境変数を保護する protected セット）。
  - Settings クラスを提供（settings インスタンス経由で使用）:
    - J-Quants / kabu / Slack / DB パスなどの設定項目をプロパティで提供。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の検証を実装。
    - duckdb/sqlite のデフォルトパス設定および is_live/is_paper/is_dev ユーティリティ。

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - レート制限遵守のための固定間隔 RateLimiter（120 req/min）を実装。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）。
  - 401 受信時は自動でリフレッシュトークンから id_token を再取得して 1 回再試行。
  - ページネーション対応の fetch_* 関数:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（マーケットカレンダー）
  - DuckDB に対する冪等保存関数（ON CONFLICT DO UPDATE）を実装:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - データ変換ユーティリティ: _to_float / _to_int（不正な値は None に変換）。
  - fetched_at に UTC タイムスタンプを記録（Look-ahead bias のトレーサビリティ確保）。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィード取得と raw_news/raw_news_symbols への保存を実装。
  - 安全性と堅牢性のための設計:
    - defusedxml を用いた XML パース（XML Bomb 等に対処）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、リダイレクト先の事前検査、プライベート IP 判定によるブロック。
    - レスポンスサイズ制限（最大 10 MB）と gzip 解凍後の再検査（Gzip bomb 対策）。
    - User-Agent 指定、Content-Length チェック、受信上限超過時はスキップ。
  - URL 正規化とトラッキングパラメータ除去（utm_* 等）による記事 ID（SHA-256 先頭32文字）生成。
  - テキスト前処理（URL 除去、空白正規化）。
  - DB 保存はチャンク INSERT とトランザクションで実施し、INSERT ... RETURNING を使って実際に挿入された件数/ID を取得。
  - 銘柄コード抽出（4桁数字）と news_symbols への紐付け機能。
  - run_news_collection による統合ジョブ実装（ソース単位で失敗を隔離）。

- DuckDB スキーマ初期化（kabusys.data.schema）
  - Raw 層のテーブル定義を実装（raw_prices, raw_financials, raw_news, raw_executions 等の DDL を含む）。
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）と Execution 層の方向性を明示。

- 研究・特徴量計算（kabusys.research.*）
  - feature_exploration モジュール:
    - calc_forward_returns: 指定日基準で複数ホライズンの将来リターンを DuckDB の prices_daily から一括取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）計算（ペア数が少ない場合は None を返す）。
    - rank: 同順位は平均ランクとするランク化ユーティリティ（浮動小数による ties を round で安定化）。
    - factor_summary: カラムごとの count/mean/std/min/max/median を計算。
    - 設計：DuckDB 接続を受け取り prices_daily のみ参照、実運用 API へはアクセスしない方針。
  - factor_research モジュール:
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200日移動平均乖離）を計算。
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio（ATR, 20日平均等）を計算。
    - calc_value: raw_financials から最新財務データを取得して PER/ROE を計算（EPS が 0 や欠損の場合は None）。
    - 各関数とも DuckDB 接続を受け取り prices_daily / raw_financials のみ参照する設計。
  - research パッケージ __init__ で代表的関数群をエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- パッケージ骨格
  - strategy および execution パッケージの初期モジュールを配置（現時点では空の __init__）。

Security
- ニュース収集で defusedxml を使用し XML に対する攻撃を軽減。
- RSS フェッチで SSRF 対策（スキーム検査、プライベートアドレスブロック、リダイレクト検査）。
- J-Quants クライアントは認証トークンの自動リフレッシュを実装し、不正な再帰を避ける設計（allow_refresh フラグ）。

Changed
- 新規リリースのため、既存プロジェクト構成（ディレクトリ・モジュール）を整備。

Fixed
- （該当なし）

Deprecated
- （該当なし）

Removed
- （該当なし）

Notes / 今後の予定
- Strategy / Execution 層（発注ロジック、ポジション管理）は現状骨格のみ。実取引機能実装は次フェーズ。
- Processed / Feature レイヤーの DDL と ETL（raw -> processed -> feature）を充実させる予定。
- 単体テスト・統合テストの整備（特にネットワーク依存部分のモック化）を推奨。
- ドキュメント（DataSchema.md, StrategyModel.md, DataPlatform.md の整備に基づいた README や使用例）を拡充予定。

作者・貢献者
- 初期実装（core modules）を収録。

--- 

（注）本 CHANGELOG は提示されたコードベースの内容から推測して作成しています。実際のリリースノートには実際のコミット履歴やリリース作業で確定した差分を反映してください。