Keep a Changelog
=================

すべての重要なリリース変更点をここに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

0.1.0 - 2026-03-20
------------------

Added
- 初回公開。パッケージ名: `kabusys`。モジュール構成（data / research / strategy / execution / monitoring）を提供。
- 環境設定管理 (`kabusys.config`)
  - .env ファイル自動ロード機能を実装（プロジェクトルート判定: `.git` または `pyproject.toml`）。
  - `.env` / `.env.local` 読み込み順序を実装。OS 環境変数を保護するための protected キー処理を導入。
  - 行パーサーは `export KEY=val` やシングル/ダブルクォート、インラインコメント、エスケープシーケンスを適切に扱う。
  - 環境変数自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - `Settings` クラスでアプリ設定をプロパティとして公開（J-Quants トークン、kabu API 設定、Slack、DB パス、環境・ログレベル検証など）。
  - `KABUSYS_ENV` と `LOG_LEVEL` の値検証（許容値を限定）。

- データ取得・保存（J-Quants クライアント） (`kabusys.data.jquants_client`)
  - J-Quants API クライアントを実装（トークン取得、自動リフレッシュ、ページネーション対応）。
  - 固定間隔スロットリングによるレート制限実装（120 req/min）。
  - リトライ（指数バックオフ、最大3回）、HTTP 408/429/5xx に対する再試行、429 の Retry-After を考慮。
  - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライするロジック。
  - ページネーション間で使うモジュールレベルの ID トークンキャッシュを導入。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT による冪等性を確保。
  - 取得時刻を UTC（ISO8601）で `fetched_at` に記録し、Look-ahead bias のトレーサビリティを確保。
  - 型変換ユーティリティ `_to_float` / `_to_int` を導入（安全なパース）。

- ニュース収集 (`kabusys.data.news_collector`)
  - RSS フィードから記事を収集して `raw_news` 等へ保存する仕組み（デフォルトソースに Yahoo Finance を設定）。
  - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、クエリソート、フラグメント除去）、SHA-256 による記事 ID 生成で冪等性を担保。
  - defusedxml を利用して XML 関連の攻撃から保護。
  - 受信サイズ制限（最大 10 MB）や HTTP スキームチェック、SSRF 対策（IP/ホストチェック等を想定）により安全性を強化。
  - バルク INSERT のチャンク処理で DB オーバーヘッドを抑制、トランザクションで原子性を確保。

- リサーチ・ファクター計算 (`kabusys.research`)
  - `factor_research`:
    - `calc_momentum`: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を DuckDB 内 SQL で計算。
    - `calc_volatility`: 20日 ATR (atr_20)、相対 ATR (atr_pct)、20日平均売買代金 (avg_turnover)、出来高比 (volume_ratio) を計算。
    - `calc_value`: raw_financials から最新の財務データを取得し PER / ROE を算出（EPS 欠損・0 は None）。
  - `feature_exploration`:
    - `calc_forward_returns`: 翌日/翌週/翌月等の将来リターンを一括 SQL で取得（LEAD を利用、ホライズンの検証あり）。
    - `calc_ic`: スピアマンのランク相関（IC）を実装（同順位は平均ランク処理）。
    - `factor_summary`: count/mean/std/min/max/median 等の統計サマリーを算出。
    - `rank`: 同順位の平均ランクを考慮したランク付けユーティリティ。
  - いずれも外部ライブラリ（pandas など）に依存せず、DuckDB と標準ライブラリで実装。

- 特徴量エンジニアリング (`kabusys.strategy.feature_engineering`)
  - `build_features` を実装。
  - research モジュールの生ファクターを取得し、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
  - 指定の列で Z スコア正規化（`kabusys.data.stats.zscore_normalize` を利用）し ±3 でクリップして外れ値影響を低減。
  - features テーブルへ日付単位で置換（削除→挿入をトランザクションで行い原子性を保証）。

- シグナル生成 (`kabusys.strategy.signal_generator`)
  - `generate_signals` を実装。
  - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
  - コンポーネントごとの計算ロジック（シグモイド変換、PER の逆数的評価、ボラティリティの反転等）を実装。
  - デフォルト重みを定義し、ユーザ指定の weights を検証・マージ・再スケールする処理を実装。
  - Bear レジーム検知ロジック（ai_scores の regime_score 平均が負なら BUY を抑制、サンプル数閾値あり）。
  - BUY/SELL の両方を生成。SELL（エグジット）はストップロス（-8%）とスコア低下を実装。保有銘柄の価格欠損や features 欠落時の動作を明示。
  - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入）。

- パッケージ公開 API
  - `kabusys.__init__` によるバージョン情報 (`__version__ = "0.1.0"`) とトップレベルエクスポート定義。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- RSS パーサで defusedxml を使用し XML 攻撃を軽減。
- ニュース URL 正規化・トラッキング除去・スキームチェック・受信サイズ制限を導入し SSRF や DoS を軽減。
- J-Quants クライアントでトークン自動リフレッシュ/リトライ制御を実装し誤った認証状態への対処を強化。

Notes / Implementation details
- Look-ahead bias 回避の設計を各データ取得・特徴量計算・シグナル生成で徹底（対象日以前のデータのみ参照、fetched_at の記録等）。
- DuckDB を主要な分析ストアとして利用。bulk insert / ON CONFLICT / トランザクションにより冪等性と原子性を確保。
- 外部依存は最小限（defusedxml 等の安全系は利用）で、分析コードは標準ライブラリ + DuckDB で完結する方針。
- ログは各モジュールで logger を使用。重要な操作（保存件数、ROLLBACK 失敗等）で警告・情報出力あり。

今後の予定（暗黙の TODO）
- strategy の追加エグジット条件（トレーリングストップ、時間決済等）には positions テーブルの拡張（peak_price / entry_date 等）が必要。
- ニュース→銘柄紐付け（news_symbols）ロジックや記事テキストの NLP 前処理・AI スコア生成パイプラインの実装。
- execution 層（kabu API との注文送信）や monitoring 周りの実装強化・統合テスト。

ライセンス・貢献
- 本 CHANGELOG はコードベースの内容から推測して記載しています。実際のリリースノートやバージョン運用ポリシーに合わせて適宜修正してください。