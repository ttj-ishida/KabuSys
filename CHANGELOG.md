# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」フォーマットに準拠しています。  
安定化リリースや後方互換性に関する方針はセマンティックバージョニングに従います。

## [Unreleased]

(現在のコードベースは初期リリース相当の実装が含まれます。リリース履歴は下記 0.1.0 を参照してください)

---

## [0.1.0] - 2026-03-18

初回公開リリース。日本株自動売買システムのコアライブラリ（KabuSys）の骨格と主要コンポーネントを追加。

### Added
- パッケージ基盤
  - パッケージルート: `kabusys` を追加。__version__ = "0.1.0"。公開 API として `data`, `strategy`, `execution`, `monitoring` を __all__ に定義。

- 設定・環境変数管理 (`kabusys.config`)
  - .env ファイルと環境変数から設定を読み込む自動ローダーを実装。読み込み優先順位は OS 環境変数 > .env.local > .env。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を起点）を採用し、CWD に依存しない動作を実現。
  - .env パーサ `_parse_env_line` を実装。コメント行、`export KEY=val` 形式、クォート内のエスケープ、行内コメントの扱い等に対応。
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト向け）。
  - 必須環境変数取得ヘルパ `_require` と Settings クラスを実装。J-Quants / kabu API / Slack / DB パスなどの主要設定プロパティを提供。
  - KABUSYS_ENV / LOG_LEVEL の妥当性チェックおよび is_live/is_paper/is_dev の便利プロパティを追加。

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - J-Quants のトークン取得 (`get_id_token`) と API リクエストラッパー `_request` を実装。JSON デコードとエラーハンドリングを含む。
  - レートリミッタ `_RateLimiter` を追加し、J-Quants の制限（120 req/min）に合わせたスロットリングを実装。
  - 再試行ロジック（指数バックオフ、最大 3 回）を実装。HTTP 429 は Retry-After を優先して待機。408/429/5xx 系をリトライ対象に設定。
  - 401 Unauthorized 受信時、自動的にリフレッシュして 1 回リトライするトークンリフレッシュ機能を実装（ループ防止のため allow_refresh フラグあり）。
  - ページネーション対応のデータ取得関数を追加:
    - fetch_daily_quotes（株価日足 OHLCV）
    - fetch_financial_statements（四半期財務データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB へ冪等に保存する関数を実装（ON CONFLICT DO UPDATE）:
    - save_daily_quotes / save_financial_statements / save_market_calendar
  - データ変換ユーティリティ `_to_float`, `_to_int` を実装し、空文字や不正値を安全に扱う。

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィード取得と前処理、DuckDB への冪等保存パイプラインを実装。
  - セキュリティと堅牢性の設計:
    - defusedxml を用いた XML パース（XML Bomb 等の軽減）
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、リダイレクト先のスキームとホスト検証、プライベートアドレス拒否（IP 直接判定 & DNS 解決して A/AAAA を検査）
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）
    - User-Agent, Accept-Encoding 対応およびリダイレクト時の事前検査用カスタムハンドラ `_SSRFBlockRedirectHandler`
  - URL 正規化とトラッキングパラメータ除去（_normalize_url）および記事 ID の決定（SHA-256 の先頭32文字）を実装。utm_* 等のパラメータを削除して冪等性を向上。
  - テキスト前処理（URL 除去・空白正規化）`preprocess_text` と RSS pubDate のパース `_parse_rss_datetime` を実装（タイムゾーン統一）。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を使用し、新規登録された記事ID一覧を返す。チャンク挿入と単一トランザクション処理を採用。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けテーブルへ一括挿入（ON CONFLICT DO NOTHING + RETURNING）。
  - 銘柄コード抽出ユーティリティ `extract_stock_codes`（4桁数字パターン）を実装。
  - RSS 複数ソースをまとめて収集する `run_news_collection` 関数を実装（ソース毎に独立したエラーハンドリング、既知銘柄による紐付け処理）。

- DuckDB スキーマ管理 (`kabusys.data.schema`)
  - Raw / Processed / Feature / Execution レイヤのテーブル定義を追加（DDL を文字列として保持）。
  - raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等のテーブルを定義。
  - パフォーマンス目的のインデックスを追加（頻出クエリに対する index）。
  - init_schema(db_path) を実装し、DB ファイルの親ディレクトリ自動作成と全テーブル・インデックスの冪等作成を行う。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン (`kabusys.data.pipeline`)
  - ETL の流れ説明と差分更新ロジックを実装（最終取得日からの差分取得、backfill のサポート）。
  - ETLResult dataclass を実装し、処理結果・品質問題・エラーを集約して返せるようにした（to_dict により品質問題を簡潔に表現）。
  - テーブル存在チェック、最大日付取得ヘルパ、トレーディング日調整ヘルパ（カレンダー参照）を実装。
  - 個別 ETL ジョブ（run_prices_etl など）の骨組みを追加。差分取得、fetch -> save の流れとログ出力を備える。
  - テスト容易性のため、id_token の注入や外部呼び出しのモックポイントを考慮した実装。

- その他
  - モジュールの分割（data, strategy, execution, monitoring）を用意し、今後の拡張ポイントを確保。
  - 詳細な docstring と設計方針を各モジュールに記載し、内部挙動（冪等性、Look-ahead 減少のための fetched_at 保持など）を明示。

### Security
- ニュース収集ルーチンにおける SSRF 対策、defusedxml の採用、レスポンスサイズ制限、gzip 解凍後の検査等を導入し、外部から与えられる XML/URL に対する攻撃面を低減。
- .env 読み込みにおいて OS 環境変数を保護するための protected set を導入（override 時の保護）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

---

Notes / 今後の TODO（コードから推測）
- strategy, execution, monitoring パッケージは現在プレースホルダ。具体的な売買戦略、発注エンジン、監視ロジックを実装予定。
- 品質チェックモジュール（kabusys.data.quality）は参照されているが実体は別途実装が必要。ETL の品質検出ルールと Severity 定義を充実させる必要あり。
- 単体テスト・統合テストの整備（外部 API のモック、ネットワーク依存箇所の差し替えを推奨）。
- ドキュメント（DataPlatform.md、DataSchema.md 等）との整合性テストと CI/CD ワークフローの整備。

------------------------------------------------------------------------
この CHANGELOG はコードの実装内容から推測して作成しています。機能追加や修正の履歴を正確に反映するため、実際のリリース時には差分に応じて適宜更新してください。