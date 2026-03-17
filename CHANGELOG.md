# CHANGELOG

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

--  
# Unreleased
（なし）

# 0.1.0 - 2026-03-17
初回リリース

## 追加 (Added)
- パッケージ基本情報
  - パッケージ名: KabuSys（src/kabusys/__init__.py）
  - バージョン: 0.1.0

- 環境設定/読み込み機能（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を基準に探索（CWD に依存しない）。
  - .env パースロジックを実装（コメント、export プレフィックス、クォート・エスケープ処理に対応）。
  - 読み込み優先順位: OS環境 > .env.local > .env。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、アプリケーションで使う各種設定（J-Quants トークン、kabu API、Slack トークン・チャンネル、DB パス、環境・ログレベル判定など）をプロパティとして取得可能。
  - 環境値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL）を実装。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダー取得 API を実装。
  - 固定間隔レートリミッター（120 req/min）を導入。
  - 再試行（指数バックオフ）ロジックを実装（最大試行回数、408/429/5xx 等で再試行、429 の Retry-After 尊重）。
  - 401 受信時にリフレッシュトークンから id_token を自動リフレッシュして 1 回リトライ。
  - ページネーション対応（pagination_key を用いた継続取得）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE により冪等性を担保。
  - 取得時刻（fetched_at）を UTC ISO 形式で記録し、Look-ahead バイアスの追跡を可能に。
  - 入力値変換ユーティリティ（_to_float, _to_int）を実装し、不正値に対する安全な変換を行う。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事収集・前処理・保存ワークフローを実装。
  - デフォルト RSS ソースを定義（Yahoo Finance カテゴリ系）。
  - XML パースに defusedxml を利用して XML Bomb 等の対策を実装。
  - SSRF 対策: URL スキーム検証（http/https 限定）、ホストがプライベート/ループバック/リンクローカルか検査、リダイレクト時に事前検査を行うカスタム RedirectHandler を導入。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を導入し、読み込み時・gzip 解凍後のサイズチェックを実施。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）と、正規化 URL からの記事 ID 生成（SHA-256 の先頭32文字）で冪等性を保証。
  - テキスト前処理（URL 除去、空白正規化）を実装。
  - 銘柄コード抽出（4桁数字、known_codes によるフィルタ）を実装。
  - DuckDB への保存はトランザクションでまとめ、チャンク分割して INSERT ... RETURNING を使い実際に挿入された件数を正確に取得（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
  - run_news_collection により複数ソースの独立処理と記事->銘柄紐付けを実装。

- スキーマ初期化（src/kabusys/data/schema.py）
  - DuckDB 用のスキーマ定義を一括で定義（Raw / Processed / Feature / Execution 層のテーブル）。
  - 各種制約（PRIMARY KEY / CHECK / FOREIGN KEY）と索引（よく使うクエリに合わせたインデックス）を定義。
  - init_schema(db_path) によりディレクトリ自動作成および DDL/インデックスの適用（冪等）を行い、接続を返す。
  - get_connection(db_path) を提供（既存 DB へ接続、初期化は行わない）。

- ETL パイプライン基盤（src/kabusys/data/pipeline.py）
  - 差分更新の考え方に基づく ETL 補助関数群を実装（最終取得日の取得、営業日調整、差分 ETL 実行のひな形）。
  - ETL 実行結果を表す ETLResult データクラスを追加（品質問題の集約、エラー判定用プロパティ、辞書化メソッド）。
  - run_prices_etl の骨子を実装（差分 date_from の自動算出、backfill_days の扱い、jquants_client を使った取得と保存の呼び出し）。  

- パッケージ構造
  - data, strategy, execution, monitoring（strategy/execution は空の __init__ が追加されパッケージ化）

## 変更 (Changed)
- 初回リリースのため該当なし。

## 修正 (Fixed)
- 初回リリースのため該当なし。

## セキュリティ (Security)
- defusedxml の採用と RSS レスポンスサイズ制限、gzip 解凍後のサイズチェックにより、XML Bomb / メモリ DoS を緩和。
- SSRF 対策（スキーム検証、プライベートアドレス検出、リダイレクト時の事前検査）を実装。
- 外部 URL を扱う際は HTTP(S) のみ許可し、mailto: 等の危険スキームを拒否。

## 既知の注意点 / 備考 (Notes)
- Settings に必須とされる環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）が未設定の場合は ValueError を送出する。
- .env 自動ロードはプロジェクトルートが特定できない場合はスキップされる（テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- jquants_client のレート制御は単純な固定間隔（スロットリング）方式。大規模並列処理時は注意が必要。
- DuckDB の INSERT 文はプレースホルダ生成により大量のパラメータを扱うため、news_collector はチャンクサイズで分割している。
- run_prices_etl は差分ロードの骨組みのみが実装されており、完全な ETL ワークフロー（品質チェックモジュール quality の利用や他ジョブとの統合）は今後整備予定。

--  
今後は機能拡張（完全な ETL ワークフロー、戦略層の実装、発注/約定の execution 層実装、監視/通知の充実）やユニットテスト・統合テストの追加を計画しています。