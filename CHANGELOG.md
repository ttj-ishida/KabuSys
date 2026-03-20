# Changelog

すべての公開変更履歴をこのファイルに記録します。  
このファイルは「Keep a Changelog」フォーマットに準拠しています。

## [Unreleased]


## [0.1.0] - 2026-03-20
初回リリース。日本株自動売買システムのコアライブラリを実装しました。以下の主要機能とモジュールを含みます。

### Added
- パッケージ基本情報
  - kabusys パッケージ初期化（version=0.1.0）。主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト向け）。
  - .env パーサ実装: コメント、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応。
  - .env 読み込み時の保護（OS 環境変数を protected として上書き回避）と override オプション。
  - Settings クラス（jquants/kabu/Slack/DB/システム設定用プロパティ）を提供。必須変数取得時のエラー報告、KABUSYS_ENV / LOG_LEVEL の検証、パスの Path 化メソッドなどを実装。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - API レート制御（120 req/min 固定間隔スロットリング）を内蔵した RateLimiter。
  - ネットワークリトライ（指数バックオフ、最大 3 回）とステータスベースの再試行方針（408/429/5xx）。
  - 401 受信時の自動トークンリフレッシュ（1 回だけ）および ID トークン取得ロジック。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes（株価日足/OHLCV）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への冪等保存関数:
    - save_daily_quotes（raw_prices テーブルへ ON CONFLICT DO UPDATE）
    - save_financial_statements（raw_financials テーブルへ ON CONFLICT DO UPDATE）
    - save_market_calendar（market_calendar テーブルへ ON CONFLICT DO UPDATE）
  - データ変換ユーティリティ (_to_float, _to_int) を実装し、型安全に変換。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news に保存する基盤を実装。
  - URL 正規化（スキーム/ホストの小文字化、トラッキングパラメータ除去、フラグメント除去、クエリキーソート）。
  - 記事 ID の生成方針（正規化 URL の SHA-256 ハッシュ先頭など）により冪等性を確保。
  - セキュリティ考慮: defusedxml を利用した XML パース、受信バイト数上限（10 MB）などの DoS 対策、HTTP/HTTPS スキーム制限やトラッキングパラメータの除去方針。
  - DB へのバルク INSERT をチャンク化して効率的かつ安全に保存。

- リサーチ機能（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率 (ma200_dev) を DuckDB SQL で算出。データ不足時の None 取り扱い。
    - calc_volatility: 20 日 ATR、相対 ATR (atr_pct)、20 日平均売買代金、volume_ratio を算出。true range の NULL 伝播制御を実装。
    - calc_value: raw_financials と prices_daily を組み合わせた PER / ROE の算出（最新財務レコードを取得）。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 与えられたホライズンに対する将来リターンを一括取得（1 クエリで効率的に取得）。
    - calc_ic: Spearman のランク相関（IC）を計算。データ不足（<3 サンプル）は None を返す。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を算出。
    - rank: 同順位は平均ランクで処理するランク付けユーティリティ。
  - いずれも外部ライブラリに依存せず、DuckDB のみに依存する設計。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research モジュールで計算した生ファクターを統合して features テーブルへ保存する build_features を実装。
  - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
  - 正規化: zscore_normalize を適用し ±3 でクリップ（外れ値抑制）。
  - 日付単位の置換（DELETE + bulk INSERT）で冪等性と原子性を確保（トランザクション使用）。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して最終スコア（final_score）を算出し、BUY / SELL シグナルを生成する generate_signals を実装。
  - コンポーネントスコア:
    - momentum / value / volatility / liquidity / news（AI）を計算するユーティリティを実装（シグモイド変換や逆数変換等）。
  - ファクタ重みのマージと正規化、無効な重みのフィルタリング（警告ログ出力）。
  - Bear レジーム検知（ai_scores の regime_score 平均が負かつサンプル数閾値以上）で BUY を抑制するロジック。
  - SELL 判定ロジック（stop_loss: -8% 超、final_score が閾値未満）。
  - BUY / SELL を signals テーブルへ日付単位で置換（トランザクション + バルク挿入）し冪等性を保証。
  - ログ出力により処理状況を可視化。

- API の設計方針・品質面の配慮
  - ルックアヘッドバイアス回避のため、全て target_date 時点のデータのみ参照する設計。
  - 発注モジュール（execution）や外部発注 API への直接依存を持たない層分離。
  - DuckDB を用いた SQL 中心の高速処理とトランザクションによる原子性確保。
  - ロギングを各所で実装し、異常時は警告／情報を明示。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

---

注: 本 CHANGELOG は提供されたコードベースの実装内容から推測して作成しています。実際の変更履歴（コミット単位の詳細）やリリース手順はバージョン管理履歴をご参照ください。