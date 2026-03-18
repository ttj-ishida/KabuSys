# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに従っています。  

※バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に準拠しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-18
初回リリース。日本株自動売買システム「KabuSys」の基礎機能群を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基礎
  - パッケージメタ情報を追加（src/kabusys/__init__.py, __version__ = "0.1.0"）。
  - モジュール構成（data, strategy, execution, monitoring）のエクスポートを追加。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機構（プロジェクトルートを .git / pyproject.toml から検出）。
  - .env 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - 強力な .env パーサを実装（export 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理など）。
  - 環境変数必須チェック（_require）および以下プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト有）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH（デフォルトパス有）
    - KABUSYS_ENV（development/paper_trading/live の検証）および LOG_LEVEL 検証
    - is_live / is_paper / is_dev ユーティリティ

- データ取得クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。
  - 固定間隔の RateLimiter（デフォルト 120 req/min）を導入。
  - HTTP リクエストユーティリティ（JSON パース、ページネーション、ヘッダ管理）。
  - 再試行ロジック（指数バックオフ、最大 3 回）、408/429/5xx を対象。429 の場合 Retry-After を尊重。
  - 401 時の自動トークンリフレッシュ（1 回のみ再試行）とモジュールレベルの ID トークンキャッシュ。
  - データフェッチ関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes（raw_prices）
    - save_financial_statements（raw_financials）
    - save_market_calendar（market_calendar）
  - 入力変換ユーティリティ _to_float / _to_int（堅牢な変換ルール）

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード取得・前処理・DuckDB 保存ワークフローを実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 回避）
    - SSRF 対策（スキーム検証、プライベートアドレス判定、リダイレクト時の検査）を行うカスタム RedirectHandler を導入
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）・gzip 解凍後の検査（Gzip bomb 対策）
    - 許可スキームは http/https のみ
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保
  - テキスト前処理（URL 除去、空白正規化）
  - 銘柄コード抽出（4桁数字を抽出し known_codes と照合）
  - DB 保存:
    - save_raw_news（チャンク分割、INSERT ... RETURNING で新規挿入IDを取得、トランザクション）
    - save_news_symbols / _save_news_symbols_bulk（記事と銘柄の紐付け、チャンク挿入）
  - run_news_collection：複数ソースの統合収集ジョブ（ソース単位で個別にエラーハンドリング）

- リサーチ / ファクター（src/kabusys/research/*.py）
  - feature_exploration:
    - calc_forward_returns（指定日から複数ホライズンの将来リターンを DuckDB の prices_daily から一括計算）
    - calc_ic（Spearman ランク相関による IC 計算、同順位は平均ランク処理）
    - rank（平均ランクの計算、丸め誤差対策）
    - factor_summary（count/mean/std/min/max/median を算出）
    - 外部ライブラリに依存せず標準ライブラリで実装
  - factor_research:
    - calc_momentum（mom_1m/mom_3m/mom_6m、ma200_dev）
    - calc_volatility（atr_20, atr_pct, avg_turnover, volume_ratio）
    - calc_value（raw_financials と prices_daily を組み合わせて PER/ROE を生成）
    - 各関数は DuckDB 接続を受け取り prices_daily / raw_financials のみ参照（本番 API へアクセスしない）
  - research パッケージ __init__ で主要関数を公開（zscore_normalize は kabusys.data.stats から）

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - Raw Layer の DDL を追加（raw_prices, raw_financials, raw_news, raw_executions の定義（raw_executions は途中まで））
  - スキーマ初期化用モジュール（DDL コメントとテーブル定義を含む）

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Security
- RSS パーサに defusedxml を使用し、SSRF 対策・プライベートアドレスブロック・レスポンスサイズ制限等の複数の防御線を導入しました。
- J-Quants クライアントのトークン管理と自動リフレッシュで認証失敗時の安全な再試行を実現。

### Developer notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- デフォルト DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- 自動 .env ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- news_collector では既知銘柄セット（known_codes）を渡すことで記事と銘柄の紐付けを行います（渡さない場合は抽出をスキップ）。

### Known limitations / TODO
- schema.py の raw_executions 定義が途中までで、実行系（Execution Layer）のテーブル定義が未完了です。
- strategy / execution / monitoring の中身は未実装（初期のパッケージ構成のみ）。
- research は pandas 等に依存しない実装だが、大量データでの性能チューニング・ベンチマークは今後必要。
- 単体テスト群は同梱されていません。ネットワーク関連コードはモック可能な設計（例: _urlopen の差し替え）になっています。

---

（以上）