# Changelog

すべての重要な変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

## [0.1.0] - 2026-03-19

初期リリース。

### Added
- パッケージの基本構成を追加
  - パッケージ名: kabusys（バージョン 0.1.0）
  - __all__ に data, strategy, execution, monitoring を公開

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に検索）
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート
  - .env 行パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）
  - Settings クラスを公開（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、Slack、DB パス等をプロパティで取得）
  - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）および is_live / is_paper / is_dev helper

- データ取得・保存（kabusys.data）
  - J-Quants API クライアント（data/jquants_client.py）
    - 固定間隔レートリミッタ（120 req/min）を実装
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）
    - 401 受信時に ID トークンを自動リフレッシュして 1 回リトライ
    - ページネーション対応の fetch_* 関数（株価 / 財務 / カレンダー）
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を追加。ON CONFLICT（重複）を回避する冪等実装
    - 型変換ユーティリティ（_to_float, _to_int）を追加し、不正データを安全に扱う
    - fetched_at に UTC タイムスタンプを記録（Look-ahead バイアス対策）

  - ニュース収集モジュール（data/news_collector.py）
    - RSS からの記事収集、前処理、raw_news への冪等保存を実装
    - 記事 ID の一意生成に URL 正規化後の SHA-256（先頭32文字）を使用
    - URL 正規化でトラッキングパラメータ（utm_*, fbclid 等）を除去、クエリキーソート、フラグメント削除
    - defusedxml を用いた XML パース（XML Bomb 等への対策）
    - HTTP レスポンスサイズ制限（MAX_RESPONSE_BYTES）や受信バイト上限の導入
    - SSRF 対策（HTTP/HTTPS スキーム制限 等）、バルク INSERT のチャンク化

- リサーチ（kabusys.research）
  - factor_research.py
    - Momentum / Volatility / Value（複数ファクター）を DuckDB の prices_daily / raw_financials を用いて計算
    - mom_1m / mom_3m / mom_6m / ma200_dev, atr_20 / atr_pct / avg_turnover / volume_ratio, per / roe などを提供
    - データ不足時は None を返す設計
  - feature_exploration.py
    - calc_forward_returns: 指定 horizon（デフォルト [1,5,21] 営業日）で将来リターンを一括取得
    - calc_ic: ファクターと将来リターン間のスピアマン IC（ランク相関）を実装（サンプル不足時は None）
    - factor_summary / rank: 基本統計量とタイ付きランク（平均ランク）機能

- 戦略（kabusys.strategy）
  - feature_engineering.build_features
    - research モジュールの生ファクターを取得してマージ、ユニバースフィルタ（最低株価、20日平均売買代金）を適用
    - 指定カラムを Z スコア正規化し ±3 でクリップ
    - features テーブルへ日付単位で置換（DELETE + bulk INSERT、トランザクションによる原子性）
  - signal_generator.generate_signals
    - features と ai_scores を統合し、コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出
    - final_score = 重み付き合算（デフォルト重みを定義。ユーザ指定 weights は検証・正規化）
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合、かつサンプル数閾値あり）
    - BUY/SELL シグナル生成（BUY は threshold 以上、Bear 時は BUY を抑制。SELL はストップロスやスコア低下を評価）
    - positions / prices を参照し、SELL 判定は価格欠損時はスキップするなど堅牢化
    - signals テーブルへ日付単位で置換（トランザクションとバルク挿入）

- ロギング・設計上の注記
  - 主要処理で logger に情報・警告を記録（例: ROLLBACK 失敗、価格欠損、無効な weights のスキップ等）
  - 外部発注 API への直接依存なし（execution 層への依存を分離）

### Changed
- （初期リリースにつき特になし）

### Fixed
- （初期リリースにつき明示的なバグ修正履歴はなし。実装時に想定される堅牢化を多数反映）
  - DuckDB への挿入で PK 欠損行をスキップして警告を出すようにし、不正データによる障害を防止
  - .env 読み込み失敗時に warnings.warn で通知するようにしてハードクラッシュを回避

### Security
- XML パースに defusedxml を採用して XML-related 脅威（XML Bomb 等）を軽減
- ニュース収集での URL 正規化とスキーム検証により SSRF のリスクを低減
- API クライアントでトークンを安全にリフレッシュし、認証失敗時の再試行制御を明示

### Performance
- J-Quants API 呼び出しに固定間隔レートリミッタを導入（120 req/min）
- API 再試行で指数バックオフを採用
- DuckDB へのバルク挿入とトランザクション（BEGIN/COMMIT）を使用して挿入コストを削減
- news_collector のバルク INSERT をチャンク化して SQL 長・パラメータ数の上限を回避

### Notes / Limitations
- 一部の戦略条件（例: トレーリングストップ、時間決済）は positions テーブルに追加情報（peak_price, entry_date 等）が必要なため未実装
- 外部依存を極力減らす設計のため、pandas 等は使用していない（標準ライブラリ + duckdb）
- calc_forward_returns のスキャン範囲は営業日を考慮した経験則（カレンダーバッファ）を用いているが、万一のデータ欠損は None を返す

もしリリースノートに追記してほしい点（例: 日付、導入方針、既知の問題、サンプル使用方法など）があれば教えてください。必要に応じてバージョン別のより詳細な項目分割も作成できます。