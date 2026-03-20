# Changelog

すべての重要な変更を記録します。フォーマットは Keep a Changelog に準拠します。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-03-20

### Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
    - 公開モジュール: data, strategy, execution, monitoring。

- 環境設定・自動 .env ロード機能
  - src/kabusys/config.py
    - プロジェクトルート検出: .git または pyproject.toml を起点に自動検出する _find_project_root。
    - .env/.env.local の自動読み込み（OS 環境変数を保護して読み込み優先度を実装）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env 行パーサーの実装（export プレフィクス、クォート・エスケープ、インラインコメント処理対応）。
    - 必須環境変数取得関数 _require および Settings クラス:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等のラッパー。
      - DUCKDB_PATH / SQLITE_PATH のデフォルトパス設定。
      - KABUSYS_ENV の値検証（development / paper_trading / live）や LOG_LEVEL の検証。
      - is_live/is_paper/is_dev ヘルパー。

- データ取得・保存（J-Quants API クライアント）
  - src/kabusys/data/jquants_client.py
    - RateLimiter 実装（120 req/min 固定間隔スロットリング）。
    - 汎用リクエストラッパー _request:
      - 指数バックオフ付きリトライ（最大 3 回）。
      - 408/429/5xx に対するリトライ、429 の Retry-After を尊重。
      - 401 受信時は自動でトークンをリフレッシュして 1 回リトライ。
      - ページネーション対応。
      - JSON デコードエラーハンドリング。
    - 認証支援: get_id_token（refresh token から id token を取得）。
    - API データ取得関数:
      - fetch_daily_quotes（株価日足、ページング対応）
      - fetch_financial_statements（財務データ、ページング対応）
      - fetch_market_calendar（JPX カレンダー）
    - DuckDB への永続化関数（冪等）:
      - save_daily_quotes, save_financial_statements, save_market_calendar
      - ON CONFLICT ... DO UPDATE を用いた重複排除
      - fetched_at を UTC ISO 形式で記録
      - 入力パース用ユーティリティ _to_float / _to_int（堅牢な変換ロジック）
    - 実装上の注記: 取得時のレート制御、トークンキャッシュ（モジュールレベル）等によりページネーション間の一貫性を保持。

- ニュース収集モジュール
  - src/kabusys/data/news_collector.py
    - RSS フィード収集パイプライン（デフォルトに Yahoo Finance のビジネスカテゴリを含む）。
    - 記事 ID は URL 正規化後の SHA-256（先頭 32 文字）で生成して冪等性を担保。
    - URL 正規化機能 _normalize_url:
      - スキーム/ホストを小文字化、トラッキングパラメータ（utm_*, fbclid など）削除、フラグメント削除、クエリパラメータソート。
    - defusedxml による XML パース（XML Bomb 等の防御）。
    - HTTP 応答サイズ制限（MAX_RESPONSE_BYTES = 10MB）や SSRF 対策（スキーム検証、IP チェック等の方針を想定）。
    - バルク INSERT のチャンク化とトランザクションでの保存、ON CONFLICT DO NOTHING による冪等保存。
    - テキスト前処理（URL 除去、空白正規化等）。

- 研究用ファクター計算・解析ライブラリ（Research）
  - src/kabusys/research/factor_research.py
    - モメンタム計算（calc_momentum）:
      - mom_1m, mom_3m, mom_6m（それぞれ営業日基準のラグ）、ma200_dev（200 日移動平均乖離。データ不足時は None）。
      - スキャン範囲のバッファにより祝日/休場日を考慮。
    - ボラティリティ / 流動性計算（calc_volatility）:
      - ATR(20) の算出（true_range を厳密に扱い、NULL 伝播を考慮）。
      - atr_pct（ATR ÷ close）、20日平均売買代金、出来高比率。
    - バリュー計算（calc_value）:
      - raw_financials から target_date 以前の最新レコードを採取して PER（close / EPS）・ROE を算出。
      - PK 欠損や EPS=0 の場合の安全処理。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）:
      - LEAD を使ったホライズン別の fwd returns（デフォルト [1,5,21]）。
      - ホライズン検証（1〜252 営業日）。
    - IC（Information Coefficient）計算（calc_ic）:
      - コードで結合後、Spearman の ρ（ランキング相関）を算出。サンプル不足（<3）では None。
      - rank 関数: 同順位は平均ランク、round(..., 12) により浮動小数誤差を軽減。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで実装。
  - research パッケージの __init__ にて主要 API を再公開（calc_momentum/calc_volatility/calc_value/zscore_normalize/calc_forward_returns/calc_ic/factor_summary/rank）。

- 戦略（Strategy）
  - src/kabusys/strategy/feature_engineering.py
    - 研究で算出した生ファクターを正規化・合成して features テーブルへ保存する一連処理（build_features）。
    - 処理内容:
      - calc_momentum / calc_volatility / calc_value を呼び出して生ファクターを取得。
      - ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を適用。
      - 数値ファクターを z スコアで正規化（kabusys.data.stats.zscore_normalize を利用）。±3 でクリップ。
      - 日付単位で DELETE → INSERT（トランザクション）による冪等アップサートを実行。
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合して最終スコア final_score を計算し、売買シグナルを生成（generate_signals）。
    - 実装内容:
      - コンポーネントスコア（momentum / value / volatility / liquidity / news）の算出ロジック（シグモイド変換、PER の逆関数等）。
      - デフォルト重みの導入、ユーザ指定 weights の検証と正規化（合計が 1 になるようリスケール）。
      - Bear レジーム判定（regime_score の平均が負かつサンプル数が閾値以上）。
      - BUY シグナルは threshold（デフォルト 0.60）を超える銘柄に付与。Bear レジームでは BUY を抑制。
      - SELL（エグジット）ロジック:
        - ストップロス（終値/avg_price - 1 < -0.08）
        - final_score が閾値未満
        - 価格欠損や avg_price 異常時の安全処理（判定スキップやログ出力）
      - SELL を優先して BUY から除外、日付単位の置換（トランザクション）で signals テーブルへ書き込み。
    - ロギングによる各種警告・情報出力を充実（weights の不正入力、features 空、Bear 検知、ROLLBACK 警告等）。

- 汎用・安全設計上の配慮（全体）
  - 各永続化処理やシグナル作成はトランザクション（BEGIN/COMMIT/ROLLBACK）とバルク挿入を利用して原子性と効率を担保。
  - 入力データ不足や数値の非有限 (NaN/Inf) に対する安全処理が多数実装。
  - 本番発注層（execution）や外部発注 API への依存を持たない設計（戦略・研究層は独立）。
  - 外部ライブラリへの依存を最小化（research の集計処理は標準ライブラリのみで実装）。ただし XML の安全パースに defusedxml を利用。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- news_collector で defusedxml を利用して XML ベースの攻撃を軽減。
- RSS / URL の正規化・追跡パラメータ除去、レスポンスサイズ制限、HTTP スキーム検証等により SSRF・DoS のリスクを考慮。

Notes:
- ドキュメント内の StrategyModel.md / DataPlatform.md 等の参照に従った実装方針が多数記載されていますが、それらの追加ドキュメントは本リリースに含まれる想定です。
- 実際の運用（特に発注・execution 部分）では、kabu ステーション API のクレデンシャル管理や安全な運用手順が別途必要です。