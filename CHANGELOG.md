# Keep a Changelog — CHANGELOG.md（日本語）

すべての変更は [Keep a Changelog](https://keepachangelog.com/) の方針に準拠して記載しています。

## Unreleased
（未リリースの変更をここに記載します）

---

## [0.1.0] - 2026-03-19

最初の公開リリース。日本株自動売買・データ基盤のコア機能を実装しました。

### Added
- パッケージ初期化
  - kabusys パッケージを導入。バージョン 0.1.0（src/kabusys/__init__.py）。

- 環境設定（src/kabusys/config.py）
  - .env ファイル（.env, .env.local）および OS 環境変数からの設定自動読み込み機能を実装。
    - プロジェクトルートを .git または pyproject.toml から検出してロード。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env 解析は export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
  - 既存の OS 環境変数を保護する protected パラメータを用いた上書きルールを実装。
  - Settings クラスを提供し、以下の主要設定をプロパティで取得可能に：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development/paper_trading/live の検証）, LOG_LEVEL（検証）
    - is_live / is_paper / is_dev ヘルパー

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しユーティリティと堅牢な HTTP レスポンス処理を実装。
  - レートリミッタ（120 req/min 固定間隔スロットリング）を実装。
  - リトライ（指数バックオフ、最大 3 回、408/429/5xx 対象）と 429 の Retry-After 優先処理を実装。
  - 401 受信時にリフレッシュトークンから id_token を取得して 1 回リトライする自動トークンリフレッシュ機能を実装。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数（冪等性）:
    - save_daily_quotes → raw_prices へ ON CONFLICT DO UPDATE
    - save_financial_statements → raw_financials へ ON CONFLICT DO UPDATE
    - save_market_calendar → market_calendar へ ON CONFLICT DO UPDATE
  - 型安全な数値変換ユーティリティ（_to_float/_to_int）を実装。
  - fetched_at に UTC の ISO タイムスタンプを記録（Look-ahead bias のトレースに配慮）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードの取得・前処理・DuckDB への永続化機能を実装。
  - セキュリティ・堅牢性のための実装:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - URL スキーム検証（http/https のみ許可）およびリダイレクト時の検査（SSRF 対策）。
    - ホストがプライベート/ループバック/リンクローカルでないか検査（DNS 解決含む）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後のサイズチェック。
  - URL 正規化（トラッキングパラメータ除去・ソート・フラグメント削除）および記事 ID の SHA-256（先頭32文字）生成による冪等性。
  - テキスト前処理（URL 除去・空白正規化）。
  - RSS -> NewsArticle 変換（content:encoded の優先採用等）。
  - DuckDB への保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING と INSERT ... RETURNING による新規挿入判定。チャンク分割・単一トランザクション。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols への紐付けをチャンク挿入、RETURNING で挿入数算出。
  - 銘柄コード抽出ユーティリティ（4桁数字の抽出と known_codes によるフィルタリング）。
  - run_news_collection: 複数 RSS ソースの統合収集ジョブ（ソース単位でのエラーハンドリング・新規件数集計）。

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - Raw レイヤーの DDL を実装（例: raw_prices, raw_financials, raw_news, raw_executions の定義を含む）。
  - 各テーブルに型チェック、NOT NULL、PRIMARY KEY、CHECK 制約等を設定してデータ整合性を強化。

- ファクター・リサーチ（src/kabusys/research/*
 ）
  - feature_exploration.py:
    - calc_forward_returns: 指定基準日から複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで計算。
    - calc_ic: Spearman ランク相関（ランク変換・同順位は平均ランク）によりファクターの IC を計算。データ不足時は None を返す。
    - rank: 値リスト→ランク変換（round(..., 12) による浮動小数エラー回避つき）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - これらは外部ライブラリに依存せず標準ライブラリのみで実装。
  - factor_research.py:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離率）を DuckDB のウィンドウ関数で計算。データ不足は None。
    - calc_volatility: 20日 ATR（true_range の平均）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を適切に制御。
    - calc_value: raw_financials の最新（target_date 以前）財務を参照して PER（EPS が 0/欠損なら None）と ROE を計算。
  - research パッケージの __init__ で主要ユーティリティを公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- その他
  - データ処理でのパフォーマンス配慮: チャンク化バルク INSERT、単一トランザクションまとめ、SQL 側でのウィンドウ関数利用による効率化。
  - ロギングを各モジュールに導入し、処理状況や警告・エラーを記録。

### Security
- RSS 収集における SSRF 対策:
  - URL スキーム制限（http/https）、リダイレクト時の事前検証、ホスト/IP のプライベート判定（DNS 解決含む）。
  - defusedxml による XML パース（外部攻撃に対する防御）。
  - レスポンスサイズ上限・gzip 解凍後サイズチェック（DoS 対策）。
- J-Quants クライアントはトークン自動リフレッシュを安全に行い、無限再帰を防止。
- DB 挿入は冪等化（ON CONFLICT）されており、同一データの二重挿入を防止。

### Performance
- API 呼び出しは固定間隔のスロットリングでレート制限を順守。
- bulk INSERT をチャンク化して SQL 長／パラメータ数を制御。
- DuckDB 側でウィンドウ関数を活用し集計を行うことで Python 側のメモリ負荷を低減。

### Notes / Known limitations
- strategy および execution パッケージは初期化ファイルのみ（未実装の可能性あり）。発注ロジックや実行管理は今後の実装予定。
- research モジュールは DuckDB の prices_daily / raw_financials テーブルに依存。実行前にスキーマとデータ初期化が必要。
- J-Quants API 利用には JQUANTS_REFRESH_TOKEN の設定が必須。
- save_* 系関数は DuckDB 接続（duckdb.DuckDBPyConnection）を前提としている。
- data.stats.zscore_normalize は参照され公開しているが、本ログにはその実装ファイルは含まれていない可能性があります（別ファイルで実装済み）。

### Fixed
- 初回リリースにつき該当なし

### Changed
- 初回リリースにつき該当なし

---

（以降のリリースでは Unreleased セクションを利用し、変更が確定したらバージョンと日付を追加してください。）