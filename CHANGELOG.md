# Changelog

すべての注目すべき変更点をここに時系列で記録します。  
このファイルは Keep a Changelog の慣例に準拠しています。

現在のバージョン: 0.1.0

## [Unreleased]
- 今後の変更点をここに記載します。

## [0.1.0] - 2026-03-19
初回公開リリース。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__init__ に __version__ = "0.1.0"、公開 API を __all__ で定義）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索するため、CWD に依存しない動作を実現。
  - .env のパースにおいて以下に対応：
    - 空行・コメント（#）対応
    - export KEY=val 形式対応
    - シングル/ダブルクォート、バックスラッシュによるエスケープ処理
    - クォートなしの行では '#' の直前が空白またはタブのときのみインラインコメント扱い
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - settings オブジェクトを提供。各種必須項目（J-Quants トークン、Kabu API パスワード、Slack トークン/チャンネル等）、デフォルト値（API ベース URL、DB パス等）および検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）を実装。

- データ収集（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - 固定間隔のスロットリングによるレート制限（120 req/min）を実装（内部 RateLimiter）。
    - 再試行機構（指数バックオフ、最大 3 回）を実装。対象はネットワーク系エラーや 408/429/5xx。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライするロジックを追加（無限再帰防止）。
    - ページネーション対応（pagination_key を用いた繰り返し取得）。
    - fetch_* 系関数: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
    - DuckDB 保存関数: save_daily_quotes / save_financial_statements / save_market_calendar を実装し、冪等性のため ON CONFLICT / DO UPDATE ロジックで重複を処理。
    - レスポンスの JSON デコードエラーやネットワークエラーに対する詳細なログと例外ハンドリングを実装。
    - fetched_at を UTC ISO8601 で記録し、Look-ahead バイアス追跡を可能に。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュースを取得して前処理し raw_news へ保存する機能を実装。
    - URL 正規化（小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソートなど）。
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）を利用して冪等性を確保。
    - defusedxml を用いた XML パースでセキュリティ対策（XML Bomb 等）を考慮。
    - 最大受信サイズ制限（MAX_RESPONSE_BYTES = 10 MiB）を導入してメモリ DoS を緩和。
    - DB 向けのバルク INSERT チャンク処理を実装（チャンクサイズ制限）。
    - デフォルト RSS ソースを追加（例: Yahoo Finance のカテゴリ RSS）。

- リサーチ / ファクター計算
  - factor_research モジュールを実装（モメンタム、ボラティリティ、バリュー、流動性の各ファクター）。
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR / 相対 ATR (atr_pct)、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播制御によりカウント精度を保持。
    - calc_value: raw_financials から直近財務データを取得し PER / ROE を算出（EPS が 0 の場合は PER を None）。
  - feature_exploration モジュールを実装（将来リターン calc_forward_returns、IC 計算 calc_ic、統計サマリー factor_summary、rank ユーティリティ）。
    - calc_forward_returns は単一クエリで複数ホライズンの将来リターンを取得。
    - calc_ic はスピアマンのランク相関を実装（有効サンプルが 3 未満の場合は None）。
    - rank / factor_summary は外部依存なしで基本統計量・ランク処理を提供。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features を実装。
    - research 層の生ファクターを取得（calc_momentum, calc_volatility, calc_value を利用）。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定列の Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへ日付単位で置換（BEGIN/DELETE/INSERT/COMMIT。失敗時は ROLLBACK の試行）し冪等性を担保。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals を実装。
    - features と ai_scores を統合して各銘柄のコンポーネント（momentum/value/volatility/liquidity/news）スコアを計算。
    - デフォルト重みとユーザー指定 weights のマージ・検証・再スケーリング処理を実装（未知キーや不正値は無視）。
    - final_score を算出し、閾値（デフォルト 0.60）超で BUY シグナルを生成（Bear レジーム時は BUY を抑制）。
    - Bear 判定は ai_scores の regime_score 平均が負かつサンプル数が閾値以上で判定。
    - エグジット判定（_generate_sell_signals）を実装（ストップロス -8% 優先、スコア低下で SELL）。保有ポジションに価格が取得できない場合は判定をスキップ。
    - signals テーブルへ日付単位の置換で書き込み（トランザクション処理）。

- パブリック API 整備
  - kabusys.strategy パッケージから build_features / generate_signals を公開。
  - kabusys.research パッケージに主要ユーティリティ（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）をエクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- news_collector で defusedxml を利用し XML パース時の既知攻撃に対処。
- API クライアントでタイムアウト・再試行・トークンリフレッシュ等の耐障害性を実装し、ネットワーク例外や認証失敗に対する堅牢性を向上。

### Notes / Known limitations / TODO
- execution パッケージは存在するが（src/kabusys/execution/__init__.py）現時点では実装は含まれていません（発注レイヤーは未実装）。
- signals の運用にあたり positions テーブルに peak_price / entry_date 等の情報が必要な一部のエグジット条件（トレーリングストップ、保有日数による時間決済）は未実装で注記あり。
- news_collector の一部セキュリティ対策（SSRF/IP の拒否など）はモジュール内で考慮するためのインポートと定数が用意されているが、完全な実装は継続して進める必要があります（実装状況はソースを参照してください）。
- jquants_client の _request は urllib を使用しており、将来的に HTTP クライアント（requests 等）への移行や接続プーリングを検討すると性能改善の余地があります。
- settings に定義されている必須環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID）を設定しないと ValueError が発生します。README/.env.example を参照してセットアップしてください。
- DuckDB スキーマ（tables: raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar 等）は本 CHANGELOG に含まれていません。初期セットアップ手順・DDL は別途ドキュメントを参照してください。

---

このリリースはシステム全体のデータ取得・保存、因子計算、特徴量作成、シグナル生成の主要なワークフローを含む初期実装を提供します。今後は execution（発注）層の実装、監視・モニタリング機能の強化、追加のファクター・リスク管理ロジックの充実を予定しています。