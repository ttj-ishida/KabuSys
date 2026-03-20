# CHANGELOG

すべての注目すべき変更点はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠します。

現在のバージョン: 0.1.0 - 2026-03-20

## [0.1.0] - 2026-03-20
最初の公開リリース。

### 追加
- パッケージ基盤
  - kabusys パッケージ初期化と公開 API を追加（kabusys.__init__ に version と __all__ 定義）。
- 環境/設定管理（kabusys.config）
  - .env / .env.local 自動読み込み機能を実装。プロジェクトルートは .git または pyproject.toml を基準に探索し、CWD に依存しない設計。
  - .env ファイルのパースを堅牢化（コメント行・export プレフィックス・クォート内のエスケープ・インラインコメント処理対応）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 環境変数保護（OS 環境変数の上書きを防ぐ protected オプション）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境モード（development/paper_trading/live）/ログレベル等の取得とバリデーション機能を実装。
  - デフォルトの DB パス（DuckDB / SQLite）を設定し、Path.expanduser による扱いをサポート。
- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - API レート制御（固定間隔スロットリング、デフォルト 120 req/min）を実装する RateLimiter。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx 対象）を実装。
  - 401 Unauthorized を受けた際の自動トークンリフレッシュ（1 回のみ）と再試行対応。
  - ページネーション対応（pagination_key を使用した繰り返し取得）。
  - fetch_* 系関数: 日足（fetch_daily_quotes）、財務（fetch_financial_statements）、マーケットカレンダー（fetch_market_calendar）を実装。
  - DuckDB への保存用ユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT（冪等）で重複を扱う。
  - レスポンスの fetched_at を UTC ISO フォーマットで記録。
  - 型変換ユーティリティ (_to_float, _to_int) を追加（空値や不正な文字列の安全な扱い）。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集処理の基礎を実装（デフォルトソース: Yahoo Finance ビジネスカテゴリ）。
  - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）を実装。
  - XML 解析に defusedxml を使用して XML Bomb 等の脅威を緩和。
  - 応答サイズ上限（MAX_RESPONSE_BYTES=10MB）設定によるメモリ DoS 防止。
  - DB へはバルク挿入を意識したチャンク処理（_INSERT_CHUNK_SIZE）で保存する方針（設計記述あり）。
  - 記事 ID 生成方針（URL 正規化後の SHA-256 ハッシュ先頭等）をドキュメント化（冪等性を保証するため）。
- リサーチ/ファクター計算（kabusys.research.*）
  - ファクター計算モジュールを実装（factor_research.py）。
    - Momentum（mom_1m / mom_3m / mom_6m, ma200_dev）、Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）、Value（per, roe）を計算。
    - SQL + DuckDB を用いた計算で prices_daily / raw_financials のみを参照。経路の独立性（発注 API 等に依存しない）を確保。
  - 解析補助モジュールを実装（feature_exploration.py）。
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: スピアマンのランク相関（Information Coefficient）の計算（同順位は平均ランクで扱う）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを計算。
    - rank: 同順位処理（平均ランク）を含むランク付けユーティリティを実装。
  - リサーチ群は外部ライブラリ（pandas 等）に依存せず、標準ライブラリ + DuckDB で実装。
  - zscore_normalize は kabusys.data.stats からエクスポートする前提で利用。
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features を実装。
    - research モジュールの生ファクターを取得し、ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5 億円）を適用。
    - 指定カラムを Z スコア正規化し ±3 でクリップ（外れ値抑制）。
    - features テーブルへ日付単位で削除→挿入（トランザクションで原子性を確保）することで冪等性を実現。
    - ルックアヘッドバイアス防止のため target_date 時点のデータのみを参照。
- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals を実装。
    - features / ai_scores / positions テーブルを参照して最終スコア（final_score）を計算。
    - コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し、デフォルト重み（momentum 0.40 等）で加重平均。
    - AI スコア未登録時は中立（0.5）で補完、欠損コンポーネントも中立補完して不当な降格を防止。
    - デフォルト BUY 閾値は 0.60。Bear レジーム判定により BUY を抑制（市場レジームの平均 regime_score が負かつ十分なサンプル数がある場合）。
    - SELL（エグジット）判定:
      - ストップロス: 終値 / avg_price - 1 < -8%（優先）
      - final_score が threshold 未満
      - 価格欠損時は判定をスキップして誤クローズを防止
    - SELL 優先のため SELL 対象を BUY から除外し、signals テーブルへ日付単位の置換で書き込み（トランザクションで原子性）。
  - ウェイトの入力は検証・補完され、合計が 1.0 になるように再スケール。無効なキーや値はログでスキップ。
- モジュールのエクスポートを整理（kabusys.strategy.__init__, kabusys.research.__init__）。

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### 検討中 / 未実装（ドキュメント化）
- signal_generator の一部エグジット条件は未実装（comments に明記）:
  - トレーリングストップ（peak_price のトラッキングが positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）など
- news_collector の記事 ID 生成・DB 保存処理の詳細（ハッシュ化・news_symbols 紐付け等）は設計に記載されているが、コード全体での完全実装は該当箇所に依存（本リリースでは URL 正規化とユーティリティを中心に実装）。

### セキュリティ/堅牢性
- defusedxml を利用し RSS/XML パースの安全性を向上。
- RSS/HTTP の応答サイズ制限や URL 正規化、SSRF に対する注意喚起を実装。
- J-Quants API クライアントでのトークン自動更新は allow_refresh フラグにより無限再帰を防止。
- DuckDB への保存は ON CONFLICT による冪等性を担保。

## 未定義 / 既知の制約
- 単体テスト / 統合テストはコード内に明示されていない（テストフレームワークやテストケースは本リリースに含まれていない）。
- 一部の高度なポジション管理（peak_price 管理等）は positions スキーマ拡張を要するため未対応。
- 外部依存（defusedxml, duckdb）は必要。Research 部分は pandas 等に依存しない方針。

---
今後のリリースでは、トレーリングストップ等エグジット条件の実装完了、news_collector の完全な記事→銘柄マッピング、モニタリング/実行層（execution / monitoring）との統合、単体テスト・CI の整備などを予定しています。