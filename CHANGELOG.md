Keep a Changelog 準拠の形式で、与えられたコードベースの内容から推測して作成した CHANGELOG.md（日本語）を下記に示します。実装の詳細はコードから推測したものであり、実際のコミット履歴とは異なる可能性があります。

Keep a Changelog
=================

全般
----
- この CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際の変更履歴やコミットメッセージがある場合はそちらを優先してください。

変更履歴
-------

## [0.1.0] - 2026-03-20
初回リリース（コードベースから推測）

### 追加
- パッケージ基礎
  - パッケージメタデータを公開（kabusys.__version__ = "0.1.0"）。
  - パッケージの公開モジュール一覧を定義（data, strategy, execution, monitoring）。

- 設定・環境管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env の行パーサーを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープに対応）。
  - _load_env_file により既存 OS 環境変数保護（protected set）や override 制御を実装。
  - Settings クラスを実装し、必須設定の取得（_require）やデフォルト値、妥当性検査（KABUSYS_ENV / LOG_LEVEL）を提供。
  - 各種設定プロパティを追加（J-Quants トークン、kabu API、Slack トークン/チャネル、DB パスなど）。

- データ取得 / 保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - 固定間隔のレートリミッタ（120 req/min）を実装。
    - 汎用リクエスト関数にリトライ（指数バックオフ、最大 3 回）、429 の Retry-After 処理、408/429/5xx の再試行判定を実装。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライするロジック（無限再帰防止のため allow_refresh フラグ）。
    - ページネーション対応（pagination_key）。
    - データ取得関数を追加（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB への保存関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。
    - ON CONFLICT DO UPDATE による冪等保存を採用。
    - fetched_at を UTC で記録（Look-ahead bias に配慮）。
    - PK 欠損レコードのスキップとログ警告。
  - データ変換ユーティリティ (_to_float, _to_int) を実装（安全な変換、空値処理、float 文字列の扱い）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news に保存する機能。
    - デフォルト RSS ソース（Yahoo Finance）を定義。
    - 記事ID を URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を担保。
    - URL 正規化: スキーム/ホストの小文字化、トラッキングパラメータ削除（utm_ 等）、フラグメント削除、クエリソート。
    - defusedxml を用いた XML パース（XML Bomb 等対策）。
    - SSRF 対策（HTTP/HTTPS スキーム制限、IP 検査などを想定する実装方針が記載）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）を設定しメモリ DoS を抑制。
    - バルク INSERT のチャンク化、トランザクションまとめ、INSERT RETURNING による正確な挿入数取得（方針説明）。
    - ログ出力・警告の実装。

- 研究用ファクター計算 (kabusys.research.factor_research)
  - Momentum / Volatility / Value に関するファクター計算を実装。
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を計算。
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算（EPS が 0/欠損の場合は None）。
  - DuckDB 上の prices_daily / raw_financials テーブルのみを参照する設計。

- 研究支援ユーティリティ (kabusys.research.feature_exploration)
  - 将来リターン計算 calc_forward_returns（任意ホライズンのページ内 LEAD を使った実装）。
  - スピアマン IC 計算 calc_ic（ランク変換、tie 対応）。
  - factor_summary（count/mean/std/min/max/median の統計サマリー）。
  - rank ユーティリティ（同順位は平均ランク、丸めによる tie 検出対策あり）。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - 研究環境で計算した生ファクターを正規化・合成し features テーブルへ保存する処理を実装（build_features）。
    - calc_momentum / calc_volatility / calc_value から生ファクターを取得、マージ、ユニバース（株価 >= 300円、20日平均売買代金 >= 5億円）フィルタを適用。
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）および ±3 でクリップ。
    - 日付単位で DELETE→INSERT のトランザクション置換により冪等性を保証。
    - DuckDB トランザクション管理とロールバック時のログ保護。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して各銘柄の final_score を計算し signals テーブルに保存する機能を実装（generate_signals）。
    - momentum/value/volatility/liquidity/news の各コンポーネントスコア算出（シグモイド変換・補完ロジック）。
    - デフォルト重み (_DEFAULT_WEIGHTS) と閾値 (_DEFAULT_THRESHOLD=0.60) を採用。ユーザ指定 weights の検証・補完・再スケーリングを実装。
    - Bear レジーム判定（ai_scores の regime_score 平均が負、ただしサンプル数閾値あり）。
    - BUY シグナルは閾値超え（Bear 時は BUY 抑制）、SELL シグナルはポジション情報に基づくエグジット判定（ストップロス -8% など）。
    - BUY/SELL を DELETE→INSERT のトランザクション置換で冪等保存。SELL 優先ポリシー（SELL 対象は BUY から除外）。
    - ロギングにより詳細情報を出力。

- パッケージエクスポート
  - kabusys.research と kabusys.strategy の __init__ で主要関数を再エクスポート（利便性向上）。

### 変更
- 設計に関する記述を多数追加（Look-ahead bias 対策、冪等性、トランザクション単位の原子性、外部依存の制限など）。これらは実装ポリシーとしてコードに明記。

### 修正 / 強化
- 安全性・堅牢性の強化（推定）
  - news_collector で defusedxml 使用や受信サイズ制限、URL 正規化によるトラッキング除去を採用しセキュリティ対策を強化。
  - jquants_client の HTTP エラー処理やトークン自動リフレッシュで堅牢性を向上。
  - .env パーサーでクォート内エスケープやインラインコメントの処理を正しく扱うよう改善。
  - DuckDB 保存処理で PK 欠損行のスキップと警告を行うようにしてデータ不整合を緩和。

### 未実装／今後の改善候補（コード中の TODO）
- signal_generator のトレーリングストップや時間決済等、positions テーブルに依存する高度なエグジット条件は未実装。
- news_collector の SSRF や IP 検査の詳細実装（図示されている設計方針に基づく追加検証が想定される）。
- 一部のユーティリティ（例: kabusys.data.stats の zscore_normalize）は別モジュールに実装済みで利用されている想定。実装・テストの補完が必要。

既知の互換性の破壊 (BREAKING CHANGES)
- 初回リリースのためなし（0.1.0）。

注記
----
- 上記は提供されたソースコードの静的解析・コメント・定義からの推測に基づく CHANGELOG です。実際のコミットログやバージョン管理履歴が利用可能な場合は、本ファイルを基に調整してください。