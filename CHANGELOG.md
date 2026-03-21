# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを使用しています。将来のリリースでは Breaking change がある場合は明示します。

## [Unreleased]

## [0.1.0] - 2026-03-21

初回リリース。本リポジトリの主要機能を実装しました。以下はコードベースから推測してまとめた主要追加点・設計上の注意点です。

### Added

- パッケージ基礎
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。パッケージの公開エントリポイントとして modules を __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - .env 自動読み込み機構（プロジェクトルートの自動検出: .git または pyproject.toml）を実装。優先順位は OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env のパーサを独自実装（export プレフィックス対応、シングル／ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱いなど）。
  - 必須環境変数取得用ユーティリティ（_require）と、env/log_level 検証（許容値のチェック）を提供。
  - J-Quants / kabuステーション / Slack / DB パス等の設定プロパティを定義（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH）。

- データ取得・保存（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。
    - 固定間隔のレートリミッタ（120 req/min）を実装。
    - 再試行（指数バックオフ、最大 3 回）、HTTP 429 の Retry-After 考慮、ネットワークエラー再試行。
    - 401 発生時はリフレッシュトークンによる id_token 自動更新を 1 回行う仕組み。
    - ページネーション対応（pagination_key を用いたループ）。
    - レスポンス JSON デコード例外の扱い。
  - DuckDB への保存ユーティリティを実装（冪等性のため ON CONFLICT DO UPDATE / DO NOTHING を利用）。
    - save_daily_quotes, save_financial_statements, save_market_calendar を提供。
    - fetched_at を UTC ISO8601 で記録し、Look-ahead バイアスのトレーサビリティに配慮。
    - 不完全レコード（PK 欠損）や型変換エラーをスキップし、ログを出力。
    - 型変換ユーティリティ（_to_float, _to_int）を実装。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集して raw_news へ冪等保存する仕組みを実装。
  - セキュリティ・耐障害設計:
    - defusedxml を用いた XML パース（XML Bomb 等の対策）。
    - 受信最大バイト数制限（10 MB）によるメモリ DoS 対策。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホストの正規化、フラグメント除去、クエリソート）。
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を担保。
    - HTTP スキームの URL のみ許容（SSRF 対策の前提）。
    - DB はバルク挿入をチャンク化して処理（パフォーマンス / SQL 上限対策）。
  - デフォルト RSS ソース（例: Yahoo Finance）を定義。

- リサーチ（src/kabusys/research/*）
  - ファクター計算（factor_research.py）:
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）を計算する calc_momentum。
    - Volatility / Liquidity（atr_20, atr_pct, avg_turnover, volume_ratio）を計算する calc_volatility。
    - Value（per, roe）を計算する calc_value（raw_financials と prices_daily を組合わせ）。
    - 各関数は DuckDB 接続を受け取り、prices_daily / raw_financials のみを参照する設計。
  - 特徴量探索（feature_exploration.py）:
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、ホライズン検証）。
    - IC（Spearman の ρ）計算 calc_ic（ランク化、同順位は平均ランク）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median）。
    - rank ユーティリティ。
  - 研究用ユーティリティを __all__ で公開。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features を実装:
    - research モジュールの calc_momentum / calc_volatility / calc_value から生ファクターを取得、マージ。
    - 株価・流動性によるユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 数値ファクターを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップ。
    - features テーブルへ日付単位での置換（DELETE + バルク INSERT をトランザクション内で実施）により冪等性を保証。
    - DuckDB を用いた atomic な更新。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals を実装:
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算。
    - 各コンポーネントはシグモイドやスコア合成関数で 0..1 にマッピング。
    - デフォルト重みを実装（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。ユーザ指定重みを受け付け、検証および再スケーリングを行う。
    - Bear レジーム判定（ai_scores の regime_score 平均 < 0 かつサンプル数閾値を満たす場合）で BUY を抑制。
    - BUY シグナル閾値（デフォルト 0.60）を実装。
    - 保有ポジションに対する SELL 判定（ストップロス -8% とスコア低下）を実装（_generate_sell_signals）。
    - SELL を優先して BUY から除外し、signals テーブルへ日付単位の置換（トランザクション）を実施。
    - 欠損コンポーネントは中立値 0.5 で補完するポリシーを採用（欠損銘柄の不当な降格防止）。

- その他
  - ロギングやエラーハンドリングを各所に実装（警告ログ、デバッグログ、ROLLBACK の失敗時の補足ログ等）。
  - DuckDB を前提とした SQL クエリ群（ウィンドウ関数・LEAD/LAG/AVG/COUNT/ROW_NUMBER を多用）。

### Changed

- 該当なし（初回リリース）。

### Fixed

- 該当なし（初回リリース）。

### Security

- news_collector: defusedxml と受信サイズ制限、URL 正規化・スキーム制限によりセキュリティ上の配慮あり。
- jquants_client: 401 自動リフレッシュの制御やレート制限を実装し、誤ったトークン更新などのリスクを軽減。

### Known limitations / Notes

- signal_generator の SELL 判定で言及されているトレーリングストップや時間決済は未実装。positions テーブルに peak_price / entry_date 等の追加データが必要。
- 一部 SQL は対象テーブル（prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar 等）のスキーマ前提があるため、利用する際はスキーマ定義が必要。
- news_collector の RSS パーサ部分（フィードパースの詳細実装の続き）は、この抜粋で終了しており、フル実装では追加のパーシング・記事整形ロジックが存在する想定。
- 外部依存を最小化する設計（research モジュールは pandas 等不使用）が取られている一方で、パフォーマンスや大規模データ処理のチューニングは今後の改善点。

---

本 CHANGELOG はソースコードのコメント・実装内容から推測して作成しています。実際のユースケースやドキュメントと差異がある場合がありますので、リリースノートとして正式に使う際は実装者による確認を推奨します。