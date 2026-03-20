# CHANGELOG

すべての重要な変更点を Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) 準拠で日本語にて記載しています。  
このファイルはコードベースから実装内容を推測して作成しています。

なおバージョン番号はパッケージの __version__（src/kabusys/__init__.py）を参照しています。

未リリース
---------
（なし）

[0.1.0] - 2026-03-20
-------------------
初期リリース。日本株自動売買プラットフォームのコア機能群を実装・公開。

Added
- パッケージ基盤
  - kabusys パッケージ初期構成を追加。公開 API として data / strategy / execution / monitoring をエクスポート。
- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数の読み込み機能を実装。
  - プロジェクトルート検出（.git または pyproject.toml）に基づく自動 .env 読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応）。
  - .env パーサを堅牢化（コメント行・export 形式・シングル/ダブルクォート、エスケープ対応、インラインコメント処理など）。
  - OS 環境変数を保護する protected オプション（.env.local による上書き制御を含む）。
  - Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, Slack トークン/チャンネル, DB パス, KABUSYS_ENV/LOG_LEVEL の検証等）。
- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアント実装（認証、ページネーション、データ取得）。
  - レートリミット（120 req/min）を固定間隔スロットリングで実装（RateLimiter）。
  - リトライロジック（指数バックオフ、最大試行回数、408/429/5xx に対するリトライ。429 の Retry-After 優先）。
  - 401 受信時のトークン自動リフレッシュ（1 回まで）と ID トークンのモジュールレベルキャッシュ。
  - fetch_* 系のページネーション対応（daily_quotes / financial statements / market_calendar）。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT を用いた冪等性確保と PK 欠損行のスキップログ。
  - 入力変換ユーティリティ（_to_float / _to_int）を実装し、不正値を安全に扱う。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集機能を実装（デフォルト Yahoo Finance を含む）。
  - URL 正規化（トラッキングパラメータ除去・ソート・フラグメント除去・スキーム/ホスト小文字化）。
  - defusedxml を用いた安全な XML パース、HTTP スキーム検査、レスポンスサイズ制限（10 MB）などの安全対策。
  - バルク INSERT チャンク処理による効率的な DB 保存、INSERT RETURNING による挿入数管理（設計方針に基づく）。
- リサーチ（kabusys.research）
  - ファクター計算群を実装（calc_momentum, calc_volatility, calc_value）。
    - Momentum: 1/3/6 ヶ月リターン、200日移動平均乖離（ma200_dev）。
    - Volatility: 20 日 ATR、ATR 比率（atr_pct）、20 日平均売買代金、出来高比率。
    - Value: PER / ROE（raw_financials からの最新レコード参照）。
  - feature_exploration: 将来リターン計算（複数ホライズン対応）、IC（Spearman の ρ）計算、factor_summary、rank ユーティリティを実装。
  - 外部ライブラリに依存しない（標準ライブラリのみ）設計を明記。
  - zscore_normalize を利用するためのエクスポートを整備。
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research 側で算出した生ファクターをマージ、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用、Z スコア正規化（対象カラム指定）および ±3 クリップを行い features テーブルへ日付単位の置換（トランザクション＋バルク挿入）で冪等保存。
  - DuckDB クエリを用いて基準日以前の最新価格取得（休場日対応）を実装。
- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合し、コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。最終スコア（final_score）は重み付き合算（デフォルト重みを定義）。
  - シグモイド変換/平均化ユーティリティ、欠損コンポーネントを中立 0.5 で補完するロジックを実装し欠損バイアスを軽減。
  - Bear レジーム検出（ai_scores の regime_score 平均が負）により BUY シグナルを抑制。
  - BUY（閾値デフォルト 0.60）と SELL（ストップロス -8% / final_score の閾値未満）を判定し signals テーブルへ日付単位で置換（トランザクション＋バルク挿入）。SELL 優先ポリシー（SELL 対象は BUY から除外）を適用。
  - 重みの入力値検証（未知キー・非数・負値・NaN/Inf を無視）、合計が 1.0 でない場合は再スケールする挙動を実装。
- トランザクションとロギング
  - DB 書き込み部分はトランザクション（BEGIN/COMMIT/ROLLBACK）で原子性を確保。ROLLBACK 失敗時は警告ログ出力。
  - 関数・処理単位で詳細な logger.debug / logger.info / logger.warning を出力。

Security
- defusedxml を用いた RSS/ XML の安全処理（XML Bomb 等の防止）。
- ニュース URL 正規化とスキーム検査による SSRF 対策を考慮。
- .env 読み込み時に OS 環境変数を上書きしないデフォルト挙動と保護セットを導入。

Known issues / Not implemented
- ポジション関連の高度なエグジット条件（トレーリングストップ、時間決済）は未実装。positions テーブルに peak_price / entry_date 等の情報が必要（TODO として設計に明記）。
- news_collector の RSS パース以降の「銘柄コード紐付け(news_symbols)」の具体的な実装詳細は設計方針として述べられているが、コードの断片から完全な紐付けロジックは推測の範囲。
- 一部の処理は DuckDB の環境（テーブル定義 / インデックス）に依存。実稼働ではスキーマ整備が必要。
- 外部 API 呼び出し周りはネットワークや API 仕様変更に依存するため、運用時に追加の監視/エラーハンドリングが推奨される。

その他メモ
- デフォルト設定・閾値（株価 300 円、売買代金 5 億円、Z スコアクリップ ±3、BUY 閾値 0.60、停止損失 -8% など）は StrategyModel.md / DataPlatform.md に基づく固定値として実装されている。調整可能なパラメータは generate_signals の weights / threshold 等。
- research モジュールは外部依存を抑えた実装になっており、分析目的で単体利用が可能。

以上。