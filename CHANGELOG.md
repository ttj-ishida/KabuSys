CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

v0.1.0 - 2026-03-18
-------------------

Added
- 初回公開リリース。
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0）。
  - サブパッケージ骨格: data, strategy, execution, monitoring を公開。

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索）。
  - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env 行パーサー実装：
    - コメント行、export プレフィックス、クォート付き値（バックスラッシュエスケープ対応）、インラインコメントの扱い等の細かい挙動に対応。
  - 上書き（override）・保護（protected）オプションにより OS 環境変数を保護して .env を安全に読み込める設計。
  - 必須環境変数取得ヘルパー _require と Settings クラスを提供：
    - J-Quants / kabu ステーション / Slack / DB パス等の設定プロパティを定義。
    - KABUSYS_ENV / LOG_LEVEL の値検証（許容値のチェック）を実装。
    - is_live / is_paper / is_dev のユーティリティプロパティを追加。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装：
    - API レート制限（120 req/min）を守る固定間隔レートリミッタ（_RateLimiter）。
    - 冪等性を考慮した DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装（ON CONFLICT DO UPDATE）。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - リトライロジック（指数バックオフ、最大3回）および HTTP 状態コード 401 時のトークン自動リフレッシュ処理。
    - ネットワーク/HTTP エラーに対する詳細なログ出力とハンドリング。
    - 値変換ユーティリティ (_to_float, _to_int) により入力データの安全な正規化。
    - 取得時の fetched_at を UTC で記録し、Look-ahead Bias を防止可能な設計。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集および DuckDB への冪等保存ワークフローを実装。
  - セキュリティと堅牢性：
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - SSRF 対策: URL スキーム検証（http/https 限定）、リダイレクト時のホスト検査、プライベートIP/ループバック判定、独自の RedirectHandler 実装。
    - レスポンス読み込みバイト数制限（MAX_RESPONSE_BYTES, デフォルト 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - トラッキングパラメータ除去・URL 正規化（_normalize_url）と SHA-256 ベースの記事 ID 生成（先頭32文字）による冪等性確保。
  - テキスト前処理（URL 削除、空白正規化）と RSS pubDate の堅牢なパース（UTC への正規化）。
  - DB へのバルク挿入はチャンク化（_INSERT_CHUNK_SIZE）かつトランザクションで実行し、INSERT ... RETURNING により実際に挿入された ID を返す実装。
  - 銘柄コード抽出ユーティリティ（4桁数字の抽出と既知コードによるフィルタリング）。
  - run_news_collection による複数ソースを横断した収集ジョブと、記事 → 銘柄の一括紐付け処理を実装。

- 研究用ファクター計算（kabusys.research）
  - feature_exploration モジュール：
    - calc_forward_returns: DuckDB の prices_daily を参照して、複数ホライズン（デフォルト: 1,5,21営業日）の将来リターンを一度のクエリで取得。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）計算。欠損値・非有限値の除外、最小データ点数チェックを実装。
    - rank: 同順位を平均ランクで扱うランク関数（丸め誤差に配慮）。
    - factor_summary: count/mean/std/min/max/median 等の基本統計量集計。
  - factor_research モジュール：
    - calc_momentum: mom_1m/mom_3m/mom_6m および ma200_dev（200日MA乖離）を DuckDB の prices_daily から計算。データ不足時は None を返す扱い。
    - calc_volatility: 20日 ATR（true range の平均）計算、相対ATR（atr_pct）、20日平均売買代金、出来高比率を計算。NULL 伝播を考慮した true_range 計算と cnt ベースの閾値判定を実装。
    - calc_value: raw_financials から target_date 以前の最新財務情報を結合し PER/ROE を計算（EPS が 0/欠損の場合は None）。
  - 研究向け API は DuckDB 接続を受け取り prices_daily/raw_financials のみを参照する方針（本番発注 API 等にはアクセスしない）。

- スキーマ定義（kabusys.data.schema）
  - DuckDB 用の DDL 定義を実装（raw_prices, raw_financials, raw_news, raw_executions などのテーブル定義を含む）。
  - 3 層アーキテクチャ（Raw / Processed / Feature / Execution）を想定したスキーマ設計に準拠。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Security
- RSS パーサーで defusedxml を採用し、SSRF/リダイレクト先のプライベートアドレスアクセスをブロック、レスポンスサイズ・gzip 解凍サイズの検査を追加。
- J-Quants クライアントで 401 時のトークン自動更新とリトライ制御を実装し、認証周りでの堅牢性を向上。

Performance
- J-Quants クライアントで固定間隔レートリミッタにより API レートを遵守（120 req/min）。
- RSS / news 保存処理でバルク挿入・チャンク化を行い DB オーバーヘッドを低減。
- feature / forward returns の集計は可能な限り単一クエリで取得するよう実装。

Notes / Known limitations
- 外部依存を極力抑える方針のため、研究モジュールは標準ライブラリのみで実装している（pandas 等未採用）。大量データでの処理の最適化は今後の課題。
- raw_executions テーブル定義等、Execution レイヤーの一部はコード上で定義が続いている箇所があり（現リリース時点で断片的）、Execution 周りの機能実装は今後の予定。
- DuckDB スキーマや SQL は DuckDB の SQL 方言に依存しているため、互換性チェックが必要な場面がある。

今後の予定（抜粋）
- strategy / execution レイヤーの実装拡充（発注実行・ポジション管理・紙トレード/本番切替の整備）。
- テストカバレッジの拡充（特にネットワーク関連・XML/RSS パーサ・DB 保存ロジック）。
- 大規模データに対するパフォーマンス最適化（メモリ使用量・クエリチューニング等）。

--- 

（本 CHANGELOG はソース内の実装から推測して作成しています。実際のリリースノート作成時は変更点の確認・補完をお願いします。）