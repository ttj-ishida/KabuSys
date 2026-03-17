# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

※ この CHANGELOG は与えられたコードベースから実装内容を推測して作成したもので、実際のコミット履歴とは異なる場合があります。

## [0.1.0] - 2026-03-17
初回リリース（推測）。日本株自動売買システム「KabuSys」の主要コンポーネントを実装。

### 追加 (Added)
- 基本パッケージ構成
  - パッケージエントリポイント: `src/kabusys/__init__.py`（バージョン = 0.1.0、公開モジュール一覧）
- 環境設定読み込み・管理 (`kabusys.config`)
  - .env ファイルと環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - .env.local を優先して読み込む挙動（OS環境変数を保護する保護機構付き）。
  - .env ファイルパースの堅牢化:
    - export キーワード対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメント処理（クォートあり/なしでの挙動差分）
  - 必須環境変数取得用の _require と Settings クラスを提供（J-Quants、kabuステーション、Slack、DB パス、環境・ログレベル等のプロパティ）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーを取得する fetch_* 関数群を実装（ページネーション対応）。
  - 認証: refresh_token から id_token を取得する get_id_token を実装。モジュールレベルで id_token をキャッシュ。
  - HTTP リクエストユーティリティ:
    - レート制限制御（固定間隔スロットリング、120 req/min を想定）
    - リトライロジック（指数バックオフ、最大3回、対象ステータス/ネットワークエラー）
    - 401 受信時は自動で id_token を再取得して一度だけリトライ（無限再帰防止）
    - JSON デコード失敗時の明示的なエラー
  - DuckDB への永続化ユーティリティ:
    - save_daily_quotes, save_financial_statements, save_market_calendar を実装
    - 全て冪等（ON CONFLICT DO UPDATE / DO NOTHING）で保存
    - fetched_at を UTC で付与し Look-ahead Bias のトレースを可能に

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードから記事を収集して raw_news に保存する機能を実装（DataPlatform.md に基づく設計）。
  - セキュリティ・堅牢性対策:
    - defusedxml による XML パース（XML Bomb 等の防止）
    - SSRF 対策: URL スキーム検証（http/https のみ）、リダイレクト先のスキーム/ホスト検査、プライベート IP/ループバック/リンクローカル判定
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリDoS対策、gzip 解凍後もサイズチェック
    - HTTP リダイレクト時に事前検証するカスタムハンドラを用意
  - URL 正規化と記事 ID 生成:
    - トラッキングパラメータ（utm_*, fbclid 等）を削除して正規化
    - SHA-256 の先頭32文字を記事IDに使用（冪等性）
  - テキスト前処理（URL除去、空白正規化）
  - 銘柄コード抽出ユーティリティ（4桁数字のパターン照合と known_codes によるフィルタ）
  - DB 保存機能:
    - save_raw_news: チャンク単位でバルクINSERT、トランザクションで一括コミット、INSERT ... RETURNING により実際に挿入されたIDを返却
    - save_news_symbols / _save_news_symbols_bulk: ニュースと銘柄の紐付けをバルクで保存（ON CONFLICT で重複スキップ）し、挿入件数を正確に返す

- DuckDB スキーマ (`kabusys.data.schema`)
  - Raw / Processed / Feature / Execution 層のテーブル定義を実装（DataSchema.md に準拠する想定）
  - 各テーブルに適切な型チェック・NOT NULL 制約・PRIMARY KEY・FOREIGN KEY を設定
  - インデックス定義（頻出クエリを想定した複数の CREATE INDEX）
  - init_schema(db_path) による初期化（親ディレクトリの自動作成含む）と get_connection を提供

- ETL パイプライン (`kabusys.data.pipeline`)
  - ETL の設計方針実装:
    - 差分更新ロジック（DBの最終取得日を参照して未取得分のみ取得）
    - backfill_days による若干の遡及取得（デフォルト 3 日）
    - 市場カレンダーの先読み（look-ahead）
    - 品質チェック呼び出しポイント（quality モジュール想定）
  - ETLResult dataclass により実行結果・品質問題・エラーを集約して返却可能
  - テーブル存在チェック、最大日付取得ユーティリティを実装
  - run_prices_etl の差分 ETL 実装（fetch → save の流れを実装）

### 変更 (Changed)
- （初回リリースのため該当なし／実装段階での設計決定を反映）
  - レート制限やリトライ方針など、外部 API 仕様（J-Quants）に合わせた挙動を採用

### 修正 (Fixed)
- （初版リリースのため該当なし）

### セキュリティ (Security)
- RSS パーサに defusedxml を採用して XML に対する脆弱性緩和を実装
- SSRF 対策を複数実装:
  - リダイレクト先のスキーム/ホスト検証
  - プライベートIP/ループバック/リンクローカル/マルチキャストの拒否
  - URL スキームの事前検証（http/https のみ）
- 外部から取得するレスポンスの受信サイズ上限（10MB）によりメモリを狙った DoS を軽減

### 内部（Internal）
- 共通ユーティリティ:
  - 型変換ヘルパー (_to_float, _to_int) を jquants_client に実装（厳密な空値・変換失敗時の扱い）
  - RSS の日付パースは RFC2822 互換でパース失敗時に UTC 現在時刻で代替（raw_news.datetime は NOT NULL 要件のため）
  - DB 挿入はトランザクションでまとめ、失敗時はロールバックして例外を再送出

### 既知の問題 (Known issues)
- run_prices_etl の末尾が不完全（提供されたソースでは `return len(records), ` のように戻り値のタプルが切れている）ため、現状のコードはそのままではランタイム/構文上の問題になる可能性があります。実際のリポジトリではこの部分が完成していることを想定するか、修正（戻り値の完全なタプルを返す）を要します。
- 単体テスト・統合テストの実装はソースからは確認できません。外部 API 呼び出しやネットワークIO 部分はモック可能な設計（id_token 注入や _urlopen の差し替え）ですが、テスト用の補助ユーティリティは追加検討が必要です。
- Slack / kabuステーション 等への実際の実行・通知フローは実装ファイルは存在するものの（config に設定取得がある）、実運用のエンドツーエンド検証は未確認。

---

今後のリリースで期待する改善点（提案）
- run_prices_etl の完全実装と他 ETL ジョブ（financials / calendar / news）の統合実装・スケジューリング
- 品質チェックモジュール (kabusys.data.quality) の具体実装と、それに基づく自動アラート/ロールバック戦略
- ロギング・メトリクスの標準化（構造化ログ、Prometheus や Sentry 連携）
- テストカバレッジの向上（外部 API をモックした CI パイプライン）
- ドキュメント（DataPlatform.md / DataSchema.md の実ドキュメント化）と運用手順の整備

以上。必要であれば、各変更点をさらに細かく日付・コミット単位で分解して追記できます。