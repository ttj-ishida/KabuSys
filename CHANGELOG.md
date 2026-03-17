# Changelog

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
このファイルは日本語で、パッケージの主要な追加・変更点・セキュリティ考慮をまとめたものです。

## [Unreleased]

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買基盤「KabuSys」のコア機能群を実装しました。以下の主要コンポーネントを含みます。

### Added
- パッケージ基盤
  - パッケージ名: `kabusys`、バージョン 0.1.0。
  - モジュール構造の骨格: data, strategy, execution, monitoring（strategy/execution は現状初期化ファイルのみ）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ローダーを実装。読み込み優先度は OS 環境 > `.env.local` > `.env`。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）により、実行カレントディレクトリに依存しない自動読み込み。
  - `.env` パーサーの強化: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理（クォートあり/なしに応じた挙動）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト等の利便性向上）。
  - 設定アクセス用の Settings クラスを提供（J-Quants トークン、kabu API 設定、Slack トークン、DB パス、環境種別・ログレベルのバリデーション等）。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API から以下データ取得機能を実装:
    - 株価日足（fetch_daily_quotes）
    - 財務データ（四半期 BS/PL）（fetch_financial_statements）
    - JPX マーケットカレンダー（fetch_market_calendar）
  - 認証: リフレッシュトークンから ID トークンを取得する get_id_token を実装。401 受信時の自動トークンリフレッシュに対応。
  - レート制御: 120 req/min のレート制限を満たす固定間隔スロットリング（内部 RateLimiter）。
  - 再試行ロジック: 指数バックオフ付きのリトライ（最大 3 回）、408/429/5xx に対する再試行、429 の場合は Retry-After ヘッダを尊重。
  - 取得時刻トレース: データ保存時に fetched_at を UTC で記録し、Look-ahead Bias の追跡を可能に。
  - DuckDB への保存: save_daily_quotes / save_financial_statements / save_market_calendar を実装。いずれも冪等性を保つため ON CONFLICT DO UPDATE（UPSERT）を使用。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news テーブルへ保存する機能を実装。
  - 主な特徴:
    - defusedxml を用いた安全な XML パース（XML Bomb 等の対策）。
    - HTTP レスポンスサイズ上限（デフォルト 10 MB）と gzip 解凍後の上限チェック（Gzip bomb 対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、リダイレクト時の事前検証ハンドラ、送信先ホストがプライベート/ループバック/リンクローカルでないことの検査。
    - 記事ID は正規化した URL の SHA-256（先頭32文字）で生成し、トラッキングパラメータ（utm_* 等）を除去して冪等性を担保。
    - テキスト前処理: URL 除去、空白正規化。
    - DB 保存: INSERT ... RETURNING を用いて実際に挿入された記事IDを返却。チャンク挿入（デフォルト 1000 件）と単一トランザクションでのコミット。
    - 銘柄コード抽出: 本文/タイトルから 4 桁銘柄コードを抽出し、既知銘柄リストに基づいて news_symbols に紐付け。
    - ユーティリティ関数: URL 正規化、ID 生成、RSS pubDate パース（タイムゾーンを UTC に正規化）等。

- DuckDB スキーマ管理（kabusys.data.schema）
  - DataSchema.md に準拠したスキーマを実装（3 層 + 実行層を考慮）:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - スキーマ初期化関数 init_schema(db_path) を提供。存在しない親ディレクトリの自動作成、冪等なテーブル作成およびインデックス作成を実施。
  - get_connection(db_path) により既存 DB へ接続可能（初回は init_schema を推奨）。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL の基本構造と補助関数を実装:
    - ETLResult データクラス: 各 ETL 実行の結果（取得数、保存数、品質問題、エラーリスト）を保持。品質問題はチェック名・重大度・メッセージ形式でシリアライズ可能。
    - 差分更新ヘルパー: テーブルの最終取得日を取得する get_last_price_date / get_last_financial_date / get_last_calendar_date。
    - 取引日調整ロジック: 非営業日に対して直近の営業日に調整する _adjust_to_trading_day（market_calendar テーブルに依存）。
    - run_prices_etl: 株価差分 ETL の実装（差分計算、backfill_days による再取得、jquants_client 経由での取得と save）。品質チェックモジュール quality と連携する設計（品質チェックは重大度に関わらず集約して返却する方針）。

### Security
- ニュース収集における SSRF 対策（スキーム制限、リダイレクト検査、プライベートアドレス検出）を実装。
- XML パーシングに defusedxml を使用して XML 関連の脆弱性を軽減。
- .env パーサーのクォート/エスケープ処理を慎重に実装し、意図しない解釈を防止。

### Documentation / Logging
- 各モジュールに設計方針や処理フロー、想定されるデータ/エラー挙動を示す docstring を豊富に追加。ログ出力箇所を適切に配置して運用時のトラブルシュートに配慮。

### Notes / Known limitations
- strategy および execution パッケージは初期化ファイルのみで、具体的な戦略や発注ロジックは未実装のままです（今後の実装予定）。
- quality モジュール（品質チェック）の具体的な実装ファイルはこのスナップショットに含まれていない可能性がありますが、pipeline は品質チェック結果を扱うインターフェースを前提に設計されています。
- run_prices_etl などパイプラインの一部は呼び出し側のフロー（スケジューラ連携、監査ログ出力、Slack 通知等）によって運用される想定です。運用統合は別途実装を推奨します。

---

この CHANGELOG はリリースで確認された設計方針と実装の要点をまとめたものです。将来のリリースでは各機能の詳細な変更（バグ修正、性能改善、API 互換性の変更など）を追記していきます。