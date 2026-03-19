CHANGELOG
=========

すべての変更は Keep a Changelog の方針に従って記載しています。
このファイルは人間に読まれることを主目的としており、安定版リリースや互換性のある変更の履歴を残します。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- セキュリティ (Security)
- 非推奨 (Deprecated)
- 削除 (Removed)

[Unreleased]
------------

- 現時点で未リリースの変更はありません。

[0.1.0] - 2026-03-19
--------------------

初回リリース（初期実装）。パッケージ名: kabusys。以下の主要機能・モジュールを追加。

Added
- パッケージ初期化
  - src/kabusys/__init__.py
    - パッケージメタ情報とエクスポート: __version__ = "0.1.0"
    - __all__ に data, strategy, execution, monitoring を設定。

- 設定・環境変数管理
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートを .git / pyproject.toml で検出）。
    - .env のパース機能を実装（コメント、export プレフィックス、クォート・エスケープ、インラインコメント処理などに対応）。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - Settings クラスを提供し、必須設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）や既定値（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH）を管理。
    - KABUSYS_ENV / LOG_LEVEL の値検証ロジック（許容値の制約）を実装。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- データ取得・保存（J-Quants クライアント）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアント実装（認証・ページネーション対応）。
    - RateLimiter による固定間隔スロットリング（120 req/min 想定）。
    - HTTP リクエストのリトライロジック（指数バックオフ、最大3回、408/429/5xx を対象）。429 の場合は Retry-After ヘッダ優先。
    - 401 Unauthorized 受信時の自動トークンリフレッシュ（1 回のみ）とキャッシュ管理。
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar のデータ取得関数（ページネーション対応）。
    - DuckDB 向け保存関数（冪等性を保つ INSERT ... ON CONFLICT DO UPDATE）
      - save_daily_quotes（raw_prices へ保存）
      - save_financial_statements（raw_financials へ保存）
      - save_market_calendar（market_calendar へ保存）
    - 型変換ユーティリティ _to_float / _to_int を提供（空値・不適切値耐性）。

- ニュース収集（RSS）
  - src/kabusys/data/news_collector.py
    - RSS フィード取得・パース・前処理・DB保存の統合モジュール。
    - セキュアな XML パース（defusedxml を利用）と XML パースエラーの耐性。
    - _normalize_url による URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）。
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
    - RSS 取得における SSRF 対策:
      - 許可スキームは http/https のみ
      - リダイレクト時の検査を行うカスタム RedirectHandler（_SSRFBlockRedirectHandler）
      - ホストがプライベート/ループバック/リンクローカルでないかの検査（_is_private_host）
    - レスポンスサイズ保護（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後サイズチェック（Gzip bomb 対策）。
    - テキスト前処理（URL除去、空白正規化）。
    - extract_stock_codes による本文からの銘柄コード抽出（4桁数字、known_codes フィルタ）。
    - DB 保存関数:
      - save_raw_news: INSERT ... RETURNING を用いたチャンク挿入（トランザクションでまとめる）。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付け挿入（チャンク・トランザクション処理）。
    - run_news_collection: 複数 RSS ソースを順次処理し、新規記事数と銘柄紐付けを行う統合ジョブ。

- リサーチ / ファクター計算
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns（DuckDB の prices_daily を参照、複数ホライズン対応、SQL 一発取得）。
    - IC（Information Coefficient）計算 calc_ic（スピアマン順位相関、欠損・非有限値処理、最小レコード数検査）。
    - rank, factor_summary（同順位は平均ランク、基本統計量 count/mean/std/min/max/median を計算）。
    - 設計上、標準ライブラリのみで実装（pandas 等外部依存なし）。DuckDB 接続入力仕様。
  - src/kabusys/research/factor_research.py
    - モメンタム・ボラティリティ・バリュー等の定量ファクター計算関数を実装:
      - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200日移動平均乖離）
      - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（ATR・出来高系指標）
      - calc_value: per, roe（raw_financials と prices_daily を組み合わせ）
    - 各関数は DuckDB の prices_daily / raw_financials テーブルのみを参照し、本番 API にはアクセスしない設計。
    - 日数スキャンのバッファ、NULL 伝播や必要行数チェック等の耐性実装。
  - src/kabusys/research/__init__.py
    - 主要ユーティリティとファクター関数をまとめてエクスポート（zscore_normalize の参照も含む）。

- スキーマ定義
  - src/kabusys/data/schema.py
    - DuckDB 用 DDL 定義（Raw Layer 等のテーブル群）。
    - raw_prices, raw_financials, raw_news, raw_executions 等の CREATE TABLE 文を実装（制約・型付き）。
    - 初期化・スキーマ管理を目的としたモジュール（DataSchema.md 準拠の設計を反映）。

- その他
  - ロギングを多用し重要なイベント（取得件数、スキップ数、警告・例外）を記録。
  - トランザクション単位での DB 操作、チャンク処理による SQL パラメータ過剰回避。
  - ドキュメント的な docstring に設計方針や注意点を多く記載。

Security
- RSS モジュールで SSRF 対策を実装（スキーム検証、プライベートホスト検出、リダイレクト先検査）。
- XML パースに defusedxml を利用して XML-based 攻撃に対処。
- HTTP レスポンスサイズ上限と gzip 解凍後の再チェックによりメモリ DoS を軽減。

Changed
- 該当なし（初回リリース）。

Fixed
- 該当なし（初回リリース）。

Deprecated
- 該当なし。

Removed
- 該当なし。

Notes / 要件
- DuckDB が依存項目として必要（DuckDB の接続オブジェクトを引数に取る関数多数）。
- research モジュールの一部は標準ライブラリのみで実装されているため、集計・解析で pandas 等を想定する既存コードとは相互互換がない可能性あり。
- 環境変数（必須）:
  - JQUANTS_REFRESH_TOKEN（J-Quants API 用）
  - KABU_API_PASSWORD（kabuステーション API 用）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（通知用）
- 設定の自動読み込みはプロジェクトルート検出に依存するため、配布後やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。

今後の検討事項（参考）
- research モジュールでの外部ライブラリ（pandas/numpy）対応による性能向上。
- schema モジュールでの完全な Execution Layer DDL の追加（raw_executions の続きの定義など）。
- 単体テスト・CI の追加（ネットワークや DB を使う部品のモック化を含む）。
- KABU API / Slack 連携の実装（現状は設定管理のみ）。

--- 

（注）上記は提供されたコードの内容・docstring から推測して作成した CHANGELOG です。実際のコミット履歴が存在する場合は、そちらに合わせて調整してください。