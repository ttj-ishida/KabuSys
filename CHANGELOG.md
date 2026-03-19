# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
初期リリースの内容はコードベースから推測して記載しています。

## [0.1.0] - 2026-03-19

### Added
- 全体
  - 初期リリース。パッケージ名 kabusys、バージョン 0.1.0 を定義。
  - パッケージ公開 API を __all__ により整理（data, strategy, execution, monitoring）。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みするユーティリティを実装。
  - プロジェクトルート検出ロジックを追加（.git または pyproject.toml を起点に探索）。これにより CWD に依存せず自動ロードが可能。
  - .env/.env.local の読み込み順（OS 環境変数 > .env.local > .env）に対応。既存の OS 環境変数を保護するための protected 機能を実装。
  - .env パーサーで以下をサポート:
    - コメント・空行の無視、`export KEY=val` 形式への対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしの値におけるインラインコメント処理（直前がスペース/タブの場合）
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を実装（テスト用途など）。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス等の設定をプロパティで取得可能に。
  - 必須環境変数未設定時に例外を投げる _require() を用意。
  - KABUSYS_ENV（development/paper_trading/live）の検証、LOG_LEVEL 値検証、便利なフラグプロパティ（is_live / is_paper / is_dev）を追加。

- データ収集・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - レート制限 (120 req/min) を守る固定間隔スロットリング RateLimiter を実装。
  - リトライ（指数バックオフ）と HTTP ステータス別の制御を実装（408/429/5xx をリトライ対象）。429 の場合は Retry-After ヘッダを尊重。
  - 401 受信時にリフレッシュトークンから id_token を再取得して 1 回リトライする自動トークン更新ロジックを実装。
  - ページネーション対応の fetch_* 系関数を実装:
    - fetch_daily_quotes: 日足データ（OHLCV）を取得
    - fetch_financial_statements: 財務（四半期）を取得
    - fetch_market_calendar: JPX カレンダーを取得
  - DuckDB への保存用関数を実装（冪等）:
    - save_daily_quotes -> raw_prices（ON CONFLICT DO UPDATE）
    - save_financial_statements -> raw_financials（ON CONFLICT DO UPDATE）
    - save_market_calendar -> market_calendar（ON CONFLICT DO UPDATE）
  - API レスポンスのパース/型変換ユーティリティ (_to_float, _to_int) を実装。
  - 取得時刻（fetched_at）を UTC ISO8601 で記録し、Look-ahead バイアス管理を意識。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからのニュース収集モジュールを実装（設計に基づいた実装）。
  - defusedxml を利用して XML 関連の安全性対策を適用。
  - 受信サイズ上限（MAX_RESPONSE_BYTES）や SSRF 対策（HTTP/HTTPS のみ許可、IP/ホスト検査など）を想定した設計。
  - URL 正規化機能を実装（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）。
  - 記事ID に SHA-256 ハッシュ（正規化 URL ベースの先頭32文字）を使用する方針を採用し、冪等性を確保する設計。
  - raw_news へのバルク挿入を想定し、チャンク処理や INSERT の最適化を設計。

- 研究 / ファクター計算 (kabusys.research)
  - factor_research モジュールを実装:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev を計算（200 日ウィンドウ満たない場合は None）。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、volume_ratio を計算。true_range の NULL 処理に注意。
    - calc_value: raw_financials から最新の財務データを結合し PER / ROE を計算（EPS が 0／欠損時は None）。
  - feature_exploration モジュールを実装:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズンのバリデーション（1〜252）を実装。
    - calc_ic: ファクターと将来リターンの Spearman rank 相関（IC）を計算。サンプル不足時は None を返す。
    - rank / factor_summary: タイ（同順位）を平均ランクで処理する rank、基本統計量（count/mean/std/min/max/median）を出力する factor_summary を実装。
  - DuckDB のみを参照し、外部ライブラリに依存しない実装方針を採用。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - research 側が出力する raw factor を取得し統合して features テーブルへ保存する build_features を実装。
  - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を実装。
  - 数値ファクターを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップ。
  - date 単位で削除→挿入する置換処理（トランザクション + バルク挿入）により冪等性と原子性を担保。
  - 欠損や価格取得のために target_date 以前の最新価格を参照することで休日などへの対応を実装。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features テーブルと ai_scores を統合して final_score を計算し、signals テーブルへ書き込む generate_signals を実装。
  - コンポーネントスコア（momentum / value / volatility / liquidity / news）とデフォルト重みを実装（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。
  - 重みはユーザ指定で上書き可能だが不正値は無視し、合計が 1.0 になるよう再スケールを行うフォールバック処理を実装。
  - Z スコアを sigmoid で [0,1] に変換するユーティリティを実装（オーバーフロー対策あり）。
  - AI スコア統合: ai_scores が無い場合は中立値（0.5）で補完。レジームスコアの平均が負なら Bear レジームと判定して BUY シグナルを抑制。
  - BUY シグナル閾値デフォルト 0.60。SELL ロジックではストップロス（-8%）とスコア低下を実装。
  - 保持ポジションの最新情報・価格を参照してエグジット判定を行う（価格欠損時は判定スキップ）。SELL が BUY より優先されるポリシーを実装。
  - signals テーブルへの日付単位置換（トランザクション + バルク挿入）で冪等性と原子性を担保。

### Changed
- (初期リリースにつき該当なし)

### Fixed
- (初期リリースにつき該当なし)

### Removed
- (初期リリースにつき該当なし)

### Known issues / TODO（コード内 docstring に基づく）
- signal_generator のエグジット条件について、トレーリングストップ（直近最高値 -10%）や時間決済（保有 60 営業日超）などは未実装。これらは positions テーブルに peak_price / entry_date 等が必要。
- research.calc_value は PBR や配当利回りを現バージョンでは未実装。
- news_collector の実装は設計を満たす形で多くのユーティリティを含むが、RSS の取得・パース→DB 挿入の完全なパイプライン（エラー時のフォールバックやネットワーク周りの詳細ハンドリング）は環境に依存するため運用時に追加の検証が必要。
- execution / monitoring パッケージはエントリをエクスポートしているが、今回提供されたソースでは発注実行層（kabuステーションとの連携等）の実装は含まれていない模様。

---

注記: 上記はソースコードの docstring・実装内容から推測して作成した CHANGELOG の初期リリース記述です。実際のリリースノートにはリリース手順、互換性に関する注意、マイグレーション手順（DB スキーマ等）があれば追記してください。