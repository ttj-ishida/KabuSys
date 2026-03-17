CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
タグ付けはセマンティックバージョニングを想定しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（なし）

0.1.0 - 2026-03-17
------------------

Added
- 初期リリース。KabuSys 日本株自動売買システムのコア実装を追加。
  - パッケージエントリポイント
    - kabusys.__version__ = "0.1.0" を設定し、主要サブパッケージ（data, strategy, execution, monitoring）を公開。
  - 設定管理（kabusys.config）
    - .env ファイルおよび環境変数から設定を読み込む自動ローダー実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）により CWD に依存しない読み込みを実現。
    - .env/.env.local の読み込み順と override/protected ロジックを実装（OS 環境変数保護）。
    - .env の行パーサを実装（export プレフィックス、シングル/ダブルクォート、インラインコメント等に対応）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを提供。
    - Settings クラスで必須環境変数取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）とバリデーション（KABUSYS_ENV、LOG_LEVEL）を提供。

  - J-Quants API クライアント（kabusys.data.jquants_client）
    - 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得機能を実装。
    - レート制限制御（120 req/min 固定間隔スロットリング）。
    - 再試行ロジック（指数バックオフ、最大 3 回、HTTP 状態 408/429/5xx を対象）。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュを実装。
    - ページネーション対応（pagination_key を利用して複数ページ取得）。
    - DuckDB へ冪等保存する save_* 関数（ON CONFLICT DO UPDATE）を実装。
    - レスポンス JSON デコード失敗やネットワーク例外の扱いを明確にログ出力／例外化。

  - ニュース収集モジュール（kabusys.data.news_collector）
    - RSS フィードから記事を収集して raw_news に保存する機能を実装。
    - セキュリティ対策:
      - defusedxml を使った XML パース（XML Bomb 対策）。
      - SSRF 防止: URL スキーム検証（http/https のみ許可）、プライベート/ループバック/リンクローカル/マルチキャスト等の内部アドレスへのアクセス拒否。
      - リダイレクト時にスキームとホスト検証を行うカスタムリダイレクトハンドラ実装。
      - レスポンスサイズ上限（10 MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）と記事ID生成（正規化 URL の SHA-256 先頭32文字）。
    - テキスト前処理（URL 除去、空白正規化）。
    - DuckDB への保存はトランザクションでまとめ、チャンク INSERT（INSERT ... RETURNING を利用）で新規挿入 ID を正確に返す実装。
    - 銘柄コード抽出ロジック（4桁数字パターンと既知コードセットによるフィルタリング）。
    - 集約ジョブ run_news_collection による複数ソース取得と記事→銘柄紐付けの一括保存を実装。各ソースは個別にエラーハンドリング。

  - DuckDB スキーマ定義／初期化（kabusys.data.schema）
    - Raw / Processed / Feature / Execution の多層スキーマを定義。
      - 例: raw_prices, raw_financials, raw_news, market_calendar, prices_daily, features, ai_scores, signals, signal_queue, orders, trades, positions 等。
    - 各種チェック制約（NOT NULL, CHECK 制約、外部キー）を設定。
    - パフォーマンス目的のインデックス定義（頻出クエリを想定した index 作成）。
    - init_schema(db_path) によりディレクトリ作成を含めて全 DDL を冪等に実行する初期化 API と get_connection を提供。

  - ETL パイプライン基盤（kabusys.data.pipeline）
    - 差分更新ロジック（DB の最終取得日を取得して差分のみ取得）と backfill_days を考慮した再取得方針を実装。
    - 市場カレンダーの先読み（lookahead）や最小データ開始日の定義。
    - ETL 実行結果格納用の ETLResult dataclass（品質問題・エラーの集約・ヘルパー）を実装。
    - テーブル存在チェック・最終日取得ユーティリティ。
    - 価格差分 ETL run_prices_etl の基礎実装（fetch と save の呼び出しとログ出力）。（※コード断片により一部処理が続く想定）

Changed
- N/A（初版のため変更履歴なし）

Fixed
- N/A（初版のため修正履歴なし）

Security
- ニュース収集での SSRF 対策、defusedxml による XML パース、レスポンスサイズ/圧縮解凍時の安全チェックを導入。
- .env パーサでのクォート・エスケープ処理により環境変数注入リスクの低減。

Notes / Implementation details
- DuckDB を主要なオンディスク/インメモリストアとして採用。init_schema は ":memory:" をサポート。
- J-Quants API のレート制御はモジュールレベルの単純スロットリングで実装（固定インターバル）。高精度なレート制御や分散環境では追加調整が必要。
- news_collector の URL 正規化は既知のトラッキングプレフィックスを基に削除する実装。追加プレフィックスは _TRACKING_PARAM_PREFIXES に追加可能。
- ETL の品質チェックは外部モジュール（kabusys.data.quality）を参照する前提。品質問題は収集を止めずに報告する設計。

Breaking Changes
- なし（初期リリース）

Acknowledgements / TODO（今後の改善案）
- strategy / execution / monitoring サブパッケージの具体的なアルゴリズムと API を整備する。
- テストスイート（単体テスト、統合テスト）と CI ワークフローの追加。
- J-Quants クライアントのレート制御をトークン別・スレッドセーフに拡張する（現状はモジュールローカルな単一レートリミッタ）。
- ニュース収集のソース管理（重複フェッチ回避、フィード更新間隔の最適化）や全文取得（記事本文スクレイピング）についての拡張。
- 大量データ時の DuckDB バルク書き込み最適化や、バックフィル運用の運用ガイド追加。

以上。必要であればセクションの追加（Unreleased、各マイナーバージョンなど）や英語版の整備も対応します。