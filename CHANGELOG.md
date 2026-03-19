# Keep a Changelog

すべての項目は SemVer に従います。  
この CHANGELOG はコードベースから推測して作成しています（実装上の意図・設計方針を要約）。

## [Unreleased]

### Added
- なし

---

## [0.1.0] - 2026-03-19

初回リリース相当。以下の主要機能・モジュールを追加しました。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ に定義。

- 設定管理
  - 環境変数 / .env 自動ロード機能を実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml を基準に探索して .env/.env.local を自動読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化をサポート。
    - .env パーサで `export KEY=val` 形式、クォート（シングル/ダブル）内のバックスラッシュエスケープ、インラインコメントの取り扱い等に対応。
    - 強制取得用の _require() と Settings クラスを提供。主な設定プロパティ:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
      - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
      - DUCKDB_PATH, SQLITE_PATH（デフォルト値を持つ）
      - KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（DEBUG/INFO/... の検証）
      - is_live / is_paper / is_dev 補助プロパティ

- Data: J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しユーティリティを実装:
    - 固定間隔のレートリミッタ（120 req/min）を実装。
    - リトライロジック（指数バックオフ、最大 3 回）と 408/429/5xx 系の再試行制御。
    - 401 受信時はリフレッシュトークンで自動的に ID トークンを再取得して 1 回再試行。
    - ページネーション対応（pagination_key を用いたループ取得）。
    - JSON デコード失敗時の詳細エラーメッセージ。
  - データ取得関数:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務四半期データ）
    - fetch_market_calendar（JPX 市場カレンダー）
  - DuckDB への保存関数（冪等性重視）:
    - save_daily_quotes → raw_prices テーブルに ON CONFLICT DO UPDATE で保存
    - save_financial_statements → raw_financials に ON CONFLICT DO UPDATE
    - save_market_calendar → market_calendar に ON CONFLICT DO UPDATE
  - 型変換ユーティリティ: _to_float, _to_int（文字列→数値変換時の安全処理）

- Data: ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を取得し raw_news / news_symbols に保存する機能を実装。
  - 主な設計・実装点:
    - defusedxml を用いた XML パース（XML ボム等の防御）。
    - URL 正規化（トラッキングパラメータ除去、スキーム・ホスト小文字化、フラグメント削除）、記事 ID を SHA-256（先頭32文字）で生成して冪等性を担保。
    - SSRF 対策:
      - HTTP(S) スキームのみ許可
      - リダイレクト時にスキームとホストを検査するカスタムハンドラ（_SSRFBlockRedirectHandler）
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストの場合は拒否（DNS 解決した複数レコードも検査）
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - content:encoded 優先、description フォールバックなど RSS の多様なフォーマットに対応。
    - raw_news への一括 INSERT はチャンク化してトランザクション内で実行、INSERT ... RETURNING で新規挿入 ID を取得。
    - news_symbols の紐付けを一括保存する内部関数（重複除去、チャンク挿入、トランザクション制御）。
    - 銘柄コード抽出ユーティリティ（4桁数字パターン、known_codes フィルタ、重複除去）。

- Research（研究・特徴量）
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト 1,5,21）に対する将来リターンを DuckDB の prices_daily を参照して一括計算。
    - calc_ic: ファクター値と将来リターンのスピアマン ランク相関（IC）を標準ライブラリのみで計算（同順位は平均ランク）。
    - rank, factor_summary（count/mean/std/min/max/median）を実装。
    - 「pandas など外部ライブラリに依存しない」方針で実装。
  - factor_research（src/kabusys/research/factor_research.py）
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を考慮。
    - calc_value: raw_financials と prices_daily を結合して PER（EPS が 0/欠損の場合は None）・ROE を取得。
    - SQL ウィンドウ関数（LEAD/LAG/AVG/COUNT）を積極的に使用してパフォーマンスを確保。

- Data スキーマ（src/kabusys/data/schema.py）
  - DuckDB 用の DDL を定義:
    - raw_prices, raw_financials, raw_news, raw_executions（テーブル定義を含む）
  - スキーマ層の設計方針（Raw / Processed / Feature / Execution）のコメントを追加。

- 研究モジュールのパッケージ公開（src/kabusys/research/__init__.py）
  - calc_momentum, calc_volatility, calc_value, zscore_normalize（data.stats から）、calc_forward_returns, calc_ic, factor_summary, rank を __all__ で公開。

### Changed
- 初期リリースのため過去バージョンからの変更なし（初回追加）。

### Fixed
- .env パースの堅牢化（空行・コメント、export プレフィックス、クォート内のエスケープ、インラインコメントの扱い）を実装し、実運用で見られる .env の多様な記法に対応。

### Security
- RSS 収集における SSRF 対策追加:
  - リダイレクト検査、スキーム検証、プライベート IP/ホスト検査、defusedxml の利用、レスポンスサイズ上限設定などを実装。
- J-Quants API クライアント:
  - トークンの自動リフレッシュを 1 回に制限し、allow_refresh フラグで再帰的リフレッシュを防止。

### Known issues / Limitations
- research モジュールは外部ライブラリ（pandas/numpy）に依存していないため、非常に大規模データでの処理は最適化余地がある（パフォーマンスチューニングが必要な場合あり）。
- NewsCollector の URL 正規化・トラッキング除去は想定されるトラッキングパラメータのプレフィックスに依存しており、未知のパラメータには対応しない可能性がある。
- get_id_token は settings.jquants_refresh_token に依存しており、該当環境変数未設定時は ValueError を送出する。導入時に .env（または環境変数）を正しく用意する必要あり。
- execution / strategy のパッケージは存在するが、トップレベルに中身が空のモジュールが含まれている（実装は今後追加予定）。
- DuckDB のテーブル定義は用意されているが、実行環境でテーブル作成・マイグレーションを行うユーティリティは別途必要。

### Migration notes
- 環境変数を必須とする項目（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）を .env または OS 環境に設定してください。
- DuckDB（および SQLite）のファイルパスはデフォルト値が設定されていますが、本番では適切なパスに変更してください（DUCKDB_PATH / SQLITE_PATH）。
- ニュース収集を有効にする場合、known_codes（銘柄コードのセット）を渡すと自動で銘柄紐付けが行われます。

---

追記・補足:
- 上記はコードベースの実装内容から推測して整理した CHANGELOG です。実際のリリースノートとして利用する際は、リリース日・責任者・既知のバグ修正等を追記してください。