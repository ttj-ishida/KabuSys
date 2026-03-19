# CHANGELOG

すべての重要な変更はこのファイルに記載します。フォーマットは Keep a Changelog に準拠します。
現在のバージョンはパッケージの src/kabusys/__init__.py に定義された __version__ に合わせています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-19
初回リリース。

### Added
- パッケージ基盤
  - パッケージ名: kabusys（src/kabusys）
  - バージョン: 0.1.0
  - パブリック API を定義する __all__（data, strategy, execution, monitoring）

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート検出: .git または pyproject.toml を起点に探索し、自動ロードを行う。
    - 環境変数自動ロードの無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env（.env.local は上書き）。
  - .env パーサーの強化:
    - export KEY=val 形式をサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - インラインコメント処理（クォート外・条件付き '#' コメント）。
  - Settings クラスを提供（settings インスタンスで使用）。
    - J-Quants / kabuステーション / Slack / データベースパス等の設定プロパティを定義。
    - env, log_level の検証（許容値のチェック）。
    - パス値は Path 型で返却（expanduser を適用）。

- データ取得・保存（src/kabusys/data）
  - J-Quants API クライアント（jquants_client.py）
    - レート制限用の固定間隔 RateLimiter（120 req/min 相当）を実装。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 受信時はリフレッシュトークンから自動的に id_token を再取得して 1 回リトライ。
    - ページネーション対応で全ページを収集。
    - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を実装。
    - DuckDB への冪等保存（ON CONFLICT DO UPDATE を利用）:
      - save_daily_quotes → raw_prices テーブル
      - save_financial_statements → raw_financials テーブル
      - save_market_calendar → market_calendar テーブル
    - 変換ユーティリティ: _to_float, _to_int（入力値の安全な変換処理）。
    - 取得時に fetched_at を UTC ISO8601 で記録（Look-ahead バイアス回避のため）。

  - ニュース収集モジュール（news_collector.py）
    - RSS フィードから記事を取得し raw_news に冪等保存する処理を実装（デフォルトソースに Yahoo Finance を含む）。
    - URL 正規化（utm_*, fbclid 等のトラッキングパラメータ除去、フラグメント削除、キーソート）。
    - 記事 ID は正規化 URL 等の SHA-256 ハッシュ（先頭 32 文字）を想定し冪等性を担保。
    - defusedxml による XML パースで XML-Bomb 等の攻撃を防止。
    - 受信サイズ上限（MAX_RESPONSE_BYTES=10MB）を導入。
    - SSRF を考慮した URL スキームチェックや IP 判定（実装指針に基づく設計）。
    - バルク INSERT チャンクサイズ制御（パフォーマンス向上と SQL 長制限対策）。

- 研究用ファクター計算（src/kabusys/research）
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離率（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: target_date 以前の最新財務データから PER / ROE を算出。
    - DuckDB の prices_daily / raw_financials テーブルのみ参照する設計。
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）の将来リターンを一度のクエリで取得。
    - calc_ic: スピアマンのランク相関（IC）を計算（有効データが 3 件未満の場合は None）。
    - rank: 同順位は平均ランクとして扱うランク付けユーティリティ（丸め処理で ties 検出の安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - research パッケージの public export を整備（calc_momentum 等を __all__ に追加）。

- 戦略（strategy）
  - feature_engineering.py:
    - 研究側で計算した生ファクターを取り込み、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 正規化: 指定カラムを zscore_normalize で正規化し ±3 でクリップ。
    - features テーブルへ日付単位の置換（DELETE→INSERT をトランザクションで実行、冪等性保持）。
    - build_features(conn, target_date) を公開。
  - signal_generator.py:
    - features と ai_scores を統合して最終スコア final_score を算出。
    - コンポーネントスコア: momentum, value, volatility, liquidity, news（AI）を計算するユーティリティを実装。
    - スコア変換にシグモイド関数を利用。
    - Bear レジーム判定（ai_scores の regime_score の平均が負のとき。ただしサンプル数閾値あり）。
    - BUY / SELL ロジックを実装:
      - BUY: final_score >= threshold（デフォルト 0.60）。Bear レジームでは BUY を抑制。
      - SELL（エグジット）: ストップロス（-8%）およびスコア低下（final_score < threshold）。
      - SELL 優先ポリシー: SELL 対象は BUY から除外、ランク付けを再付与。
    - signals テーブルへ日付単位の置換（トランザクションで冪等）。
    - generate_signals(conn, target_date, threshold, weights) を公開。weights はデフォルト重みから補完・再スケールされ、無効値はスキップされる。

- データ統計ユーティリティ（src/kabusys/data/stats から参照）
  - zscore_normalize を利用する設計（research と strategy で共通利用）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- news_collector で defusedxml を利用し XML 関連攻撃を軽減。
- ニュース取得時の受信バイト上限や URL 正規化／スキーム制約により SSRF / DoS リスクを低減。
- J-Quants クライアントでのトークン自動リフレッシュ時に無限再帰を回避するガード（allow_refresh フラグ）。

---

注記:
- 多くのモジュールは DuckDB 接続（DuckDBPyConnection）を前提に設計されており、prices_daily / raw_prices / raw_financials / features / ai_scores / positions / signals / market_calendar 等のテーブル構造を想定しています。テーブル定義やマイグレーションは別途管理されることを前提としています。
- 実行層（execution）や monitoring はパッケージに含まれることが示されていますが、本リリース時点では実装が薄い/未実装の箇所がある可能性があります（src/kabusys/execution/__init__.py は存在）。
- 将来的な改善候補（未実装機能の明示）:
  - signal_generator のトレーリングストップおよび時間決済（positions に peak_price / entry_date が必要）。
  - news_collector の実働 RSS フィード追加や記事→銘柄紐付けロジックの拡張。