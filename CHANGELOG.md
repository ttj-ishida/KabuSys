# CHANGELOG

すべての変更は Keep a Changelog の仕様に従って記載しています。  
このファイルはプロジェクトのリリース履歴を人間が読みやすい形式でまとめたものです。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-20

初回公開リリース — 日本株自動売買システム "KabuSys" の基礎機能を実装しました。

### Added
- パッケージ初期化
  - パッケージメタ情報を `src/kabusys/__init__.py` に追加（version=0.1.0）。
  - 公開モジュール: data, strategy, execution, monitoring を公開。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは OS 環境変数から設定を読み込む機能を実装（`src/kabusys/config.py`）。
  - プロジェクトルート（.git または pyproject.toml を起点）を探索して .env/.env.local を自動読み込みする仕組みを追加。
  - 自動読み込みを無効化するフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供。
  - export 形式や引用符、エスケープ、インラインコメントに対応した堅牢な .env パーサーを実装。
  - OS 環境変数を保護する protected 上書きロジックを実装。
  - 必須環境変数取得関数 `_require` と `Settings` クラスを実装（J-Quants / kabuAPI / Slack / DB パス / 環境切替 / ログレベル等）。

- Data 層（kabusys.data）
  - J-Quants API クライアントを実装（`src/kabusys/data/jquants_client.py`）。
    - 固定間隔スロットリングによるレート制限（120 req/min）を実装（_RateLimiter）。
    - 指数バックオフを伴うリトライロジック（最大3回、408/429/5xx 等をリトライ対象）。
    - 401 を検出した場合の自動トークンリフレッシュ（1回のみ）とモジュールレベルの id_token キャッシュ。
    - ページネーション対応の fetch 関数:
      - fetch_daily_quotes（株価日足、ページネーション処理）
      - fetch_financial_statements（財務データ、ページネーション処理）
      - fetch_market_calendar（JPX カレンダー）
    - DuckDB への保存ユーティリティ:
      - save_daily_quotes：raw_prices へ冪等保存（ON CONFLICT DO UPDATE）
      - save_financial_statements：raw_financials へ冪等保存（ON CONFLICT DO UPDATE）
      - save_market_calendar：market_calendar へ冪等保存（ON CONFLICT DO UPDATE）
    - 型変換ユーティリティ `_to_float`, `_to_int` を提供し、データ不整合に寛容な保存を実現。
    - 取得時刻を UTC で記録し、look-ahead bias のトレースを容易にする設計。
  - ニュース収集モジュール（`src/kabusys/data/news_collector.py`）
    - RSS フィード収集の基盤実装（デフォルトソースに Yahoo Finance）。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、スキーム/ホスト小文字化、フラグメント除去）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）やチャンク挿入（_INSERT_CHUNK_SIZE）などの DoS 対策。
    - defusedxml を用いた XML の安全パース、SSRF 対策・不正スキーム拒否などセキュリティ配慮。
    - 記事 ID を URL 正規化の SHA-256 ハッシュ（先頭 32 文字）で生成して冪等性を担保する方針（ドキュメント記述）。

- Research 層（kabusys.research）
  - 要研究・解析用ユーティリティとファクター計算を実装（`src/kabusys/research/`）:
    - factor_research:
      - calc_momentum: 1/3/6 ヶ月リターン、MA200 乖離率を計算（営業日ベースのラグ窓）。
      - calc_volatility: 20日 ATR / atr_pct、平均売買代金、出来高比率を計算。
      - calc_value: 財務テーブルと株価を組み合わせて PER / ROE を算出。
    - feature_exploration:
      - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）での将来リターンを計算。
      - calc_ic: スピアマンランク相関（IC）を計算するユーティリティ。
      - factor_summary: 各ファクターの count/mean/std/min/max/median を算出。
      - rank: 同順位は平均ランクとするランク付け実装（丸め処理あり）。
    - research パッケージの __all__ を整備し、再利用しやすい API を提供。

- Strategy 層（kabusys.strategy）
  - 特徴量作成（feature_engineering）:
    - research の生ファクターを読み込み、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）し ±3 でクリップ。
    - 日付単位で features テーブルへトランザクション＋バルク挿入により置換（冪等）する処理を実装。
  - シグナル生成（signal_generator）:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - コンポーネントスコアはシグモイド変換や PER ベースの変換などを適用。
    - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）と閾値（BUY=0.60）をサポート。ユーザ指定 weights の検証・正規化を実装。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値到達時に BUY を抑制）。
    - エグジット判定（STOP-LOSS -8% および final_score の閾値未満で SELL）を導入。保有ポジションの欠損時の扱い（features に無い保有銘柄は score=0 と見なす）も定義。
    - signals テーブルへ日付単位の置換（トランザクション＋バルク挿入）で冪等性を保証。

### Changed
- （初回リリースのため変更履歴はありません）

### Fixed
- （初回リリースのため修正履歴はありません）

### Security
- .env パーサーでの引用符・エスケープ処理、コメント取り扱いの強化により誤読やインジェクション風味の問題を軽減。
- news_collector で defusedxml を使用して XML 関連の脆弱性（XML Bomb 等）を回避。
- ニュース取得で受信バイト数制限、URL 正規化と不正スキーム拒否等を導入して SSRF / DoS リスクを低減。
- J-Quants クライアントで 401 発生時の安全なトークンリフレッシュ制御（無限再帰回避）を実装。

### Notes / Known limitations
- 一部の戦略ルールは将来的な拡張を想定:
  - signal_generator の SELL 条件には「トレーリングストップ」「時間決済（保有 60 営業日超）」が未実装で、positions テーブルに peak_price / entry_date 等が必要。
- news_collector の一部挿入処理（例えば INSERT RETURNING を用いた挿入件数の正確な取得）や銘柄紐付け処理（news_symbols）等は設計方針として記述されており、実装は継続の対象。
- 外部モジュール（kabusys.data.stats の zscore_normalize 等）は本リリースで利用前提となっており、互換性を保つ必要がある。

---

今後はバグ修正、内部設計の改善、追加の戦略ルールや execution 層（発注連携）・monitoring（アラート等）の実装を予定しています。必要であれば各モジュールごとの詳細な変更履歴や、導入手順（.env.example, DB スキーマ等）を別途作成します。