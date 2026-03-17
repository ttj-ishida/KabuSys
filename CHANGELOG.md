# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
このプロジェクトはセマンティックバージョニング（MAJOR.MINOR.PATCH）に従います。

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買システム "KabuSys" の基盤機能を実装しました。以下の主要コンポーネントと特徴を含みます。

### 追加 (Added)
- パッケージ基本情報
  - パッケージ名とバージョンを定義（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開 API: data, strategy, execution, monitoring。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルおよび OS 環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出: `.git` または `pyproject.toml` を基準に検索（CWD 非依存）。
  - .env のパース機能:
    - `export KEY=val` 形式対応。
    - 単／二重クォート内のバックスラッシュエスケープ処理。
    - コメントの扱い（クォート外かつ直前が空白/タブの場合に `#` をコメントと扱う）に対応。
  - .env 読み込みの優先順位: OS 環境変数 > `.env.local` > `.env`。既存 OS 環境変数は保護（protected）。
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを抑止可能。
  - Settings クラス:
    - J-Quants / kabu API / Slack / DB パス等のプロパティを提供。
    - 環境変数必須チェック（未設定時は ValueError を送出）。
    - `KABUSYS_ENV` と `LOG_LEVEL` の値検証（許可値の制約）。
    - ユーティリティプロパティ: is_live/is_paper/is_dev。

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - 基本機能:
    - 日次株価（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得する API クライアントを実装。
    - ページネーション対応で全件取得。
  - レート制御:
    - API レート制限を守る固定間隔スロットリング（120 req/min、最小間隔 = 60/120 秒）。
  - リトライ／エラーハンドリング:
    - 指数バックオフ付きリトライ（最大 3 回、base=2.0）。
    - 再試行対象ステータス: 408, 429, 5xx。
    - 429 の場合は `Retry-After` ヘッダを優先して待機。
    - ネットワーク系エラー（URLError / OSError）にもリトライ。
  - 認証トークン管理:
    - ID トークンのモジュールレベルキャッシュを保持し、必要時リフレッシュ。
    - 401 受信時はトークンを自動リフレッシュして 1 回だけリトライ（無限再帰防止）。
  - 保存（DuckDB）:
    - 取得データを DuckDB に保存する save_* 関数を提供（save_daily_quotes / save_financial_statements / save_market_calendar）。
    - 冪等性を保つため INSERT ... ON CONFLICT DO UPDATE を利用。
    - 保存時に fetched_at を UTC で記録（Look-ahead bias のトレーサビリティ確保）。
  - ユーティリティ:
    - 安全な型変換ヘルパー `_to_float` / `_to_int`。

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードからニュースを収集して `raw_news` テーブルに保存する一連の機能を実装。
  - 主な仕様・設計:
    - デフォルトソースとして Yahoo Finance のビジネス RSS を設定。
    - 受信サイズ制限: MAX_RESPONSE_BYTES = 10 MB（Gzip 解凍後も同様に検査）。
    - defusedxml を用いた XML パース（XML Bomb 等への耐性）。
    - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid, gclid 等の既知プレフィックスを除外）。
    - 記事ID は正規化 URL の SHA-256 の先頭32文字で生成（冪等性確保）。
    - SSRF 対策:
      - リダイレクト先のスキームとホストを検査するカスタム HTTPRedirectHandler（プライベートアドレスや非 http(s) スキームを拒否）。
      - フェッチ前にホストのプライベートアドレス検査を実施。
    - gzip 対応と Gzip-bomb 対策（解凍後サイズチェック）。
    - DB 保存:
      - `save_raw_news` はチャンク（デフォルト 1000 件）で INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、新規挿入 ID を返す。
      - `save_news_symbols` / `_save_news_symbols_bulk` により (news_id, code) ペアをトランザクションで一括挿入（ON CONFLICT DO NOTHING、実際に挿入された件数を返す）。
    - 銘柄抽出:
      - 正規表現 `\b(\d{4})\b` により 4 桁数値を候補とし、known_codes セットでフィルタリング・重複除去。

- DuckDB スキーマ定義 (`kabusys.data.schema`)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）＋ Execution 層のテーブルを定義。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約・チェック:
    - 各カラムに対する型制約および CHECK 制約を多数定義（負値排除や side/status/order_type の列挙など）。
  - インデックス:
    - 頻出クエリ向けのインデックスを複数定義（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - 初期化 API:
    - `init_schema(db_path)`：親ディレクトリ自動作成、全 DDL とインデックスを実行して接続を返す（冪等）。
    - `get_connection(db_path)`：既存 DB への接続を返す（スキーマ初期化は行わない）。

- ETL パイプライン (`kabusys.data.pipeline`)
  - ETL 設計:
    - 差分更新（DB の最終取得日を基に未取得分のみ取得）。
    - デフォルトのバックフィル: 最終取得日から数日前（デフォルト 3 日）を再取得して API の後出し修正に対応。
    - 市場カレンダーの先読み (_CALENDAR_LOOKAHEAD_DAYS = 90)。
    - 品質チェックは収集処理を継続しつつ検出結果を報告する設計（Fail-Fast ではない）。
  - ETLResult データクラス: 取得件数、保存件数、品質問題リスト、エラー概要を保持。quality_issues は辞書形式に変換可能。
  - 補助ユーティリティ:
    - テーブル存在チェック、最大日付取得、営業日調整ロジック。
    - run_prices_etl: 差分取得 → 保存 の流れ（J-Quants クライアント利用）。最小データ日付の定数 `_MIN_DATA_DATE = 2017-01-01` を使用。

### セキュリティ (Security)
- RSS パーシングに defusedxml を使用して XML 関連の攻撃を防止。
- RSS フェッチでの SSRF 対策:
  - リダイレクト時のスキーム検査とプライベートアドレス検査（リダイレクトハンドラ実装）。
  - 初回フェッチ前にホストのプライベート/ループバック/リンクローカル/マルチキャスト判定を行い内部アドレスへのアクセスを拒否。
- HTTP レスポンスの最大読み取りサイズ（10MB）を超える場合はフェッチを中止しメモリ DoS を防止。
- URL 正規化でトラッキングパラメータを除去し、記事同一性の攻撃ベクタを低減。

### 既知の制限・注意点 (Notes)
- ETL パイプラインは基本的な差分更新ロジックを実装していますが、品質チェックモジュール（quality）の詳細実装や一部の統合処理は運用で追加・調整される想定です。
- ネットワーク / API 呼び出しでは urllib を直接使っており、より高度な機能（セッション管理や接続プール）が必要な場合は将来的に移行を検討してください。
- 一部モジュール（strategy、execution、monitoring）は __init__.py のみ存在し、各機能の詳細実装は今後の追加対象です。

---

今後のリリースでは以下を予定しています（例）:
- strategy / execution 層の戦略実装と発注フローの統合
- 監視（monitoring）機能の実装（Slack 通知等）
- 品質チェック（quality）ルールの充実と自動レポート化
- 単体テスト・統合テストの追加と CI パイプライン構築

もし CHANGELOG に追加して欲しい点や、より詳細な差分説明（ファイル別の変更点など）が必要であればお知らせください。