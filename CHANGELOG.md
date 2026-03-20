# CHANGELOG

すべての注目すべき変更履歴を記録します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。

フォーマットの意味:
- Added: 新規機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated: 非推奨
- Removed: 削除
- Security: セキュリティ関連の修正

※以下の履歴は、提供されたソースコードから実装内容・設計意図を推測して作成しています。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-03-20

### Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py）

- 設定・環境変数管理モジュールを追加（kabusys.config）
  - .env ファイルまたは OS 環境変数から設定値を読み込む自動読み込み機構を実装
  - プロジェクトルート判定ロジックを導入（.git または pyproject.toml を基準）
  - .env / .env.local の読み込み優先度: OS 環境変数 > .env.local > .env
  - 読み込み無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート
  - export プレフィックス対応、クォート内エスケープ、行内コメント処理を備えた .env パーサ実装
  - 必須環境変数取得ヘルパー _require と Settings クラスを提供
  - 設定プロパティ例:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（値検証）

- データ取得・保存（J-Quants）クライアントを追加（kabusys.data.jquants_client）
  - API 呼び出しラッパー _request を実装（JSON デコード、エラーハンドリング）
  - レート制限（120 req/min）を守る固定間隔スロットリング _RateLimiter を実装
  - 再試行ロジック（指数バックオフ、最大3回）と 401 時の自動トークンリフレッシュ対応
  - ページネーション対応の fetch_* 関数を実装:
    - fetch_daily_quotes（株価日足 / OHLCV）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（市場カレンダー）
  - DuckDB への冪等保存関数を実装:
    - save_daily_quotes（raw_prices, ON CONFLICT DO UPDATE）
    - save_financial_statements（raw_financials, ON CONFLICT DO UPDATE）
    - save_market_calendar（market_calendar, ON CONFLICT DO UPDATE）
  - データ加工ユーティリティ (_to_float, _to_int)、UTC fetched_at 記録を導入
  - モジュールレベルの ID トークンキャッシュを実装（ページネーション間でトークン共有）

- ニュース収集モジュールを追加（kabusys.data.news_collector）
  - RSS フィード取得・記事整形・raw_news への冪等保存の仕組み（設計文書に基づく）
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保
  - トラッキングパラメータ（utm_*, fbclid 等）除去、クエリソート、フラグメント除去などの URL 正規化実装
  - defusedxml による XML パース、安全対策（XML Bomb 等）を考慮
  - HTTP レスポンスサイズ上限（MAX_RESPONSE_BYTES）や受信スキームの検査などメモリ / SSRF 対策
  - バルク INSERT のチャンク処理 (CHUNK_SIZE) とトランザクションによる原子的保存

- 研究（research）モジュール群を追加（kabusys.research）
  - feature_exploration:
    - calc_forward_returns（任意ホライズンの将来リターンを一度の DuckDB クエリで取得）
    - calc_ic（ファクターと将来リターンの Spearman ランク相関を計算）
    - factor_summary（基本統計量: count/mean/std/min/max/median）
    - rank（同順位は平均ランクにするランク変換、丸めによる ties 対策）
    - 標準ライブラリのみで実装（pandas 等に依存しない設計）
  - factor_research:
    - calc_momentum（mom_1m/mom_3m/mom_6m, ma200_dev の算出）
    - calc_volatility（atr_20, atr_pct, avg_turnover, volume_ratio の算出）
    - calc_value（per, roe の算出。raw_financials の最新レコードを利用）
    - DuckDB のウィンドウ関数（LAG/AVG/COUNT 等）を活用した効率的な実装
    - データ不足時の None ハンドリング（ウィンドウサイズ未満等）

- 戦略（strategy）モジュール群を追加（kabusys.strategy）
  - feature_engineering.build_features:
    - research の raw ファクターを取り込み、ユニバースフィルタ（最低株価・平均売買代金）適用
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）し ±3 でクリップ
    - features テーブルへの日付単位の置換（DELETE → INSERT、トランザクションで原子性を保証）
    - ルックアヘッドバイアス回避設計（target_date 時点のデータのみ使用）
  - signal_generator.generate_signals:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
    - シグモイド変換、欠損コンポーネントは中立値 (0.5) で補完
    - デフォルト重みを提供し、ユーザー指定の重みを妥当性検査・再スケール
    - Bear レジーム検知（ai_scores の regime_score 平均が負なら BUY を抑制）
    - BUY（threshold ベース）および SELL（ストップロス・スコア低下）シグナル生成
    - positions / prices_daily を参照したエグジット判定（SELL ロジック）
    - signals テーブルへの日付単位の置換（トランザクション／バルク挿入）
    - ログ出力による挙動トレース（info/warning/debug）

- パッケージのエクスポートを明示
  - kabusys.strategy.__all__ に build_features / generate_signals を追加
  - kabusys.research.__all__ に主な研究ユーティリティを追加

### Changed
- なし（初期リリース）

### Fixed
- なし（初期リリース）

### Security
- ニュース収集において defusedxml を利用し XML 攻撃から保護
- URL 正規化でスキーム検査を想定し、SSRF リスクを低減する方針を導入
- J-Quants クライアントはトークンの自動リフレッシュと厳格な再試行制御を実装

### Known issues / Notes
- signal_generator のトレーリングストップや時間決済（長期保有の自動クローズ）は未実装（positions テーブル側で peak_price / entry_date 等の追加が必要）
- 一部のユーティリティ（kabusys.data.stats.zscore_normalize など）は本履歴作成時に参照されているが、ここに示したコードスニペットでは未表示（別ファイルに実装されている想定）
- news_collector の URL / HTTP 検証ロジックは設計意図を示すコメントがあるが、追加のホワイトリスト/ブラックリスト要件次第で実装拡張が必要
- DuckDB スキーマ（tables / PK / ON CONFLICT の定義）は本コードから参照される想定であり、運用前にスキーマ整備が必要

---

作成: kabusys コードベースの初期リリース（機能追加を中心に推測して記載）