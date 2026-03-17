Keep a Changelog
=================

すべての重要な変更はこのファイルに記載します。  
このプロジェクトはセマンティックバージョニングに従います。

フォーマット: https://keepachangelog.com/ja/1.0.0/ に準拠

Unreleased
----------

- なし

[0.1.0] - 2026-03-17
--------------------

初回リリース。以下の主要機能とモジュールを実装しています。

Added
-----

- パッケージ基盤
  - kabusys パッケージを追加。__version__ を "0.1.0" に設定。
  - パッケージ公開 API を __all__ で定義（data, strategy, execution, monitoring）。

- 設定 / 環境変数管理 (kabusys.config)
  - .env/.env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env パーサーを実装（export 形式やクォート、インラインコメント対応、エスケープ処理）。
  - 自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数に対応。
  - 環境変数の強制取得関数 _require と、Settings クラスを提供：
    - J-Quants / kabuステーション / Slack / DB パス / 実行環境等の設定プロパティを用意。
    - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）。
    - is_live / is_paper / is_dev ヘルパーを提供。

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアント実装：
    - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得関数を実装（ページネーション対応）。
    - API レート制限対応（固定間隔スロットリング、デフォルト 120 req/min）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。429 の場合は Retry-After ヘッダを優先。
    - 401 受信時の自動トークンリフレッシュ（1 回まで）を実装。ID トークンのモジュール内キャッシュを共有。
    - JSON デコード失敗時の明示的エラー通知。
  - DuckDB への永続化関数を実装（冪等性を重視）：
    - save_daily_quotes, save_financial_statements, save_market_calendar：ON CONFLICT DO UPDATE を利用して重複更新を回避。
    - 型変換ユーティリティ（_to_float, _to_int）を提供。空値や不正値の扱いを明確化。
  - ロギングを多用し、取得件数やスキップ件数を報告。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからの記事収集パイプラインを実装：
    - RSS 取得、XML パース（defusedxml を使用して XML 攻撃対策）、記事テキスト前処理（URL除去、空白正規化）を実装。
    - 記事 ID を URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を担保。UTM 等のトラッキングパラメータ削除・クエリソートを実施。
    - SSRF 対策を強化：URL スキーム検証（http/https のみ許可）、取得前のホストプライベート判定、リダイレクト時の検証（カスタム RedirectHandler）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後の再検査を実装（Gzip bomb 対策）。
    - raw_news テーブルへのバルク挿入（チャンク分割、INSERT ... RETURNING を利用）と news_symbols への銘柄紐付け保存機能を実装。トランザクションによるロールバック対応。
    - 銘柄コード抽出ユーティリティ（4桁数字パターン + known_codes によるフィルタリング）を実装。
    - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを追加。

- スキーマ / DB 初期化 (kabusys.data.schema)
  - DuckDB 用スキーマ定義を実装（Raw / Processed / Feature / Execution 層を含む）。
    - raw_prices, raw_financials, raw_news, raw_executions などの Raw レイヤー。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols などの Processed レイヤー。
    - features, ai_scores などの Feature レイヤー。
    - signals, signal_queue, orders, trades, positions, portfolio_performance などの Execution レイヤー。
  - インデックスを作成（頻出クエリ向け）および順序を考慮した DDL 実行。
  - init_schema(db_path) でディレクトリ作成 → テーブル作成を行い DuckDB 接続を返す。
  - get_connection(db_path) で既存 DB へ接続可能（初期化は行わない旨を明記）。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の基本構造を実装：
    - 差分更新（最終取得日を元に必要範囲のみ取得）、バックフィル（デフォルト backfill_days=3）サポート。
    - 市場カレンダー先読み（_CALENDAR_LOOKAHEAD_DAYS）などの方針を明示。
    - ETLResult データクラスを定義（取得件数、保存件数、品質問題、エラー一覧を格納）とユーティリティ（to_dict, has_errors, has_quality_errors）。
    - テーブル存在チェック、最大日付取得、営業日に調整するヘルパーを提供。
    - run_prices_etl の実装（差分取得 → 保存）を含む（J-Quants クライアントを呼び出す）。
  - 品質チェック（quality モジュール）との連携ポイントを設け、品質問題は収集するが ETL を継続する設計。

- その他
  - 空のパッケージエントリ（kabusys.data.__init__, kabusys.strategy.__init__, kabusys.execution.__init__）を配置して拡張を容易にする。
  - ロギング出力を各モジュールに配置して運用時の可観測性を向上。

Security
--------

- RSS XML パーシングに defusedxml を使用し、XML Bomb 等の攻撃対策を実施。
- RSS 取得時およびリダイレクト時にスキーム/プライベートIPチェックを実施し SSRF を防止。
- .env 読み込み時のファイル読み込み失敗は警告により通知（例外炸裂は回避）。

Changed
-------

- 初回リリースのため該当なし。

Fixed
-----

- 初回リリースのため該当なし。

Deprecated
----------

- 初回リリースのため該当なし。

Removed
-------

- 初回リリースのため該当なし。

Known issues / Notes
--------------------

- ETL パイプラインは基本的な部分を実装済みですが、品質チェックモジュール（quality）や一部の運用ロジックは外部モジュールとの連携を前提としており、統合テストが必要です。
- strategy / execution モジュールは未実装（プレースホルダ）。オーダー送信やポジション管理の実装は別途必要です。
- 実運用時は .env に機密情報（トークン等）を設定する際の取り扱いに注意してください（プロジェクトは KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化が可能）。
- DuckDB に対する SQL 文は直接文字列連結する箇所があるため、クエリインジェクションに相当する外部入力を渡す場面は注意が必要（現在は内部生成値・パラメータ化で対策済みの箇所が多い）。

ライセンスなど
--------------

- この CHANGELOG.md はコードの内容から推測して作成されています。実際のリリースノートは運用方針や履歴に応じて調整してください。