Keep a Changelog に準拠した CHANGELOG.md（日本語）を作成しました。ソースコードから推測できる機能追加・改善点・注意点を記載しています。

注意: 日付は本日（2026-03-21）をリリース日として使用しています。必要に応じて変更してください。

---
# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

## [Unreleased]

## [0.1.0] - 2026-03-21

### Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - エクスポート: data, strategy, execution, monitoring

- 環境設定・自動読み込み機能を追加（src/kabusys/config.py）
  - .env/.env.local ファイルまたはOS環境変数から設定をロードする自動ロード機能を実装
  - 読み込み優先順: OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）
  - プロジェクトルート判定は .git または pyproject.toml を基準に行い、__file__ を起点に探索するため CWD に依存しない
  - .env パーサは以下をサポート:
    - export KEY=val 形式
    - シングル/ダブルクォート、バックスラッシュエスケープの処理
    - インラインコメントの扱い（クォート有無で挙動を区別）
  - Settings クラスを提供（settings インスタンス）
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として取得（未設定で ValueError）
    - KABUSYS_ENV の検証（development, paper_trading, live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - データベースのデフォルトパス（DUCKDB_PATH, SQLITE_PATH）を提供
    - is_live / is_paper / is_dev 判定プロパティを提供

- データ取得・保存（J-Quants クライアント）を追加（src/kabusys/data/jquants_client.py）
  - API ベースURL、レート制限（120 req/min）を考慮した固定間隔の RateLimiter を実装
  - リトライロジック（指数バックオフ、最大 3 回）を実装（HTTP 408/429 および 5xx を対象）
  - 401 Unauthorized 受信時にリフレッシュトークンで ID トークンを自動更新して再試行（1 回のみ）
  - ページネーション対応で fetch_* 系関数を実装:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（マーケットカレンダー）
  - DuckDB への冪等保存関数を実装（ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes -> raw_prices
    - save_financial_statements -> raw_financials
    - save_market_calendar -> market_calendar
  - 型変換ユーティリティ: _to_float, _to_int（不正値を安全に None にする）

- ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）
  - RSS フィード取得・パース・前処理・DB 保存（raw_news, news_symbols 想定）を実装
  - 記事 ID の冪等化: 正規化した URL の SHA-256（先頭 32 文字）を使用
  - URL 正規化: スキーム/ホストの小文字化、トラッキングパラメータ（utm_*, fbclid 等）の除去、フラグメント削除、クエリソート
  - defusedxml を用いた安全な XML パース（XML Bomb 等への対策）
  - 最大受信バイト数制限（MAX_RESPONSE_BYTES: 10MB）を導入
  - バルク INSERT のチャンク処理で DB への負荷を抑制

- 研究（research）用モジュールを追加（src/kabusys/research）
  - factor_research.py
    - calc_momentum（mom_1m, mom_3m, mom_6m, ma200_dev）
    - calc_volatility（atr_20, atr_pct, avg_turnover, volume_ratio）
    - calc_value（per, roe：raw_financials と prices_daily を結合）
    - 設計は DuckDB の SQL ウィンドウ関数を活用し、営業日欠損を考慮するスキャン範囲バッファを導入
  - feature_exploration.py
    - calc_forward_returns（複数ホライズンの将来リターンを一括計算、ホライズン検証）
    - calc_ic（Spearman のランク相関による IC 計算、最小サンプル数判定）
    - factor_summary（count, mean, std, min, max, median）
    - rank（同順位は平均ランクで処理、丸め誤差対策に round 12 を使用）
  - research パッケージ公開 API に主要関数をエクスポート

- 特徴量エンジニアリング・パイプラインを追加（src/kabusys/strategy/feature_engineering.py）
  - 研究で算出した生ファクターを結合・ユニバースフィルタ適用・Zスコア正規化・クリップして features テーブルに UPSERT（日付単位での置換）する build_features を実装
  - ユニバースフィルタ: 最低株価（300 円）・20 日平均売買代金（5 億円）でフィルタ
  - 正規化対象カラム定義・±3 でのクリップ実装
  - トランザクション + バルク挿入で原子性を担保、エラー時はロールバック

- シグナル生成モジュールを追加（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合して最終スコア（final_score）を計算し、BUY / SELL シグナルを生成して signals テーブルに書き込む generate_signals を実装
  - デフォルト重みと閾値を定義（momentum/value/volatility/liquidity/news、閾値 0.60）
  - コンポーネントスコア計算ロジック:
    - momentum: momentum_20, momentum_60, ma200_dev をシグモイド→平均
    - value: per を 1/(1+per/20) に変換（低 PER に高スコア）
    - volatility: atr_pct の Z スコアを反転してシグモイド
    - liquidity: volume_ratio をシグモイド
    - news: ai_score をシグモイド（未登録は中立 0.5）
  - 欠損コンポーネントは中立 0.5 で補完（不当評価回避）
  - Bear レジーム判定: ai_scores の regime_score 平均が負なら Bear（ただしサンプル数閾値あり）
  - SELL 条件（現状実装）:
    - ストップロス（現在値 / avg_price - 1 < -8%）
    - final_score が threshold 未満（スコア低下）
    - SELL は BUY 処理より優先、signals の日付単位置換はトランザクションで実行
  - positions / prices_daily / features / ai_scores を参照（DuckDB）

- strategy パッケージで主要関数を公開（build_features, generate_signals）

### Changed
- （初回リリースのため該当なし）

### Fixed
- エラーハンドリングと耐障害性の向上
  - DuckDB 操作時にトランザクション（BEGIN/COMMIT/ROLLBACK）を適切に使用し、ROLLBACK 失敗時はログ出力して例外再送出
  - J-Quants API 呼び出しで JSON デコード失敗時にわかりやすい例外を投げるように改善
  - fetch/save 系で PK 欠損行をスキップし、スキップ件数を警告ログに出力

### Security
- ニュースパーサに defusedxml を採用し XML による攻撃リスクを低減
- RSS の URL 正規化とトラッキング除去により一意 ID の正当性を確保
- ニュース取得時の最大受信バイト制限（10MB）でメモリ DoS を緩和
- J-Quants クライアントでトークン自動リフレッシュ実装により認証失敗時の安全な再試行を実現
- （news_collector に SSRF/IP フィルタ等の対策を行う意図がコードに見られる。実装の有無はモジュール全体の実装状況に依存）

### Notes
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - .env.example を参考に .env を用意してください
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
- デバッグ/稼働モード:
  - KABUSYS_ENV は development / paper_trading / live のいずれか
  - LOG_LEVEL は標準的なログレベル（DEBUG/INFO/...）を指定
- design docs（StrategyModel.md, DataPlatform.md 等）に言及するコメントが多数あり、実装は仕様書に準拠する方針

---

この CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノートとして使用する際は、チーム方針やリリース手順に合わせて調整してください。必要であれば各機能に対する既知の制限（未実装のトレーリングストップや時間決済など）や、移行手順（DB スキーマやマイグレーション）を追記します。