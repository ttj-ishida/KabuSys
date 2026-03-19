Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。<br>
The project adheres to Semantic Versioning.

テンプレート
-----------

- Unreleased: 現在開発中の変更（次バージョンでリリース予定）
- 各リリース: 追加（Added）、変更（Changed）、修正（Fixed）、削除（Removed）、セキュリティ（Security）などのセクションで記載

Unreleased
----------

（なし）

0.1.0 - 2026-03-19
------------------

初期リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。主な追加点は以下の通りです。

Added
- パッケージ基礎
  - パッケージ名: kabusys、バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - __all__ に主要サブパッケージを公開: data, strategy, execution, monitoring。
- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - ロード優先度: OS 環境変数 > .env.local > .env
    - プロジェクトルート検出は .git または pyproject.toml を探索して決定（CWD に依存しない）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テストなどで利用）。
  - .env パーサ実装:
    - コメント行・空行のスキップ、export プレフィックス対応、クォート（シングル/ダブル）とバックスラッシュエスケープ処理、インラインコメント処理等に対応。
  - 環境変数保護機能:
    - OS 環境変数を保護（.env ファイルによる上書き防止）および .env.local での上書き挙動を制御。
  - Settings クラスを提供（settings インスタンス経由でアクセス）:
    - J-Quants / kabu ステーション / Slack / DB パス等のプロパティを定義。
    - env / log_level の検証（許容値チェック）や is_live / is_paper / is_dev 補助プロパティ。
    - duckdb/sqlite の既定パスを Path で返す。
- Data 層（src/kabusys/data）
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - レートリミッタ（120 req/min）の実装（固定間隔スロットリング）。
    - リトライロジック（指数バックオフ、最大 3 回。408/429/5xx を対象）を実装。
    - 401 受信時にリフレッシュトークンから自動で ID トークンを再取得して 1 回リトライする仕組み。
    - ページネーション対応のデータ取得（fetch_daily_quotes / fetch_financial_statements）。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等保存を行う。
    - JSON デコードエラーハンドリング、型変換ユーティリティ（_to_float / _to_int）を提供。
    - データ取得時の fetched_at を UTC ISO 形式で記録（Look-ahead バイアス対策）。
  - ニュース収集（src/kabusys/data/news_collector.py）
    - RSS フィード収集の基本実装（デフォルトで Yahoo Finance のカテゴリ RSS を設定）。
    - URL 正規化（トラッキングパラメータ除去、ソート、スキーム/ホスト小文字化、フラグメント除去）を実装。
    - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を保証。
    - defusedxml を用いた XML パース（XML Bomb 等の防御）、受信サイズ上限（10 MB）によるメモリ DoS 対策、HTTP スキームの検査などのセキュリティ考慮。
    - バルク INSERT のチャンク化（_INSERT_CHUNK_SIZE）とトランザクションまとめ挿入、挿入件数の正確な返却を想定。
- 研究（research）モジュール（src/kabusys/research）
  - factor_research.py
    - モメンタム（1m/3m/6m リターン、200 日移動平均乖離）、ボラティリティ（20 日 ATR / atr_pct）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER/ROE）を DuckDB の prices_daily / raw_financials を参照して計算する関数を実装（calc_momentum / calc_volatility / calc_value）。
    - 各種ウィンドウサイズやスキャン範囲の定数化と欠損時の None ハンドリング。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応、入力検証あり）。
    - スピアマン IC（ランク相関）計算（calc_ic）と rank ユーティリティ（同順位は平均ランク）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算するユーティリティ。
  - research パッケージ __all__ に主要関数を公開。
- Strategy 層（src/kabusys/strategy）
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - research モジュールで計算した生ファクターを結合・フィルタ・正規化して features テーブルに UPSERT（日付単位の置換）する処理を実装（build_features）。
    - ユニバースフィルタ実装:
      - 株価 >= 300 円、20 日平均売買代金 >= 5 億円（_MIN_PRICE / _MIN_TURNOVER）。
    - Z スコア正規化（zscore_normalize を利用）と ±3 でクリップ（_ZSCORE_CLIP）。
    - DuckDB トランザクションで日付単位の原子的置換を実行（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合して最終スコア（final_score）を算出し、BUY/SELL シグナルを生成して signals テーブルへ日付単位で置換保存する処理を実装（generate_signals）。
    - 重みと閾値の取扱い:
      - デフォルト重み: momentum 0.40 / value 0.20 / volatility 0.15 / liquidity 0.15 / news 0.10（_DEFAULT_WEIGHTS）。
      - BUY 閾値デフォルト: 0.60（_DEFAULT_THRESHOLD）。
      - ユーザ渡しの weights は検証（非数値・負値など無効値をスキップ）、既定とマージし合計が 1.0 でなければ再スケール。
    - コンポーネントスコア計算:
      - momentum: momentum_20, momentum_60, ma200_dev（シグモイド→平均）
      - value: PER を 1/(1+per/20) で変換（per が正である場合のみ）
      - volatility: atr_pct の逆符号をシグモイド変換（低ボラは高スコア）
      - liquidity: volume_ratio をシグモイド変換
      - news: ai_scores の ai_score をシグモイド（未登録は中立補完）
    - Bear レジーム判定:
      - ai_scores の regime_score の平均が負かつサンプル数 >= 3 の場合は Bear とみなし BUY を抑制（_is_bear_regime）。
    - SELL（エグジット）判定:
      - ストップロス: 現在終値 / avg_price - 1 < -8%（_STOP_LOSS_RATE）
      - スコア低下: final_score < threshold
      - price 欠損時は SELL 判定をスキップして誤クローズを防止
    - signals テーブルへの原子的書き込み（トランザクション + バルク挿入）。SELL 優先ポリシー（SELL 対象は BUY から除外してランクを再付与）。
- その他
  - research パッケージや strategy の主要関数を __all__ で公開（import 時の利便性向上）。
  - ロギングを各モジュールに追加し、重要な操作や警告を記録。

Security
- news_collector で defusedxml を使用し、XML に対する安全対策を導入。
- RSS 受信サイズ上限（10MB）や URL スキームチェック、トラッキングパラメータ除去等の処理で外部入力に対する堅牢性を向上。

Notes / Implementation details
- DuckDB のテーブルスキーマ（raw_prices, raw_financials, prices_daily, features, ai_scores, signals, positions, market_calendar, raw_news 等）を前提として実装しているため、実稼働前にスキーマ準備が必要です。
- 外部依存は最小化（research モジュールでは pandas 等に依存しない実装）。
- execution パッケージはプレースホルダ（発注層との結合は別途実装予定）。

Breaking Changes
- 初期リリースのため該当なし。

Deprecated
- なし。

Acknowledgements / TODO
- トレーリングストップや時間決済など、StrategyModel に記載の一部エグジット条件は未実装（positions に peak_price / entry_date 情報が必要）。
- news_collector の詳細な URL 安全性チェックや SSRF 対策の拡張、INSERT RETURNING による正確な挿入件数の実装など、今後改善予定。

以上。