# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルでは kabusys パッケージの初期リリース（v0.1.0）で導入された主要な機能・設計・注意点を記載します。

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-03-20

### 追加 (Added)
- 初期リリースとして kabusys パッケージを追加。
  - パッケージメタ情報:
    - バージョン: 0.1.0（src/kabusys/__init__.py）
    - エクスポート: data, strategy, execution, monitoring

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを追加。
    - プロジェクトルートは .git または pyproject.toml を基準に探索して特定（CWD 非依存）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーは export KEY=val、クォート、インラインコメント等の多数のケースに対応。
  - _load_env_file により OS 環境変数を保護しつつ .env/.env.local の上書き制御を実装。
  - Settings クラスを提供（プロパティで必須設定値・既定値・バリデーションを行う）。
    - 例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パス設定: DUCKDB_PATH, SQLITE_PATH（Path 型で展開）
    - KABUSYS_ENV / LOG_LEVEL の検証、is_live / is_paper / is_dev 補助プロパティ

- データ取得・保存: J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 固定間隔スロットリングによるレート制御（120 req/min）。
  - _request に指数バックオフと最大リトライ（3回）を導入。408/429/5xx に対するリトライ処理。
  - 401 受信時は ID トークンを自動リフレッシュして1回のみ再試行する仕組みを実装。
  - ページネーション対応の fetch_* 関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務四半期データ、ページネーション対応）
    - fetch_market_calendar（マーケットカレンダー）
  - DuckDB への保存関数（冪等: ON CONFLICT 用の UPSERT）:
    - save_daily_quotes → raw_prices
    - save_financial_statements → raw_financials
    - save_market_calendar → market_calendar
  - データ保存時に fetched_at を UTC ISO8601 で記録（Look-ahead バイアスのトレース可能性）
  - 型変換ユーティリティ _to_float / _to_int を提供（堅牢な変換ルール）

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード収集の実装（デフォルトに Yahoo Finance のビジネス RSS を含む）。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）。
  - defusedxml を用いた安全な XML パース、受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）、SSRF/スキーム検証等のセキュリティ対策を考慮。
  - raw_news への冪等保存（ON CONFLICT DO NOTHING）、news_symbols など銘柄紐付けを想定した設計。
  - バルク挿入のチャンク化によるパフォーマンス配慮。

- 研究用モジュール（Research） (src/kabusys/research/)
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算
    - calc_volatility: atr_20、atr_pct、avg_turnover、volume_ratio を計算
    - calc_value: per、roe を raw_financials と prices_daily から組合せて計算
    - 各関数は DuckDB の SQL ウィンドウ関数と Python を組合せて効率的に実装
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得
    - calc_ic: スピアマンのランク相関（IC）計算
    - factor_summary: 基本統計量（count/mean/std/min/max/median）集計
    - rank: 同順位は平均ランクで処理（round による tie 対応）
  - これらは research パッケージとして再エクスポートされる（src/kabusys/research/__init__.py）

- 戦略モジュール (src/kabusys/strategy/)
  - feature_engineering.build_features:
    - research で算出した生ファクターをマージ、ユニバースフィルタ（最低株価=300円、最低平均売買代金=5億円）を適用。
    - 数値ファクターを zscore_normalize で正規化し ±3 でクリップして features テーブルへ日付単位で置換（トランザクションで原子性を保証、冪等）。
    - 欠損・外れ値への配慮（非有限値の処理等）。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して component スコア（momentum/value/volatility/liquidity/news）を算出。
    - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完。
    - デフォルト重みと閾値（threshold=0.60）を用いた final_score 計算。ユーザー指定 weights の検証・正規化機能。
    - Bear レジーム判定（ai_scores の regime_score の平均が負かつサンプル数閾値を満たす場合）で BUY を抑制。
    - エグジット判定（SELL）:
      - ストップロス（終値/avg_price - 1 <= -8%）
      - final_score が threshold 未満（score_drop）
      - SELL は BUY より優先して除外、signals テーブルへ日付単位で置換（原子性を保証）
    - 出力は signals テーブルに書き込まれ、関数は書き込んだシグナル数を返す。

- 再利用可能なユーティリティ
  - data.stats.zscore_normalize を research と strategy で活用（research/__init__.py で再エクスポート）

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- RSS の XML パースに defusedxml を使用して XML Bomb 等に対処。
- ニュース収集で受信サイズ上限を設定（メモリ DoS 緩和）。
- URL 正規化でトラッキングパラメータを除外、スキーム検証により非 HTTP/HTTPS スキームを排除する設計を反映（SSRF 緩和）。
- J-Quants クライアントでトークン管理と自動リフレッシュを実装し、401 の取り扱いを安全に行う。

### 既知の制限・今後の注意点 (Known issues / Notes)
- execution パッケージは __init__.py が空であり、発注ロジックの具現化は今後の課題。
- features / signals / positions 等の DuckDB スキーマ（テーブル定義）は本リリースでは別途用意する必要があります。関数群は既存のテーブルスキーマを前提として実装されています。
- signal_generator のトレーリングストップ／時間決済等の一部エグジット条件は未実装（factor_research の注釈や signal_generator 内コメント参照）。
- get_id_token は settings.jquants_refresh_token が未設定の場合に ValueError を投げます。環境変数のセットが必要です。
- .env 自動読み込みはプロジェクトルートの特定に依存するため、パッケージ配布後や特殊な配置では KABUSYS_DISABLE_AUTO_ENV_LOAD による制御が必要な場合があります。
- 重み（weights）の入力検証では未知キーや負値、非数値を無視します。合計が 1.0 でない場合は再スケーリングされます。

---

今後のリリースでは以下の改良を検討しています:
- execution 層の実装（kabu API 経由の発注・注文管理）
- signals/positions の追加エグジット戦略（トレーリングストップ・時間決済）
- モニタリング・アラート（Slack 統合など）の実装（monitoring）
- パフォーマンス最適化（DuckDB クエリのチューニング、並列化）

もし誤りや補足してほしい点があればお知らせください。