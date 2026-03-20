CHANGELOG
=========

すべての重要な変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。
リリース日付はこの出力時点のものを使用しています。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-03-20
--------------------

Added
- 初期リリースを追加。
- パッケージ構成:
  - kabusys パッケージの公開 API を定義（kabusys.__init__ にて version="0.1.0"、data/strategy/execution/monitoring をエクスポート）。
- 環境設定管理:
  - .env および OS 環境変数の読み込み機能を実装（kabusys.config）。
  - プロジェクトルート検出（.git または pyproject.toml を基準）により cwd に依存しない自動 .env ロードを実現。
  - .env の行パーサは export プレフィックス、シングル/ダブルクォート、エスケープシーケンス、インラインコメントなどに対応。
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを実装し、J-Quants / kabu API / Slack / DB パス / 環境 (development/paper_trading/live) / ログレベル等の取得とバリデーションを提供。
- データ取得・保存:
  - J-Quants API クライアントを実装（kabusys.data.jquants_client）。
    - 固定間隔スロットリングによるレート制御（120 req/min）。
    - 冪等に保存するための DuckDB 向け save_* 関数（raw_prices, raw_financials, market_calendar）。
    - ページネーション対応、JSON デコード検査、リトライ（指数バックオフ／最大3回、408/429/5xx 対応）、429 の Retry-After 利用。
    - 401 受信時はトークン自動リフレッシュを1回行うロジックを実装。
    - 取得時刻（fetched_at）を UTC で記録し、look-ahead-bias のトレースが可能。
    - 型変換ユーティリティ（_to_float/_to_int）を実装し不正データを安全に扱う。
  - ニュース収集モジュール（kabusys.data.news_collector）を追加（RSS 収集のためのパーサ基盤）。
    - URL 正規化（トラッキングパラメータ削除、スキーム/ホスト小文字化、フラグメント削除、クエリソート）を実装。
    - 受信サイズ上限、チャンク化バルク挿入、記事 ID の SHA-256 による冪等化等の設計方針を導入。
    - defusedxml を利用した XML 安全解析を想定。
- 研究（research）モジュール:
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1/3/6 ヶ月相当）、200日移動平均乖離、20日 ATR、平均売買代金、出来高比率、PER/ROE などを DuckDB 上で計算する関数を実装。
    - 欠損・データ不足時の扱い（必要行数未満では None を返す）を明確化。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（指定ホライズンの fwd リターン、デフォルト [1,5,21]）。
    - IC（Spearman の ρ）計算、ランク関数、カラム統計サマリー（count/mean/std/min/max/median）。
  - research の __all__ に主な関数をエクスポート。
- 戦略（strategy）モジュール:
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
    - research の生ファクターを取得し、ユニバースフィルタ（最低株価・平均売買代金）、Z スコア正規化（±3 でクリップ）を適用して features テーブルへ UPSERT（トランザクションによる日付単位の置換）を行う build_features を実装。
    - ルックアヘッドバイアス防止のため target_date 時点のデータのみ使用。
  - シグナル生成（kabusys.strategy.signal_generator）
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算、重み付け合算で final_score を算出。
    - デフォルト重みと閾値を定義（デフォルト閾値 0.60）。ユーザ指定の weights を受け付け、妥当性検査・再スケールを実施。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつ十分なサンプル数）により BUY シグナル抑制。
    - SELL（エグジット）判定はストップロス（-8%）およびスコア低下を実装。SELL は BUY より優先して除外し、signals テーブルへ日付単位の置換を行う generate_signals を実装。
    - 欠損コンポーネントは中立 0.5 で補完する方針で降格を緩和。
- ロギング:
  - 各処理において詳細なログメッセージ（info/warning/debug）を導入し運用観測性を向上。

Changed
- 該当なし（初期リリース）

Fixed
- 該当なし（初期リリース）

Security
- ニュースパーサで defusedxml の利用を想定し XML 関連の攻撃対策を考慮。
- RSS 受信時の受信バイト数制限や URL 正規化によりメモリ DoS／トラッキング／一部 SSRF リスク軽減の設計を導入。
- J-Quants クライアントでのトークン管理（キャッシュ・自動更新）により認証エラー処理を堅牢化。

Notes / Implementation details
- DuckDB をストレージ層として想定し、各保存関数は ON CONFLICT / UPSERT を用いることで冪等性を担保。
- ルックアヘッドバイアス防止のため、すべての分析・シグナル計算は target_date 時点の利用可能データのみを参照する設計になっています。
- 一部モジュール（例: data.stats の zscore_normalize）は他モジュールから利用される前提で存在します（このリリースで同梱）。

Acknowledgements
- 最初の安定化バージョンとして、データ収集・前処理・研究用ユーティリティ・戦略シグナル生成の基盤を提供します。今後、execution 層（発注実装）、監視/メトリクスの拡充、テストカバレッジ強化、例外ケースの追加ハンドリング等を予定しています。