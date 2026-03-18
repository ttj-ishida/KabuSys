# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

現在のリリース: 0.1.0 — 2026-03-18

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-18

初期公開リリース。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。トップレベルで data, strategy, execution, monitoring モジュールを公開。
  - バージョン情報: __version__ = 0.1.0。

- 設定 / 環境変数読み込み（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート検出ロジックを導入（.git または pyproject.toml を探索し、自動ロードの対象を決定）。
  - .env/.env.local の読み込み順序を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
  - .env パーサを強化（コメント行、export プレフィックス、シングル/ダブルクォート、エスケープシーケンス、インラインコメントの扱いなどに対応）。
  - 必須環境変数取得時に例外を投げる _require()、env/log_level のバリデーション、duckdb/sqlite パスのデフォルト処理などを実装。

- データ取得・保存関連（kabusys.data）
  - J-Quants API クライアント（jquants_client）
    - 固定間隔レートリミッタ（120 req/min）を実装。
    - 冪等性のある DuckDB 保存関数（save_daily_quotes、save_financial_statements、save_market_calendar）を実装（ON CONFLICT DO UPDATE）。
    - ページネーション対応のフェッチ関数（fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar）。
    - リトライ戦略（指数バックオフ・最大試行回数、408/429/5xx 対象）と 401 発生時のトークン自動リフレッシュ（1 回のみ）。
    - トークンキャッシュ機構をモジュールレベルで実装。
    - 型変換ユーティリティ（_to_float, _to_int）を実装。

  - ニュース収集モジュール（news_collector）
    - RSS フィード取得と記事整形機能を実装（fetch_rss, preprocess_text）。
    - XML パースに defusedxml を使用して XML ボム等の脅威に対策。
    - Gzip 圧縮対応および受信バイト数上限チェック（MAX_RESPONSE_BYTES）でメモリDoS対策。
    - SSRF 対策：
      - リダイレクト時のスキーム・ホスト検証用ハンドラ（_SSRFBlockRedirectHandler）。
      - ホストがプライベート/ループバック等でないかを判定する _is_private_host。
      - 許可スキームは http/https のみ。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）と記事ID生成（URL 正規化→SHA-256 の先頭 32 文字）。
    - raw_news / news_symbols への冪等保存（INSERT ... ON CONFLICT DO NOTHING、INSERT RETURNING による実際に挿入された件数取得）。
    - 銘柄コード抽出（4 桁数字）と既知コードフィルタリング。
    - run_news_collection により複数ソースを順次取得して DB に保存、失敗ソースはスキップする堅牢なワークフローを実装。

- DuckDB スキーマ定義（kabusys.data.schema）
  - DataSchema に基づく初期 DDL を追加（raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義）。
  - Raw / Processed / Feature / Execution 層構造に対応した設計コメントを含む。

- リサーチ / ファクター計算（kabusys.research）
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns）を実装（DuckDB の prices_daily を参照、指定ホライズンの戻り値を計算）。
    - Information Coefficient（Spearman ρ）計算（calc_ic）とランク付けユーティリティ（rank）。
    - factor_summary による基本統計量集計（count/mean/std/min/max/median）。
    - 標準ライブラリのみで実装（pandas 等の外部依存を避ける設計）。
  - factor_research モジュール
    - モメンタムファクター（calc_momentum）：1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）。
    - ボラティリティ / 流動性ファクター（calc_volatility）：20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率。
    - バリューファクター（calc_value）：raw_financials の最新財務データと価格を組み合わせて PER / ROE を計算。
    - 各関数は DuckDB 接続を受け取り prices_daily / raw_financials のみ参照（実取引 API には触れない設計）。
    - スキャン期間や窓サイズ等の定数（例: _MA_LONG_DAYS=200, _ATR_DAYS=20）を定義。

- その他
  - 研究用ユーティリティ（kabusys.research.__init__）で主要関数群をエクスポート。
  - ロギング呼び出しを随所に追加し、処理のトレースとデバッグを容易に。

### Security
- news_collector:
  - defusedxml による XML パースで XML 関連攻撃を軽減。
  - SSRF 対策（リダイレクト検査・プライベートIP検査・スキーム制限）。
  - レスポンスサイズ制限と gzip 解凍後の再チェックによる Gzip ボム対策。
- jquants_client:
  - トークン取り扱い（自動リフレッシュ・キャッシュ）を実装し、401 発生時に安全に処理。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Notes
- 多くの処理は DuckDB 接続を前提としており、SQL を活用した一括集計／窓関数を利用する設計になっています。
- Research モジュールの関数は本番口座や注文 API にはアクセスしない設計で、バックテスト / ファクター評価用途を想定しています。
- 外部依存は必要最小限に抑えられており（duckdb, defusedxml など）、標準ライブラリで安全性と互換性に配慮しています。

--- 

貢献・バグ報告は Issue を通じてお願いします。