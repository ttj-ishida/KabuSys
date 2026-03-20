# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」仕様に準拠しています。

履歴はセマンティックバージョニングに従います。  

## [Unreleased]

- なし

## [0.1.0] - 2026-03-20

Added
- パッケージ全体の初期実装を追加（バージョン 0.1.0）。
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring

- 環境設定 / ローダー (kabusys.config)
  - .env ファイルまたは環境変数から設定値を自動読み込みする仕組みを実装。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を基準に探索（__file__ を起点）。
  - .env と .env.local を読み込み、OS 環境変数を保護する protected 上書き制御を実装。
  - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント処理）。
  - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - Settings クラスを実装し、必須環境変数の取得メソッド（_require）や各種プロパティ（J-Quants / kabu API / Slack / DB パス / ログレベル / 環境種別判定）を提供。
  - KABUSYS_ENV / LOG_LEVEL の値検証（許容値のチェック）を追加。

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter を実装。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx 対象）を実装。
    - 401 応答時にリフレッシュトークンで自動トークン更新し 1 回リトライする挙動を実装。
    - ページネーション対応のフェッチ関数を実装:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（財務データ）
      - fetch_market_calendar（JPX カレンダー）
    - レスポンスの JSON デコードエラーやネットワークエラーをハンドリング。
  - DuckDB への保存関数を実装（冪等性を確保する ON CONFLICT アップサートを使用）:
    - save_daily_quotes (raw_prices)
    - save_financial_statements (raw_financials)
    - save_market_calendar (market_calendar)
  - レスポンス→型変換ユーティリティを実装:
    - _to_float / _to_int（安全な変換、空値・不正値の扱い）

- ニュース収集 (kabusys.data.news_collector)
  - RSS ベースのニュース収集モジュールを実装（記事の正規化・安全対策を実装）。
    - URL 正規化（トラッキングパラメータ除去、スキーム・ホスト小文字化、フラグメント削除、クエリソート）。
    - defusedxml を用いた XML パースで XML Bomb 等の攻撃対策。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 対策。
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）を用いる方針（冪等性確保）。
    - 記事テキストの前処理（URL 除去、空白正規化）やパラメータ除去ルールを実装。
    - バルク挿入のチャンク化や ON CONFLICT ベースの冪等保存方針を想定（実装方針記載）。

- 研究用ファクター計算 (kabusys.research)
  - factor_research モジュール:
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev を DuckDB SQL で計算（ウィンドウ集約）。
    - calc_volatility: atr_20, atr_pct（ATR の相対値）、avg_turnover, volume_ratio を計算。true_range の NULL 伝播制御を実装。
    - calc_value: per, roe を raw_financials と prices_daily から結合して計算（target_date 以前の最新財務データを取得）。
  - feature_exploration モジュール:
    - calc_forward_returns: 与えたホライズン群に対する将来リターンを 1 クエリで取得（LEAD を活用）。
    - calc_ic: スピアマンのランク相関（IC）を実装（同順位は平均ランクで処理、最小サンプル数チェック）。
    - factor_summary: count/mean/std/min/max/median といった基礎統計を計算。
    - rank: ランク変換（同順位は平均ランク、丸めによる ties 対応）。
  - 研究 API は DuckDB の prices_daily / raw_financials のみ参照し、本番口座/API へのアクセスは行わない方針。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features を実装:
    - research モジュール（calc_momentum / calc_volatility / calc_value）から生ファクターを取得。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラムを zscore_normalize（kabusys.data.stats 依存）し ±3 でクリップ。
    - DuckDB の features テーブルへ日付単位で DELETE→INSERT の置換（トランザクションで原子性確保）。
    - target_date 以前の最新終値を参照して休場日やデータ欠損に対応。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals を実装:
    - features / ai_scores / positions を参照して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - Z スコアをシグモイドで [0,1] に変換し、欠損コンポーネントは中立 0.5 で補完。
    - デフォルト重みを実装（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。外部指定 weights を検証・正規化。
    - Bear レジーム判定 (ai_scores の regime_score 的評価) を実装し、Bear 時は BUY シグナルを抑制。
    - BUY シグナル閾値のデフォルトを 0.60 として実装。
    - SELL（エグジット）判定を実装:
      - ストップロス（終値 / avg_price - 1 < -8%）
      - スコア低下（final_score が threshold 未満）
    - signals テーブルへ日付単位の置換（トランザクションで原子性確保）。
    - SELL が BUY を優先して除外するポリシーを採用（SELL 優先）。

- パッケージエクスポート
  - strategy パッケージの __init__ で build_features / generate_signals を公開。

Changed
- 初版のため「変更」は該当なし。

Fixed
- 初版のため「修正」は該当なし。

Notes / Known limitations
- signal_generator の未実装・保留事項:
  - トレーリングストップ（直近最高値からの -10%）や時間決済（保有 60 営業日超過）は未実装（positions テーブルに peak_price / entry_date が必要）。
- news_collector の一部保存ロジック（raw_news への実際の INSERT 実装など）は方針・ユーティリティが記述されているが、提供されたスニペットでは完全な保存処理の実装/検証が確認できないため、保存周りは実運用前に確認が必要。
- API クライアントは HTTP/URL エラーや JSON エラーをハンドリングするが、実運用ではネットワーク制御・監視・テスト（レート/リトライの挙動確認）が推奨される。
- DuckDB テーブル定義（スキーマ）は CHANGELOG に含まれていません。実運用前にスキーマ（raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar など）を整備してください。

Acknowledgements / Design
- 本リリースはルックアヘッドバイアス回避、冪等性、セキュリティ（XML パース/SSRF/DoS 対策）を設計方針として重視して実装されています。
- 研究（research）コードは標準ライブラリのみで動作するように設計されており、外部依存（pandas など）を避けています。

リリース / バージョン情報
- バージョン: 0.1.0
- 付記: __version__ = "0.1.0" に対応

（必要であれば、次回リリース向けに Unreleased セクションに機能追加・改善予定を追記してください。）