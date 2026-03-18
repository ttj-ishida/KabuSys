# Changelog

すべての重要な変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-18

初回リリース。本リポジトリは日本株自動売買システム（KabuSys）のコアライブラリ群を提供します。以下はコードベースから推測される主要な追加点、設計上の方針、実装の注目点です。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
  - サブパッケージの公開: data, strategy, execution, monitoring（__all__ に定義）。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルートの検出ロジック: .git または pyproject.toml を基準に自動検出（CWD 非依存）。
  - .env パーサーは以下に対応:
    - 空行、コメント行、export プレフィックス
    - シングル／ダブルクォートとバックスラッシュエスケープ
    - クォート無しの場合のインラインコメント処理
  - .env 読み込み挙動:
    - 読み込み優先順位: OS環境 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能
    - 既存 OS 環境変数は protected として上書きを防止
  - Settings クラスを提供（プロパティ経由で必須変数を取得）
    - J-Quants / kabuステーション / Slack / DB パス等の設定を取得
    - env, log_level に対する値検証（許容値チェック）
    - is_live / is_paper / is_dev のヘルパー

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - OHLCV（株価日足）、財務データ（四半期 BS/PL）、市場カレンダー取得の実装。
  - 設計方針の反映:
    - レート制限 (120 req/min) を固定間隔スロットリングで遵守する RateLimiter 実装。
    - 冪等性を考慮した DuckDB 保存（ON CONFLICT DO UPDATE を前提とした save_* 関数）。
    - ページネーション対応（pagination_key を用いた取得ループ）。
    - リトライロジック（指数バックオフ、最大 3 回、対象: 408/429/5xx、およびネットワークエラー）。
    - 401 受信時はトークン自動リフレッシュを1回行って再試行（無限再帰回避のため allow_refresh フラグ）。
    - id_token のモジュールレベルキャッシュ（ページネーション間共有）を実装し、get_id_token を経由して取得可能。
    - データ取得時に取得時刻 (fetched_at) を UTC で記録（Look-ahead Bias 対策）。
  - データ保存関数:
    - save_daily_quotes, save_financial_statements, save_market_calendar — いずれも入力検証、PK 欠損行スキップ、ON CONFLICT DO UPDATE の冪等保存を実装。
  - 型変換ユーティリティ: _to_float, _to_int（空値・不正値を安全に扱う）

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからニュース記事を収集し raw_news, news_symbols に保存するフルスタック機能。
  - 主な実装点:
    - デフォルト RSS ソース (例: Yahoo Finance)。
    - URL 正規化とトラッキングパラメータ除去（_normalize_url）。
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を保証。
    - defusedxml を使った XML パース（XML Bomb 対策）。
    - SSRF 対策:
      - fetch 前にホストがプライベートかチェック（_is_private_host）。
      - リダイレクト時にスキーム・プライベートアドレス検証を行うカスタム RedirectHandler。
      - 許可スキームは http/https のみ。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を超えるレスポンスは拒否。gzip 解凍後も再チェック。
    - ネットワークリクエストはカスタマイズ可能な _urlopen（テスト用に差し替え可能）。
    - テキスト前処理（URL 除去、空白正規化）と pubDate パース（RFC2822 互換）。
    - DB 保存:
      - save_raw_news はバルク INSERT をチャンク単位で実行、INSERT ... RETURNING で実挿入IDを取得、トランザクションで一括コミット/ロールバック。
      - save_news_symbols / _save_news_symbols_bulk で記事と銘柄コードの紐付けを一括挿入（重複除去、トランザクション）。
    - 銘柄コード抽出: 正規表現で4桁数字を抽出し、known_codes に含まれるものだけ返す（重複除去）。

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution 層のテーブル群を網羅する DDL を定義。
  - 代表的テーブル: raw_prices, raw_financials, raw_news, market_calendar, prices_daily, features, ai_scores, signal_queue, orders, trades, positions, portfolio_performance 等。
  - 制約（CHECK, PRIMARY KEY, FOREIGN KEY）やインデックス定義（頻出クエリに対するインデックス）を備える。
  - init_schema(db_path) によりディレクトリ作成→接続→全テーブル・インデックス作成が冪等に実行可能。
  - get_connection(db_path) を提供（初期化は行わない）。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 差分更新・バックフィル・品質チェックを想定した ETL 支援機能を実装。
  - ETLResult dataclass を導入（実行結果、品質問題、エラーの集約、シリアライズ用 to_dict）。
  - 市場カレンダー調整ヘルパー（_adjust_to_trading_day）を実装。非営業日の調整ロジックを提供。
  - 差分更新用ユーティリティ:
    - テーブル存在チェック、最大日取得 (_get_max_date)。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date を実装。
  - run_prices_etl を実装（差分取得ロジック、backfill_days を利用した部分取得、jquants_client の fetch/save を呼び出し）。（ファイル末尾は一部切れているが、差分ETLの骨格と設計方針が実装されている）

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- RSS XML パースで defusedxml を採用、SSRF 対策を複数レイヤーで実装。
- ネットワークリクエストに対して Content-Length と実際読み取りバイト数のチェック、gzip 解凍後サイズ検査を実施（DoS対策）。
- .env の読み込みでは OS 環境変数を保護する仕組みを実装して、誤ってcredentialを上書きしないように配慮。

### パフォーマンス (Performance)
- J-Quants API 呼び出しに固定間隔の RateLimiter を導入しレートを安定化。
- DB バルク挿入はチャンク化して一度のトランザクションでまとめることでオーバーヘッドを削減。
- id_token のモジュールキャッシュでページネーション間の再認証を抑制。

### テスト支援 (Testability)
- jquants_client のリクエスト関数は id_token を注入可能（テスト容易性）。
- news_collector の _urlopen を差し替え可能にして外部ネットワークをモックしやすくしている。

### 既知の制限 / 注意点
- run_prices_etl のファイル末尾が切れている箇所があり（コード断片で終わっている）、ETL 完成形の詳細処理（品質チェックの統合など）がまだ続く可能性がある。
- schema のバージョン管理や将来的なマイグレーション機構は未実装（初期スキーマを idempotent に作成するのみ）。
- news_collector の extract_stock_codes は4桁数字ベースの単純抽出のため、文脈誤検出の可能性がある（known_codes による絞り込みで軽減）。

---

今後のリリースでは、strategy / execution / monitoring の具体実装、品質チェックモジュール（quality）、ETL の完全ワークフロー、運用監視・通知（Slack 連携など）の詳細を追加していく想定です。必要であれば、各モジュールごとにより細かい変更履歴や設計起源の注記を追記します。