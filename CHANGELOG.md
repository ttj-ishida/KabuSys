# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-21

初回リリース。本リポジトリは日本株自動売買システムのコアライブラリ群（データ取得・保存、ファクター計算、特徴量生成、シグナル生成、リサーチユーティリティ、設定管理、ニュース収集）を提供します。

### Added
- パッケージ基礎
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` に設定。
  - モジュール公開: data, strategy, execution, monitoring（execution はパッケージ存在）。
- 設定・環境変数管理（kabusys.config）
  - .env ファイル自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。（環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロード無効化可）
  - .env パースの実装強化:
    - コメント行・空行スキップ、`export KEY=val` 形式への対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを処理。
    - クォートなし値のインラインコメント判定（直前がスペース/タブの場合のみ）。
  - 上書き動作制御: `_load_env_file(..., override, protected)` により OS 環境変数を保護して上書き可否を制御。
  - Settings クラスを提供し、アプリケーションから安全に設定値へアクセス可能（必須キーは未設定時に ValueError を投げる）。
  - 主要環境変数（例）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアント実装:
    - 固定間隔レートリミッタ（120 req/min）実装。
    - 再試行（最大3回）+ 指数バックオフ、HTTP 408/429/5xx をリトライ対象。
    - 401 の際は自動トークンリフレッシュ（1回）して再試行。
    - ページネーション対応（pagination_key）。
    - 取得時刻（fetched_at）を UTC ISO8601 で記録し、look-ahead バイアスの追跡を可能に。
  - DuckDB への保存ユーティリティ:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。PK 欠損行はスキップし警告ログを出力。
    - 冪等性を確保するため INSERT ... ON CONFLICT DO UPDATE（重複更新）で保存。
  - 型変換ユーティリティ `_to_float`, `_to_int` を追加（安全な変換・不正データの扱いを明示）。
- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）:
    - Momentum（mom_1m/mom_3m/mom_6m）, MA200 乖離率（ma200_dev）計算。
    - Volatility（20日 ATR / atr_pct）, 20日平均売買代金（avg_turnover）, 出来高比率（volume_ratio）計算。
    - Value（per, roe）: raw_financials の最新財務データを参照して算出。
    - DuckDB + ウィンドウ関数を用いた効率的な実装。データ不足時は None を返す挙動を採用。
  - 研究用ユーティリティ（kabusys.research.feature_exploration）:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: スピアマンランク相関（IC）を実装。サンプル数不足（<3）の場合は None。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクにするランク付けユーティリティ（丸め誤差対策で round(...,12) を使用）。
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date):
    - research の calc_momentum / calc_volatility / calc_value から生ファクターを取得。
    - ユニバースフィルタを実装（最低株価 300 円、20日平均売買代金 5 億円）。
    - 指定カラムの Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップして外れ値影響を抑制。
    - DuckDB の features テーブルへ日付単位で置換（DELETE + bulk INSERT）して冪等性・原子性を保証（トランザクション使用）。
- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features, ai_scores, positions テーブルを参照して BUY / SELL シグナルを生成し signals テーブルへ日付単位で置換保存。
    - コンポーネントスコア: momentum, value, volatility, liquidity, news を計算（シグモイド変換等）。
    - AI スコアは未登録時に中立（0.5）で補完。欠損コンポーネントも中立値で補完して公平性を保つ。
    - 重み（weights）はデフォルト値を用い、不正な入力はスキップ。合計が 1.0 でなければ再スケール。
    - Bear レジーム判定（ai_scores の regime_score 平均が負のとき、サンプル数制限あり）で BUY を抑制。
    - SELL（エグジット）ロジック:
      - ストップロス（終値ベースで -8% 以下）を最優先。
      - final_score が閾値未満の場合も SELL。
      - SELL 優先ポリシー: SELL 対象は BUY から除外し、BUY のランクは再付与。
    - トランザクション + bulk INSERT により signals テーブルの置換を原子化。
  - 設計上の未実装項目（ドキュメントに明記）:
    - トレーリングストップ（peak_price / entry_date が positions に必要）
    - 時間決済（保有 60 営業日超の自動決済）
- ニュース収集（kabusys.data.news_collector）
  - RSS ベースのニュース収集機能を実装（デフォルトソース: Yahoo Finance のカテゴリ RSS）。
  - セキュリティ強化:
    - defusedxml を用いた XML パース（XML Bomb 等の防止）。
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ（utm_*, fbclid, gclid 等）削除、フラグメント削除、クエリパラメータをキー順ソート。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）を設けてメモリ DoS を防止。
    - HTTP/HTTPS 以外の URL を拒否して SSRF をある程度抑止する方針（実装コメントとして記載）。
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）を用いることで冪等性を確保。
  - DB へのバルク挿入（チャンクサイズ）・1 トランザクションでの保存・INSERT RETURNING 相当の考慮を行う実装方針。

### Fixed
- J-Quants クライアント:
  - HTTP エラー時のリトライ挙動（429 の Retry-After を優先）やネットワークエラーの再試行ロジックを整備して安定性を向上。
- DuckDB への保存:
  - PK 欠損行をスキップして処理を続行し、ログで件数を通知することで不正データによる処理停止を回避。

### Security
- ニュース収集で defusedxml を使用し XML パーサ攻撃に備えた。
- RSS の処理で受信サイズ上限を設け、URL 正規化でトラッキングパラメータを除去、HTTP スキームの検証を行う方針を採用。
- J-Quants クライアントはトークンの自動リフレッシュとレート制御を実装し、不正な再帰やトークン漏洩リスクを抑制する設計。

### Known limitations / Notes
- signals のエグジット条件で記載されているトレーリングストップや時間決済は未実装。positions テーブルに peak_price / entry_date を保持するスキーマ拡張が必要。
- news -> 銘柄コード紐付け（news_symbols）ロジックは設計に含まれるが、本実装の一部は研究/後続実装を想定。
- 一部ユーティリティ（zscore_normalize 等）は別モジュール（kabusys.data.stats）に依存しているため、その実装が必要。
- DB スキーマの前提テーブル（例: raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals, raw_news 等）をプロジェクト側で用意する必要あり。
- .env 自動ロードはプロジェクトルート検出に依存するため、配布後や異なる配置での動作を確認してください（必要に応じ KABUSYS_DISABLE_AUTO_ENV_LOAD を使用）。

### Migration / Usage tips
- 環境変数の必須項目を設定してください（特に JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。未設定で Settings の該当プロパティにアクセスすると ValueError が発生します。
- デフォルトの DB パス: DUCKDB_PATH=data/kabusys.duckdb、SQLITE_PATH=data/monitoring.db。必要に応じ環境変数で上書きしてください。
- J-Quants API を利用する際は API 利用制限（120 req/min）を考慮して運用してください（内部で RateLimiter を適用しています）。
- シグナル生成の重みや閾値は generate_signals の引数で上書き可能ですが、不正値は無視されデフォルト重みにフォールバックします。

---

今後の予定（短期ロードマップ）:
- positions スキーマ拡張とトレーリングストップ・時間決済の実装。
- news と銘柄紐付け（正規表現 / NER）実装。
- monitoring / execution 層の実装（発注 API 統合、オーダー管理）。
- 単体テスト・統合テストの充実。