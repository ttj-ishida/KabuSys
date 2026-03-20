# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
バージョン番号はパッケージの __version__ に基づいています。

フォーマット:
- "Added" = 新機能
- "Changed" = 既存機能の変更
- "Fixed" = 修正
- "Security" = セキュリティに関する重要事項
- リリース日には本ドキュメント作成日を使用しています。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-20

Added
- パッケージ初期リリース: kabusys (日本株自動売買システム) を公開。
- 環境設定管理モジュール (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする機能を追加。
  - 読み込みの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env 行パーサを実装（コメント行、export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの扱いを考慮）。
  - .env ファイル読み込み時の上書き制御（override）と、OS 環境変数を保護する protected キーセットを実装。
  - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DBパス / システム env/log_level などのプロパティ経由で設定を取得可能に。
  - 必須環境変数未設定時は ValueError を送出する _require ユーティリティを提供。
  - KABUSYS_ENV の許容値 (development, paper_trading, live) と LOG_LEVEL のバリデーションを実装。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - 固定間隔のレートリミッタ（120 req/min）を組み込み。
  - 冪等性を考慮した保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。DuckDB 側は ON CONFLICT DO UPDATE を使用。
  - ページネーション対応の fetch_* 関数（daily_quotes, financial_statements, market_calendar）。
  - HTTP リトライロジック（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）を実装。モジュールレベルで ID トークンをキャッシュしページネーション間で共有。
  - 型変換ユーティリティ (_to_float / _to_int)、PK 欠損レコードのスキップと警告ログを実装。
  - fetched_at を UTC ISO8601 形式で記録（look-ahead bias のトレースに対応）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからのニュース収集機能を実装（既定ソースに Yahoo Finance RSS を追加）。
  - URL 正規化・トラッキングパラメータ除去、ハッシュベースの記事ID（重複排除）により冪等性を確保する設計。
  - defusedxml を用いた安全な XML パース、受信サイズ上限（10 MB）、HTTP スキーム検証などのセキュリティ対策を実装。
  - テキスト前処理（URL除去・空白正規化）、news <-> 銘柄紐付けを想定。
  - DB へのバルク挿入はチャンク分割とトランザクションで実行し、実際に挿入された件数を正確に返す設計。

- リサーチモジュール (kabusys.research)
  - factor_research: Momentum / Volatility / Value のファクター計算を実装（prices_daily / raw_financials を利用）。
    - Momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）。データ不足時は None を返す。
    - Volatility: 20日 ATR（atr_20）と相対 ATR（atr_pct）、20日平均売買代金、volume_ratio。true_range の NULL 伝播を制御。
    - Value: per（price / eps）と roe。target_date 以前の最新財務データを使用。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを高速に取得する SQL 実装。
    - calc_ic: スピアマンのランク相関（IC）を実装（同順位は平均ランクで処理）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー関数を実装。
    - rank: 同順位を平均ランクにするランク化ユーティリティ（丸めで ties の検出漏れを防止）。

- 戦略モジュール (kabusys.strategy)
  - feature_engineering.build_features
    - research モジュールで計算した生ファクターをマージしてユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップし features テーブルへ日付単位でUPSERT（トランザクションで原子性保証）。
    - ルックアヘッドバイアスを避けるため target_date 時点のデータのみを使用する設計。
  - signal_generator.generate_signals
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum, value, volatility, liquidity, news）を算出。
    - final_score を重み付き合算（デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。重みは正規化され合計 1.0 になるよう補正。
    - デフォルト BUY 閾値 0.60、STOP_LOSS -8% を実装。Bear レジーム（AI の regime_score 平均が負）では BUY シグナルを抑制。
    - BUY/SELL シグナルの生成と signals テーブルへの日付単位の置換（トランザクションで原子性保証）。SELL は BUY より優先し、優先した後に BUY のランクを再付与。
    - 欠損コンポーネントは中立 0.5 で補完するポリシーを採用。

Changed
- なし（初回リリースのため）

Fixed
- なし（初回リリースのため）

Security
- news_collector: defusedxml を利用した安全な XML パースを採用し、XML Bomb 等の攻撃耐性を考慮。
- RSS 取得時に最大受信バイト数を設定してメモリ DoS を緩和。
- J-Quants クライアント: 401 によるトークン更新時の無限再帰防止（allow_refresh 制御）とリトライポリシーを実装。

Notes / Migration
- 環境変数
  - 自動 .env 読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で有用）。
  - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。未設定時は Settings のプロパティアクセスで ValueError が発生します。
  - KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかに設定してください。LOG_LEVEL は "DEBUG","INFO","WARNING","ERROR","CRITICAL" のいずれかを指定してください。
- DB
  - デフォルトの DuckDB / SQLite パスは Settings.duckdb_path / Settings.sqlite_path で確認できます。必要に応じて環境変数（DUCKDB_PATH / SQLITE_PATH）で上書きしてください。
- J-Quants
  - API 利用にあたっては JQUANTS_REFRESH_TOKEN を必ず用意してください。get_id_token() はこのリフレッシュトークンから idToken を取得します。
  - レート制限とリトライは組み込まれていますが、高頻度呼び出し時はシステム全体の呼び出し量に注意してください。
- Strategy / Research
  - すべての戦略・リサーチ関数は DuckDB 接続を受け取り prices_daily / raw_financials / features / ai_scores / positions 等のテーブルを参照します。本実装は外部の発注 API への直接呼び出しを行いません（execution 層とは分離）。
  - build_features / generate_signals は日付単位での置換（DELETE→INSERT）により冪等性を担保します。実運用では十分なテストと監視を行ってください。

今後の予定（短期）
- strategy の保有ポジションに関する追加条件（トレーリングストップ、時間決済）を実装予定（positions テーブルに peak_price / entry_date が必要）。
- news_collector の記事ID生成やシンボル抽出ロジックの継続改善。
- テストカバレッジの拡充と CLI / daemon 化の検討。

---
この CHANGELOG はソースコードから推測して作成しています。実際の変更履歴やリリースノートと差異がある場合は、正確な履歴に合わせて修正してください。