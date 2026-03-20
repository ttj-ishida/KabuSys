# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
フォーマット: https://keepachangelog.com/（日本語訳準拠）

注: 以下の記載はリポジトリ内のソースコードから推測して作成した初期リリースの要約です。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-03-20

Added
- パッケージ初期リリース "KabuSys" を追加
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
- 環境・設定管理
  - .env ファイルおよび環境変数の自動ロード機能を実装（プロジェクトルートの検出は .git または pyproject.toml に基づく）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（src/kabusys/config.py）。
  - .env 行パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、コメント処理などに対応（細かいケースを考慮）。
  - 必須設定取得関数（_require）と Settings クラスを提供。J-Quants / kabu API / Slack / DB パス / 実行環境・ログレベルの検証ロジックを含む。
  - 環境値の妥当性検査（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。

- データ取得・保存（J-Quants クライアント）
  - J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）。
    - 固定間隔レートリミッタ（120 req/min）を実装し API 呼び出し間隔を管理。
    - 再試行ロジック（指数バックオフ、最大 3 回）とステータスコード 408/429/5xx の再試行対応。
    - 401 受信時はリフレッシュトークンから ID トークンを自動更新して 1 回リトライする仕組みを実装。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装し、ON CONFLICT（Upsert）で冪等性を確保。
    - 型変換ユーティリティ：_to_float / _to_int（不正値や空値を安全に扱う）。
    - 取得時の fetched_at に UTC ISO タイムスタンプを付与（Look-ahead バイアス追跡のため）。

- ニュース収集
  - RSS フィード収集モジュールを実装（src/kabusys/data/news_collector.py）。
    - デフォルト RSS ソース（Yahoo Finance）を定義。
    - URL 正規化（トラッキングパラメータ削除、スキーム/ホスト小文字化、フラグメント削除、クエリソート）と記事 ID のハッシュ化による冪等性。
    - defusedxml を用いた XML 解析で XML Bomb 等を軽減。
    - 受信サイズ上限（10 MB）や SSRF に配慮した URL 扱いの方針を記載。
    - DB へのバルク挿入をチャンク化して効率化・安全化（チャンクサイズ定義）。
    - raw_news / news_symbols への紐付けを想定した設計。

- 研究・ファクター計算
  - research パッケージに複数ユーティリティを追加（src/kabusys/research/ 以下）。
    - ファクター計算モジュール（factor_research.py）
      - Momentum（1M/3M/6M リターン、200 日移動平均乖離）、Volatility（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率）、Value（PER、ROE）を計算する関数を実装。
      - 各算出は prices_daily / raw_financials テーブルのみを参照し、データ不足時は None を返す仕様。
      - DuckDB 上でのウィンドウ関数・ラグ・平均等を活用した SQL ベースの実装。
    - 特徴量探索モジュール（feature_exploration.py）
      - 将来リターン計算（calc_forward_returns: 複数ホライズン対応、範囲チェックあり）。
      - IC（Information Coefficient）計算（calc_ic: Spearman の ρ をランク計算で実装、最小サンプル判定）。
      - 基本統計量要約（factor_summary）とランク変換ユーティリティ（rank）。
    - research パッケージの __init__ で主要関数を再公開。

- 戦略（feature engineering / signal generation）
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - research で計算した生ファクターを結合して features テーブルへ保存する build_features を実装。
    - ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - Z スコア正規化（外部 zscore_normalize を使用）後に ±3 でクリップし、日付単位での置換（DELETE + INSERT）による冪等な保存をトランザクションで保証。
    - 休場日や当日の欠損を考慮して target_date 以前の最新価格を参照する実装。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合して final_score を計算し、BUY / SELL シグナルを生成する generate_signals を実装。
    - コンポーネントスコア（momentum/value/volatility/liquidity/news）を個別に算出（シグモイド変換等）。
    - デフォルト重みのマージ・バリデーション・合計が 1.0 でない場合の再スケール処理を実装。無効な重みは警告して無視。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値以上の場合）により BUY を抑制。
    - SELL 条件にストップロス（終値基準 -8%）とスコア低下（threshold 未満）を実装。価格欠損や features 欠損時の安全処理（ログ出力してスキップ・score=0 扱い）あり。
    - signals テーブルへの日付単位置換（トランザクション）で冪等性を保証。
    - 生成後の BUY/Sell 列の優先ルール（SELL を優先して BUY から除外し、ランクを再付与）。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- news_collector で defusedxml を使用するなど外部入力（RSS/XML）に対する防御策を組み込み。
- J-Quants クライアントでトークン管理と再試行時のトークンリフレッシュを制御し、無限再帰を防止するフラグ（allow_refresh）を導入。
- ニュース収集で受信バイト数上限・URL 正規化・トラッキングパラメータ除去などを実装。

Notes / Implementation details
- DuckDB をストレージ層として想定し、各モジュールは主に prices_daily / raw_prices / raw_financials / features / ai_scores / positions / signals / market_calendar 等のテーブルを参照・更新する設計。
- 多くの DB 操作は DELETE + bulk INSERT をトランザクション内で行い、日付単位の「置換（upsert by date）」で冪等性と原子性を担保。
- 外部依存を最小化する方針（research モジュールは pandas 等に依存しない純 Python + SQL 実装）。

Authors
- ソースコード内のモジュール実装に基づく推測による CHANGELOG。

--- 

（補足）上記はリポジトリ内のソースコードから機能や設計意図を推測してまとめた CHANGELOG です。実際のコミット履歴やリリースノートとは差異がある可能性があります。必要であれば、コミット履歴ベースのより正確な CHANGELOG へ更新できます。