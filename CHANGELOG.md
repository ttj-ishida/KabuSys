# Changelog

すべての重要な変更はこのファイルに記録します。本ドキュメントは「Keep a Changelog」の形式に準拠します。

フォーマット: 年-月-日（リリース日）

## [Unreleased]

（現時点のコードベースは初回リリースとして 0.1.0 を記録しています。今後の変更はここに追記します。）

## [0.1.0] - 2026-03-18

初回リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化（バージョン 0.1.0、公開 API: data, strategy, execution, monitoring）。
- 環境設定 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを追加。
    - 読み込み優先度: OS 環境変数 > .env.local > .env
    - プロジェクトルートの自動検出 (.git または pyproject.toml を探索) により CWD に依存しない動作。
    - 自動ロード無効化用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1（テスト等で利用可能）。
  - .env 行パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い）。
  - Settings クラスを追加し、J-Quants / kabu ステーション / Slack / DB パス / システム設定（KABUSYS_ENV, LOG_LEVEL）の取得とバリデーションを提供。
    - KABUSYS_ENV は "development" / "paper_trading" / "live" のみ許可。
    - LOG_LEVEL は標準ログレベル文字列のみ許可。
- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API 用クライアントを実装（株価日足、財務データ、マーケットカレンダーの取得）。
  - レートリミッタを実装（120 req/min 固定間隔スロットリング）。
  - 再試行（リトライ）ロジックを実装（指数バックオフ、最大 3 回、408/429/5xx を対象）。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）を実装し、ページネーション間で ID トークンをキャッシュ。
  - データ取得日時（fetched_at）を UTC 形式で記録し、Look-ahead Bias の追跡を容易にする設計。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。冪等性を保つため ON CONFLICT DO UPDATE を利用。
  - 型変換ユーティリティ (_to_float, _to_int) を実装（不正値は None を返す、"1.0" のような文字列を安全に整数化するロジックなど）。
- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからニュース記事を収集し DuckDB の raw_news / news_symbols に保存する一連の処理を実装。
  - セキュリティおよび堅牢性対策を多数実装:
    - defusedxml による XML パース（XML Bomb 等の防御）。
    - SSRF 対策: リダイレクト先のスキーム/ホストの検証、プライベート IP 判定（IP 直解析および DNS 解決による A/AAAA 検査）。
    - URL スキームは http/https のみ許可。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）をチェック、gzip 解凍後も上限を確認（Gzip bomb 対策）。
    - User-Agent と圧縮エンコーディング対応。
  - 記事 ID の生成: URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）後に SHA-256 の先頭32文字を使用し冪等性を確保。
  - テキスト前処理 (URL 除去・空白正規化) を提供。
  - DuckDB への保存はトランザクションでまとめて行い、INSERT ... RETURNING を用いて実際に挿入された記事IDや紐付け件数を正確に返す実装（チャンク単位挿入で SQL 長・パラメータ数を抑制）。
  - 銘柄コード抽出機能を実装（4桁数字パターン、known_codes によるフィルタリング、重複除去）。
  - デフォルト RSS ソースに Yahoo Finance のカテゴリフィードを追加。
- DuckDB スキーマ (src/kabusys/data/schema.py)
  - DataPlatform の設計に基づくスキーマ初期化機能を追加。
  - Raw / Processed / Feature / Execution 各レイヤーのテーブル定義を追加（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - データ整合性のための CHECK 制約、PRIMARY KEY、外部キー、各種インデックスを定義。
  - init_schema(db_path) を提供し、DB ファイル親ディレクトリの自動作成とテーブル/インデックスの一括初期化を行う。get_connection() で既存 DB へ接続可能。
- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETLResult データクラスを追加（実行結果・品質問題・エラーメッセージを格納、辞書化メソッドを提供）。
  - 差分更新ヘルパー（テーブル存在チェック、最大日付取得、最終取得日に基づく差分計算）を実装。
  - 市場カレンダーを考慮した営業日調整ヘルパーを実装。
  - run_prices_etl を実装（差分取得ロジック、backfill_days による再取得、jquants_client 経由の取得と保存、ログ出力）。
  - ETL の設計方針を文書化（差分更新、backfill による後出し修正吸収、品質チェックは非フェイルファーストで収集を継続）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- news_collector において SSRF・XML インジェクション・ZIP/Gzip bomb 等を考慮した防御策を実装。
- HTTP リダイレクト時にスキーム/ホストの検査を行うカスタムリダイレクトハンドラを追加。

### 既知の制限 / 注意点 (Known limitations / Notes)
- jquants_client の HTTP 実装は urllib を使った同期的な実装。高スループット用途では別途設計（非同期化や並列制御）が必要となる可能性がある。
- ETL パイプラインは品質チェックモジュール（quality）との連携を想定しているが、品質チェックの具体的実装は別モジュールに委譲されている。
- 一部のモジュール（strategy, execution, monitoring）はパッケージに含まれるが、初期リリース時点で実装が限定的／空の __init__.py にとどまる可能性があるため、上位ロジックは今後追加予定。

---

発行者: KabuSys 開発チーム
問い合わせ: リポジトリ内 README / issue tracker を参照してください。