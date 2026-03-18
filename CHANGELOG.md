# CHANGELOG

すべての変更は Keep a Changelog の慣例に従って記載しています。  
配列や関数名などはソースコードから推測してまとめています。

## [Unreleased]

（無し）

## [0.1.0] - 2026-03-18

初期リリース。日本株自動売買システム「KabuSys」のコアモジュール群を導入します。以下はソースコードから推測した主要な機能と実装上の注意点です。

### Added
- パッケージ基盤
  - パッケージバージョンを `0.1.0` に設定（src/kabusys/__init__.py）。
  - 公開モジュールとして data, strategy, execution, monitoring を定義。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機構を実装。
    - プロジェクトルートは .git または pyproject.toml を探索して特定（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト時に利用）。
  - .env のパースは以下に対応:
    - コメント行（#）や `export KEY=val` 形式、シングル/ダブルクォート内のエスケープ処理。
    - クォートなしの場合のインラインコメント取り扱い（直前が空白/タブならコメントとみなす）。
  - Settings クラスを提供し、各種必須設定をプロパティとして取得:
    - J-Quants 用 `jquants_refresh_token`
    - kabu API 用 `kabu_api_password` / `kabu_api_base_url`（デフォルト: http://localhost:18080/kabusapi）
    - Slack 用 `slack_bot_token` / `slack_channel_id`
    - DB パス設定 `duckdb_path` / `sqlite_path`
    - 環境種別 `KABUSYS_ENV` とログレベル `LOG_LEVEL` の入力検証（有効値を限定）
    - env 判定ユーティリティ: is_live / is_paper / is_dev

- データ取得・保存（J-Quants クライアント）（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。
  - レート制限（120 req/min）を守る固定間隔 RateLimiter 実装。
  - 再試行ロジック（最大 3 回、指数バックオフ）を実装。HTTP 408/429/5xx を再試行対象に設定。
  - 401 受信時はリフレッシュトークンで自動的に ID トークンを再取得して 1 回リトライする仕組みを実装。
  - ページネーション対応の fetch 関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への冪等保存用 save_* 関数:
    - save_daily_quotes（raw_prices へ upsert）
    - save_financial_statements（raw_financials へ upsert）
    - save_market_calendar（market_calendar へ upsert）
  - 型変換ユーティリティ `_to_float`, `_to_int` を実装し、空文字列や不正値を None として扱う。

- ニュース収集（RSS）モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード取得と前処理、DuckDB への保存を行う包括的モジュールを実装。
  - セキュリティ・堅牢性:
    - defusedxml を用いた XML パース（XML ボム等の軽減）。
    - SSRF 対策: リダイレクト検査用ハンドラ、スキーム検証（http/https のみ）およびホスト/IP のプライベート判定。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）チェック、gzip 検査と解凍後サイズ確認。
    - URL 正規化でトラッキングパラメータ（utm_* 等）を除去。
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保。
  - DB 保存:
    - save_raw_news: INSERT ... RETURNING id を用い、新規挿入された記事 ID のみを返す。チャンク化・単一トランザクションで実行。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付けを一括保存（ON CONFLICT DO NOTHING + RETURNING で正確な挿入数を取得）。
  - 銘柄抽出ユーティリティ:
    - extract_stock_codes: 4桁数字を候補として抽出し、既知銘柄セットでフィルタ（重複除去）。
  - 全体ジョブ run_news_collection を提供し、複数ソースを独立処理して集約結果を返す。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - Raw Layer テーブル定義を含む DDL を追加（raw_prices, raw_financials, raw_news, raw_executions など）。
  - Data 層のテーブル定義は DataSchema.md に基づく設計を想定。

- 研究（Research）用解析モジュール（src/kabusys/research/*）
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定基準日から複数ホライズン（デフォルト [1,5,21]）の将来リターンを DuckDB の prices_daily から一度に取得。
      - horizons の入力検証（正の整数かつ <=252）。
      - パフォーマンス考慮でスキャン範囲を max_horizon*2 のカレンダー日で限定。
    - calc_ic: Spearman（ランク相関）による IC 計算（同順位は平均ランク）。有効レコード 3 件未満では None を返す。
    - rank: 同順位は平均ランク、丸め（round 12 桁）による ties の安定化。
    - factor_summary: count/mean/std/min/max/median を計算（None 値は除外）。
    - 研究モジュールは pandas 等に依存せず標準ライブラリ・DuckDB のみで実装される設計方針を明示。
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200日移動平均乖離）を計算。ウィンドウ不足時は None。
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、volume_ratio を計算。true_range は high/low/prev_close のいずれかが NULL の場合 NULL と扱いカウント制御。
    - calc_value: raw_financials から基準日以前の最新財務を取得して PER（close / EPS）・ROE を計算。EPS が 0 または欠損時は PER を None とする。
    - 各関数は prices_daily/raw_financials のみ参照し、外部 API へのアクセスを行わない設計。

- research パッケージの公開 API（src/kabusys/research/__init__.py）
  - calc_momentum, calc_volatility, calc_value, zscore_normalize（data.stats から輸入）, calc_forward_returns, calc_ic, factor_summary, rank を __all__ で公開。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- RSS 収集に対して以下のセキュリティ対策を導入:
  - defusedxml による XML パース（XML 攻撃軽減）。
  - リダイレクト先のスキーム/ホスト検査およびプライベート IP 判定による SSRF 対策。
  - レスポンスサイズ制限と gzip 解凍後のサイズ検査（DoS / Gzip bomb 対策）。
- J-Quants クライアントは認証トークン自動リフレッシュと再試行ロジックを組み込み、失敗時の堅牢性を向上。

### Notes / Implementation details
- 多くのモジュールで「DuckDB 接続（duckdb.DuckDBPyConnection）」を受け取り SQL と組み合わせて計算／保存する設計になっており、本番の発注 API 等にはアクセスしないモジュールと、外部 API（J-Quants）へアクセスするモジュールとで責務が分かれている。
- research モジュールは pandas 等に依存しない実装とされているため、データ処理は SQL と標準ライブラリで行う前提。
- .env パーサはエスケープやクォート、コメントの扱いなど細かなケースに対応しており、CI/ローカルの違いに強い設計。
- DuckDB への保存処理は ON CONFLICT での upsert や INSERT ... RETURNING を活用して冪等性と正確な挿入判定を実現している。
- 現在のスキーマ定義は Raw Layer の DDL が明示されているが、ファイルの一部は切れており Execution Layer 等の完全な DDL は継続実装が想定される。

もし CHANGELOG を個別のコミットに紐付けたい／日付やカテゴリの調整を行いたい場合は、該当箇所（ファイル・関数名）を指定してください。追加の詳細（例: 各関数の返り値例やサンプル使用法）も生成できます。