# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従い記載しています。

最新版: 0.1.0 — 2026-03-20

## [0.1.0] - 2026-03-20

初回リリース。パッケージ「kabusys」の基礎機能を実装しました。主な追加点・設計方針は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - パッケージルート: src/kabusys/__init__.py にバージョン `0.1.0` を追加し、公開 API を定義（data, strategy, execution, monitoring）。
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込み。
  - 自動ロード優先度: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .git または pyproject.toml を基準にプロジェクトルートを探索（パッケージ配布後も CWD に依存せず動作）。
  - .env のパース実装:
    - コメント、export プレフィックス、クォート内のエスケープ、インラインコメントなどに対応。
  - 必須設定取得用 _require()（設定未定義時に ValueError を送出）。
  - Settings クラスで各種設定値をプロパティとして取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などの必須値。
    - KABU_API_BASE_URL / DUCKDB_PATH / SQLITE_PATH 等のデフォルト値。
    - KABUSYS_ENV / LOG_LEVEL の検証（許可値の検査）と利便性プロパティ（is_live / is_paper / is_dev）。
- データ取得・保存 (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装（ページネーション対応）。
  - レート制御: 固定間隔スロットリングで 120 req/min を順守（_RateLimiter）。
  - 再試行ロジック: 指数バックオフ（最大 3 回）、HTTP 408/429/5xx を再試行対象に。
  - 401 応答時はトークンを自動リフレッシュして 1 回リトライ（無限再帰を防止）。
  - モジュールレベルの ID トークンキャッシュを実装しページ間で共有。
  - fetch_* 系（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）はページネーションを安全に処理。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）:
    - 冪等化（ON CONFLICT DO UPDATE / DO NOTHING）を採用。
    - PK 欠損レコードはスキップし警告ログ出力。
    - 保存時に fetched_at（UTC）を付与。
  - 入力変換ユーティリティ _to_float / _to_int を提供（不正値は None に正しく変換）。
- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィード収集モジュールを追加（デフォルトは Yahoo Finance のビジネス RSS）。
  - URL 正規化（小文字化、トラッキングパラメータ除去、フラグメント除去、クエリのキーソート）。
  - defusedxml による XML パース（XML Bomb 等への対策）。
  - 応答サイズ上限（MAX_RESPONSE_BYTES = 10MB）を想定。
  - 挿入はバルクチャンク（_INSERT_CHUNK_SIZE）で処理し、DB 負荷を抑制。
  - 設計として記事 ID を正規化 URL の SHA-256 ハッシュで生成し冪等性を確保する方針（説明コメントに記載）。
- リサーチ / ファクター計算 (src/kabusys/research/)
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、volume_ratio を計算。
    - calc_value: 最新の raw_financials を参照して PER/ROE を計算（EPS が無効な場合は None）。
    - 各関数は DuckDB の prices_daily / raw_financials テーブルのみを参照する設計。
  - feature_exploration.py:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度の SQL クエリで取得。
    - calc_ic: スピアマンのランク相関（IC）を計算（有効サンプル数 < 3 の場合は None）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー関数。
    - rank: 同順位は平均ランクとするランク関数（round(...,12) を用いて丸めて ties を安定化）。
  - research/__init__.py で主要関数群を公開。
- 特徴量作成（Strategy） (src/kabusys/strategy/feature_engineering.py)
  - build_features(conn, target_date):
    - research の calc_momentum / calc_volatility / calc_value を用いてファクターを取得。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用。
    - 数値ファクターを zscore_normalize（data.stats 由来）で標準化し ±3 でクリップ。
    - features テーブルへ日付単位で置換（DELETE → INSERT をトランザクションで行い原子性を保証）。処理は冪等。
- シグナル生成（Strategy） (src/kabusys/strategy/signal_generator.py)
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features と ai_scores を読み込み、component スコア（momentum/value/volatility/liquidity/news）を計算。
    - シグモイド変換や欠損コンポーネントの中立補完（0.5）を採用して final_score を算出。
    - weights のバリデーション・補完・リスケール（既知キーのみ受け付け、非数値や負値は無視）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負：BUY を抑制）。サンプル不足時は Bear とみなさない。
    - BUY シグナル閾値（デフォルト 0.60）を超えた銘柄に BUY、保有ポジションに対してはエグジット判定で SELL（stop_loss: -8% など）。
    - SELL が決まった銘柄は BUY から除外し、signals テーブルへ日付単位で置換（原子性）。
    - トランザクションの失敗時は ROLLBACK を試行しログ出力。
- 研究 API の公開（src/kabusys/research/__init__.py）と戦略公開（src/kabusys/strategy/__init__.py）

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）。ただし、各モジュールに堅牢性向上のための検証・例外処理・ログ出力が盛り込まれています（例: DB 保存時の PK 欠損スキップ、HTTP エラー時のリトライ/ログ、価格欠損時の SELL 判定スキップ等）。

### セキュリティ関連 (Security)
- RSS パースに defusedxml を使用して XML 攻撃を軽減。
- news_collector の設計において受信サイズ制限（MAX_RESPONSE_BYTES）を想定しメモリ DoS を抑制。
- J-Quants クライアントでトークン管理・自動リフレッシュ、またネットワークエラーに対するリトライとバックオフを実装し、堅牢性を強化。

### 既知の制限 / 今後の実装予定
- signal_generator のエグジット条件における一部機能（トレーリングストップ、時間決済）は未実装（コメントで言及）。positions テーブルに peak_price / entry_date が必要。
- news_collector の一部防御（SSRF や IP フィルタ等）は設計コメントに示されていますが、提供コードの切り出し部分では完全な実装が未確認です（ファイル内の import は存在）。
- data.stats.zscore_normalize の実装はコード参照を前提に使用されている（別モジュールで提供）。

### 注意 / マイグレーションノート
- 新規導入時は必須環境変数を設定してください（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）。Settings._require() は未設定時に ValueError を送出します。
- DuckDB スキーマ（raw_prices, raw_financials, prices_daily, features, signals, ai_scores, positions, market_calendar など）が必要です。各関数はこれらのテーブルを前提に動作します。
- 自動 .env ロードはプロジェクトルート検出に依存します（.git または pyproject.toml）。テスト環境等で自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

（注）本 CHANGELOG は提供されたソースコードの実装内容およびコメント・ドキュメント文字列から推測してまとめたものです。実際のリリースノート作成時はコミットログやリリース日付、追加の変更点を反映して更新してください。