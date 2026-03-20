# CHANGELOG

このプロジェクトでは Keep a Changelog の形式に準拠し、変更履歴を記録します。  
フォーマットや粒度は今後のリリースで調整する予定です。

※ 初期リリース（0.1.0）はコードベースから推測して作成しています。

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-03-20

### Added
- パッケージの初期公開
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。
  - パッケージ外部公開 API に data, strategy, execution, monitoring を __all__ で定義。

- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env / .env.local ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルートを .git または pyproject.toml から特定するロジックを導入（CWD に依存しない）。
  - .env 行パーサーを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応）。
  - .env 読み込み時の上書き制御（override）と OS 環境変数を保護する protected 機能を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用途）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境種類 / ログレベルなどの取得とバリデーションを実装。

- データ取得・保存（src/kabusys/data）
  - J-Quants クライアント（src/kabusys/data/jquants_client.py）
    - API 呼び出しユーティリティ (_request) を実装（JSON デコード、ページネーション、再試行ロジック、401 時のトークン自動リフレッシュ）。
    - 固定間隔のレートリミッタ実装（120 req/min を尊重）。
    - リトライ時の指数バックオフ、429 の Retry-After 優先処理、ネットワーク例外対策を実装。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar のページネーション対応取得関数を実装。
    - DuckDB へ保存する save_daily_quotes / save_financial_statements / save_market_calendar を実装（ON CONFLICT による冪等保存、PK 欠損行のスキップロギング）。
    - 取得タイミングを追跡する fetched_at を UTC で記録。
    - 型変換ユーティリティ _to_float / _to_int を実装（安全な変換・欠損処理）。

  - ニュース収集モジュール（src/kabusys/data/news_collector.py）
    - RSS フィード取得・記事抽出機能（デフォルトに Yahoo Finance Business RSS を定義）。
    - 記事 ID を URL 正規化後の SHA-256 によるハッシュで生成し冪等性を確保。
    - URL 正規化でトラッキングパラメータ除去、クエリ整列、フラグメント除去、スキーム/ホスト小文字化を実装。
    - defusedxml を用いた XML パースで XML Bomb 等に対する安全対策を実施。
    - 受信サイズ上限（MAX_RESPONSE_BYTES）や SSRF（非 http/https スキーム拒否）等の安全対策を導入。
    - DB 保存はバルクインサート（チャンク化）で効率化、INSERT RETURNING を想定した実装方針。

- リサーチ・ファクター計算（src/kabusys/research）
  - factor_research.py
    - calc_momentum（1/3/6 か月リターン、200 日移動平均乖離率）を実装。欠損データハンドリングやウィンドウ長チェックを含む。
    - calc_volatility（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率）を実装。true_range の NULL 伝播制御を実施。
    - calc_value（最新の財務データを参照し PER / ROE を計算）を実装。
    - DuckDB を用いた SQL ベースの計算でパフォーマンス配慮（スキャン範囲バッファ等）。

  - feature_exploration.py
    - calc_forward_returns（指定ホライズンの将来リターンを一括取得）を実装。horizons のバリデーションを実施。
    - calc_ic（スピアマンランク相関による IC 計算）を実装。欠損・同順位処理・最小サンプルチェックを含む。
    - rank（平均ランク処理、同順位は平均ランク）を実装。丸めによる ties 検出漏れ対策を採用。
    - factor_summary（count/mean/std/min/max/median の統計サマリ）を実装。

  - research パッケージの __all__ で主要関数群を公開。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features を実装。research 側で計算した生ファクターを統合し、ユニバースフィルタ（最低株価・最低売買代金）適用、Z スコア正規化、±3 でクリップ、features テーブルへ日付単位の置換（トランザクションで冪等）を行う。
  - ルックアヘッドバイアス対策として target_date 時点のデータのみを使用。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals を実装。features と ai_scores を統合して momentum/value/volatility/liquidity/news コンポーネントを計算し、重み付き合算で final_score を算出。
  - デフォルト重み・閾値を実装。ユーザ指定 weights を部分的に受け入れ、検証・正規化（合計が 1 に再スケール）を実施。
  - Bear レジーム（AI regime_score の平均が負かつサンプル十分）検知時は BUY を抑制。
  - SELL シグナル生成ロジック（ストップロス、スコア低下）を実装。保有銘柄の価格欠損時の判定スキップや features に存在しない保有銘柄は score=0 扱いとするなどの安全策を導入。
  - signals テーブルへ日付単位の置換で書き込み（トランザクション＋バルク挿入で冪等）。

- 戦略パッケージの __all__ で build_features / generate_signals を公開。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- news_collector で defusedxml を採用し XML パースの安全性を確保。
- ニュース取得時の受信サイズ制限、SSRF 対策、URL 正規化によるトラッキング除去など複数の安全対策を実装。
- J-Quants クライアントでのトークン自動リフレッシュ時に無限再帰を防ぐ設計（allow_refresh フラグ）。

### Notes / Design Decisions
- DuckDB を主要な分析ストレージとして利用し、SQL と Python の組合せで高速にファクター計算を行う設計。
- ルックアヘッドバイアス対策をプロジェクト設計の主要方針として全モジュールで徹底（target_date 時点のデータのみ使用、fetched_at の記録など）。
- 冪等性を優先（DB への INSERT は ON CONFLICT、signals/features の日付単位置換はトランザクションで実施）。
- 可能な限り外部依存を抑え（pandas 等不使用）、標準ライブラリと最小限の安全ライブラリを活用する設計方針。

--- 

今後のリリースでは、以下のような改善が想定されます（予定・推測）:
- execution 層（発注インターフェース）の実装（kabu ステーション API 連携）。
- monitoring 層（Slack 通知、監視ダッシュボード）の具体化。
- 追加のファクター（PBR, 配当利回り等）やトレーリングストップ・時間決済のエグジット条件実装。
- 単体テストの整備、CI/CD パイプライン導入。

もし CHANGELOG の粒度や書式に希望があれば指示してください。