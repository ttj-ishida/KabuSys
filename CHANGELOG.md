# Changelog

すべての変更は Keep a Changelog の形式に従います。  
初版 (v0.1.0) はリポジトリ内のソースコードから推定して記載しています。

## [Unreleased]

## [0.1.0] - 2026-03-21
初回リリース — 基本的なデータ取得・ファクター計算・特徴量生成・シグナル生成・設定管理を実装。

### 追加
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0）。
  - サブパッケージ公開: data, strategy, execution, monitoring のエクスポート設定。

- 設定管理
  - 環境変数自動ロード機能（.env / .env.local）を実装。プロジェクトルートは .git または pyproject.toml を起点に探索。
  - .env パーサを実装（コメント、export プレフィックス、クォート・エスケープ、インラインコメント対応などを考慮）。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供し、以下の設定値をプロパティで取得可能:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live）
    - LOG_LEVEL（DEBUG, INFO, WARNING, ERROR, CRITICAL）
  - Settings に便利なプロパティ: is_live / is_paper / is_dev。

- Data モジュール（J-Quants クライアント）
  - J-Quants API クライアントを実装（urllib ベース）。
  - レート制限 (120 req/min) を守る固定間隔スロットリング実装（_RateLimiter）。
  - リトライロジック（指数バックオフ、最大リトライ 3 回、HTTP 408/429/5xx を再試行対象）。
  - 401 受信時のトークン自動リフレッシュ（1 回リトライ）。
  - ページネーション対応の fetch_* 関数:
    - fetch_daily_quotes (株価日足)
    - fetch_financial_statements (財務データ)
    - fetch_market_calendar (JPX カレンダー)
  - DuckDB へ冪等保存する save_* 関数:
    - save_daily_quotes -> raw_prices（ON CONFLICT DO UPDATE）
    - save_financial_statements -> raw_financials（ON CONFLICT DO UPDATE）
    - save_market_calendar -> market_calendar（ON CONFLICT DO UPDATE）
  - データ変換ユーティリティ: _to_float / _to_int（不正データ安全処理）。
  - データ取得時に fetched_at を UTC ISO8601 で記録（ルックアヘッドバイアス対応トレーサビリティ）。

- News モジュール（RSS ニュース収集）
  - RSS フィードから記事を取得し raw_news に保存する処理の骨組みを実装。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）。
  - セキュリティ考慮: defusedxml を利用して XML 関連攻撃を防止、受信最大バイト数制限（10MB）、HTTP/HTTPS スキーム検証、IP/SSRF 柔軟性への配慮。
  - デフォルト RSS ソースに Yahoo Finance のビジネス RSS を登録。

- Research モジュール（研究用ファクター計算／解析）
  - factor_research: 定量ファクター計算（prices_daily, raw_financials を参照）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を実装（200日移動平均は行数チェックあり）
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を実装（true_range ロジック・欠損制御）
    - calc_value: per, roe を実装（raw_financials から target_date 以前の最新レコードを参照）
  - feature_exploration:
    - calc_forward_returns: 複数ホライズンに対する将来リターンを一括取得（LEAD を使用）
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装（同順位は平均ランク）
    - factor_summary: count/mean/std/min/max/median を計算
    - rank: ランク付けユーティリティ（同順位は平均ランク、丸め考慮）
  - 研究側は pandas 等の外部依存を避け、標準ライブラリ + DuckDB で実装。

- Strategy モジュール（特徴量整形・シグナル生成）
  - feature_engineering.build_features:
    - research 側の生ファクター（calc_momentum / calc_volatility / calc_value）を統合。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5億円）を実装。
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）、±3 でクリップして外れ値対策。
    - features テーブルへ日付単位の置換（トランザクション + バルク挿入で原子性を担保）。
    - 正規化対象カラム: mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev。per は正規化対象外（逆数扱いの方針）。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - スコア変換ユーティリティ: シグモイド変換、コンポーネント平均、AI スコアの補完（未登録時は中立 0.5）。
    - デフォルト重みを実装 (momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10)。外部から weights を受け取り検証・正規化して適用。
    - Bear レジーム判定: ai_scores の regime_score の平均が負であれば Bear（ただしサンプル数が閾値未満なら Bear としない）。
    - BUY シグナル: final_score >= threshold (デフォルト 0.60)、Bear の場合は BUY を抑制。
    - SELL シグナル（エグジット判定）:
      - ストップロス: 終値/avg_price - 1 < -8%
      - スコア低下: final_score < threshold
      - 未実装のエグジット条件（コード内に TODO コメントあり）: トレーリングストップ、時間決済（60営業日など）
    - signals テーブルへ日付単位の置換（トランザクション + バルク挿入）。

### 変更
- （初回リリースにつき過去変更なし）

### 修正
- （初回リリースにつき過去修正なし）

### 非推奨
- なし

### 削除
- なし

### セキュリティ
- 外部データ取り扱い時の安全対策を実装:
  - defusedxml による XML パースの安全化（ニュース収集）
  - URL 正規化とトラッキングパラメータ除去
  - J-Quants API のトークン自動リフレッシュと限定的リトライポリシー

---

## 既知の制限・注意点
- signal_generator の一部エグジットロジック（トレーリングストップ、時間決済）は未実装。positions テーブルに peak_price / entry_date が必要。
- J-Quants クライアントは urllib を使用しており、スレッド安全性や並列化は保証していない（グローバルなトークンキャッシュとレートリミッタを使用）。マルチスレッド/マルチプロセス運用時は注意。
- NewsCollector の URL/ネットワーク検証は基本的な対策を行っているが、完全な SSRF 保護や詳細なホワイトリスト制御は実装されていない。
- calc_forward_returns はホライズンに対して calendar buffer（max_h * 2 日）でスキャン範囲を限定している。営業日数とカレンダー日数の扱いに注意。
- settings の自動 .env ロードはプロジェクトルートを .git または pyproject.toml で検出するため、配布/インストール後の実行環境によっては自動ロードがスキップされる可能性がある（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定）。

## 将来の予定（想定）
- SELL 条件の追加実装（トレーリングストップ、時間決済）。
- 並列/非同期での J-Quants API 利用改善（トークン管理・レート制御の強化）。
- ニュース記事の銘柄紐付け（news_symbols）ロジック実装。
- テスト・CI整備（ユニットテスト・統合テスト・エンドツーエンド）。
- ドキュメントの充実（StrategyModel.md / DataPlatform.md などを完全実装、外部公開用の利用ガイド）。

---

著者: ソースコードから自動生成された CHANGELOG（内容はコードのコメント・実装から推定）