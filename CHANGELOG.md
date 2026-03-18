# Changelog

すべての重要な変更点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

全バージョンはセマンティックバージョニングに従います。

## [Unreleased]

- 現在未リリースの変更はありません。

## [0.1.0] - 2026-03-18

初回公開リリース。主要な機能と設計方針の概要は以下の通りです。

### Added
- パッケージ基盤
  - パッケージメタ情報と公開 API を定義（kabusys.__init__）。
  - __all__ に data, strategy, execution, monitoring を含むモジュール構成を提供。

- 設定管理（kabusys.config）
  - Settings クラスを実装し環境変数から設定を取り出すプロパティを提供（J-Quants トークン、kabuステーション API、Slack、DB パス、実行環境、ログレベル等）。
  - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を起点）。
  - 読み込み順序: OS 環境 > .env.local (> .env)、既存 OS 環境は保護（protected）される。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - .env パーサ機能（export プレフィックス、シングル/ダブルクォートのエスケープ、インラインコメント処理、無効行スキップ）を実装。
  - env / log_level の値検証（許容値チェック）と is_live / is_paper / is_dev の便宜プロパティ。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出し共通処理を実装（_request）。
    - 固定間隔スロットリングによるレート制限遵守（120 req/min）。
    - 再試行ロジック（指数バックオフ、最大 3 回。対象: 408, 429, 5xx およびネットワークエラー）。
    - 401 レスポンス時はリフレッシュトークンで ID トークンを自動更新して 1 回リトライ。
    - ページネーション対応（pagination_key を扱うループ）。
    - JSON デコード失敗時のエラーハンドリングとログ。
  - ID トークン取得（get_id_token）とモジュールレベルキャッシュを実装。
  - データ取得ユーティリティ:
    - fetch_daily_quotes（株価日足）、fetch_financial_statements（財務データ）、fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存（冪等）ユーティリティ:
    - save_daily_quotes / save_financial_statements / save_market_calendar：ON CONFLICT DO UPDATE を使った冪等保存。
    - fetched_at を UTC で記録して Look-ahead bias を抑止。
  - 型変換ユーティリティ _to_float / _to_int（堅牢な変換と空値/不正値処理）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードの取得・前処理・DB 保存ワークフローを実装。
  - セキュリティ・堅牢性:
    - defusedxml を使用した XML パース（XML Bomb 対策）。
    - SSRF 対策: URL スキーム検証、プライベート/ループバック/リンクローカル/IP の検出、カスタムリダイレクトハンドラでリダイレクト先も検査。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後の再チェック（Gzip bomb 対策）。
    - 不正なスキームの URL を排除（mailto:, file:, javascript: 等）。
  - URL 正規化と記事 ID 生成:
    - トラッキングパラメータ（utm_*, fbclid 等）除去、クエリのソート、フラグメント削除。
    - 正規化 URL の SHA-256 ハッシュ先頭 32 文字を記事 ID として使用（冪等性）。
  - テキスト前処理（URL 除去、空白正規化）。
  - DB 保存:
    - save_raw_news: チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、実際に挿入された記事 ID のリストを返す。トランザクション管理あり。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols への紐付けをチャンク INSERT + RETURNING で行い、正確な挿入件数を返す。重複除去とトランザクション管理あり。
  - 銘柄コード抽出ユーティリティ extract_stock_codes（4桁数字を抽出し known_codes に基づきフィルタ、重複排除）。

- データスキーマ（kabusys.data.schema）
  - DuckDB 用 DDL を定義（Raw Layer の raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義を含む）。
  - Data Platform の 3 層構造（Raw / Processed / Feature / Execution）設計に沿った初期化を想定。

- 研究用モジュール（kabusys.research）
  - feature_exploration:
    - calc_forward_returns: 指定基準日から各ホライズンの将来リターンを一括取得（DuckDB を用いた窓関数利用）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算。データ不足時は None を返す。
    - rank: 同順位は平均ランクとするランク関数（round による丸めで ties 検出）。
    - factor_summary: count/mean/std/min/max/median を計算。
    - 実装方針として pandas 等外部依存を使わず標準ライブラリで実装。
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200日移動平均乖離）を計算。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算（ATR の NULL 伝播制御やカウントチェックあり）。
    - calc_value: raw_financials の直近財務データと prices_daily を組み合わせて PER / ROE を算出（EPS が 0/欠損時は None）。
    - 各関数は DuckDB 接続を受け取り prices_daily / raw_financials のみ参照することを明記。運用 API など外部にアクセスしない設計。
  - research パッケージ __init__ で主要関数を再エクスポート（zscore_normalize を含む）。

### Security
- news_collector:
  - SSRF 対策、XML パースの安全化、レスポンスサイズ上限等のセキュリティ強化を実装。
- jquants_client:
  - API 呼び出しのリトライ制御やトークンリフレッシュにより不正な認証状態や過負荷時の踏み越えを低減。

### Notes / Implementation Details
- 全体設計として DuckDB を中心にデータ取得 → raw 格納 → feature 計算 を完結させる方針。
- Research モジュールは外部ライブラリに依存しない純 Python 実装を目指しており、実行環境での再現性を重視。
- 一部ファイル（例: execution モジュールや schema の一部 DDL）が実装途中で切れている箇所があるため、今後の拡張で Execution Layer（発注・約定・ポジション管理）や追加テーブルの完成が想定される。

---

過去のリリースや将来の更新はここに逐次追記します。仕様の解釈やリリースノート記載内容に誤りがあれば指摘ください。