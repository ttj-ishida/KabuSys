# Changelog

すべての変更点は「Keep a Changelog」準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/

## [Unreleased]
- なし

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買システム KabuSys のコア機能群を実装しました。以下はコードベースから推測してまとめた主な追加・実装内容です。

### Added
- パッケージ基盤
  - パッケージのエントリポイントを追加: `src/kabusys/__init__.py`（バージョン: 0.1.0、公開モジュール: data, strategy, execution, monitoring）
- 設定管理（環境変数 / .env 読み込み）
  - `.env` / `.env.local` 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）
  - 自動読み込みの無効化機能: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
  - .env パース強化:
    - コメント行、`export KEY=val` 形式対応
    - シングル / ダブルクォート内のバックスラッシュエスケープ対応
    - クォートなしでの `#` を用いたインラインコメント処理（直前が空白またはタブの場合のみ）
  - 環境変数保護機能: OS 環境変数を protected として .env による上書きを制御
  - Settings クラスを実装し、各種必須設定をプロパティ経由で取得（J-Quants, kabu API, Slack, DBパス等）
  - 入力検証: `KABUSYS_ENV`（development/paper_trading/live）と `LOG_LEVEL` の検証ロジック

- J-Quants API クライアント（データ取得）
  - `kabusys.data.jquants_client`:
    - ベース機能: 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダー取得
    - レート制御: 固定間隔スロットリングで 120 req/min を保障（RateLimiter 実装）
    - 再試行ロジック: 指数バックオフ、最大 3 回、対象ステータス（408/429/5xx）に対応
    - トークン管理: モジュールレベルの ID トークンキャッシュ、401 受信時は自動リフレッシュして 1 回リトライ
    - ページネーション対応（pagination_key を使った連続取得）
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）:
      - 冪等性を考慮した INSERT ... ON CONFLICT DO UPDATE を利用
      - PK 欠損行のスキップとログ出力
    - ユーティリティ: 型変換ヘルパー `_to_float`, `_to_int`（不正値は None にフォールバック）

- ニュース収集（RSS）
  - `kabusys.data.news_collector`:
    - RSS フィードから記事収集（デフォルトソース: Yahoo Finance ビジネス RSS）
    - セキュリティ対策:
      - defusedxml による XML パース（XML Bomb 等の防御）
      - SSRF 対策: リダイレクト先のスキームとホスト検証、プライベートIPチェック（DNS 解決を含む）
      - URL スキーム検証（http/https のみ許可）
      - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後のサイズ検査（Gzip bomb 対策）
    - URL 正規化とトラッキングパラメータ削除（utm_* 等）
    - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証
    - テキスト前処理（URL除去・空白正規化）
    - DuckDB への保存関数:
      - save_raw_news: チャンク単位の INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された記事IDを返す。トランザクションでまとめて実行。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンク挿入で保存、INSERT ... RETURNING を利用して挿入数を正確に返す
    - 銘柄コード抽出: 4桁数字（例: "7203"）を正規表現で抽出し、known_codes に基づきフィルタ（重複除去）
    - run_news_collection: 複数RSSソースの統合収集ジョブ。ソース単位でエラーハンドリングを行い、1 ソース失敗でも他ソースは継続

- DuckDB スキーマ
  - `kabusys.data.schema`:
    - Raw / Processed / Feature / Execution 層を想定したテーブル群を定義
    - 各テーブルのDDL（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）
    - 各種制約（NOT NULL, CHECK, PRIMARY KEY, FOREIGN KEY）を設定
    - 頻出クエリ向けインデックス群を定義
    - init_schema(db_path): 親ディレクトリ自動作成、DDL・インデックスを実行して DB を初期化（冪等）
    - get_connection(db_path): 既存 DB への接続取得（初期化は行わない）

- ETL パイプライン
  - `kabusys.data.pipeline`:
    - ETL の設計方針に基づく差分更新パターン実装（最終取得日を参照して差分のみ取得）
    - 定数: 最小データ日付、カレンダー先読み日数、デフォルトバックフィル日数など
    - ETLResult データクラス:
      - ETL 実行結果（取得数・保存数・品質問題・エラー一覧）を表現
      - 品質チェック結果のシリアライズ（check_name, severity, message）
    - DB ヘルパー:
      - テーブル存在チェック、最大日付取得ユーティリティ
      - 市場カレンダーを用いた営業日調整ヘルパー（_adjust_to_trading_day）
      - raw_prices / raw_financials / market_calendar の最終取得日取得関数
    - run_prices_etl 実装（差分計算、backfill の適用、jquants_client.fetch_daily_quotes → save_daily_quotes の呼び出しまで）
      - backfill_days により API の後出し修正を吸収する方針を実装

### Changed
- ドキュメンテーション的な注釈をソースに多数追加（設計原則、セキュリティ考慮、冪等性の説明、トランザクション方針など）

### Fixed
- 初回リリースのため既知の修正履歴はなし（ただし下記「既知の問題」を参照）

### Security
- ニュース収集処理における SSRF 対策、XML パーサに defusedxml を採用、受信サイズ上限・gzip 解凍後の検査を実装
- .env パーサのクォート・エスケープ処理やコメント扱いは安全性・互換性を強化

### Known issues / Notes
- run_prices_etl の戻り値
  - 実装の末尾が切れている（ソースでは `return len(records),` のように見え、ドキュメント通りの (fetched, saved) タプルが返らない可能性があります。呼び出し側と一貫した戻り値に修正が必要です。
- pipeline モジュールでは品質チェック（quality モジュール）を参照しているが、quality モジュールの実体はこのスナップショットでは確認できません。ETL と品質検査の統合は追加実装・テストが必要です。
- 一部 API のタイムアウトや例外ハンドリングの動作は本番環境での検証を推奨します（例: ネットワーク異常や大規模バックフィル時の挙動）。

---

貢献・バグ報告・改善提案は README や issue トラッカーで受け付けてください。