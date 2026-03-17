# CHANGELOG

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
このプロジェクトはセマンティックバージョニングを使用します。

なお、コード内容から推測して初回リリース相当の変更点をまとめています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-17
初回公開リリース。日本株自動売買システムのコア基盤を実装しました。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ骨格を追加（src/kabusys/__init__.py）。
  - strategy、execution、monitoring のモジュール名を公開（プレースホルダ）。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - 自動ロードの優先度: OS環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - プロジェクトルート検出は __file__ を基点に .git または pyproject.toml を探索して判定。
    - .env のパースは export プレフィックス、クォート、コメント処理に対応。
    - 既存の OS 環境変数は保護できる（protected set）。
  - Settings クラスを提供し、各種必須設定をプロパティで取得可能に。
    - J-Quants/Kabu API/Slack/DBパス等の設定プロパティを実装。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証を実装。
    - is_live / is_paper / is_dev のユーティリティプロパティを追加。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しの共通処理を実装（_request）。
    - 固定間隔レートリミッタ（120 req/min）を実装。
    - 再試行ロジック（指数バックオフ、最大 3 回）、対象ステータスコードを考慮。
    - 401 受信時はリフレッシュ（1回のみ）して再試行するトークン自動更新機能。
    - JSON デコードの失敗時の明確なエラーメッセージ。
  - 認証ヘルパー get_id_token を実装（リフレッシュトークンから id_token を取得）。
  - データ取得関数を実装（ページネーション対応）
    - fetch_daily_quotes（株価日足 OHLCV）
    - fetch_financial_statements（四半期財務データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
    - 取得時の fetched_at 記録方針を考慮した設計説明を含む。
  - DuckDB への冪等保存関数を実装（ON CONFLICT DO UPDATE）
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - PK 欠損行はスキップしてログ出力、保存件数を返す。
  - 値変換ユーティリティ（_to_float, _to_int）を実装（入力の頑健性を考慮）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集し DuckDB に保存する一連の処理を実装。
    - fetch_rss: RSS 取得・XML パース・記事整形（defusedxml 使用）・記事 ID 生成。
      - 記事IDは正規化した URL の SHA-256 ハッシュ先頭 32 文字で生成し冪等性を確保。
      - URL 正規化でトラッキングパラメータ（utm_ 等）やフラグメントを削除。
      - content:encoded の優先使用、description フォールバック。
      - 公開日時パース（RFC 2822）と UTC 変換の実装。パース失敗時は代替時刻を使用。
      - gzip 圧縮対応、最大受信サイズ制限（10 MB）でメモリ DoS / Gzip bomb を防止。
      - SSRF 対策:
        - URL スキームは http/https のみ許可。
        - リダイレクト時にスキームとホスト（プライベート / ループバック / リンクローカル / マルチキャスト）検査を実施。
        - 初回 URL と最終 URL の両方を検証。
    - save_raw_news: INSERT ... RETURNING を使い、新規に挿入された記事 ID を返す実装（チャンク&トランザクション）。
    - save_news_symbols, _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（ON CONFLICT DO NOTHING、RETURNING を使用）。
    - extract_stock_codes: テキスト中から 4 桁の銘柄コードを抽出するユーティリティ（既知コードの絞り込み・重複除去）。
    - preprocess_text: URL 除去・空白正規化などの前処理ユーティリティ。
    - デフォルト RSS ソースとして Yahoo Finance のカテゴリ RSS を登録。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層を想定したテーブル群の DDL を実装。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 運用を想定した制約（CHECK、PRIMARY KEY、FOREIGN KEY）を定義。
  - 頻出クエリを想定したインデックス群を追加。
  - init_schema(db_path) による初期化ユーティリティを提供（親ディレクトリ自動作成、冪等でテーブル作成）。
  - get_connection(db_path) で既存 DB への接続を取得。

- ETL パイプライン基盤（src/kabusys/data/pipeline.py）
  - ETLResult データクラスを導入して ETL 結果・品質問題・エラーを集約。
  - 差分更新のためのヘルパー実装:
    - _table_exists / _get_max_date / get_last_price_date / get_last_financial_date / get_last_calendar_date
    - _adjust_to_trading_day: 非営業日の調整ロジック（market_calendar 参照、最大 30 日遡り）
  - run_prices_etl: 株価差分 ETL のエントリ（差分取得ロジック、backfill_days による再取得開始日算出、jquants_client を用いた取得と保存）を実装（差分 ETL の骨格）。
  - ETL 全体設計:
    - 差分更新、backfill による後出し修正吸収、品質チェック（別モジュール quality を利用）の方針をドキュメントに記載。

### セキュリティ (Security)
- defusedxml を利用した XML パースで XML Bomb を軽減。
- ニュース収集時に複数の SSRF 対策を実装:
  - URL スキーム検証（http/https のみ）。
  - リダイレクト先のスキーム・ホスト検証（プライベートアドレス拒否）。
  - レスポンスサイズチェック / gzip 解凍後のサイズ検査。
- .env 読み込みで OS 環境変数の保護（protected set）をサポート。

### 改善 / 設計上の注記 (Notes)
- J-Quants クライアントの再試行 / レート制御は単一プロセス内の固定間隔スロットリングに基づく実装。マルチプロセスや分散環境での共有レート制御は別途検討が必要。
- DuckDB 保存関数は SQL の ON CONFLICT に依存するため、スキーマ変更時は注意が必要。
- run_prices_etl は基本的な差分 ETL の流れを実装しているが、品質チェックモジュール（quality）の実装や ETL の運用通知（Slack 等）は別実装を想定。

### 既知の制限 (Known limitations)
- pipeline モジュールは ETL の骨格を提供する段階で、品質チェック（quality）の詳細実装や全データフローの単体テストは別途実装が必要。
- strategy / execution / monitoring の各モジュールは現状プレースホルダとなっており、戦略ロジック・発注実装は未実装。

---

参考: 実装ファイル
- src/kabusys/config.py
- src/kabusys/data/jquants_client.py
- src/kabusys/data/news_collector.py
- src/kabusys/data/schema.py
- src/kabusys/data/pipeline.py
- その他パッケージ初期ファイル

（この CHANGELOG は、提供されたコードベースの内容から推測して作成しています。）