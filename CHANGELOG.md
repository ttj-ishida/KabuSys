# Changelog

すべての重要な変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」準拠です。

全般方針:
- 意味のあるリリースごとにセクションを作成しています。
- ここに記載されていない内部的な実装調整は含めていません。

## [0.1.0] - 2026-03-18

### Added
- 初期リリース。日本株自動売買システム「KabuSys」の基本モジュール群を追加。
  - パッケージメタ情報
    - src/kabusys/__init__.py に __version__="0.1.0" を設定。
    - パブリック API: data, strategy, execution, monitoring を __all__ に公開。

  - 設定 / 環境変数管理（src/kabusys/config.py）
    - .env ファイルおよび環境変数から設定を自動読み込み（優先順位: OS 環境変数 > .env.local > .env）。
    - プロジェクトルートの自動検出（.git または pyproject.toml を起点に探索）により CWD 非依存で動作。
    - .env のパースは export KEY=val 形式、クォートやインラインコメント、エスケープ等に対応。
    - 環境変数読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用）。
    - 必須変数取得時に未設定なら ValueError を投げる _require() を提供。
    - KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL の検証ロジックを実装。
    - DB パスのデフォルト（duckdb/sqlite）を提供。

  - Data モジュール
    - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
      - /token/auth_refresh による id_token 取得（get_id_token）。
      - レート制御（120 req/min）を固定間隔スロットリングで実装する RateLimiter。
      - 再試行ロジック（指数バックオフ、最大3回、408/429/5xx を再試行対象）。
      - 401 受信時は自動でトークンリフレッシュして 1 回だけリトライする仕組み。
      - ページネーション対応でデータを取得する fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
      - DuckDB へ冪等に保存する save_daily_quotes / save_financial_statements / save_market_calendar（ON CONFLICT DO UPDATE）。
      - 入力変換ユーティリティ _to_float / _to_int（文字列・数値変換の安全処理）。
      - 取得時刻を UTC（ISO）で記録し、Look-ahead バイアス追跡に配慮。

    - ニュース収集（src/kabusys/data/news_collector.py）
      - RSS フィードを取得して raw_news テーブルへ保存する機能を提供。
      - デフォルト RSS ソースに Yahoo Finance ビジネスカテゴリを設定。
      - セキュリティ対策:
        - defusedxml を使用して XML の攻撃（XML bomb 等）を緩和。
        - SSRF 対策: リダイレクト先のスキームとホスト（プライベート/ループバック等）を検証。初回ホスト検査も実施。
        - URL スキーム検証（http/https のみ許可）。
        - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
      - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し、トラッキングパラメータ（utm_* など）を削除して冪等性を担保。
      - テキスト前処理（URL 除去、空白正規化）。
      - raw_news の INSERT は ON CONFLICT DO NOTHING と INSERT ... RETURNING を併用し、実際に挿入された ID を返す save_raw_news。
      - 銘柄紐付け（news_symbols）を一括挿入する _save_news_symbols_bulk / save_news_symbols。チャンク処理により SQL 長の抑制。
      - テキストから銘柄コードを抽出する extract_stock_codes（4桁数値に基づくフィルタリング、重複排除）。

    - DuckDB スキーマ定義（src/kabusys/data/schema.py）
      - Raw Layer のテーブル DDL を追加（raw_prices, raw_financials, raw_news, raw_executions の定義を含む）。
      - テーブルの制約（CHECK / PRIMARY KEY）やデフォルト値を定義。

  - Research モジュール
    - 特徴量探索（src/kabusys/research/feature_exploration.py）
      - 将来リターン計算 calc_forward_returns（1,5,21 日等のホライズン対応、DuckDB の prices_daily を参照）。
      - IC（Information Coefficient）計算 calc_ic（Spearman の ρ をランクで計算、欠損/非有限値の除外、最小有効サンプルは 3）。
      - ランク計算ユーティリティ rank（同順位は平均ランク、浮動小数点誤差対策に round(v,12) を使用）。
      - ファクター統計 summary を計算する factor_summary（count/mean/std/min/max/median）。
      - 設計方針として pandas 等に依存せず標準ライブラリのみで実装。DuckDB 接続のみ参照し外部 API 呼び出しを行わない旨を明記。

    - ファクター計算（src/kabusys/research/factor_research.py）
      - Momentum ファクター calc_momentum（1M/3M/6M リターン、MA200 乖離率、データ不足時は None）。
      - Volatility / Liquidity ファクター calc_volatility（20日 ATR / ATR 比率 / 20日平均売買代金 / 出来高比率）。
      - Value ファクター calc_value（raw_financials から直近財務データを取得して PER/ROE を計算）。
      - 各関数は prices_daily / raw_financials のみ参照し、本番 API にアクセスしないことを保証。
      - 計算ではウィンドウ長に応じたスキャン範囲バッファを設け、週末/祝日を吸収する実装。

  - パッケージ (research/__init__.py) で主なユーティリティ / 関数をエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

  - 空のパッケージ初期化ファイルを追加
    - src/kabusys/execution/__init__.py
    - src/kabusys/strategy/__init__.py
    （将来の拡張ポイントとして確保）

### Security
- ニュース収集での SSRF 対策（リダイレクト検査・プライベートアドレス検出）を実装。
- defusedxml を用いた XML パースで外部攻撃に対する耐性を向上。
- HTTP レスポンスサイズ上限と gzip 解凍後のチェックでメモリ DoS を緩和。

### Performance / Reliability
- J-Quants API クライアントに固定間隔の RateLimiter を導入し、API レート上限（120 req/min）に整合。
- 再試行ロジックと指数バックオフで一時的なネットワーク障害に耐性を持たせる。
- DuckDB への保存は冪等化（ON CONFLICT）とトランザクション制御により整合性を確保。
- RSS 保存・銘柄紐付けはチャンク挿入で SQL 長・パラメータ数を抑制。

### Documentation / Usage Notes
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings._require により未設定はエラー）。
  - デフォルトの DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。
  - KABUSYS_ENV は development / paper_trading / live のいずれかでなければならない。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基に行われる。CI/テスト等で自動ロードを抑止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB テーブル名（prices_daily, raw_prices, raw_financials, raw_news, market_calendar 等）に依存するため、既存 DB を流用する場合はスキーマ互換を確認してください。

### Known limitations / Todo
- strategy/ execution / monitoring パッケージは初期プレースホルダ（詳細実装は未提供）。
- 一部のファクター（例: PBR、配当利回り）は未実装（calc_value 注記参照）。
- research は標準ライブラリのみで実装しているため、大規模データ処理では pandas 等を利用した高速化が将来的に必要になる可能性あり。

### Breaking Changes
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。