# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の慣例に従って記載します。  
バージョンはセマンティックバージョニングに基づいています。

なお、本ファイルはコードベースの内容から推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-17
初回公開リリース。主な追加点は以下の通りです。

Added
- パッケージの基本構成を追加
  - kabusys パッケージのエントリポイントとバージョン管理（src/kabusys/__init__.py）。
- 環境設定管理（src/kabusys/config.py）
  - プロジェクトルートを .git または pyproject.toml を基に検出する自動検出機能を実装。
  - .env / .env.local の自動読み込み機構を実装（OS環境変数優先、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env ファイルのパースは export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント処理などに対応。
  - 環境変数必須チェック用の _require と Settings クラスを提供（J-Quants トークン、kabuAPI パスワード、Slack トークン・チャンネル、DB パス等）。
  - KABUSYS_ENV と LOG_LEVEL のバリデーションと便利な is_live / is_paper / is_dev プロパティを追加。
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（RateLimiter）。
  - リトライロジック（指数バックオフ、最大 3 回、対象: 408/429/5xx）。429 の場合は Retry-After ヘッダを優先。
  - 401 受信時は ID トークンを自動リフレッシュして 1 回だけ再試行（無限再帰保護）。
  - ID トークンのモジュールレベルキャッシュを実装し、ページネーション間で共有。
  - データ保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）は fetched_at を UTC で記録し、DuckDB へ冪等な INSERT ... ON CONFLICT DO UPDATE を行う。
  - 値変換ユーティリティ（_to_float / _to_int）を実装し、不正値に対する堅牢性を強化。
- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集し raw_news に保存する機能を追加。既定の RSS ソース（Yahoo Finance のカテゴリフィード）を含む。
  - セキュリティ対策：
    - defusedxml を使用して XML Bomb 等を防止。
    - HTTP/HTTPS スキーム以外を拒否する検証（SSRF 対策）。
    - リダイレクト時もスキーム/ホストを検証するカスタムリダイレクトハンドラを実装（_SSRFBlockRedirectHandler）。
    - ホストがプライベート/ループバック/リンクローカルでないかをチェック（DNS 解決／IP 判定）。
    - レスポンスサイズに上限（MAX_RESPONSE_BYTES=10MB）を設け、gzip 解凍後も検査。
    - URL 正規化でトラッキングパラメータ（utm_ 等）を削除し、記事 ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保。
  - XML パースエラーやサイズ超過等は警告ログを出して該当ソースのみスキップする堅牢な設計。
  - DB 保存はバルク挿入とトランザクションを使用。INSERT ... RETURNING により実際に挿入された記事IDを返す。
  - 銘柄コード抽出機能（4桁数値）と news_symbols への一括紐付け機能を実装（重複除去、チャンク分割）。
  - テスト向けに _urlopen を差し替え可能に設計。
- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の多層スキーマを定義（raw_prices, raw_financials, raw_news, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など）。
  - カラム制約（NOT NULL / CHECK / PRIMARY KEY / FOREIGN KEY）を明示。
  - よく使うクエリに対するインデックス群を追加。
  - init_schema(db_path) による自動ディレクトリ作成と DDL 適用、get_connection(db_path) を提供。
- ETL パイプライン骨子（src/kabusys/data/pipeline.py）
  - 差分更新に基づく ETL 処理の設計（最終取得日を基に未取得分のみ取得、backfill により後出し修正を吸収）。
  - 市場カレンダーの先読み（_CALENDAR_LOOKAHEAD_DAYS = 90）、バックフィルデフォルト（_DEFAULT_BACKFILL_DAYS = 3）を定義。
  - ETLResult データクラスを導入し、取得数・保存数・品質問題・エラーをまとめて返却できるように実装。
  - テーブル存在チェック・最大日付取得・非営業日の調整（_adjust_to_trading_day）などのユーティリティを提供。
  - run_prices_etl の差分ロジックを実装（date_from の計算、fetch -> save の流れ）。品質チェックフック（quality モジュール）との連携を想定。
- パッケージモジュール構成（空の __init__ ファイルでサブパッケージ準備）
  - src/kabusys/data/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/execution/__init__.py（将来的な拡張用に保持）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- ニュース収集に関して SSRF と XML 攻撃、巨大レスポンス（DoS）対策を導入（前述の通り）。

Notes / Implementation details（重要な設計決定）
- J-Quants クライアントはレートリミットとリトライを組み合わせ、かつ 401 時は自動でトークンをリフレッシュして再試行するため、長時間のページネーション取得時でも安定して動作する設計になっています。
- DuckDB への保存は可能な限り冪等（ON CONFLICT）にしてあり、再実行に耐える ETL を目指しています。
- 環境変数の自動ロードはデフォルトで有効ですが、テストや特殊環境向けに KABUSYS_DISABLE_AUTO_ENV_LOAD を使って抑止できます。
- RSS フィードは不完全・非標準なフィードにも寛容にフォールバックする設計（<channel> がない場合など）。

既知の制限・今後の予定（推奨追加機能）
- quality モジュール（品質チェック）の具体的な実装やルールは別モジュールとして実装する必要がある（pipeline は quality.QualityIssue 型に依存）。
- strategy / execution パッケージは骨組みのみで、実際の売買戦略や発注ロジックは今後実装予定。
- 単体テストおよび統合テスト（ネットワーク依存部分のモック化を含む）の追加を推奨。

---

（この CHANGELOG はコードベースの読み取りから推測して作成しています。実際のリリースノートに組み込む際は、コミット履歴やリリース日・著者情報を合わせて更新してください。）