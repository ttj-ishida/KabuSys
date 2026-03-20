# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
現在のバージョンは 0.1.0 です（初回リリース）。日付はコードベースの提示日付を使用しています。

## [0.1.0] - 2026-03-20

### Added
- パッケージ初期リリース: KabuSys — 日本株自動売買システムのコアライブラリを追加。
  - src/kabusys/__init__.py
    - パッケージエントリポイント。公開 API として data / strategy / execution / monitoring を公開。
    - バージョン情報 `__version__ = "0.1.0"` を含む。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml で検出）。
    - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用途）。
    - 高度な .env パーサ実装:
      - 行の先頭の `export KEY=val` 形式をサポート。
      - シングル／ダブルクォート、バックスラッシュエスケープを適切に処理。
      - インラインコメント処理（クォートあり/なしのルール区別）。
    - `_load_env_file` による `.env` / `.env.local` の優先読み込み (`.env.local` は上書き)。
    - `Settings` クラス:
      - 必須設定に対する `_require()` の明確なエラーメッセージ。
      - J-Quants / kabuステーション / Slack 等の設定プロパティを提供（例: `jquants_refresh_token`, `kabu_api_password`, `slack_bot_token`, `slack_channel_id`）。
      - DB パスのデフォルト（DuckDB `data/kabusys.duckdb`, SQLite `data/monitoring.db`）。
      - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）のバリデーション（許容値のチェック）。
      - `is_live` / `is_paper` / `is_dev` のユーティリティプロパティ。

- データ取得・永続化（J-Quants クライアント）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装。
    - レート制限対応（120 req/min）: 固定間隔の RateLimiter を実装。
    - リトライロジック（指数バックオフ、最大 3 回）。408/429/5xx をリトライ対象に含む。
    - 401 受信時にリフレッシュトークンで自動的にトークンを更新して 1 回リトライ。
    - ページネーション対応の fetch_* API: `fetch_daily_quotes`, `fetch_financial_statements`, `fetch_market_calendar`。
    - DuckDB への保存ユーティリティ: `save_daily_quotes`, `save_financial_statements`, `save_market_calendar`。  
      - 保存は冪等（ON CONFLICT DO UPDATE / DO NOTHING を利用）。
      - 型変換ユーティリティ `_to_float` / `_to_int` を用意。
      - `fetched_at` を UTC ISO8601 で記録（Look-ahead バイアス対策）。

- ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィードからニュース記事を安全に収集して `raw_news` へ保存するモジュール。
    - 設計上のセキュリティ対策/堅牢化:
      - defusedxml を用いた XML パース（XML Bomb 等の防御）。
      - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）。
      - URL 正規化: トラッキングパラメータ（utm_* 等）を削除、スキーム/ホストの小文字化、フラグメント除去、クエリソート。
      - 記事 ID は正規化後の URL の SHA-256（先頭 32 文字）などで冪等性を確保する（設計方針）。
      - バルク INSERT のチャンク処理で SQL 長制限を回避。
    - デフォルト RSS ソース（例: Yahoo Finance）を定義。

- 研究（Research）機能
  - src/kabusys/research/factor_research.py
    - ファクター計算モジュールを実装:
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を計算。データ不足を考慮。
      - calc_volatility: 20日 ATR（atr_20 / atr_pct）、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を適切に扱う。
      - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算。
    - DuckDB の window 関数を活用した高効率 SQL 実装。営業日とカレンダー日を扱うためのスキャンバッファを採用。
    - 外部ライブラリに依存せず、prices_daily / raw_financials のみを参照する設計。

  - src/kabusys/research/feature_exploration.py
    - 研究用途の指標・解析ユーティリティ:
      - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
      - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算。データ不足（<3 件）の場合は None。
      - factor_summary: 各ファクター列の基本統計量（count, mean, std, min, max, median）。
      - rank: 同順位は平均ランクを返す実装（丸めで ties を扱う）。

  - src/kabusys/research/__init__.py で上記ユーティリティを公開。

- 特徴量エンジニアリング（Feature Engineering）
  - src/kabusys/strategy/feature_engineering.py
    - build_features: research の raw ファクター（momentum / volatility / value）を取得し、ユニバースフィルタ・Z スコア正規化・±3 クリップを行い `features` テーブルへ日付単位で冪等に保存。
    - ユニバースフィルタ:
      - 最低株価 >= 300 円
      - 20日平均売買代金 >= 5 億円
    - 正規化対象カラムやクリップ値は定数で明示（例: _NORM_COLS, _ZSCORE_CLIP）。
    - トランザクション + バルク挿入で原子性を保証。

- シグナル生成
  - src/kabusys/strategy/signal_generator.py
    - generate_signals: `features` と `ai_scores` を統合し、各銘柄の最終スコア final_score を計算して `signals` テーブルへ保存（日付単位の置換で冪等）。
    - スコア構成:
      - momentum / value / volatility / liquidity / news の重み付け（デフォルトは 0.40 / 0.20 / 0.15 / 0.15 / 0.10）。
      - デフォルト BUY 閾値: 0.60。
      - ストップロス閾値: -8%（SELL の判定要素）。
      - AI ニューススコアが欠けている場合は中立 (0.5) で補完。
    - Bear レジーム判定:
      - ai_scores の regime_score の平均が負かどうかで判定（サンプル数が最低数を満たさない場合は Bear としない）。
      - Bear 時は BUY シグナルを抑制。
    - SELL シグナル生成:
      - ストップロス優先、その後スコア低下によるエグジット。
      - 現在未実装の一部エグジット条件（トレーリングストップ、時間決済）はコード中に注記あり。
    - weights 引数の検証・正規化（未知キー/非数値/負値を無視、合計が 1 でない場合にリスケール）。
    - トランザクション + バルク挿入による原子性確保。

- パッケージ構成
  - src/kabusys/strategy/__init__.py で build_features / generate_signals を公開。
  - src/kabusys/research/__init__.py で研究用関数群を公開。

### Changed
- 初回リリースにおける内部設計の注記:
  - データ取得/処理は Look-ahead バイアスを避ける設計（target_date の時点で利用可能なデータのみを使用）。
  - 外部発注 API（execution 層）への直接依存を避けるように設計（execution パッケージは空のプレースホルダとして存在）。

### Fixed
- （該当なし）初回リリース。

### Known limitations / TODO
- execution パッケージは現時点で実装が含まれていません（発注ロジックは別実装を想定）。
- signal_generator のエグジット条件のうち以下は未実装（コード内に注記あり）:
  - トレーリングストップ（ピーク価格のトラッキングが positions テーブルに必要）
  - 時間決済（保有日数に基づく決済）
- news_collector の一部の実装（記事 ID の生成手順や URL スキームの完全検証など）は設計方針として記載されており、実運用で追加の堅牢化・テストが推奨されます。
- 単体テスト・統合テストの実装はこのリリースに含まれていないため、外部 API を使う処理はモックを用いたテスト環境での検証を推奨。

### Security
- XML パースに defusedxml を使用し、RSS の悪意ある XML 攻撃を想定した処理を導入。
- news_collector にて受信サイズ制限、URL 正規化、トラッキングパラメータ除去などの対策を実施。
- J-Quants クライアントは認証トークンの自動リフレッシュ・リトライ制御を備え、レート制限を厳守する設計。

---

この CHANGELOG はコードから推測して作成しています。実際のリリースノートとして使用する際は、開発履歴・コミットログ・リリース時の決定事項に合わせて適宜調整してください。