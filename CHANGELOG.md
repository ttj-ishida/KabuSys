CHANGELOG
=========

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

なお、本リポジトリはバージョン 0.1.0 が初回リリース相当の内容となります。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-20
--------------------

### Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - export: data, strategy, execution, monitoring（__all__）

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動ロード機能（プロジェクトルートは .git または pyproject.toml を探索して特定）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応
  - .env パーサ実装（export プレフィックス、クォート文字列、エスケープ、コメント処理を考慮）
  - .env 読み込み時の override / protected（OS 環境変数保護）制御
  - settings オブジェクト提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID の必須チェック
    - KABU_API_BASE_URL / DB パス（DUCKDB_PATH / SQLITE_PATH）等の既定値
    - KABUSYS_ENV / LOG_LEVEL の検証と is_live / is_paper / is_dev ヘルパー

- データ収集（kabusys.data.jquants_client）
  - J-Quants API クライアント実装
  - レートリミッタ（120 req/min 固定間隔スロットリング）
  - 再試行ロジック（指数バックオフ、最大3回、408/429/5xx を対象）
  - 401 受信時にリフレッシュトークンで自動的にトークン再取得して1回リトライ
  - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）
    - 挿入は冪等（ON CONFLICT DO UPDATE）
    - 値変換ユーティリティ (_to_float / _to_int)
    - fetched_at を UTC ISO8601 で記録（Look-ahead バイアス追跡）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得設計（デフォルトで Yahoo Finance ビジネス RSS を参照）
  - URL 正規化（小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）
  - 記事ID: 正規化 URL の SHA-256（先頭32文字）を想定して冪等性を担保
  - defusedxml を用いた XML パースによる安全化
  - SSRF・メモリDoS を考慮した入力検証（スキーム制限、受信最大バイト数制限）
  - バルク挿入のチャンク化、1 トランザクション単位での保存設計

- 研究向け・ファクター計算（kabusys.research）
  - ファクター計算エントリ:
    - calc_momentum（1/3/6M リターン、200 日移動平均乖離）
    - calc_volatility（20 日 ATR / atr_pct、avg_turnover、volume_ratio）
    - calc_value（per, roe：raw_financials と prices_daily を参照）
  - 研究ユーティリティ:
    - zscore_normalize を data.stats から利用（正規化ワークフローに組込）
    - calc_forward_returns（将来リターン fwd_1d / fwd_5d / fwd_21d 等）
    - calc_ic（Spearman ランク相関による IC 計算）
    - factor_summary（count/mean/std/min/max/median）
    - rank（同順位は平均ランクにする実装）
  - 実装方針: DuckDB に対する SQL + 標準ライブラリのみで実装（pandas 等に依存しない）

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features 実装:
    - research モジュール（calc_momentum / calc_volatility / calc_value）結果をマージ
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）
    - 指定カラムを Z スコア正規化、±3 でクリップ
    - features テーブルへ日付単位の置換（トランザクション + バルク挿入で原子性確保）
    - 欠損や外れ値を考慮した堅牢な処理

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals 実装:
    - features と ai_scores を統合して final_score を計算（デフォルト重みを定義）
    - 重みの検証・正規化（不正値・未知キーは無視、合計が 1.0 に再スケール）
    - シグモイド変換、コンポーネント（momentum/value/volatility/liquidity/news）スコア算出
    - AI の regime_score の平均で Bear レジーム判定（サンプル閾値あり） → Bear 時に BUY を抑制
    - BUY シグナル閾値デフォルト 0.60、SELL はストップロス（-8%）とスコア低下で判定
    - positions / prices_daily / ai_scores を参照して SELL 判定
    - signals テーブルへ日付単位の置換（原子性保証）
    - BUY と SELL の優先関係（SELL を優先して BUY から除外）とランク付け処理

### Security
- news_collector: defusedxml による XML パースで XML Bomb 等の脆弱性に配慮
- news_collector: URL スキーム検査や受信サイズ制限により SSRF / メモリ DoS のリスク低減
- jquants_client: トークン管理と自動更新で認証失敗時の安全な再試行を実装

### Changed
- 初期リリースのため該当なし（初回追加のみ）

### Fixed
- 初期リリースのため該当なし

### Known limitations / 未実装（設計上の注記）
- signal_generator のエグジット条件:
  - トレーリングストップ（直近最高値に基づく -10%）や時間決済（保有 60 営業日超過）は未実装（positions テーブルに peak_price / entry_date が必要）
- news_collector:
  - 記事の銘柄タグ付け（news_symbols との紐付け）等、実際の紐付けロジックは設計方針に記載されているが実装の全体はコード一部に留まる
- テスト/運用:
  - .env 自動ロードはプロジェクトルート検出に依存するため、配布後テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を使用することを推奨
- 外部依存:
  - DuckDB を前提とする SQL 実行やテーブル定義（raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals 等）は事前に準備する必要がある
- パフォーマンス/運用:
  - large-scale 運用時のページネーションやバルク挿入のチューニングは今後の課題

---

もし CHANGELOG に追記したいリリース日や別のバージョニング方針（プレリリース表記など）があれば指示してください。必要に応じて英語版や細かいコミット毎のエントリ分割も作成できます。