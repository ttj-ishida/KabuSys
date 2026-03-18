CHANGELOG
=========

全体方針: この CHANGELOG は "Keep a Changelog" 形式に準拠しています。  
リリース日はコードベースから推定できる初期公開バージョンとして記載しています。

[Unreleased]
------------

- 現在未リリースの変更はありません。

[0.1.0] - 2026-03-18
-------------------

Added
- パッケージ初期リリース (kabusys 0.1.0)
  - パッケージエントリポイントとバージョンを追加（src/kabusys/__init__.py）。
- 環境設定管理
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込みする仕組みを追加（src/kabusys/config.py）。
  - .env のパースルールを詳細に実装（コメント行、export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの扱い等）。
  - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須設定取得時に未設定なら明示的なエラーを投げる _require を提供し、J-Quants/Slack/DB 等の必須環境変数を明示（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - KABUSYS_ENV（development, paper_trading, live）と LOG_LEVEL（DEBUG/INFO/...）のバリデーションを実装。デフォルトの DB パス（DUCKDB_PATH, SQLITE_PATH）を提供。
- Data: J-Quants クライアント
  - J-Quants API からのデータ取得ユーティリティを実装（src/kabusys/data/jquants_client.py）。
  - レート制限制御（120 req/min 固定間隔スロットリング）を実装する RateLimiter を追加。
  - 再試行ロジック（指数バックオフ、HTTP 408/429/5xx のリトライ、最大 3 回）および 401 受信時の自動トークンリフレッシュを実装。
  - ページネーション対応の fetch_* 系関数を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB へ冪等に保存する save_* 関数を追加（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT DO UPDATE を使い重複を排除。
  - 値変換ユーティリティ（_to_float, _to_int）を実装し不正データへの寛容性を確保。
  - id_token キャッシュ（モジュールレベル）でページネーション間のトークン再利用・自動リフレッシュを最適化。
- Data: ニュース収集
  - RSS ベースのニュース収集モジュールを実装（src/kabusys/data/news_collector.py）。
  - URL 正規化とトラッキングパラメータ除去、記事ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保。
  - defusedxml を用いた安全な XML パース、Gzip 対応、受信サイズ上限（MAX_RESPONSE_BYTES=10MB）によるメモリDoS対策を実装。
  - SSRF 対策: リダイレクト先のスキーム検証、プライベート IP/ループバック判定（DNS 解決を含む）、カスタム RedirectHandler の導入、初期ホスト検査を実装。
  - 記事保存はチャンク化（_INSERT_CHUNK_SIZE）してトランザクション内で一括INSERTし、INSERT ... RETURNING を用いて実際に挿入されたID/件数を返す（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
  - テキスト前処理（URL 除去・空白正規化）、銘柄コード（4桁）抽出ロジックを実装し、known_codes を使った記事と銘柄の紐付けをサポート。
- Research（特徴量・ファクター）
  - 特徴量探索モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）：指定日から複数ホライズンにわたる将来リターンを DuckDB の prices_daily から一度に取得。
    - IC（Information Coefficient）計算（calc_ic）とランク変換ユーティリティ（rank）：スピアマン相関（ランク相関）を標準ライブラリのみで計算。
    - ファクター統計サマリー（factor_summary）：count/mean/std/min/max/median を算出。
    - pandas 非依存かつ DuckDB 接続を受け取る設計（Research 環境での安全性を意識）。
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - Momentum（calc_momentum）：1M/3M/6M リターン、MA200 乖離を計算。
    - Volatility（calc_volatility）：20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算。
    - Value（calc_value）：raw_financials と prices_daily を組み合わせ PER / ROE を算出（target_date 以前の最新財務レコードを取得）。
    - DuckDB のウィンドウ関数・SQL を活用して効率的に集計。
  - research パッケージのエクスポートを整備（src/kabusys/research/__init__.py）。
- スキーマ定義
  - DuckDB 用スキーマ定義の雛形を追加（src/kabusys/data/schema.py）。
  - Raw レイヤー向けテーブル定義（raw_prices, raw_financials, raw_news, raw_executions 等のDDL雛形）を追加（初期化ユーティリティ等はスキーマファイル内で管理）。
- 実行系・戦略系のパッケージ構造を用意（src/kabusys/execution, src/kabusys/strategy の __init__.py を追加）し外部からの参照ポイントを確保。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Security
- RSS パーサーで defusedxml を使用し XML 関連の攻撃を緩和（news_collector）。
- SSRF 対策: リダイレクト前後でスキームとホストの検証、プライベート/ループバックIPの拒否、URL スキーム制限を実装（news_collector）。
- HTTP レスポンスサイズと gzip 解凍後サイズの上限チェックでメモリ爆発を防止。

Notes / Migration / 使用上の注意
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN（J-Quants 用）
  - KABU_API_PASSWORD（kabu API 用）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（通知用）
  これらが未設定の場合、settings の該当プロパティ呼び出しで ValueError が発生します（src/kabusys/config.py）。
- 自動 .env ロード:
  - デフォルトでプロジェクトルートの .env および .env.local を読み込みます。OS 環境変数は上書きされません（.env.local は上書き可能だが OS 環境は保護）。
  - テスト・特殊用途で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB パスのデフォルト:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- Research モジュール:
  - pandas などの外部ライブラリに依存せず純粋な標準ライブラリ + DuckDB SQL で実装されています。大量データ分析では DuckDB 側での最適化を行ってください。
- NewsCollector のテスト性:
  - _urlopen はテストでモックして取り替え可能な設計になっています（外部 HTTP を直接叩かないユニットテストが可能）。
- J-Quants クライアント:
  - 内部で固定レート制限（120 req/min）を保証します。高頻度の並列リクエスト時は注意してください。
  - 401 受信時は自動的にリフレッシュを試行し 1 回だけリトライします。トークン再取得に失敗すると例外となります。
- 制約 / 未実装の点:
  - factor_research の Liquidity の一部（PBR・配当利回り等）は現バージョンでは未実装。
  - schema.py は一部DDLの定義が記載されていますが、プロジェクト全体の初期化ロジック（スキーマ適用スクリプト）は別途実行する必要がある想定です。

Acknowledgements / Reference
- 実装の設計方針や関数名・挙動はリポジトリ内の doc（StrategyModel.md, DataPlatform.md, DataSchema.md 等）に基づいている想定です。

今後の予定（例）
- Strategy と Execution 層の実装（発注ロジック、ポジション管理）
- 追加のデータソース（ニュースソース追加、外部ファイナンスAPI）
- 性能最適化・並列収集の安全な実装（レート制御強化、ジョブ管理）

---- 

（この CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時はコミット履歴・ PR 説明等を参照のうえ更新してください。）