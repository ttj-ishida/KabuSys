# Changelog

すべての注記は Keep a Changelog の形式に従います。  
このプロジェクトの初期リリース（v0.1.0）では、データ取得・スキーマ管理・監査・データ品質チェック・環境設定まわりの基本機能を実装しています。

注意: 日付はリリース日です。

## [Unreleased]

---

## [0.1.0] - 2026-03-16

### Added
- パッケージ初期化
  - kabusys パッケージを導入。公開 API: data, strategy, execution, monitoring を __all__ で宣言。
  - バージョン: `0.1.0` を __version__ に設定。

- 環境設定モジュール (kabusys.config)
  - .env/.env.local または OS 環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能（テスト用途を想定）。
    - プロジェクトルート判定は __file__ を起点に `.git` または `pyproject.toml` を探索するため、CWD に依存しない。
  - .env パーサー実装:
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のエスケープに対応。
    - インラインコメント処理（クォートあり／なしのケースを考慮）。
  - env 読み込み時の上書き制御:
    - `override` と `protected`（OS 環境変数を上書きしないための保護セット）を実装。
  - Settings クラスを提供（インターフェース経由で設定値を取得）:
    - J-Quants / kabu API / Slack / DB パス / システム設定（環境種別、ログレベル判定など）。
    - 必須変数未設定時は ValueError を投げる `_require` を備える。
    - `env` や `log_level` の値検証（許容値チェック）と convenience プロパティ (`is_live`, `is_paper`, `is_dev`) を追加。

- J-Quants データクライアント (kabusys.data.jquants_client)
  - J-Quants API から以下を取得する機能を実装:
    - 株価日足（OHLCV）: `fetch_daily_quotes`
    - 財務データ（四半期 BS/PL）: `fetch_financial_statements`
    - JPX マーケットカレンダー: `fetch_market_calendar`
  - 設計的特徴:
    - API レート制限遵守（120 req/min）を固定間隔スロットリングで制御する RateLimiter を実装。
    - リトライロジック（指数バックオフ、最大 3 回）。対象は 408/429/5xx などのネットワーク・サーバーエラー。
    - 401 Unauthorized 受信時はリフレッシュトークンでトークンを自動リフレッシュして 1 回リトライ（無限再帰を防止）。
    - ID トークンのモジュールレベルキャッシュを実装（ページネーション間で共有）。
    - ページネーション対応（pagination_key を利用して全ページ取得）。
    - 取得時刻（fetched_at）を UTC で付与し、Look‑ahead Bias のトレースを可能に。
  - DuckDB への保存関数を追加（冪等性を考慮）:
    - `save_daily_quotes`, `save_financial_statements`, `save_market_calendar`
    - INSERT ... ON CONFLICT DO UPDATE を使って重複を排除・更新。
    - PK 欠損行はスキップし、スキップ件数をログ出力。
  - ユーティリティ関数:
    - `_to_float`, `_to_int`（安全な変換、空値や不正値に対して None を返す。`_to_int` は小数部が非ゼロの場合は None を返す等の挙動を定義）。

- DuckDB スキーマ管理 (kabusys.data.schema)
  - DataPlatform.md に基づく 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル群を DDL として定義。
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス定義（頻出クエリに備えた複数の CREATE INDEX）を用意。
  - `init_schema(db_path)` によりディレクトリ作成→接続→全テーブルとインデックス作成を行う（冪等）。
  - `get_connection(db_path)` を提供（既存 DB への接続。スキーマ初期化は行わない）。

- 監査ログ（Audit）モジュール (kabusys.data.audit)
  - シグナル → 発注要求 → 約定 のトレーサビリティを保持する監査用テーブルを定義。
    - signal_events（戦略が生成したすべてのシグナルを記録）
    - order_requests（order_request_id を冪等キーとして扱う発注要求ログ）
    - executions（証券会社からの約定ログ、broker_execution_id をユニーク冪等キーとして保持）
  - `init_audit_schema(conn)` および `init_audit_db(db_path)` を提供（UTC タイムゾーン設定を強制）。
  - 監査用のインデックスを追加（ステータス検索、signal_id 連結、broker_order_id での検索等）。
  - 設計原則として、監査ログは削除しない前提（FK は ON DELETE RESTRICT）や created_at/updated_at の扱いを明記。

- データ品質チェックモジュール (kabusys.data.quality)
  - QualityIssue データクラスを導入（チェック名、テーブル、severity、detail、サンプル行）。
  - チェック実装:
    - 欠損データ検出（raw_prices の OHLC 欄の NULL 検出）: `check_missing_data`
    - スパイク検出（前日比の変動率が閾値超、デフォルト 50%）: `check_spike`
    - 重複チェック（raw_prices の主キー重複）: `check_duplicates`
    - 日付不整合検出（未来日付・market_calendar と矛盾する非営業日のデータ）: `check_date_consistency`
  - `run_all_checks(conn, ...)` により全チェックをまとめて実行し、検出された QualityIssue のリストを返す。
  - 各チェックはサンプル行（最大 10 件）を返し、Fail‑Fast ではなく全件収集する設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- .env 自動読み込み時の保護機構（protected set）を導入し、既存の OS 環境変数を意図せず上書きしないように設計。
- .env パーサーでクォート内のエスケープ処理を正しく扱うことで、意図しない文字列解釈を抑止。

### Notes / Implementation details
- すべての TIMESTAMP は UTC 保存を基本方針としている（監査ログ初期化時に SET TimeZone='UTC' を実行）。
- DuckDB のスキーマ初期化は冪等に実装してあるため、既存 DB に対して何度でも適用可能。
- J-Quants API クライアントは外部ネットワークの信頼性に合わせて堅牢なリトライとレート制御を実装しているが、実運用ではさらに監視やメトリクスの導入を推奨。
- 現時点で strategy と execution、monitoring のパッケージはプレースホルダ（__init__.py のみ）として存在。戦略実装・発注処理・監視ロジックは今後追加予定。

---

（注）この CHANGELOG はコードベースからの挙動・設計意図を推測して記載しています。実際の利用にあたっては README やドキュメント、ソースコード本体を参照してください。