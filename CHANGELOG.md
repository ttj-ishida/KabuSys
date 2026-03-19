# CHANGELOG

すべての重要な変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。  
初期リリースの内容はソースコードから推測して記載しています。

現在のバージョン: 0.1.0

## [Unreleased]
- 次回リリースに向けた変更点はここに記載します。

## [0.1.0] - 2026-03-19
最初の公開リリース（推測）。自動売買/リサーチ用の基礎ライブラリを実装。

### Added
- 基本パッケージ構成
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring（__all__ に定義）

- 環境設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能（プロジェクトルートを .git または pyproject.toml から検索）
  - 行単位の .env パーサ実装（export 構文対応、クォート/エスケープ、インラインコメント処理）
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - Settings クラスによる設定取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）
  - 環境・ログレベル検証（KABUSYS_ENV は development/paper_trading/live、LOG_LEVEL は標準レベルのみ許容）
  - デフォルトファイルパスの提供（DUCKDB_PATH, SQLITE_PATH）

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントの実装
    - 固定間隔のレートリミッタ（120 req/min）を実装
    - リトライ（指数バックオフ、最大 3 回）、HTTP 408/429/5xx に対応
    - 401 発生時にリフレッシュトークンで ID トークンを自動再取得（1 回だけリトライ）
    - ページネーション対応のフェッチ関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への冪等保存関数
    - save_daily_quotes（raw_prices へ ON CONFLICT DO UPDATE）
    - save_financial_statements（raw_financials へ ON CONFLICT DO UPDATE）
    - save_market_calendar（market_calendar へ ON CONFLICT DO UPDATE）
  - 入力変換ユーティリティ: _to_float, _to_int
  - fetched_at を UTC (ISO8601) で記録して Look-ahead バイアスのトレースに対応

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからの記事収集処理
  - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント削除）
  - 受信サイズ上限 (MAX_RESPONSE_BYTES) や XML パースに defusedxml を利用して安全性を考慮
  - 記事 ID を正規化 URL の SHA-256（先頭 32 文字等）で生成して冪等性を確保
  - DB へのバルク挿入をトランザクション単位で実施、INSERT チャンク分割実装

- ファクター計算・リサーチ (kabusys.research, kabusys.research.factor_research)
  - モメンタム、ボラティリティ、バリュー系ファクターを DuckDB 上で計算する関数を実装
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200 日移動平均のカウントチェック含む）
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（true_range の NULL 伝播制御）
    - calc_value: per, roe（raw_financials の target_date 以前の最新財務を結合）
  - 研究用ユーティリティ
    - calc_forward_returns: 指定ホライズン（既定: [1,5,21]）の将来リターンを一括取得
    - calc_ic: スピアマンランク相関（IC）計算
    - factor_summary: 基本統計量（count/mean/std/min/max/median）
    - rank: 同順位は平均ランクとなるランク付け（round による丸めで ties 検出）
  - DuckDB の SQL ウィンドウ関数を活用した効率重視の実装（スキャン範囲バッファ等の措置あり）

- 特徴量工程 (kabusys.strategy.feature_engineering)
  - 研究環境で計算された raw ファクターをマージし、正規化→クリップ→features テーブルへ日付単位で UPSERT（冪等）
  - ユニバースフィルタ（最低株価、20日平均売買代金）を実装
  - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ
  - トランザクション + バルク挿入で原子性を保証

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して final_score を計算、BUY / SELL シグナルを生成して signals テーブルへ書き込み（冪等）
  - スコア構成要素: momentum, value, volatility, liquidity, news（デフォルト重みを採用）
  - weights 引数のバリデーションと合計が 1.0 になるようリスケール
  - Sigmoid 変換／欠損補完（None を中立 0.5）による堅牢化
  - Bear レジーム判定（ai_scores の regime_score 平均が負の場合、かつサンプル数閾値以上）
  - エグジット判定（ストップロス、スコア低下）。保有銘柄の価格欠損時は SELL 判定をスキップして誤クローズを防止
  - signals テーブルへのトランザクション置換で原子性を保証

- ロギング、型注釈、設計ドキュメントに準拠した実装
  - 各モジュールに詳細な docstring と設計方針を記載（StrategyModel.md, DataPlatform.md 等を参照する想定）
  - duckdb.DuckDBPyConnection を明示的に受け取り外部依存を限定

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- news_collector で defusedxml を採用し XML 脆弱性対策を実施
- RSS URL の正規化およびスキーム制限により SSRF / 不正スキームリクエストのリスク低減を意識
- J-Quants クライアントで認証トークンの自動リフレッシュ、リトライ制御、レート制限を実装して API 使用上の安全性・安定性を向上

### Known issues / Limitations
- signal_generator のトレーリングストップ、時間決済など一部エグジット条件は未実装（positions テーブルに追加データが必要）
- calc_value では PBR・配当利回りは未実装
- news_collector の記事 ID・シンボル紐付け詳細（news_symbols）などは実装想定だが、コードの続きに依存している可能性あり
- .env パーサはかなり寛容に実装しているが、極端なフォーマットの .env では挙動が予期せぬものとなる場合がある
- J-Quants API のエラー処理で最終的に RuntimeError を投げる設計。呼び出し側での更なるハンドリングが必要

---

この CHANGELOG はコードベースの docstring と実装から推測して作成しています。実際のリリースノート作成時はコミット履歴やリリース手順・日付を確認して適宜調整してください。