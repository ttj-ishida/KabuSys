# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
リリースは安定した API と内部設計を示す初回公開バージョン 0.1.0 を想定して記載しています（コードベースから推測）。

## [Unreleased]
- 特になし（初回リリースが 0.1.0 のため未リリース項目はありません）。

## [0.1.0] - 2026-03-20
初回公開リリース。日本株自動売買システムのコア機能群を含むモジュール群を提供します。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージの公開 API を定義（kabusys.__init__）。
  - モジュール構成: data, strategy, execution（空シェル含む）, research, monitoring（エクスポート設定）。

- 設定管理（kabusys.config）
  - .env / .env.local 自動読み込み機能（プロジェクトルートを .git / pyproject.toml で検出）。
  - .env パーサー: コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラス: 必須環境変数取得（_require）、各種プロパティを提供：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID の必須チェック
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH のデフォルト値
    - KABUSYS_ENV (development / paper_trading / live) と LOG_LEVEL 検証
    - is_live / is_paper / is_dev の便宜プロパティ

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアント実装:
    - 固定間隔のレートリミッタ（120 req/min）を実装。
    - リトライ（指数バックオフ、最大 3 回）。対象はネットワーク系と一部 HTTP ステータス（408, 429, 5xx）。
    - 401 発生時はリフレッシュトークンを使った ID トークン自動リフレッシュを 1 回行い再試行。
    - ページネーション対応の fetch_* API（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - 取得時刻（fetched_at）を UTC ISO で記録し、Look-ahead バイアスのトレースを可能にする設計方針を反映。
  - DuckDB への保存ユーティリティ:
    - save_daily_quotes, save_financial_statements, save_market_calendar を提供。いずれも冪等（ON CONFLICT DO UPDATE / DO NOTHING）で保存。
    - 型変換ユーティリティ _to_float / _to_int を実装し、異常データを安全に扱う。
    - PK 欠損行はスキップし、スキップ件数をログに出力。

- ニュース収集（kabusys.data.news_collector）
  - RSS から記事を収集して raw_news に保存する処理の実装方針とユーティリティを追加。
  - セキュリティ上の配慮を実装（defusedxml を用いた XML パース、安全な URL 検証、受信サイズ上限）。
  - URL 正規化（トラッキングパラメータ削除、キーソート、スキーム/ホスト小文字化、フラグメント削除）。
  - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を確保。
  - バルク挿入のチャンク処理、INSERT RETURNING を想定した最適化設計。

- ファクター計算・リサーチ（kabusys.research）
  - factor_research モジュール:
    - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials テーブルのみを参照する設計。
    - 各関数は date, code をキーとする dict リストを返す。欠損・データ不足時は None を返す設計。
    - momentum: 1M/3M/6M リターン、200 日移動平均乖離率（データ不足チェックあり）。
    - volatility: 20 日 ATR / 相対 ATR (atr_pct)、20 日平均売買代金、出来高比率等。
    - value: PER（EPS が無効な場合は None）、ROE（最新開示データを target_date 以前から取得）。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（1 クエリで効率取得）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算。サンプル不足（<3）時は None。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - rank: 同順位の平均ランクを返す実装（小数丸めによる ties 対応）。

- 特徴量生成（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date):
    - research の生ファクター calc_momentum / calc_volatility / calc_value を組み合わせ、ユニバースフィルタ（最低価格 300 円、20 日平均売買代金 5 億円）を適用。
    - 正規化: zscore_normalize を利用し指定列を Z スコア化、±3 でクリップ（外れ値抑制）。
    - 日付単位で features テーブルへ冪等に UPSERT（DELETE→INSERT のトランザクション）で保存。
    - DuckDB を前提とした SQL を使用（prices_daily 等参照）。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features と ai_scores を統合し、momentum / value / volatility / liquidity / news のコンポーネントスコアを計算。
    - シグモイド変換・欠損値は中立（0.5）で補完。重みはデフォルト値でフォールバックし、ユーザ指定は検証・再スケールして適用。
    - Bear レジーム判定: ai_scores の regime_score 平均が負の場合を Bear（ただしサンプル数閾値あり）。
    - BUY シグナルは threshold を超えた銘柄（Bear 時は BUY を抑制）。SELL シグナルはストップロス（-8%）およびスコア低下で判定。
    - 保有銘柄の SELL は BUY から除外し、SELL 優先でランク再付与。
    - 日付単位で signals テーブルへ冪等に書き込み（トランザクション）。

### Changed
- （初回リリースにつき既存バージョンからの差分はありませんが）設計方針・注意点を明示化:
  - Look-ahead バイアス防止のため取得時刻/fetched_at の記録と target_date 時点のデータのみを参照する方針。
  - DuckDB を中心としたデータフロー（raw_prices/raw_financials → prices_daily / features / ai_scores / positions → signals）。
  - 外部依存を最小限（research の一部関数は標準ライブラリのみ）に留める方針。

### Fixed
- 該当なし（初回リリース）。

### Security
- news_collector で defusedxml を使用し XML パースに対する攻撃（XML Bomb など）を防止。
- RSS 処理で受信バイト数上限を設け、メモリ DoS を緩和。
- URL 正規化・スキーム検証により SSRF リスクを低減。
- jquants_client の HTTP エラー処理で 401 リフレッシュ時の無限再帰を回避する制御（allow_refresh フラグ）。

### 注意・移行メモ
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を設定する必要があります。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト等で自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB 側の期待スキーマ（テーブル名 / カラム）はソース内 SQL に依存します。初期化スキーマ（raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar, raw_news 等）が必要です。
- jquants_client のレート制限・リトライや news_collector の受信制限などは運用時の API 制約に合わせて調整可能です。
- Signal/Feature のアルゴリズムや閾値（例: threshold=0.60、STOP_LOSS_RATE=-0.08、ユニバース基準など）は StrategyModel.md 等に準拠した設計であり、今後の実運用にあわせてパラメータのチューニングが想定されます。

---

開発・運用上の補足やリリースノート追記希望があれば、対象箇所（例: 重要な設計決定、DB スキーマ、環境変数の一覧）を指定してください。必要に応じてより詳細な「移行手順」や「データベーススキーマ草案」も作成できます。