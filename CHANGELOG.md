CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-17
--------------------

Added
- 基本パッケージ初期リリース: kabusys 0.1.0
  - パッケージルート: src/kabusys/__init__.py にバージョン情報と公開サブパッケージを定義。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動読み込み（優先度: OS 環境 > .env.local > .env）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - プロジェクトルート検出: .git または pyproject.toml を基準に探索（CWD に依存しない実装）。
  - .env パーサーを実装:
    - export KEY=val 形式に対応
    - シングル／ダブルクォート、エスケープシーケンス、行内コメントの扱いに対応
    - 上書き制御（override, protected）をサポート
  - Settings クラスを公開:
    - J-Quants / kabu ステーション / Slack / DB パスなど主要設定のプロパティ
    - KABUSYS_ENV と LOG_LEVEL の値検証（許可値を制限）
    - 辞書的な is_live / is_paper / is_dev ヘルパー

- J-Quants データクライアント (src/kabusys/data/jquants_client.py)
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得機能を実装
  - レート制限制御: 固定間隔スロットリングで 120 req/min を遵守（_RateLimiter）
  - 再試行ロジック:
    - 指数バックオフ（base=2.0）、最大リトライ回数=3
    - 408/429/5xx 系でリトライ、429 の場合は Retry-After ヘッダを優先
    - 401 受信時はトークンを自動リフレッシュして 1 回だけリトライ（無限再帰防止）
  - ページネーション対応（pagination_key を用いたループ）
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead bias を回避
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）
    - 冪等性: INSERT ... ON CONFLICT DO UPDATE を使用
    - PK 欠損レコードはスキップしてログ出力
  - 数値変換ユーティリティ (_to_float, _to_int)
    - 不正な値は None を返す。_to_int は "1.0" を int に変換するが "1.9" のような非整数は None を返す設計

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード取得・前処理・DuckDB への保存ワークフローを実装
  - セキュリティと堅牢性:
    - defusedxml を用いた XML パース（XML Bomb 対策）
    - HTTP(s) スキームのみ許可、SSRF 対策としてプライベート/ループバック/リンクローカルアドレスを拒否
    - リダイレクト時にも検証するカスタム RedirectHandler を使用
    - レスポンスサイズ上限: MAX_RESPONSE_BYTES = 10MB（読み込み時に超過チェック）。gzip 解凍後も検査
    - トラッキングパラメータ（utm_*, fbclid 等）除去、URL 正規化
    - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保
  - fetch_rss: RSS の多様なレイアウトに対応し、title/description/content:encoded を扱う
  - DB 保存:
    - save_raw_news: INSERT ... RETURNING id を使い実際に挿入された記事IDを返却。チャンク処理とトランザクションで高効率かつ安全に保存
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING で重複排除）
  - 銘柄コード抽出ロジック: 4桁の数字を検出し、既知銘柄セットでフィルタ（重複排除）

- DuckDB スキーマ管理 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution の各レイヤー用テーブル定義を実装
  - 代表的テーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, orders, trades, positions, portfolio_* 等
  - 制約（PRIMARY KEY / CHECK / FOREIGN KEY）やインデックスを定義してデータ整合性とクエリ効率を確保
  - init_schema(db_path): 親ディレクトリ自動作成、DDL を順序に従って実行（冪等）
  - get_connection(db_path): 既存 DB への単純接続を提供（初期化は行わない）

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 差分更新（差分 ETL）を想定したジョブ群の基礎を実装
  - 特徴:
    - 最小データ開始日: 2017-01-01（初回ロード用）
    - 市場カレンダー先読み: デフォルトで 90 日先読み
    - デフォルトのバックフィル日数: 3 日（後出し修正吸収用）
    - ETLResult dataclass: フェッチ数 / 保存数 / 品質問題・エラーを集約、品質問題は (check_name, severity, message) に変換可能
    - 品質チェックはフェイルファストとせず、問題を収集して呼び出し元に委ねる設計
    - get_last_* ヘルパーで raw テーブルの最終日取得
    - run_prices_etl: 差分算出ロジック（最終取得日 - backfill_days から再取得）および jq.fetch_* / save_* の呼び出しを実装（部分実装あり）

Changed
- ドキュメント的注記やコード内コメントで設計方針（レート制限、冪等性、SSRF 対策、品質チェックポリシー等）を明確化。

Security
- RSS/HTTP 関連で多数のセキュリティ対策を導入:
  - defusedxml による安全な XML パース
  - URL スキーム検証とプライベートアドレス拒否（SSRF 対策）
  - レスポンスサイズ制限・gzip 解凍後検査（メモリDoS / Gzip Bomb 対策）
  - .env 読み込み時に OS 環境変数の上書きを保護する protected キーの概念

Notes / Known limitations
- 現時点は 0.1.0 の初期実装であり、実運用に向けた追加テスト（特にネットワーク例外・DB ロック競合・大量データ処理時のパフォーマンス評価）が推奨されます。
- run_prices_etl の戻り値や一部機能はコードの途中までの実装（例: 最終 return が途中で切れているなど）に注意。実装を継続・統合する必要がある箇所があります。

---

今後の予定 (例)
- ETL 完全実装と品質チェックモジュールの統合
- strategy / execution / monitoring の具現化と end-to-end テスト
- 詳細なログ、メトリクス、モニタリング用フックの追加
- 単体テスト・統合テスト・CI/CD パイプラインの整備

--------------------------------------------------------------------------------
参考: 本 CHANGELOG はコードベースから推測して作成しています。実際のリリースノートとして使用する際は、コミット履歴や変更差分に基づいて適宜調整してください。