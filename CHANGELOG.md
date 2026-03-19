Keep a Changelog 準拠 — CHANGELOG.md
※このファイルは、現在のコードベースの内容から推測して作成した変更履歴です。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
- 特になし（初回リリースとして 0.1.0 を追加済み）

[0.1.0] - 2026-03-19
-------------------
Added
- パッケージ基盤
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。公開モジュール: data, strategy, execution, monitoring。
  - バージョン: 0.1.0

- 設定・環境変数管理（src/kabusys/config.py）
  - .env / .env.local を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - .env パーサ実装（コメント、export プレフィックス、クォート／エスケープ処理、インラインコメント扱いなどを考慮）。
  - Settings クラスを提供し、J-Quants・kabuステーション・Slack・DBパス等の設定プロパティを用意。
  - 必須環境変数チェック（未設定時は ValueError を送出）。
  - 有効値検証: KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL。

- Data モジュール: J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しユーティリティ（_request）: ページネーション対応、JSON デコード検査、詳細なエラーハンドリング。
  - レート制限実装: 固定間隔スロットリングで 120 req/min を保証（_RateLimiter）。
  - 再試行ロジック: 指数バックオフ、最大 3 回、HTTP 408/429/5xx をリトライ対象。429 では Retry-After を尊重。
  - 401 ハンドリング: トークン期限切れ時に自動で ID トークンをリフレッシュして 1 回リトライ。モジュールレベルのトークンキャッシュを保持。
  - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）。
  - DuckDB への保存関数（冪等）: save_daily_quotes, save_financial_statements, save_market_calendar。いずれも ON CONFLICT DO UPDATE を使用して重複を排除。
  - 値変換ユーティリティ: _to_float / _to_int（空値・不正値の厳格な扱い、"1.0" のような文字列の扱いを明示）。

- Data モジュール: ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード取得と記事保存ワークフローを実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
  - 安全対策:
    - defusedxml による XML パース、安全なパースエラーハンドリング。
    - SSRF 防止: リダイレクト前後でスキームとホストを検査、プライベート・ループバック・リンクローカル・マルチキャストを拒否。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）チェックおよび gzip 解凍後のサイズ再チェック（Gzip bomb 対策）。
  - トラッキングパラメータ除去（utm_* ほか）と URL 正規化に基づく記事 ID（SHA-256 の先頭32文字）生成で冪等性を担保。
  - テキスト前処理（URL 除去・空白正規化）。
  - 銘柄コード抽出（4桁数字パターン）と既知コードセットによるフィルタリング。
  - DB 保存はチャンク化＆トランザクションで処理し、INSERT ... RETURNING を使って実際に挿入されたレコードを返す。

- Research モジュール（src/kabusys/research/）
  - feature_exploration: calc_forward_returns（複数ホライズン対応、DuckDB SQL でリード窓を利用）、calc_ic（スピアマンランク相関、欠損/有限性チェック、最小サンプル数判定）、factor_summary（基本統計量計算）、rank（同順位は平均ランク、丸めで ties 検出漏れ対策）。
  - factor_research: calc_momentum（1m/3m/6m リターン、MA200乖離）、calc_volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）、calc_value（PER/ROE、raw_financials の最新財務レコードを結合）。いずれも DuckDB で SQL ウィンドウ関数を活用し、不足データ時は None を返す設計。
  - research パッケージの __all__ を通して主要関数と zscore_normalize（kabusys.data.stats から）を再エクスポート。

- DuckDB スキーマ定義 / 初期化（src/kabusys/data/schema.py）
  - Raw レイヤーのテーブル DDL（raw_prices, raw_financials, raw_news, raw_executions 等）を定義（部分的に掲示）。DataSchema.md に基づく設計方針を明記。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- RSS / XML 処理に defusedxml を採用して XML 攻撃を低減。
- RSS フェッチでの SSRF 対策を強化（事前/事後ホスト検査・リダイレクト検査・スキーム制限）。
- ニュース収集時に外部 URL を正規化・トラッキングパラメータ削除して記事IDを生成、冪等性を向上。

Performance
- J-Quants API 呼び出しに固定間隔のレートリミッタを採用（120 req/min 固定）して API 制限を遵守。
- DuckDB への大量挿入はチャンク化して一括挿入、トランザクションでまとめてオーバーヘッドを低減。
- calc_forward_returns / factor 計算で必要最小限のスキャン範囲（カレンダーバッファ）を見積もり、SQL 側で窓関数により効率的に集計。

Notes / Developers
- 必須環境変数（Settings で _require を使ってチェックされるもの）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 任意／デフォルト値:
  - KABUSYS_ENV (default: development)、LOG_LEVEL (default: INFO)
  - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
  - DUCKDB_PATH (default: data/kabusys.duckdb)、SQLITE_PATH (default: data/monitoring.db)
- self-contained 設計方針:
  - Research / Factor 計算は prices_daily / raw_financials のみ参照し、本番発注 API へはアクセスしない。
  - 外部ライブラリ依存を極力抑えているが、DuckDB と defusedxml は利用している。
- 例外/バリデーション:
  - calc_ic は有効レコード数 < 3 や分散が 0 の場合 None を返す。
  - _to_int は小数部が 0 以外の float 文字列を None として扱い、意図しない切り捨てを回避する。
- 空のパッケージプレースホルダ:
  - src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py は存在するが実装は未追加（整理済みのエントリポイント）。

Breaking Changes
- なし（初回リリース）

Known issues / TODO（推測）
- schema.py の DDL は raw_executions の定義が途中で切れている（現行コードのスナップショットに基づく）。実運用前にスキーマの完成とマイグレーション手順が必要。
- strategy / execution / monitoring の具象実装は未提供。実運用の発注や監視処理を追加する必要あり。

付記
- この CHANGELOG はコードの内容から機能・設計を推測して作成しています。正式な仕様・リリースノートが存在する場合はそちらに合わせて調整してください。