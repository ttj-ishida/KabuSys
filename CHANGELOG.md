# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-20

初回公開リリース。日本株自動売買システムのコア機能（データ取得・保存、ファクター計算、特徴量生成、シグナル生成、環境設定ユーティリティ等）を実装しました。

### Added
- パッケージ基礎
  - パッケージメタ情報（src/kabusys/__init__.py, バージョン `0.1.0`）。
  - public API: strategy.build_features / strategy.generate_signals を公開。

- 環境変数・設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
    - プロジェクトルート検出は __file__ を起点に `.git` または `pyproject.toml` を探索（配布後も動作するよう設計）。
  - .env の行パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
  - Settings クラスにより型安全に設定値を取得:
    - 必須: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`
    - DB パスのデフォルト: `DUCKDB_PATH=data/kabusys.duckdb`, `SQLITE_PATH=data/monitoring.db`
    - `KABUSYS_ENV`（development/paper_trading/live）と `LOG_LEVEL`（DEBUG/INFO/WARNING/ERROR/CRITICAL）のバリデーションとユーティリティプロパティ（is_live/is_paper/is_dev）。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter 実装。
  - リトライ / 再試行ロジック:
    - 指数バックオフ（最大 3 回）、HTTP 408/429/5xx / ネットワークエラーに対応。
    - 401 受信時はリフレッシュトークンで ID トークンを自動更新して 1 回だけリトライ。
  - ページネーション対応のデータ取得:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存ユーティリティ（冪等）:
    - save_daily_quotes / save_financial_statements / save_market_calendar：INSERT ... ON CONFLICT DO UPDATE を使った重複排除。
  - 実運用向けユーティリティ関数: _to_float, _to_int（堅牢な型変換を提供）。
  - 取得時刻（fetched_at）を UTC ISO8601 で記録し、look-ahead バイアス解析が可能。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィード収集の実装（デフォルト: Yahoo Finance ビジネス RSS）。
  - セキュリティと堅牢性:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - URL 正規化（トラッキングパラメータ削除、スキーム/ホスト小文字化、フラグメント除去、クエリソート）。
    - HTTP/HTTPS スキームのみ許可、受信最大バイト数制限（10 MB）などの DoS/SSRF 対策。
  - 記事 ID は URL の正規化後に SHA-256 を使って生成（先頭 32 文字）し冪等性を確保。
  - DB 保存はバルク INSERT（チャンク）かつトランザクションで行い、挿入件数を正確に返す設計。
  - news_symbols など銘柄紐付け処理のための基盤を提供。

- ファクター計算（research）(src/kabusys/research/factor_research.py)
  - momentum, volatility, value ファクター計算関数を実装:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日のデータ不足時は None）。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（ATR は NULL 伝播を適切に制御）。
    - calc_value: per（EPS が 0/欠損なら None）, roe（raw_financials から最新レコードを使用）。
  - DuckDB の時系列ウィンドウ関数を活用し、休日や欠損への耐性を意識したスキャン範囲を採用。

- 研究用特徴量探索 (src/kabusys/research/feature_exploration.py)
  - 将来リターン計算 calc_forward_returns（複数ホライズン対応、データ不足時は None）。
  - IC（Information Coefficient）計算 calc_ic（Spearman の ρ、有効サンプル < 3 の場合は None）。
  - factor_summary（count/mean/std/min/max/median）とランク関数 rank を実装。
  - 外部依存を避け、標準ライブラリ + DuckDB のみで実装。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - build_features 実装:
    - research の calc_momentum/calc_volatility/calc_value を利用して生ファクターを取得。
    - ユニバースフィルタ: 株価 >= 300 円、20 日平均売買代金 >= 5 億円。
    - 指定列を z-score 正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップして外れ値影響を抑制。
    - 日付単位の置換（DELETE + bulk INSERT）で冪等に features テーブルを更新。
    - トランザクションで原子性を保証。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - generate_signals 実装:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - コンポーネントはシグモイド変換・平均化され、重み付け合算で final_score を生成（デフォルト重みを実装）。
    - ユーザ渡しの weights を検証してフォールバック/再スケール（不正値は無視）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）は BUY を抑制。
    - SELL（エグジット）判定を実装:
      - ストップロス（終値 / avg_price - 1 < -8%）
      - final_score が閾値未満
      - （将来的にトレーリングストップや時間決済を追加する旨の注記あり）
    - SELL 優先ポリシー: SELL 対象は BUY から除外し、BUY のランクを再付与。
    - signals テーブルへの日付単位置換をトランザクションで実行。
    - ログ出力を通じて運用状況を追跡可能。

- 研究パッケージの公開（src/kabusys/research/__init__.py）
  - 主要関数をパッケージレベルで公開（calc_momentum/calc_volatility/calc_value/zscore_normalize/calc_forward_returns/calc_ic/factor_summary/rank）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Notes / Known limitations
- execution パッケージは初期化ファイルのみで、発注ロジック・kabu ステーション連携の実装は含まれていません（別途実装予定）。
- 一部のユースケース（例: positions テーブルに peak_price / entry_date がない場合のトレイリングストップ等）は未実装として明記しています。
- zscore 正規化ユーティリティ（kabusys.data.stats）は本リリースで参照されますが、その実装が別途存在する前提です。
- .env の自動読み込みはプロジェクトルート検出に依存するため、配布後や特殊な配置では KABUSYS_DISABLE_AUTO_ENV_LOAD を使用して手動で設定することを推奨します。

### 開発者向け（環境変数）
以下は本リリースで使用される主な環境変数（必須は明示）:
- 必須:
  - JQUANTS_REFRESH_TOKEN (J-Quants API リフレッシュトークン)
  - KABU_API_PASSWORD (kabu API 用パスワード)
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (運用通知用)
- 任意 / デフォルトあり:
  - KABUSYS_ENV (development|paper_trading|live) — デフォルト: development
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
  - DUCKDB_PATH, SQLITE_PATH — デフォルト: data/kabusys.duckdb / data/monitoring.db
- 自動 .env ロードを無効化する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

（以降のバージョンでは、発注層（execution）の追加、AI スコア生成パイプライン、ニュース→銘柄紐付けの強化、追加のリスク管理機能（トレーリングストップ、時間決済）等を予定しています。）