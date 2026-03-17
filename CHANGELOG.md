# CHANGELOG

すべての注目に値する変更点をこのファイルに記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。

なお、本CHANGELOGは提供されたコードベースの内容から実装済み機能を推測して作成したものであり、実際のコミット履歴に基づくものではありません。

## [Unreleased]

- なし（初期リリース相当の状態）

---

## [0.1.0] - 2026-03-17

初期リリース。日本株自動売買基盤のコア機能を実装。

### 追加 (Added)
- パッケージ構成
  - kabusys パッケージ（__version__ = 0.1.0）
  - サブモジュールの骨組み: data, strategy, execution, monitoring

- 設定・環境読み込み機能 (`kabusys.config`)
  - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を基準に探索）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能
  - .env パーサ実装（export PREFIX、引用符対応、インラインコメント処理）
  - protected（OS環境変数）を尊重する上書きロジック
  - Settings クラスでアプリ設定をプロパティとして公開（J-Quants トークン、kabu API、Slack、DBパス、環境モード、ログレベル判定等）
  - env / log_level のバリデーション（有効値チェック）および is_live / is_paper / is_dev 判定ユーティリティ

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - ベースHTTPユーティリティ（urllib ベース）
  - レートリミッタ実装（固定間隔スロットリング、120 req/min）
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx の再試行）
  - 401 受信時の自動トークンリフレッシュ（1回のみ）とモジュールレベルの id_token キャッシュ
  - API データ取得関数（ページネーション対応）
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（四半期財務データ）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への idempotent 保存関数（ON CONFLICT DO UPDATE）
    - save_daily_quotes、save_financial_statements、save_market_calendar
  - データ変換ユーティリティ (_to_float / _to_int)
  - 各取得で fetched_at を UTC ISO8601 形式で記録し、Look-ahead バイアス対策に配慮

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードからの記事取得・正規化・保存ワークフロー実装
  - URL 正規化（トラッキングパラメータ除去、キーソート、フラグメント削除）
  - 記事ID を URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を確保
  - defusedxml を用いた XML パース（XML Bomb 等への対策）
  - SSRF 対策:
    - HTTP/HTTPS スキームのみ許可
    - ホスト名/IP のプライベートアドレス（ループバック・リンクローカル等）判定と拒否
    - リダイレクト時にもスキーム/ホストを検査するカスタム RedirectHandler
  - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 展開後のサイズチェック（Gzip bomb 対策）
  - テキスト前処理（URL 除去、空白正規化）
  - DB 保存:
    - save_raw_news: チャンク／トランザクション単位で INSERT ... RETURNING により新規挿入ID一覧を取得
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（ON CONFLICT DO NOTHING、戻り値は実際に挿入された件数）
  - 銘柄コード抽出ユーティリティ（4桁数字パターン → known_codes に基づくフィルタ）
  - run_news_collection: 複数 RSS ソースを対象にした統合収集ジョブ（各ソースは独立してエラーハンドリング）

- DuckDB スキーマ定義・初期化モジュール (`kabusys.data.schema`)
  - Raw / Processed / Feature / Execution の 3 層＋実行レイヤのテーブル定義を実装
  - 各テーブルに制約（NOT NULL、PRIMARY KEY、CHECK、FOREIGN KEY 等）を設定
  - インデックス定義（頻出クエリを想定したインデックス群）
  - init_schema: DB ファイルの親ディレクトリ自動作成、DDL を実行してテーブル/インデックスを作成（冪等）
  - get_connection: 既存 DB への接続取得（初期化は行わない）

- ETL パイプライン基盤 (`kabusys.data.pipeline`)
  - ETLResult dataclass（処理結果、品質問題、エラー保持、辞書変換）
  - テーブル存在チェック、最大日付取得ユーティリティ
  - market_calendar を使った取引日補正ヘルパー（過去方向に最寄りの営業日へ調整）
  - 差分更新ヘルパー（raw_prices / raw_financials / market_calendar の最終取得日取得）
  - run_prices_etl の実装（差分取得ロジック、バックフィル日数の扱い、jquants_client を経由した取得と保存）

### 修正 (Changed)
- なし（初期リリース）

### 修正 (Fixed)
- なし（初期リリース）

### セキュリティ (Security)
- ニュース収集における SSRF 対策と XML パースの安全化（defusedxml）
- RSS レスポンスのサイズ上限と gzip 解凍後の検査によるメモリ DoS 対策
- .env 読み込みで OS 環境変数を保護する仕組み（protected set）

### 既知の制約・注意点 (Known issues / Notes)
- HTTP クライアントは urllib を使用しており、非同期処理や高並列取得は想定していない（レートリミットは固定インターバルで制御）。
- id_token キャッシュはモジュールレベルで管理しているため、プロセス単位での共有設計になっている。
- ETL パイプライン（pipeline モジュール）は差分取得ロジックや品質チェック呼び出しの基礎を実装しているが、運用上のスケジューリングや詳細な品質チェックルール（quality モジュールの実装依存）などは別実装が必要。
- news_collector の URL 正規化・トラッキング除去は既知のプレフィックスをベースにしている（カスタムパラメータは考慮外）。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの具体的実装（シグナル生成、発注ロジック、監視・アラート）
- 品質チェック（kabusys.data.quality）の実装と ETL への組み込み
- テストカバレッジ強化、外部 API 呼び出しのモック化・統合テスト
- 非同期・並列取得オプションの検討と実装

（以上）