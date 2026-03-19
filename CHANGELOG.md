# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
このドキュメントはコードベース（初期リリース）から推測して作成しています。

全般:
- バージョニングはパッケージの __version__ に合わせて 0.1.0 としています。
- 本リリースは初期機能の実装を中心とした「ベースライン」リリースです。

## [0.1.0] - 2026-03-19

### Added
- パッケージ基盤
  - パッケージ初期化とバージョン管理を追加（src/kabusys/__init__.py）。
  - モジュール分割: data, research, strategy, execution, monitoring の想定された名前空間を用意。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読込する仕組みを実装。プロジェクトルート検出は .git または pyproject.toml を基準に行うため、CWD に依存しない。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
  - .env パーサ実装（クォート処理、エスケープ処理、インラインコメント処理、export プレフィックス対応）。
  - Settings クラスによる型付き設定アクセス（必須設定の検査・例外投げ、パスの Path 変換、KABUSYS_ENV/LOG_LEVEL のバリデーション等）。
  - 必須環境変数例:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID

- データ収集クライアント（J-Quants） (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。
  - レートリミッタ（固定間隔スロットリング）により 120 req/min を順守。
  - リトライロジック（指数バックオフ、最大3回）を実装。408/429/5xx をリトライ対象に含める。
  - 401 受信時はリフレッシュトークンで id_token を自動取得して再試行（1回のみ）。
  - ページネーション対応の fetch_daily_quotes / fetch_financial_statements 実装。
  - JPX マーケットカレンダー取得（fetch_market_calendar）。
  - DuckDB への冪等保存関数を提供:
    - save_daily_quotes（raw_prices）、save_financial_statements（raw_financials）、save_market_calendar（market_calendar）
  - データ変換ユーティリティ: _to_float, _to_int（堅牢な変換ルール）

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード取得と前処理、一括保存ワークフローを実装。
  - セキュリティ & 堅牢性機能:
    - defusedxml による XML パース（XML Bomb 対策）
    - SSRF 対策: URL スキーム検証、ホストがプライベート/ループバック/リンクローカルでないかチェック、リダイレクト先の再検証、専用 RedirectHandler 実装
    - 最大受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後のサイズチェック（Gzip bomb 対策）
    - URL 正規化（トラッキングパラメータ除去）、記事 ID を SHA-256（先頭32文字）で生成して冪等性を確保
  - DB 保存:
    - save_raw_news: INSERT ... RETURNING を用いて実際に挿入された記事 ID を返却。チャンク化・トランザクション処理。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの銘柄紐付けをチャンクで挿入（ON CONFLICT DO NOTHING を使用）。
  - 銘柄コード抽出ユーティリティ（4桁数字パターン）およびテキスト前処理関数 preprocess_text。
  - run_news_collection により複数 RSS ソースの収集を統合制御。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution レイヤを想定したスキーマ定義の土台を追加。
  - raw_prices, raw_financials, raw_news, raw_executions などの DDL を定義（CHECK 制約や PRIMARY KEY 設定含む）。

- リサーチ（特徴量・ファクター計算） (src/kabusys/research/)
  - feature_exploration.py:
    - calc_forward_returns: 指定日から各ホライズン（デフォルト [1,5,21]）の将来リターンを DuckDB の prices_daily テーブルから一括取得して計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。レコード不足・定数列を考慮して None を返すロジックを実装。
    - rank: 平均ランクを返すランク付け実装（同順位は平均順位、丸めで ties の検出漏れを低減）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - factor_research.py:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離率）を計算。必要なウィンドウ不足時は None を返す。
    - calc_volatility: 20日 ATR、atr_pct、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を適切に制御。
    - calc_value: raw_financials と prices_daily を組み合わせ、per（EPS による計算）と roe を算出。最新の target_date 以前の財務レコードを取得するロジックを実装。
  - 研究モジュールは DuckDB の prices_daily / raw_financials のみ参照し、本番 API へのアクセスは行わない設計。

- 再利用可能ユーティリティ
  - research/__init__.py で主要関数をエクスポート（calc_momentum 等と zscore_normalize の統合エクスポートを想定）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- RSS 収集における SSRF 対策、XML パースの安全化、受信サイズ制限など多数の防御機構を追加。
- J-Quants クライアントは 401 時のトークン自動リフレッシュとレート制御・リトライで耐障害性を向上。

### Notes / Known limitations / Migration
- strategy/ と execution/ のパッケージはプレースホルダとして存在するが、具体的な発注ロジック・モジュールは未実装。
- research モジュールは標準ライブラリのみを利用する実装方針を掲げているが、実行には duckdb パッケージが必要。
- 環境変数の名称や必須項目は Settings クラスにて定義されているため、導入時は .env.example を参照して設定すること。
- DuckDB スキーマ関係は schema.py に DDL を定義しているが、初期化関数のラッパやマイグレーションツールは現状含まれていない。

もし追加で次のリリースノート（機能要望、改善予定、具体的なマイグレーション手順など）を含めたい場合は、優先度やターゲット日程を教えてください。