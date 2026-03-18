# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
このプロジェクトの初期リリースを記録しています。

全般方針:
- バージョニングは Semantic Versioning を想定。
- 日付は本 CHANGELOG の作成日（2026-03-18）を使用しています。

## [0.1.0] - 2026-03-18

初回リリース — 基本的なデータ収集・スキーマ・設定基盤を実装。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期構成を追加。パッケージバージョンは 0.1.0。
  - モジュール公開: data, strategy, execution, monitoring（strategy と execution のパッケージはスキャフォールドを含む）。

- 設定管理
  - 環境変数・設定管理モジュールを実装（kabusys.config.Settings）。
  - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings にて主要設定項目をプロパティで提供（J-Quants トークン、kabu API、Slack、DB パス、環境フラグ、ログレベル等）。
  - 環境変数の必須チェック (_require) を追加し、未設定時は明確な例外を送出。

- J-Quants API クライアント
  - jquants_client モジュールを追加。
  - 取得対象: 日次株価（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー。
  - レート制御: 固定間隔スロットリングで 120 req/min を順守する RateLimiter を実装。
  - 再試行ロジック: 指数バックオフ（最大試行回数 3 回）、HTTP 408/429/5xx をリトライ対象。
  - 401 Unauthorized を検出した場合の自動トークンリフレッシュ（1 回のみ）を実装。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB へ冪等に保存する save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装（ON CONFLICT DO UPDATE）。
  - トークンのモジュールレベルキャッシュと注入可能なパラメータでテスト容易性を考慮。

- ニュース収集
  - news_collector モジュールを追加。
  - RSS フィードから記事を取得し、前処理（URL 除去・空白正規化）→ raw_news テーブルへ冪等保存するフローを実装。
  - 記事 ID を URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を担保。
  - defusedxml を用いた XML パース（XML Bomb 対策）を導入。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）
    - リダイレクト先のスキーム/ホスト検証（カスタム HTTPRedirectHandler）
    - ホストがプライベート/ループバック/リンクローカルか判定し拒否
  - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）を設け、読み込み超過時はスキップ（Gzip 解凍後も検証）。
  - DB への一括挿入はチャンク分割とトランザクションで行い、INSERT ... RETURNING を利用して実際に挿入された件数を返す。
  - 銘柄コード抽出ユーティリティ（4桁数字の検出、既知コードフィルタリング）。
  - run_news_collection により複数ソースの収集〜保存〜銘柄紐付けを実行可能。

- DuckDB スキーマと初期化
  - data.schema モジュールで DuckDB のスキーマ定義を実装。
  - Raw / Processed / Feature / Execution 層に対応する多数のテーブル DDL を追加（raw_prices, raw_financials, raw_news, market_calendar, prices_daily, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など）。
  - 各種制約（PRIMARY KEY / CHECK / FOREIGN KEY）を定義。
  - パフォーマンス向けインデックス定義を用意（頻出クエリパターンに対する索引）。
  - init_schema(db_path) によりディレクトリ自動作成 → テーブル/インデックス作成（冪等）。
  - get_connection(db_path) を提供。

- ETL パイプライン
  - data.pipeline モジュールを追加。
  - ETLResult データクラス（実行結果、品質問題、エラー一覧など）を実装。
  - 差分更新ヘルパー（最終取得日の取得 get_last_price_date / get_last_financial_date / get_last_calendar_date）を提供。
  - 市場カレンダーに基づく営業日調整ヘルパー (_adjust_to_trading_day) を実装。
  - run_prices_etl を実装（差分取得、backfill_days による後方再取得、jquants_client を使った fetch & save、ログ出力）。デフォルトの backfill は 3 日。

### 改善 (Changed)
- ログと例外の扱いを明確化
  - API/ネットワークエラー、XML パースエラー、トランザクション失敗時などでのログ出力を充実させ、失敗時の挙動を明確化（例: ソース単位での例外捕捉により他ソースへ影響を与えない）。

### セキュリティ (Security)
- 外部入力（RSS URL）に対する検証強化（スキーム、ホストの事前検証、リダイレクト検査）を実装し SSRF リスクを低減。
- defusedxml を採用して XML による攻撃（XML Bomb 等）から保護。
- レスポンス受信サイズ制限と Gzip 解凍後の再検査によるメモリ DoS 対策。

### 内部 (Internal)
- コードの設計方針とコメントを充実させ、将来の拡張（rate limit 適応、品質チェック、戦略/実行モジュールの実装）を容易化。
- 単体テストが容易になるよう、HTTP open 関数（news_collector._urlopen）や jquants の id_token 注入ポイントなどでモック差替えを想定した設計を採用。

### 既知の制限 / TODO
- strategy / execution パッケージはスキャフォールド（__init__.py のみ）。実際の戦略ロジック・注文実行ロジックは未実装。
- pipeline モジュールは品質チェック（quality モジュール）への依存を持つが、その実装は本リリースに含まれていない（quality モジュールは別途実装が必要）。
- run_news_collection / run_prices_etl 等はエラーを記録して処理を継続する方針だが、運用上のアラートや自動復旧ポリシーは今後の課題。
- DB スキーマは現時点で設計に基づくが、運用に伴いインデックスやカラムの調整が必要になる可能性がある。

---

今後の予定（例）
- execution（kabu ステーション）との統合、注文送信と約定取り込みの実装。
- strategy 層でのシグナル生成・ポートフォリオ最適化ロジックの追加。
- 品質チェック（quality モジュール）と監査ログの強化。
- 単体テスト / 統合テストの追加と CI パイプライン整備。