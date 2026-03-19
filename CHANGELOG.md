KEEP A CHANGELOG
すべての変更は https://keepachangelog.com/ja/ に準拠して記載しています。

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しました。

### Added
- パッケージ構成
  - パッケージルート (src/kabusys/__init__.py) を追加し、version を "0.1.0" に設定。公開 API として data, strategy, execution, monitoring をエクスポート。
  - strategy/ と execution/ の初期 __init__.py（プレースホルダ）を追加。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env のパースは export プレフィックス、クォート文字列（エスケープ対応）、行内コメント処理などに対応する堅牢な実装。
  - OS 環境変数を保護する protected 上書き制御（.env.local は override=True で上書きするが OS 変数は保護）。
  - 必須項目取得用の _require と Settings クラスを追加。以下の設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH（デフォルトパスを提供）
    - KABUSYS_ENV（development / paper_trading / live のバリデーション）、LOG_LEVEL（許容値チェック）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- データ取得・保存クライアント：J-Quants (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装（/prices/daily_quotes, /fins/statements, /markets/trading_calendar 等の取得関数）。
  - レートリミッタ実装（120 req/min 固定間隔スロットリング）。
  - 冪等的保存：DuckDB への挿入は ON CONFLICT DO UPDATE を用いて重複を排除。
  - リトライロジック（指数バックオフ、最大 3 回）。408/429/5xx を再試行対象に、429 の Retry-After ヘッダを尊重。
  - 401 受信時は refresh token で id_token を自動更新して 1 回リトライ。
  - ページネーション対応（pagination_key の扱い）。
  - 日付/数値変換ユーティリティ _to_float / _to_int（厳格な変換・空値処理）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS 取得と raw_news 保存の実装。デフォルトRSSソースとして Yahoo Finance を登録。
  - セキュリティ対策:
    - defusedxml を用いた XML パーサ（XML Bomb 対策）。
    - SSRF 対策: リクエスト前のホスト検査、リダイレクト時スキーム/ホスト検証用ハンドラ。
    - URL スキーム検証（http/https のみ許可）。
    - 応答サイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）、SHA-256 先頭 32 文字による記事 ID 生成。
  - テキスト前処理（URL 除去・空白正規化）。
  - 銘柄コード抽出（4桁数字、既知コードセットによるフィルタリング）。
  - DB 保存はトランザクションでまとめ、INSERT ... RETURNING を使って実際に新規挿入された ID を取得。news_symbols のバルク保存も実装。
  - fetch_rss は XML パースエラー時に空リストを返し、各ソースは独立して失敗処理される（run_news_collection）。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - DataSchema に基づく初期 DDL を実装（Raw Layer の raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義を含む）。
  - 各テーブルに適切な型チェック・PRIMARY KEY を設定し、データ整合性を担保。

- リサーチ / ファクター計算 (src/kabusys/research/)
  - feature_exploration.py:
    - calc_forward_returns: 与えた基準日から複数ホライズンの将来リターンを高速に取得（1クエリで LEAD を使用）。horizons の入力検証あり。
    - calc_ic: ファクター値と将来リターンに基づくスピアマンランク相関（IC）を実装。データ不足やゼロ分散のケースで None を返す。
    - rank / factor_summary: ランク付け（同順位は平均ランク、浮動小数誤差対策で round( ,12) を使用）と統計サマリー（count/mean/std/min/max/median）。
    - pandas 等外部依存を使わず標準ライブラリと DuckDB 結果で実装。
  - factor_research.py:
    - calc_momentum: mom_1m/3m/6m、ma200_dev（200日MA乖離）を計算。ウィンドウ未満は None を返す。
    - calc_volatility: 20日 ATR（true_range ベース）、atr_pct、avg_turnover、volume_ratio を計算。high/low/prev_close が NULL の場合の true_range 処理を明確に実装。
    - calc_value: raw_financials から target_date 以前の最新財務を結合して PER/ROE を算出（EPS=0/欠損時は None）。
    - 全関数とも prices_daily / raw_financials のみ参照し、本番 API へのアクセスは行わない設計。

- research パッケージの公開 API (src/kabusys/research/__init__.py)
  - calc_momentum/calc_volatility/calc_value/zscore_normalize/calc_forward_returns/calc_ic/factor_summary/rank を __all__ に登録。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- news_collector に SSRF 対策、defusedxml の使用、レスポンスサイズ制限、リダイレクト検査を導入。
- J-Quants クライアントのトークン自動リフレッシュと堅牢なエラーハンドリング（401 / 5xx / ネットワークエラーに対するリトライ）を実装。

### Notes / 注意事項
- Python 要件: 型アノテーションに | を使用しているため Python 3.10 以上を想定しています。
- DuckDB が必須のランタイム依存です（DuckDB 接続を受け取る関数が多数存在します）。
- Settings の必須環境変数（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）未設定時は起動時に ValueError を送出する箇所があります。 .env.example を参考に設定してください。
- research モジュールは外部ライブラリ（pandas など）に依存せず実装されているため、大規模データでのパフォーマンスチューニングが必要になる場合があります。
- calc_value は現時点で PBR や配当利回り等のバリューメトリクスは未実装です（TODO として明示）。
- _find_project_root がプロジェクトルートを特定できない場合は .env 自動ロードをスキップします（テスト環境等で動作）。

### Known issues / 既知の制限
- news_collector の URL 正規化/トラッキング除去は一般的なケースを想定していますが、すべてのトラッキングパラメータを網羅するものではありません。
- _to_int の実装は "1.9" のような小数文字列を None にします（意図しない切り捨て防止のため）。必要に応じて変換ポリシーを調整してください。
- 一部テーブル定義や execution 層の DDL は継続的に拡張される想定（raw_executions の定義はファイル中で途中まで実装されています）。

---

今後の予定（例）
- Execution 層（kabu ステーション連携）および monitoring 機能の実装強化。
- research のパフォーマンス改善（大規模データ向け）と追加ファクター（PBR、配当利回り等）。
- テストカバレッジ追加（特にネットワーク/SSRF/パーサ関連の堅牢性確認）。

もし特に強調したい変更点や、別バージョンのリリース履歴（Unreleased を含めた細かい差分）を望まれる場合は、追加情報を教えてください。