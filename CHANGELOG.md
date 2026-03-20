Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」の形式に準拠します。

フォーマット
-----------
- 変更はカテゴリ（Added, Changed, Fixed, Security, etc.）ごとに分類します。
- バージョンごとにリリース日を記載します。

Unreleased
----------
（現在未リリースの変更はここに記載）

[0.1.0] - 2026-03-20
--------------------

Added
- 初期リリース。日本株自動売買システム "KabuSys" のコアモジュールを追加。
  - パッケージ初期化:
    - src/kabusys/__init__.py に version (0.1.0) と公開モジュール一覧を追加。
  - 環境設定:
    - src/kabusys/config.py
      - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
      - .env 読み込みの上書き挙動: OS 環境変数を保護する protected 機構、.env と .env.local の優先度制御。
      - .env パースの堅牢化（export プレフィックス対応、クォート中のエスケープ、行末コメント処理等）。
      - 必須環境変数取得ヘルパ（_require）。Settings クラスで各種設定（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス、環境/ログレベル判定）を提供。
      - KABUSYS_ENV / LOG_LEVEL の入力検証（許容値の定義）。
  - データ取得 / 保存:
    - src/kabusys/data/jquants_client.py
      - J-Quants API クライアントを実装（ページネーション対応）。
      - レート制限制御（固定間隔スロットリング、デフォルト 120 req/min）。
      - リトライ（指数バックオフ、最大3回）、HTTP 408/429/5xx に対する再試行、429 の Retry-After 優先処理。
      - 401 受信時にリフレッシュトークンで自動的に ID トークンを再取得して 1 回だけ再試行。
      - id_token のモジュールレベルキャッシュを実装（ページネーション間で共有）。
      - fetch_* 系関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）と、DuckDB へ冪等保存する save_* 関数（ON CONFLICT DO UPDATE）を実装。
      - データ変換ユーティリティ（_to_float, _to_int）を実装し、型安全に変換。
    - src/kabusys/data/news_collector.py
      - RSS フィードからニュースを収集して raw_news へ保存する処理を実装。
      - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント削除）、記事ID を SHA-256 ハッシュ（先頭32文字）で生成して冪等性を担保。
      - defusedxml を用いた XML パース（XML Bomb 対策）、HTTP スキーム制限、受信サイズ制限（10MB）等の安全対策。
      - バルク INSERT のチャンク化とトランザクションまとめ保存、INSERT 結果に基づく正確な挿入件数取得。
  - 研究用モジュール（research）:
    - src/kabusys/research/factor_research.py
      - モメンタム（mom_1m, mom_3m, mom_6m, ma200_dev）、ボラティリティ（atr_20, atr_pct）、流動性（avg_turnover, volume_ratio）、バリュー（per, roe）を DuckDB の prices_daily / raw_financials を参照して計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
      - 過去データのスキャン範囲や最小サンプル条件を明示（例: MA200 の窓が 200 行未満なら ma200_dev は None）。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算（calc_forward_returns、デフォルト horizon=[1,5,21]）を実装（単一クエリで複数ホライズン取得、カレンダーバッファで週末/祝日を吸収）。
      - IC（Information Coefficient）計算（calc_ic、Spearman の ρ をランクに変換して計算）、rank ユーティリティ、factor_summary（各ファクターの count/mean/std/min/max/median）を実装。
    - research パッケージの __init__.py で主要関数を再エクスポート。
  - 戦略（strategy）:
    - src/kabusys/strategy/feature_engineering.py
      - 研究環境で算出した生ファクターをマージ・ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5億円）を適用し、数値ファクターを Z スコア正規化（zscore_normalize を利用）して ±3 でクリップ、features テーブルへ日付単位置換（トランザクション＋バルク挿入で冪等）する build_features を実装。
    - src/kabusys/strategy/signal_generator.py
      - features と ai_scores を統合して最終スコア final_score を計算し、BUY/SELL シグナルを生成して signals テーブルへ日付単位置換で保存する generate_signals を実装。
      - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）と BUY 閾値 0.60 を採用。重みのバリデーションと合計 1.0 に再スケーリングを実装。
      - コンポーネントスコア計算（シグモイド変換、欠損は中立 0.5 で補完）、AI レジーム平均による Bear 判定（サンプル閾値あり）で BUY を抑制。
      - エグジット判定（_generate_sell_signals）としてストップロス（終値/avg_price -1 < -8%）とスコア低下（final_score < threshold）を実装。SELL 優先のロジックで BUY から除外し再ランク付け。
    - strategy パッケージの __init__.py で build_features / generate_signals を公開。

Changed
- （初回リリースのため変更履歴はなし）

Fixed
- （初回リリースのため修正履歴はなし）

Security
- news_collector で defusedxml を使用した安全な XML パースを導入。RSS の受信サイズ上限、HTTP スキームチェック、トラッキングパラメータ除去による URL 正規化などの対策を実施。
- jquants_client の HTTP リトライでは 429 の Retry-After を考慮、401 時はトークン再取得を 1 回のみ行うことで無限再帰を回避。

Notes / Implementation details
- DuckDB を主要なストレージとして想定し、各種 save_* 関数は raw_* / market_calendar / raw_financials 等のテーブルへ冪等に保存する挙動。
- ルックアヘッドバイアス対策として、strategy / research の計算はいずれも target_date 時点のデータのみを使用する設計方針。
- ロギングを各モジュールに組み込み、警告・情報を出力する（例: 読み込みスキップ、ROLLBACK 失敗など）。
- public API は各パッケージの __init__.py で必要な関数を明示的に公開。

今後の予定（例）
- PBR / 配当利回り等バリューファクターの追加実装。
- positions テーブルに peak_price / entry_date 等を格納して、トレーリングストップ・時間決済を実装。
- execution 層（kabu ステーション連携）およびモニタリング（Slack 通知など）の実装・統合。

References
- 各モジュール内のコメント（StrategyModel.md, DataPlatform.md 等）にアルゴリズム仕様や設計意図が記載されています。必要に応じて参照してください。