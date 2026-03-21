# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従って記載しています。  
このファイルはソースコードから推測して作成した初期の変更履歴です。

## [0.1.0] - 2026-03-21

### Added
- パッケージ基盤
  - kabusys パッケージを導入。パッケージのバージョンは `0.1.0`。
  - パブリック API として `data`, `strategy`, `execution`, `monitoring` をエクスポート（`src/kabusys/__init__.py`）。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動ロードする仕組みを実装。
    - プロジェクトルートは `__file__` を起点に `.git` または `pyproject.toml` を探索して特定（CWD に依存しない）。
    - 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - .env パーサーの実装
    - `export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
    - 無効行（コメントや形式不正）は適切に無視。
  - `Settings` クラスを提供し、各種必須設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）をプロパティで公開。
  - 値検証
    - `KABUSYS_ENV` は `development | paper_trading | live` のみ有効。
    - `LOG_LEVEL` は `DEBUG | INFO | WARNING | ERROR | CRITICAL` のみ有効。
  - DB パス取得ヘルパー（`duckdb_path`, `sqlite_path`）を提供。

- データ取得・保存（src/kabusys/data）
  - J-Quants クライアント（src/kabusys/data/jquants_client.py）
    - API レート制限（120 req/min）を守る固定間隔スロットリング `_RateLimiter` を実装。
    - 汎用 HTTP リクエスト関数 `_request` を実装（JSON パース、最大リトライ、指数バックオフ、429 の Retry-After 考慮、401 時の自動トークンリフレッシュを1回許可）。
    - ID トークン取得 `get_id_token` 実装（リフレッシュトークンを使用）。
    - ページネーション対応のフェッチ関数を実装:
      - `fetch_daily_quotes`（日足 OHLCV）
      - `fetch_financial_statements`（財務データ）
      - `fetch_market_calendar`（JPX マーケットカレンダー）
    - DuckDB への保存関数（冪等）
      - `save_daily_quotes` → `raw_prices` に対して ON CONFLICT DO UPDATE
      - `save_financial_statements` → `raw_financials` に対して ON CONFLICT DO UPDATE
      - `save_market_calendar` → `market_calendar` に対して ON CONFLICT DO UPDATE
    - 入力データの PK 欠損行はスキップして警告ログを出力。
    - ユーティリティ `_to_float` / `_to_int` を提供し、安全に型変換する。

  - ニュース収集（src/kabusys/data/news_collector.py）
    - RSS フィード取得と記事の前処理（URL 正規化、トラッキングパラメータ除去、テキスト正規化）。
    - 記事 ID を URL 正規化後の SHA-256（先頭 32 文字）で作成し冪等性を担保。
    - defusedxml を用いて XML 関連の脆弱性対策。
    - ネットワーク受信サイズを `MAX_RESPONSE_BYTES`（デフォルト 10 MB）で制限。
    - トラッキングパラメータ（例: utm_*, fbclid, gclid, _ga 等）を削除する URL 正規化を実装。
    - SSRF 対策の方針（HTTP/HTTPS スキーム制限や IP チェックなど）を設計に含む。
    - バルク挿入時のチャンクサイズ制御とトランザクション運用を想定（挿入件数を正確に返す設計）。

- 研究・リサーチモジュール（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）計算 (`calc_momentum`)。
    - Volatility / Liquidity（atr_20, atr_pct, avg_turnover, volume_ratio）計算 (`calc_volatility`)。
    - Value（per, roe）取得・計算 (`calc_value`)。raw_financials から target_date 以前の最新財務を結合。
    - DuckDB のウィンドウ関数を利用した効率的な実装。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算 `calc_forward_returns`（複数ホライズンに対応、引数で検証あり）。
    - IC（Spearman の ρ）計算 `calc_ic`（ランク相関、同順位の平均ランク処理）。
    - 基本統計量サマリ `factor_summary`。
    - ランク付けユーティリティ `rank`。
  - 研究向けユーティリティ `zscore_normalize` を `kabusys.data.stats` から再エクスポート（src/kabusys/research/__init__.py）。

- 戦略モジュール（src/kabusys/strategy）
  - 特徴量生成（src/kabusys/strategy/feature_engineering.py）
    - 研究環境で計算した raw factor を取り込み、ユニバースフィルタ（最低株価 / 最低 20 日平均売買代金）を適用。
    - 指定カラムを Z スコア正規化し ±3 でクリップ（外れ値抑制）。
    - features テーブルへ日付単位で置換（トランザクション + バルク挿入で原子性保証）。
    - ルックアヘッドバイアス回避のため target_date 時点のデータのみ使用。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合して最終スコア（final_score）を算出。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI）を計算するユーティリティを実装。
    - スコア変換にシグモイド関数を使用。None 値は中立値（0.5）で補完して不当な降格を防止。
    - ファクター重みのマージ / 検証 / 再スケール処理を実装（不正な重みは無視・警告）。
    - Bear レジーム判定（market-wide regime_score の平均が負である場合）を実装。Bear の際は BUY シグナルを抑制。
    - BUY シグナルは threshold（デフォルト 0.60）超の銘柄に付与、SELL シグナルはポジションに対してストップロス・スコア低下で判定。
    - SELL を優先して BUY リストから除外、ランク再付与。
    - signals テーブルへ日付単位の置換で書き込み（トランザクション + バルク挿入）。
  - strategy パッケージの公開関数として `build_features`, `generate_signals` をエクスポート。

### Security
- XML パースに defusedxml を使用して XML ベースの攻撃（XML bomb 等）に対処（news_collector）。
- ニュース URL の正規化とトラッキングパラメータ除去により、識別子の安定化および攻撃面減少を実現。
- RSS フェッチにおいて受信サイズ制限を導入しメモリ DoS を軽減。
- J-Quants クライアントでの認証トークン自動リフレッシュは 1 回のみ行い、無限再帰を防止。

### Notes / Known limitations
- signal_generator のエグジット条件のうち、トレーリングストップ（ピーク価格に基づく）および時間決済（保有 60 営業日超過）は未実装（positions テーブルに peak_price / entry_date 情報が必要）。
- calc_value では現時点で PER・ROE を提供するが、PBR や配当利回り等は未実装。
- news_collector の DB 側での INSERT RETURNING の挙動は設計上想定しているが、DuckDB のバージョンや実装状況により細部の挙動差があり得る。
- features 側ではユニバースフィルタのため avg_turnover を一時的に利用するが、features テーブル自体には avg_turnover を保存しない（設計上の判断）。
- 一部の設計・挙動（ログ出力、警告メッセージ、トランザクションのロールバックハンドリング）は実運用での検証が必要。

### Logging / Observability
- 各主要処理で詳細なログ（info/debug/warning）を出力する設計。トランザクションの ROLLBACK 실패は警告ログに記録。

---

この CHANGELOG はコードベースから推測して作成した初回リリース記録です。実際のリリースノートにはユーザ向けのインストール手順やマイグレーション手順（DB スキーマ等）を補足すると利便性が向上します。必要であれば、その点も含めて追記を作成します。