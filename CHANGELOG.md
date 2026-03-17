CHANGELOG
=========

この変更履歴は「Keep a Changelog」仕様に準拠しています。  
コードベースの内容から推測して作成した初期リリースの要約です。

フォーマット
-----------
- すべて日本語で記載
- 各項目は機能追加（Added）、変更（Changed）、修正（Fixed）、セキュリティ（Security）等に分類

Unreleased
----------
- 今後の変更点や未実装機能（なし）

0.1.0 - 2026-03-17
-----------------

Added
- 基本パッケージ初期化
  - パッケージ名: kabusys、バージョン 0.1.0 を定義（src/kabusys/__init__.py）。
  - サブパッケージのエクスポート: data, strategy, execution, monitoring を公開。

- 環境設定・ロード機能（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード実装。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を基準に自動検出（CWD非依存）。
  - .env パーサ実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープに対応。
    - インラインコメントとクォートの扱いを適切に処理。
  - .env 読み込みルール:
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用途）。
    - OS 環境変数を保護する protected 設定を導入。
  - Settings クラス:
    - J-Quants / kabuステーション / Slack / DB パス等の必須/デフォルト設定をプロパティで提供。
    - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）。
    - is_live / is_paper / is_dev の利便性プロパティ。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しユーティリティ:
    - 固定間隔スロットリングによるレート制限（120 req/min）。
    - 冪等性・ページネーション対応の fetch_* API 実装:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（財務四半期データ）
      - fetch_market_calendar（JPX マーケットカレンダー）
    - HTTP リトライロジック（最大 3 回、指数バックオフ、408/429/5xx を再試行）。
    - 401 応答時にリフレッシュトークンで自動リフレッシュ＆1回リトライ（無限再帰を防止）。
    - モジュールレベルの ID トークンキャッシュを実装しページネーション間で共有。
  - DuckDB への保存関数（冪等性対応）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - 各保存は ON CONFLICT DO UPDATE を使用して重複や差分更新に対応。
    - PK 欠損レコードのスキップとログ出力。
  - 入力変換ユーティリティ:
    - _to_float / _to_int（空値・不正値の安全な変換、"1.0" のような文字列対応、切り捨て防止ロジックなど）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード収集/正規化/保存の統合実装。
  - 安全対策と堅牢性:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時にスキーム・ホストを検査するカスタムハンドラ。
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストならブロック。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
    - User-Agent、Accept-Encoding の設定。
  - 正規化・ID 生成:
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリパラメータソートなど）。
    - 記事ID は正規化URLの SHA-256 の先頭32文字で生成（冪等性確保）。
  - 前処理・抽出:
    - テキスト前処理（URL除去、空白正規化）。
    - 銘柄コード抽出（4桁数字、既知コードセットとの照合、重複除去）。
    - RSS pubDate の安全なパース（UTC で正規化、失敗時は現在時刻で代替）。
  - DB 保存（DuckDB）:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、実際に挿入された記事IDのみを返却。チャンク処理とトランザクション管理あり。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付けをバルク挿入、ON CONFLICT DO NOTHING、トランザクションで安全に実行。
  - デフォルト RSS ソースの定義（例: Yahoo Finance ビジネス RSS）。

- スキーマ定義と初期化（src/kabusys/data/schema.py）
  - DuckDB 用の包括的スキーマを定義:
    - Raw, Processed, Feature, Execution 層のテーブルを定義。
    - raw_prices, raw_financials, raw_news, raw_executions 等。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等。
    - features, ai_scores（特徴量 / AI スコア層）。
    - signals, signal_queue, orders, trades, positions, portfolio_performance（実行層）。
  - 各カラムに対する CHECK 制約を定義（値域チェック、NOT NULL、列の整合性）。
  - インデックス定義（頻出クエリのための複数インデックス）。
  - init_schema(db_path) によりファイルシステム上のディレクトリを自動作成し、テーブルとインデックスを一括作成（冪等）。
  - get_connection(db_path) で既存 DB への接続を提供（初期化は行わない）。

- ETL パイプライン基盤（src/kabusys/data/pipeline.py）
  - ETLResult データクラス: ETL 実行結果、品質問題、エラー情報を格納し、辞書化 API を提供。
  - 差分更新ヘルパー:
    - テーブル存在チェック、最大日付取得ユーティリティ。
    - 市場カレンダーに基づく営業日調整（非営業日なら直近の営業日に調整）。
  - 個別 ETL ジョブ（部分実装）:
    - run_prices_etl: 差分更新ロジック（最終取得日から backfill_days を使った再取得）、デフォルト最小データ日付の使用、fetch と save の統合。取得/保存件数を返す。
  - 設計方針:
    - 差分更新とバックフィル（デフォルト backfill_days = 3）による後出し修正吸収。
    - 品質チェックモジュール（quality）との連携を想定（品質問題は収集を継続し呼び出し元で判断）。

- テスト容易性とモック対応
  - news_collector._urlopen をテストでモック差し替え可能な設計。
  - jquants_client の id_token 注入によりテスト時に外部依存を切り離せる設計。

Security
- XML パースに defusedxml を使用し XML 関連攻撃を防御。
- RSS フェッチで SSRF を防止するためスキーム・ホストチェック、リダイレクト検証を実装。
- レスポンスサイズ制限と gzip 解凍後の再チェックでストレス攻撃を緩和。

Compatibility / Requirements (推測)
- duckdb を利用（DuckDBPyConnection が必要）。
- defusedxml を使用（XML 安全パース）。
- 標準ライブラリ urllib, json, datetime 等に依存。
- 環境変数または .env により外部 API トークン（JQUANTS_REFRESH_TOKEN 等）を設定する必要あり。

Notes / Known limitations（推測）
- strategy/execution/monitoring サブパッケージは初期状態でほとんど未実装（プレースホルダ）。
- pipeline.run_prices_etl の戻り値定義が途中で切れている（コードスニペットの末尾で続きが必要）ため、完全な ETL ワークフローは追加実装が必要。
- 品質チェック（quality モジュール）の実装はこのスナップショットに含まれていないため、品質ルールの具体的実装は別途提供が必要。
- J-Quants API の利用に伴うレート制限やエラーハンドリングは実装済みだが、実運用での詳細な検証が推奨される。

作者メモ（推測）
- 初期リリースは「データ基盤」と「ニュース収集」「J-Quants 接続」を中心に設計されており、将来的に戦略、発注・モニタリングの実装・連携を想定している。

ライセンス / 貢献
- 本 CHANGELOG はコード内容の推測に基づいて作成されています。実際のリリースノートとして利用する場合は、差分やコミット履歴に基づく追記・修正を推奨します。