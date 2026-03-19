# Keep a Changelog
すべての注目すべき変更点を追跡します。  
このファイルは Keep a Changelog の形式に準拠しています。  

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティ修正

## [Unreleased]
- 今後のリリースに向けた未リリースの変更点をここに記載します。

## [0.1.0] - 2026-03-19
初期リリース。プロジェクトのコア機能を実装しました。

### Added
- パッケージ構成
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - public API: kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring を __all__ として定義。

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込みを実装（OS 環境変数の保護・優先度管理）。
  - プロジェクトルート自動検出ロジック（.git または pyproject.toml を基準）。
  - .env 行パーサの実装（コメント行・export 形式・クォート・エスケープ・インラインコメント処理に対応）。
  - Settings クラスを提供し、J-Quants トークン、kabu API 設定、Slack 設定、DB パス、実行環境フラグ（development/paper_trading/live）などをプロパティで取得。
  - 設定値のバリデーション（env 値・LOG_LEVEL 等の検証、未設定時は ValueError を送出）。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - 固定間隔スロットリングによるレート制限制御（120 req/min）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx 対応、429 の Retry-After 考慮）。
  - 401 の場合の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ共有。
  - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar 実装。
  - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）。ON CONFLICT を用いた更新に対応。
  - レスポンス整形ユーティリティ（_to_float, _to_int）を実装。

- ニュース収集 (kabusys.data.news_collector)
  - RSS からニュースを収集して raw_news に保存する設計とユーティリティを追加。
  - セキュリティおよび堅牢性対策を導入: defusedxml による XML パース、受信サイズ上限、URL 正規化（トラッキングパラメータ除去、スキーム/ホスト正規化）、SSRF 対策（HTTP/HTTPS のみ想定）、記事ID の SHA-256 ハッシュ化（冪等性）など。
  - デフォルト RSS ソース定義、チャンクサイズや最大受信バイト数等の定数を定義。

- リサーチ（研究）機能 (kabusys.research)
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率の計算。ウィンドウのデータ不足を考慮。
    - calc_volatility: 20日 ATR、相対 ATR (atr_pct)、20日平均売買代金、出来高比率の計算。true_range の NULL 伝播処理に配慮。
    - calc_value: raw_financials と価格を組み合わせて PER / ROE を計算。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト 1/5/21）の将来リターンを一度のクエリで取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。サンプル不足時は None を返す。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
    - rank: 同順位は平均ランクとするランク化ユーティリティ。
  - 研究用 API は外部ライブラリに依存せず、DuckDB のみ参照（prices_daily 等）。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date): research モジュールで計算した raw ファクターをマージし、ユニバースフィルタ（最小株価、平均売買代金）、Z スコア正規化（外部 zscore_normalize を使用）、±3 クリップを行い features テーブルへ日付単位で置換（トランザクション）する。冪等性を担保。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold, weights): features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算、重み付け合算して final_score を求め、BUY/SELL シグナルを生成して signals テーブルへ日付単位で置換（トランザクション）。
  - 特徴:
    - シグモイド変換、欠損コンポーネントの中立補完（0.5）、重みの検証と正規化（合計が 1 ではない場合の再スケール）、不正な重みの警告。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合。サンプル数不足時は Bear とみなさない）。
    - SELL 判定（ストップロス -8% と final_score の閾値割れ）。価格欠損時の処理、保有銘柄が features に無ければ警告とともに score=0 と見なす。
    - BUY と SELL の優先順位管理（SELL 対象は BUY から除外しランク再付与）。
    - ロギングによる詳細メッセージ。

- strategy パッケージのエクスポート
  - build_features / generate_signals をトップレベルにエクスポート。

### Changed
- 初期リリースのため該当なし。

### Fixed
- 初期リリースのため該当なし。

### Security
- news_collector で defusedxml を利用し XML 関連の脆弱性を軽減。
- RSS URL 正規化や受信サイズ制限、HTTP スキームチェックなどにより SSRF / DoS 対策を考慮。

### Known limitations / TODO / 注意事項
- news_collector の一部実装はファイル末尾で切れている（継続実装が必要）。
- generate_signals の SELL 条件について、トレーリングストップ（peak_price が必要）や時間決済（保有 60 営業日超）などは未実装で注記あり。
- 一部テーブルスキーマ（features, ai_scores, signals, positions, raw_prices, raw_financials, market_calendar 等）や zscore_normalize の実装はこの差分に含まれないため、実運用時には DB スキーマ・ユーティリティ実装の確認が必要。
- J-Quants クライアントはネットワーク呼び出しを行うため、テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD 等の環境変数を利用して自動ロードを制御し、モックを用いたテストを推奨。

---

（本 CHANGELOG はソースコードの docstring と実装から推測して作成しています。実際のリリースノートを作成する際はコミット履歴やリリース方針に基づいて調整してください。）