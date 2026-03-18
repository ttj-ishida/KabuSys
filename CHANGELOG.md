# CHANGELOG

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog の形式に準拠します。  

[Unreleased]: #unreleased
[0.1.0]: #010---2026-03-18

## [Unreleased]

- 次回リリースに向けた小改善・追加予定事項をここに記載します。

---

## [0.1.0] - 2026-03-18

初回公開リリース。日本株自動売買システム「KabuSys」の基盤的なモジュールを追加しました。主な追加内容は以下の通りです。

### Added
- パッケージ基礎
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。
  - 公開 API としてサブパッケージ (`data`, `strategy`, `execution`, `monitoring`) をエクスポート。

- 環境設定管理（kabusys.config）
  - .env ファイルと環境変数から設定を読み込む自動ロード機能を実装（優先順位: OS 環境 > .env.local > .env）。
  - プロジェクトルート判定は __file__ から親ディレクトリを探索し `.git` または `pyproject.toml` を検出する方式を採用（配布後も動作）。
  - .env パーサを実装:
    - `export KEY=val` の形式を許容。
    - シングル/ダブルクォート内でのバックスラッシュエスケープに対応。
    - コメント（`#`）の扱いを考慮した堅牢なパースロジック。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - 必須環境変数取得のための `_require()` と、Settings クラスを提供（J-Quants トークン、kabu API、Slack、DB パス、環境種別/ログレベル検証など）。
  - 環境値の検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）を実装。

- J-Quants クライアント（kabusys.data.jquants_client）
  - J-Quants API からのデータ取得（株価日足、財務データ、マーケットカレンダー）を実装。
  - API レート制限を守る固定間隔スロットリング実装（120 req/min）。
  - リトライロジック（指数バックオフ、最大3回、408/429/5xx を再試行対象）を実装。
  - 401 受信時はリフレッシュトークン経由で id_token を自動更新して 1 回だけリトライする仕組みを実装（無限再帰防止）。
  - モジュールレベルの id_token キャッシュを実装し、ページネーション間でトークンを共有。
  - ページネーション対応（pagination_key ベースの繰り返し取得）。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。いずれも冪等性を保証（ON CONFLICT DO UPDATE）。
  - レスポンス JSON デコード失敗時や HTTP エラー時の明確なエラーメッセージ、ログ出力を充実。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュース記事を収集し raw_news / news_symbols に保存する機能を実装。
  - 主要機能:
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）。
    - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保。
    - defusedxml を用いた XML パース（XML Bomb 等への対策）。
    - SSRF 対策:
      - リダイレクト時にスキームとホストを検査するカスタムリダイレクトハンドラを実装。
      - ホストがプライベート/ループバック/リンクローカルかを検査し内部アドレスへのアクセスを拒否。
      - http/https 以外のスキームを拒否。
    - 大きなレスポンスへの保護:
      - Content-Length の事前チェックと読み取り上限（MAX_RESPONSE_BYTES = 10MB）。
      - gzip 圧縮レスポンスの解凍後もサイズ上限検査（Gzip bomb 対策）。
    - DB 保存:
      - INSERT ... RETURNING を使い、新規に挿入された記事IDのみを返す設計。
      - チャンク分割（_INSERT_CHUNK_SIZE）・1トランザクションでの処理・ロールバック対応。
    - 銘柄コード抽出機能（4桁日本株コード検出）と、news_symbols への一括保存ロジック。
  - デフォルト RSS ソースとして Yahoo Finance のカテゴリフィードを用意。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - DataSchema に基づく 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル定義を追加。
  - 各テーブルに適切な型チェック・制約（CHECK / PRIMARY KEY / FOREIGN KEY）を付与。
  - 頻出クエリ向けにインデックス定義を追加。
  - init_schema() により DB ファイルの親ディレクトリ自動作成、DDL 実行、インデックス作成を行い、初期化済みの接続を返す。
  - get_connection() で既存 DB への接続を返す（スキーマ初期化は行わない）。

- ETL パイプライン基盤（kabusys.data.pipeline）
  - 差分更新 ETL のためのユーティリティと ETLResult dataclass を実装。
  - 特徴:
    - 差分更新のための最終取得日取得ヘルパー（get_last_price_date 等）。
    - 市場カレンダーを参照して営業日に調整するヘルパー（_adjust_to_trading_day）。
    - 差分取得のデフォルト単位・backfill_days による後出し修正吸収戦略を採用。
    - ETL の品質チェックを統合するための hook（quality モジュールとの連携を想定）。
    - run_prices_etl 等、個別 ETL ジョブの雛形を実装（差分取得 → 保存 → ログ記録の流れ）。

### Fixed
- 初期リリースにつき既知のバグ修正履歴はなし。

### Security
- ニュース収集モジュールで複数のセキュリティ対策を導入:
  - defusedxml を用いた XML パースで XXE 等を防止。
  - SSRF 対策（スキーム検証、プライベートIP検査、リダイレクト時の検査）。
  - レスポンスサイズや gzip 解凍後サイズのチェックで DoS（メモリ消費）対策を実装。
- 環境変数の自動読み込みで OS 環境変数を保護するための protected 機構を導入（.env の上書き制御）。

### Performance
- J-Quants クライアントに固定間隔の RateLimiter を導入し API のレート制限遵守を容易化。
- DB へのバルク挿入はチャンク化（INSERT チャンク）してオーバーヘッドを軽減。
- raw_news / news_symbols の一括処理はトランザクションでまとめて処理しオーバーヘッド削減と整合性確保。

### Notes / Known limitations
- quality モジュールは pipeline 側から参照される設計になっているが、本リリースでの詳細な品質チェックルールは別途実装を想定。
- run_prices_etl など ETL ジョブの一部は今後細かい品質チェック、ログ/メトリクス出力やスケジューリング連携を強化予定。
- 初期リリースのため、strategy / execution / monitoring サブパッケージ内の具体的実装は引き続き追加予定。

---

作業ログや追加要望があれば、この CHANGELOG を更新していきます。