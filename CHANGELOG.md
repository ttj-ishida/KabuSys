# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

なお、本リポジトリの初回公開リリースとして v0.1.0 を記載しています。

## [Unreleased]
（次リリースに向けた変更はここに記載してください）

## [0.1.0] - 2026-03-20

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基礎
  - パッケージ初期化: kabusys モジュールを追加し、バージョンを "0.1.0" に設定。
  - 公開 API: strategy 層（build_features, generate_signals）など主要サブパッケージを __all__ で公開。

- 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を起点に探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - 高度な .env パーサ:
    - コメント行・export プレフィックスに対応
    - 単一/二重クォート内のバックスラッシュエスケープ処理対応
    - インラインコメント取り扱い（クォートの有無に応じた扱いの差別化）
  - Settings クラスを提供（型付きプロパティ経由で必須値チェックとデフォルト値管理）。
  - 環境変数バリデーション: KABUSYS_ENV / LOG_LEVEL の許容値チェック。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - 主な特徴:
    - レート制限対応: 固定間隔スロットリング（120 req/min）。
    - 再試行ロジック: 指数バックオフ、最大 3 回リトライ（408/429/5xx 等を対象）。429 の場合は Retry-After を尊重。
    - 401 受信時にリフレッシュトークンで自動的に id_token を更新して 1 回リトライ（トークンキャッシュによる共有）。
    - ページネーション対応（pagination_key を用いた全件取得）。
    - 取得時刻（fetched_at）を UTC で記録してルックアヘッドバイアスのトレーサビリティを確保。
    - DuckDB への冪等保存関数:
      - save_daily_quotes: raw_prices へ ON CONFLICT DO UPDATE により冪等保存。
      - save_financial_statements: raw_financials へ冪等保存。
      - save_market_calendar: market_calendar へ冪等保存。
    - 型安全な数値パースユーティリティ (_to_float / _to_int)。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事収集して raw_news に保存する機能を実装（デフォルトで Yahoo Finance のビジネス RSS を準備）。
  - 実装上の配慮:
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性確保。
    - トラッキングパラメータ（utm_* 等）を削除し URL 正規化を実施。
    - defusedxml を用いて XML Bomb 等の脆弱性を軽減。
    - 受信サイズ上限（10 MB）を設け、メモリ DoS を防止。
    - HTTP/HTTPS スキーム検証など SSRF 対策を考慮。
    - バルク INSERT をチャンク化して DB へまとめて保存（INSERT RETURNING 想定）。

- 研究用ファクター計算 (kabusys.research)
  - ファクター計算モジュール群を実装（prices_daily / raw_financials を参照）。
  - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）を計算。データ不足時は None を返す。
  - calc_volatility: 20 日 ATR / atr_pct、20 日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。欠損制御あり。
  - calc_value: raw_financials と組み合わせて PER / ROE を計算（EPS 欠損時の扱いに注意）。
  - 研究ユーティリティ:
    - zscore_normalize を data.stats から利用可能にする（再利用を想定）。
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）までの将来リターンを一括取得。
    - calc_ic: Spearman（ランク相関）による IC 計算（同順位は平均ランク）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - rank: 同順位の平均ランク処理と浮動小数の丸めを実装。

- 特徴量作成 (kabusys.strategy.feature_engineering)
  - research 層で計算した raw factors を集約して features テーブルを作成するパイプラインを実装。
  - 処理フロー:
    - calc_momentum / calc_volatility / calc_value を呼び出して原データを取得。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 定義されたカラム群を Z スコア正規化（data.stats.zscore_normalize を使用）し ±3 でクリップ。
    - DuckDB 上で日付単位の置換（DELETE + bulk INSERT）をトランザクションで実行し原子性を確保（冪等）。
  - 設計方針により発注層への依存は持たない（戦略信号のための特徴量生成に専念）。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して最終スコア（final_score）を算出し、signals テーブルへ出力する機能を実装。
  - 実装詳細:
    - momentum/value/volatility/liquidity/news のコンポーネントスコアを定義し、シグモイド変換や PER の逆数スケール等で評価。
    - コンポーネントが欠損した場合は中立値 0.5 で補完して不当に降格しない設計。
    - デフォルト重みはドキュメント(StrategyModel.md)に基づく（momentum 0.40 など）。ユーザ指定 weights は妥当性を検証し合計を 1.0 に正規化。
    - Bear レジーム判定: ai_scores の regime_score の平均が負の場合（ただしサンプル数が閾値未満なら Bear 判定しない）に BUY シグナルを抑制。
    - BUY シグナル閾値デフォルト 0.60（カスタム可）。
    - エグジット（SELL）判定:
      - ストップロス（終値ベースの損失率 <= -8%）を最優先。
      - final_score が閾値未満の場合に売却。
      - 未実装だが設計上トレーリングストップ・時間決済の余地を確保。
    - 日付単位の置換（DELETE + bulk INSERT）をトランザクションで行い冪等性を保証。
    - 生成された BUY / SELL 数をログ出力。

### 変更 (Changed)
- （初回リリースのため無し）

### 修正 (Fixed)
- （初回リリースのため無し）

### 削除 (Removed)
- （初回リリースのため無し）

### セキュリティ (Security)
- news_collector:
  - XML パースに defusedxml を使用して XML 関連攻撃を緩和。
  - URL 正規化とスキーム検証、受信サイズ制限を導入し SSRF / DoS リスクを軽減。
- jquants_client:
  - API トークンの刷新処理は無限再帰を避ける設計（allow_refresh フラグ）を採用。

### 注意事項 / マイグレーション
- DuckDB スキーマ:
  - 本コードは特定のテーブル（raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals, raw_news 等）を前提としています。これらのスキーマが未作成の場合は事前にスキーマ定義（DDL）を作成してください。
- 環境変数:
  - 必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）は Settings プロパティ経由で参照され、未設定時は ValueError を送出します。
- 挙動:
  - research モジュールは外部ライブラリ（pandas 等）に依存しない実装のため、同等の集計処理は pure Python + DuckDB で記述されています。
  - ニュースの記事 ID 生成や URL 正規化は実運用のトラッキング除去要件に合わせた挙動をします。既存 DB の URL 格納ルールに依存する実装／運用の場合は注意してください。

---

「さらに詳細な動作仕様」や「テーブル DDL」「StrategyModel.md / DataPlatform.md」等の設計ドキュメントはリポジトリ内の該当ファイルを参照してください。