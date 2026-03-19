# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
初版リリース (v0.1.0) における主要な機能・設計上の決定・既知の制約をコードベースから推測して記載しています。

格式:
- 変更履歴はセクション別に整理（Added / Changed / Fixed / Security / Known limitations / Migration notes）
- 各項目は該当モジュール名と概要を日本語で記載

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-19
初回公開リリース。以下の機能セットと設計方針を実装。

### Added
- 基本パッケージ
  - パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py）
  - パブリックサブパッケージ: data, strategy, execution, monitoring をエクスポート

- 設定・環境変数管理（src/kabusys/config.py）
  - .env/.env.local ファイルと OS 環境変数の読み込み自動化（プロジェクトルートを .git / pyproject.toml から検出）
  - .env パーサー実装（コメント・export 前置・クォート内エスケープ・インラインコメント処理に対応）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - OS 環境変数を保護するための protected 上書き制御（.env.local は既存 OS 変数を上書きしない設定も可能）
  - 必須環境変数の取得ユーティリティ（_require）と Settings クラス
  - 検証機能: KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/INFO/...） の値チェック
  - DB パス設定：DUCKDB_PATH / SQLITE_PATH の既定値

- データ取得・保存（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアント（認証・ページネーション・データ取得関数）
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter 実装
  - リトライロジック: 指数バックオフ、最大試行回数 3 回、408/429/5xx を対象にリトライ
  - 401 応答時のトークン自動リフレッシュ（1 回のみ）と再試行
  - ページネーション対応の fetch_* 関数:
    - fetch_daily_quotes (日足)
    - fetch_financial_statements (財務)
    - fetch_market_calendar (マーケットカレンダー)
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes → raw_prices
    - save_financial_statements → raw_financials
    - save_market_calendar → market_calendar
  - 保存時に fetched_at を UTC (Z) で記録
  - レスポンス変換ユーティリティ: _to_float / _to_int（不正値や空文字を安全に None に）

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード収集と raw_news への冪等保存（記事ID は正規化 URL の SHA-256 ハッシュ先頭を利用）
  - URL 正規化（スキーム/ホストの小文字化、tracking パラメータ除去、フラグメント除去、クエリソート）
  - defusedxml を使った XML パース（XML Bomb 対策）
  - HTTP 応答サイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 対策
  - SSRF / 不正 URL に対する防御方針（スキーム制限などを想定）
  - バルク INSERT のチャンク化（_INSERT_CHUNK_SIZE）で SQL 長上限対策
  - デフォルト RSS ソースとして Yahoo ビジネスカテゴリを設定

- 研究用ファクター計算（src/kabusys/research/factor_research.py）
  - momentum / volatility / value ファクター計算関数:
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200 日データ判定を含む）
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（ATR の NULL 伝播制御等）
    - calc_value: per, roe（raw_financials の最新レコードを参照）
  - DuckDB 上の prices_daily / raw_financials を用いた完全スタンドアロン実装（外部 API へアクセスしない）

- 研究支援ユーティリティ（src/kabusys/research/feature_exploration.py）
  - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD により一括取得。horizons のバリデーションを実施
  - calc_ic: スピアマンランク相関 (Information Coefficient) の計算（結合・無効値フィルタ・最小サンプル判定）
  - rank: 同順位は平均ランクとするランク関数（浮動小数点の丸めで ties を安定化）
  - factor_summary: 各ファクター列について count/mean/std/min/max/median を計算

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features: research 側の生ファクターを統合・ユニバースフィルタ・Z スコア正規化・±3 clip・features テーブルへ日付単位で UPSERT（トランザクションで原子性）
  - ユニバースフィルタ: 株価 >= 300 円、20 日平均売買代金 >= 5 億円
  - 正規化対象カラムの明示化と外れ値クリップ

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals: features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを生成して signals テーブルへ日付単位で置換保存
  - スコア計算:
    - コンポーネント: momentum, value, volatility, liquidity, news（デフォルト重みを実装）
    - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完
    - ユーザー指定 weights の検証・合成・正規化（負値/NaN/非数は無視）
  - Bear レジーム判定: ai_scores の regime_score 平均が負なら Bear（サンプル閾値あり）
  - BUY シグナル閾値（デフォルト 0.60）、Bear 時は BUY を抑制
  - SELL（エグジット）判定:
    - ストップロス: 現在終値/avg_price - 1 <= -8% を最優先
    - final_score < threshold の場合は売り
    - 価格欠損時は SELL 判定をスキップして誤クローズを回避
  - signals テーブルへの原子置換（トランザクション + バルク挿入）

- モジュール間エクスポート整備
  - src/kabusys/research/__init__.py と src/kabusys/strategy/__init__.py による主要関数の再エクスポート（研究・戦略 API を明示）

### Changed
- （初版につき該当なし）

### Fixed
- （初版につき該当なし）

### Security
- RSS パーサーに defusedxml を利用（XML 脆弱性対策）
- ニュース収集における URL 正規化・トラッキング除去・スキーム制限・受信サイズ制限等の考慮
- J-Quants クライアントでの認証トークン管理において token refresh の無限再帰を回避（allow_refresh フラグ）
- ネットワークエラー / HTTP エラー時に安全にリトライし、429 の Retry-After を考慮

### Known limitations / Notes
- DB スキーマの前提
  - 本実装は以下のテーブル構造を前提に動作（例示）:
    - raw_prices, raw_financials, market_calendar, features, ai_scores, positions, signals, raw_news
  - 実際のスキーマ定義は別途用意する必要あり
- 未実装のエグジット条件
  - トレーリングストップ（peak_price が positions に必要）
  - 時間決済（保有期間 60 営業日超）
- News collector の SSRF / IP 検査等の具体実装（ipaddress / socket をインポートしているが、コード全体での適用箇所は将来拡張の余地あり）
- 一部ユーティリティ（zscore_normalize 等）は kabusys.data.stats に依存し、その実装は本差分では提示されていない
- calc_forward_returns のスキャン範囲は「営業日 ≒ カレンダー日×2」を仮定しており、極端な欠損市場では調整が必要

### Migration notes (導入時の注意)
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID の設定が必要（Settings が ValueError を投げる）
- .env 自動ロード:
  - プロジェクトルートは .git または pyproject.toml により検出。配布後やテスト時に自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- DB ファイルパス:
  - デフォルトの DUCKDB_PATH= data/kabusys.duckdb, SQLITE_PATH= data/monitoring.db を使用するか環境変数で上書き
- J-Quants API の利用:
  - API レート制限と認証トークンの取得（get_id_token）の流れを理解の上で運用すること
- signals / positions 等の運用:
  - execution 層（発注・実注文）は本リリースでは独立しており、signals テーブルに書き込むだけで自動発注は行われない設計

### Contributors
- 初期実装（コードベース）に基づく推定のため、実際の貢献者情報はソース管理履歴を参照してください。

---

今後のリリース案（想定）
- データ品質向上: raw_prices/raw_financials のバリデーション強化
- execution 層との連携実装（発注 API のラッパー、注文管理、トレーリングストップ）
- monitoring サービスの追加（Slack 通知や DB のメトリクス収集）
- NewsCollector の NLP 前処理 / 銘柄マッピング精度改善

必要があれば、上記 CHANGELOG の英語版作成、あるいは各モジュールごとのより細かい欄（例: 実装した関数ごとにサンプル入出力、想定スキーマ）を追記します。どのレベルの詳細が必要か教えてください。