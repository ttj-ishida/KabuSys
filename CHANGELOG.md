# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
このプロジェクトの初期バージョンは 0.1.0 です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-18

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（src/kabusys/__init__.py、__version__ = "0.1.0"）。
  - パッケージ公開時に利用するトップレベルのモジュール構成を宣言（data, strategy, execution, monitoring）。

- 環境設定/ロード機能（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化対応（テスト用）。
    - プロジェクトルート検出ロジックは __file__ を起点に .git または pyproject.toml を探索。
  - .env 行パーサーの実装（export プレフィックス、シングル/ダブルクォート、インラインコメント取り扱い等に対応）。
  - 環境変数取得ユーティリティ（必須項目チェック）および Settings クラスを提供。
    - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（各プロパティで検査）。
    - 既定値: KABU_API_BASE_URL（http://localhost:18080/kabusapi）、DUCKDB_PATH（data/kabusys.duckdb）、SQLITE_PATH（data/monitoring.db）。
    - KABUSYS_ENV の検証（development / paper_trading / live）と log レベル検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - is_live / is_paper / is_dev の便宜プロパティ。

- データモジュール: J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しユーティリティを実装（_request）。
    - レート制限対応（120 req/min の固定間隔スロットリング）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライ（トークンキャッシュ実装）。
    - ページネーション対応（pagination_key を用いた反復取得）。
    - JSON デコード／エラーハンドリング。
  - 認証ユーティリティ: get_id_token(refresh_token=None)（settings からのトークン取得をサポート）。
  - データ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務データ、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB 保存関数（冪等設計、ON CONFLICT 句を使用）:
    - save_daily_quotes -> raw_prices（fetched_at を UTC で記録）
    - save_financial_statements -> raw_financials
    - save_market_calendar -> market_calendar
  - 型変換ユーティリティ: _to_float / _to_int（不正値を None にする堅牢な変換）。

- データモジュール: ニュース収集（RSS）機能（src/kabusys/data/news_collector.py）
  - RSS フィード取得・パース・正規化機能を実装。
    - defusedxml を用いた安全な XML パース（XML Bomb 対策）。
    - URL 正規化（トラッキングパラメータ除去・ソート・スキーム/ホスト小文字化・フラグメント削除）。
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
    - URL スキーム検証（http/https のみ許可）、プライベートホスト判定（SSRF 対策）。
    - リダイレクト時にスキーム/プライベートアドレスを事前検査するカスタムリダイレクトハンドラ。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）および gzip 解凍後サイズ検査（Gzip bomb 対策）。
    - コンテンツ前処理（URL 除去、空白正規化）。
  - データベース保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を用いた新規挿入IDの取得。チャンク挿入・トランザクション制御をサポート。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols への銘柄紐付けを一括保存（重複排除、チャンク、トランザクション）。
  - 銘柄抽出ユーティリティ: extract_stock_codes（テキスト中の4桁数字を既知銘柄セットでフィルタ）。
  - 統合収集ジョブ: run_news_collection（複数ソースの独立処理、新規件数集計、紐付け処理）。

- Research モジュール（src/kabusys/research）
  - 目的: DuckDB の prices_daily / raw_financials を使った特徴量・探索機能（外部ライブラリ不使用）。
  - feature_exploration:
    - calc_forward_returns: 指定日の終値から複数ホライズン（デフォルト: 1,5,21 営業日）先のリターンを一括取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。欠損や ties に対応。有効レコード数が3未満なら None を返す。
    - rank: 同順位は平均ランクにするランク化実装（浮動小数丸めで ties 検出の安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を標準ライブラリのみで集計。
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m と 200 日移動平均乖離（ma200_dev）を計算。必要な過去データ不足時は None。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。true_range の NULL 伝播制御あり。
    - calc_value: raw_financials の最終財務データと prices_daily を組み合わせて PER（eps が 0/NULL の場合は None）、ROE を計算。
  - research パッケージ __init__ で上記ユーティリティを公開。

- スキーマ定義（src/kabusys/data/schema.py）
  - DuckDB 用 DDL を追加（Raw Layer の主要テーブル定義を含む）。
    - raw_prices, raw_financials, raw_news を含む CREATE TABLE 文を定義。
    - raw_executions テーブル定義の実装開始（ファイルは途中で抜粋あり）。
  - スキーマ初期化用モジュール骨組みを用意。

### Security
- ニュース収集周りで多数のセーフティ機構を導入:
  - defusedxml による安全な XML パース。
  - URL スキーム制限（http/https のみ）、正規化、トラッキングパラメータ除去。
  - プライベート/ループバック/リンクローカル IP の検出・拒否（SSRF 対策）。
  - リダイレクト先の検査、レスポンスサイズ制限、gzip 解凍後のサイズ検査。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Deprecated
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Notes / Known limitations
- Research 関数群は外部ライブラリ（pandas 等）に依存せず標準ライブラリと DuckDB の SQL によって実装されています。大量データでの性能チューニングやベンチマークは今後の課題です。
- 一部機能（例: PBR、配当利回り、Liquidity の追加指標等）は現バージョンでは未実装。
- strategy/execution/monitoring パッケージはエントリポイントが用意されているものの、発注ロジック・ポジション管理などの実装は含まれていません（今後の実装対象）。
- DuckDB の RETURNING を前提とした実装になっているため、実行環境の DuckDB バージョン互換性に注意してください。
- .env の自動読み込みはプロジェクトルートの検出に依存するため、配布後やインストール先での挙動に注意が必要です。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化できます。

### Authors / Contributors
- 初期実装（機能群の設計・実装）

----
（今後のリリースでは各モジュールの機能追加・バグ修正・パフォーマンス改善・テスト追加などを逐次記載します。）