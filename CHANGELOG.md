# Changelog

すべての変更は Keep a Changelog のフォーマットに従って記載されています。  
現在のバージョン: 0.1.0

形式: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-17
初回公開リリース。このリリースでは以下の主要機能・モジュールを実装しています（日本株自動売買システムの基盤実装）。

### 追加 (Added)
- パッケージ基盤
  - パッケージルート: kabusys (version 0.1.0)
  - サブパッケージの公開: data, strategy, execution, monitoring（各 __init__.py を含む基本構成）

- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定読み込みする自動ローダーを実装
    - プロジェクトルートは .git または pyproject.toml を基準に自動検出（CWD に依存しない）
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能
    - .env パース機能: export プレフィックス、シングル/ダブルクォート対応、インラインコメント処理などの堅牢な処理
    - .env 読み込み時の I/O エラーは警告で扱う
  - Settings クラス（プロパティベース）の実装
    - J-Quants / kabuステーション / Slack / DB パス等の必須・デフォルト値を明示
    - KABUSYS_ENV の検証（development, paper_trading, live）
    - LOG_LEVEL の検証（DEBUG, INFO, ...）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - ベース機能
    - API ベース URL 定義、タイムアウト/レート制御等の定数設定
  - レート制限
    - 固定間隔スロットリングによるレート制御（120 req/min 想定）
  - 再試行・認証
    - 指数バックオフ付きリトライ（最大 3 回）、408/429/5xx を対象
    - 401 受信時はリフレッシュトークンで自動取得して 1 回だけ再試行
    - id_token のモジュールレベルキャッシュを提供（ページネーション間で共有）
  - データ取得
    - fetch_daily_quotes（日足、ページネーション対応）
    - fetch_financial_statements（四半期財務、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存（冪等）
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - INSERT ... ON CONFLICT DO UPDATE による上書きで冪等性を確保
  - 変換ユーティリティ
    - _to_float / _to_int：堅牢な型変換ルール（空値や不正値は None）

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS 取得と前処理の実装
    - RSS フィード取得 (fetch_rss)：名前空間や非標準レイアウトへのフォールバック
    - defusedxml を用いた安全な XML パース
    - Content-Length/受信バイト上限チェック（MAX_RESPONSE_BYTES = 10 MB）
    - gzip 解凍時のサイズ検査（Gzip bomb 対策）
    - リダイレクト時の事前検証用ハンドラ (_SSRFBlockRedirectHandler) を実装（スキーム・プライベートIPの検査）
    - URL スキーム検証（http/https のみ許可）とホストのプライベートアドレスチェック
    - レスポンス上限超過時はスキップして安全性を確保
  - テキスト前処理
    - preprocess_text: URL 除去、空白正規化
  - URL 正規化・記事ID生成
    - トラッキングパラメータ除去（utm_*, fbclid 等）、クエリソート、フラグメント削除
    - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成（重複排除）
  - DB 保存（DuckDB）
    - save_raw_news: チャンク化バルク INSERT、トランザクション、INSERT ... RETURNING により実際に挿入された ID を返す
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付けを一括保存（ON CONFLICT DO NOTHING）
  - 銘柄抽出
    - extract_stock_codes: 正規表現で 4 桁コードを抽出し、known_codes に基づいて有効性を保証
  - 統合ジョブ
    - run_news_collection: 複数 RSS ソースを巡回し、個別ソースの失敗に耐性を持たせて収集・保存・銘柄紐付けを実施

- DuckDB スキーマ管理 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく多層スキーマ（Raw / Processed / Feature / Execution）を定義
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw テーブル
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols などの Processed テーブル
  - features, ai_scores などの Feature テーブル
  - signals, signal_queue, orders, trades, positions, portfolio_performance などの Execution 関連テーブル
  - 頻出クエリ向けのインデックス定義
  - init_schema(db_path): 親ディレクトリ自動作成を含むスキーマ初期化関数（冪等）
  - get_connection(db_path): 既存 DB への接続取得

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETLResult dataclass による結果集約（品質問題・エラー一覧を保持）
  - テーブル存在チェックや最大日付取得のユーティリティ
  - 市場カレンダーによる営業日調整ヘルパー (_adjust_to_trading_day)
  - 差分更新ロジックの考慮点（最終取得日の backfill 日数による再取得）
  - run_prices_etl の実装（差分取得→保存の流れ、バックフィル日数指定、J-Quants 呼び出し）
  - 定数: 最小データ日 (2017-01-01), カレンダー先読み日数, デフォルトバックフィル日数 など
  - 品質チェックモジュール (quality) を想定した設計（実行中の重大度集約）

### セキュリティ (Security)
- XML パースに defusedxml を採用し XML Bomb 等の攻撃を緩和
- RSS フィードでの SSRF 対策
  - URL スキーム検証（http/https のみ）
  - ホストがプライベート/ループバック/リンクローカル/マルチキャストの場合は拒否
  - リダイレクトハンドラでの事前検証
- レスポンス受信サイズ上限（MAX_RESPONSE_BYTES）と gzip 解凍後の検査によりメモリ DoS を軽減
- .env 読み込み時に OS 環境変数を保護するための protected セットを実装（上書き制御）

### 変更点の注記 (Notes)
- ロギングを各モジュールに導入し、情報/警告/例外のトレースを整備
- テストしやすさを意識
  - news_collector の _urlopen はモック差し替え可能
  - jquants_client は id_token を注入可能（テスト用）
- DuckDB を中心にトランザクション管理やバルク挿入を最適化（チャンクサイズ等を調整）

### 既知の制限 / 今後の課題 (Known issues / TODO)
- pipeline モジュールは run_prices_etl 等の一部ジョブを実装済みだが、完結した ETL ワークフロー（品質チェックの適用や calendar/financials の ETL ジョブの統合）については追加実装が想定される
- quality モジュールの実装本体は本コードベースに含まれていない（参照はあるが別実装を前提）
- strategy / execution / monitoring の具象実装は今回の初期実装では最小限の入口のみ（将来的に戦略実装・注文実行ロジック・監視アラートを実装予定）
- エラーハンドリングのポリシーは設計段階で決められているが、運用でのエッジケース検証が必要
- 日時・タイムゾーンの扱いは注意が必要（RSS の pubDate を UTC naive に変換して扱う設計）

---

今後のリリースでは以下を想定しています:
- 完全な ETL ワークフロー（品質チェック・再試行方針の強化）
- strategy / execution の具体的実装（注文送信・約定処理・ポジション管理）
- モニタリング/アラート（Slack 連携等）の統合
- テストカバレッジ拡充と CI 設定

（この CHANGELOG はソースコードの内容から推測して作成しています。実際のコミット履歴やリリースノートとは差異があり得ます。）