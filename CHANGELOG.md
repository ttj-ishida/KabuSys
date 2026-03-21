# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
非互換な変更は Breaking Changes セクションに明記します。

## [0.1.0] - 2026-03-21

### Added
- 基本パッケージ初期実装を追加
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"`、公開モジュール `data`, `strategy`, `execution`, `monitoring` を定義。
- 環境設定管理 (`kabusys.config`)
  - プロジェクトルート検出: `.git` または `pyproject.toml` を基準に自動でプロジェクトルートを探索するユーティリティを実装（配布後でも CWD に依存しない実装）。
  - .env ローダー: `.env` / `.env.local` を自動読み込み（読み込み順: OS 環境 > .env.local > .env）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能。
  - `.env` パースの堅牢化: コメント、export プレフィックス、クォート付き値、エスケープシーケンス、インラインコメント扱いを考慮して1行ずつパース。
  - 保護された OS 環境変数を上書きしないオプションサポート。
  - 必須設定取得ユーティリティ `_require` と `Settings` クラスを提供。J-Quants / kabuステーション / Slack / DB パス等のプロパティを提供（`jquants_refresh_token`, `kabu_api_password`, `slack_bot_token`, `slack_channel_id`, `duckdb_path`, `sqlite_path` 等）。
  - 環境 (`KABUSYS_ENV`) とログレベル (`LOG_LEVEL`) の検証（許容値を限定）。

- データ取得・保存機能 (`kabusys.data.jquants_client`)
  - J-Quants API クライアントを実装（認証・ページネーション・保存ユーティリティ）。
  - レート制限対応: 固定間隔スロットリング（120 req/min）を実装する `_RateLimiter`。
  - リトライ機構: 指数バックオフ（最大 3 回）、HTTP 408/429/5xx の再試行、429 の `Retry-After` サポート。
  - 401 発生時の自動トークンリフレッシュ（1 回のみ）と再試行処理を実装。モジュール内トークンキャッシュを保持。
  - JSON レスポンスデコードの検証とエラー報告。
  - ページネーション対応の取得関数:
    - `fetch_daily_quotes`（日足 OHLCV）
    - `fetch_financial_statements`（財務データ）
    - `fetch_market_calendar`（JPX カレンダー）
  - DuckDB への冪等保存ユーティリティ（ON CONFLICT DO UPDATE）:
    - `save_daily_quotes` → `raw_prices`
    - `save_financial_statements` → `raw_financials`
    - `save_market_calendar` → `market_calendar`
  - 入力データの型安全な変換ユーティリティ `_to_float` / `_to_int` を追加。

- ニュース収集 (`kabusys.data.news_collector`)
  - RSS から記事を収集して `raw_news` へ保存するモジュールを追加。
  - セキュリティ対策: defusedxml を用いた XML パース、HTTP/HTTPS スキーム制限、受信サイズ上限（10 MB）によるメモリ DoS 緩和、SSRF/トラッキングパラメータ除去（utm_* 等）。
  - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を確保。
  - bulk insert のチャンク化による DB 負荷軽減。

- 研究用ユーティリティ（research）
  - ファクター計算 (`kabusys.research.factor_research`)
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）
    - Volatility / Liquidity（atr_20, atr_pct, avg_turnover, volume_ratio）
    - Value（per, roe） — `raw_financials` と `prices_daily` を組み合わせて算出
    - DuckDB SQL とウィンドウ関数を用いた効率的実装（スキャン範囲にバッファを入れて祝日・週末に対応）
  - 特徴量探索 (`kabusys.research.feature_exploration`)
    - 将来リターン計算: `calc_forward_returns`（複数ホライズンに対応、最大ホライズンに応じたカレンダーバッファ）
    - スピアマン IC 計算: `calc_ic`（rank ベース、同位は平均ランクで処理、最小サンプル数チェック）
    - 基本統計サマリ: `factor_summary`（count/mean/std/min/max/median）
    - ランク変換ユーティリティ `rank`
  - これらは research パッケージのエクスポートに追加（`__all__` 宣言済み）。

- 戦略モジュール（strategy）
  - 特徴量エンジニアリング (`kabusys.strategy.feature_engineering`)
    - `build_features(conn, target_date)` を実装。research の生ファクターを取得、ユニバースフィルタ（最低株価・最低平均売買代金）を適用、Zスコア正規化（±3 クリップ）、`features` テーブルへ日付単位で置換（トランザクションで原子性保証）。
    - 正規化対象カラムや閾値（_MIN_PRICE=300円, _MIN_TURNOVER=5e8 円, _ZSCORE_CLIP=3.0）を定義。
  - シグナル生成 (`kabusys.strategy.signal_generator`)
    - `generate_signals(conn, target_date, threshold=0.60, weights=None)` を実装。`features` と `ai_scores` を統合して final_score を計算し、BUY/SELL シグナルを `signals` テーブルへ日付単位で置換。
    - コンポーネントスコア計算（momentum/value/volatility/liquidity/news）、シグモイド変換、欠損コンポーネントは中立値 0.5 で補完。
    - 重みの検証と再スケーリング、ユーザ指定重みのフィルタリング（未知キー・非数値等は無視）。
    - Bear レジーム検知（AI の regime_score 平均が負かつサンプル数閾値満たす場合に BUY 抑制）。
    - エグジット判定（`_generate_sell_signals`）:
      - ストップロス（終値 / avg_price - 1 < -8%）
      - スコア低下（final_score < threshold）
      - 価格欠損時の SELL 判定スキップ等の堅牢化。
    - signals テーブルへの書き込みはトランザクション＋バルク挿入で原子性を保証。SELL 優先のポリシーを適用（SELL 対象は BUY から除外しランクを再付与）。

- データ処理ユーティリティ
  - `kabusys.data.stats.zscore_normalize`（research / strategy で使用）を research の公開 API に追加（`__all__` 経由で再エクスポート）。

### Changed
- （初版）パッケージ設計に沿ったモジュール分割を反映。各モジュールは発注レイヤーや外部実行に依存しないよう分離（strategy は execution に依存しない設計方針を明記）。

### Fixed
- N/A（初期リリースのため該当なし）

### Security
- ニュース収集で defusedxml を使用して XML 関連の攻撃を軽減。
- URL 正規化／スキーム検査、受信サイズ上限により SSRF / メモリ DoS のリスクを低減。
- J-Quants クライアントでは認証エラー時に明示的なメッセージを出し、トークンの自動リフレッシュ処理を実装して不整合を防止。

### Notes / Implementation details
- 多くの DB 書き込みは「日付単位の置換（DELETE + INSERT）」を採用し、トランザクションで原子性を保証しています。大規模データ・運用時にはパフォーマンス面（DELETE のコストやインデックス）を考慮してください。
- research 側の集計は DuckDB のウィンドウ関数に依存しています。DuckDB のバージョンや SQL 挙動によっては微調整が必要になる場合があります。
- `Settings` は環境変数に厳格な検証を行います。CI / 実行環境で必須の環境変数が不足していると ValueError を送出します。
- `generate_signals` の売買ロジックには未実装のエグジット条件（トレーリングストップ・時間決済）に関する注記があります。将来的に `positions` テーブルに `peak_price` / `entry_date` を追加すると対応可能です。

### Breaking Changes
- 初回リリースのため該当なし。

---

今後のリリースでは以下を予定しています（例）:
- execution 層の実装（kabu API を用いた発注/約定処理）
- モニタリング・アラート送信（Slack 統合）の実装
- ニュース記事の銘柄紐付け（symbol tagging）の強化
- 単体テスト・統合テストの追加と CI パイプライン整備

もし CHANGELOG に追加したい詳細（リリース日やリリースノートの表現上の要望など）があれば教えてください。