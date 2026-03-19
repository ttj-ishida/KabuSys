Changelog
=========

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に沿って管理されています。  

[Unreleased]
------------

なし

[0.1.0] - 2026-03-19
--------------------

Added
- 初回リリース。パッケージ名: kabusys、バージョン 0.1.0 を導入。
- パッケージ初期化:
  - src/kabusys/__init__.py に __version__ = "0.1.0" と基本 __all__ 定義を追加。
- 設定・環境変数管理:
  - src/kabusys/config.py を追加。
  - .env/.env.local 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - .env パーサーの実装（コメント、export 形式、クォートおよびエスケープ対応、インラインコメント処理）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを追加（テスト用途）。
  - Settings クラスを提供し、J-Quants / kabu / Slack / DB パス等の設定プロパティを公開。
  - KABUSYS_ENV / LOG_LEVEL の検証ロジックと is_live/is_paper/is_dev ヘルパーを実装。
- Research（特徴量・ファクター探索）:
  - src/kabusys/research/feature_exploration.py を追加。
    - calc_forward_returns: DuckDB の prices_daily を参照して将来リターンを一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - rank: 同順位は平均ランクとするランク化ユーティリティ（丸め誤差対策あり）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - pandas 等の外部ライブラリに依存せず標準ライブラリのみで実装する方針。
  - src/kabusys/research/factor_research.py を追加。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（EPS がゼロ/欠損時は None）。
    - DuckDB 経由で SQL ウィンドウ関数を活用した効率的スキャンと欠損制御。
  - src/kabusys/research/__init__.py で主要関数をエクスポート（zscore_normalize を含む）。
- Data（外部データ取得・保存）:
  - src/kabusys/data/jquants_client.py を追加。
    - J-Quants API クライアント実装（ページネーション対応）。
    - 固定間隔レートリミッター（120 req/min）を実装。
    - リトライ（指数バックオフ、最大3回）、429/408/5xx に対応。429 の場合は Retry-After を優先。
    - 401 レスポンス時はリフレッシュトークンで自動的に ID トークンを更新して一度だけリトライ。
    - fetch_* 系（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）と
      save_* 系（save_daily_quotes / save_financial_statements / save_market_calendar）で
      DuckDB への冪等保存（ON CONFLICT DO UPDATE）を実装。
    - 値変換ユーティリティ (_to_float, _to_int) を提供し不正値の安全な取り扱いを行う。
  - src/kabusys/data/news_collector.py を追加。
    - RSS フィード取得（fetch_rss）と raw_news への冪等保存（save_raw_news）機能を実装。
    - RSS の前処理: URL 正規化（トラッキングパラメータ削除）、記事ID は正規化 URL の SHA-256（先頭32文字）を採用。
    - セキュリティ対策: defusedxml を利用した XML パース、SSRF 対策（リダイレクト検査・プライベートIP拒否）、スキーム検証（http/https のみ許可）。
    - メモリ DoS 対策: 受信最大サイズ MAX_RESPONSE_BYTES（10MB）制限、gzip 解凍後も検査。
    - NEWS → 銘柄紐付け機能: extract_stock_codes で本文中の 4 桁銘柄コード抽出（known_codes に基づきフィルタ）、news_symbols への一括保存（チャンク化とトランザクション管理）。
    - DB 保存は INSERT ... RETURNING を活用して実際に挿入された件数を正確に得る実装。
  - src/kabusys/data/schema.py を追加。
    - DuckDB スキーマ（raw_prices, raw_financials, raw_news, raw_executions 等の DDL）を定義。
    - Raw / Processed / Feature / Execution の3層構造設計を明記（DataSchema.md 準拠）。
- パッケージ構成:
  - 空のモジュールプレースホルダを追加: src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py（今後の拡張用）。
- ロギング/エラーハンドリング:
  - 各所で詳細なログ（info/warning/exception）を出力するように実装。
  - DB トランザクション失敗時はロールバックし例外を再送出する堅牢な実装。

Security
- RSS パーサに defusedxml を使用して XML 関連の攻撃を軽減。
- fetch_rss においてリダイレクト先のスキーム／ホスト検証とプライベートアドレス拒否を実装（SSRF 対策）。
- ニュース取得時のレスポンスサイズ上限を導入し Gzip Bomb / メモリ過負荷を防止。

Notes / Limitations
- research モジュールは pandas 等に依存せず標準ライブラリ + DuckDB SQL を利用する設計のため、
  大規模データの操作や実験的な高速化は今後の課題。
- 一部の戻り値はデータ不足時に None を返します（呼び出し側で欠損処理が必要）。
- J-Quants クライアントの rate limit は固定間隔（スロットリング）実装。将来的にトークンバケット等への変更を検討。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Deprecated
- なし

---

注: この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートやバージョン運用方針に合わせて必要に応じて調整してください。