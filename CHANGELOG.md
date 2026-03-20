CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

- 現時点で未リリースの変更はありません。

[0.1.0] - 2026-03-20
--------------------

Added
- 初回リリース (0.1.0)。
- パッケージ構成:
  - kabusys パッケージの基本エクスポートを追加（data, strategy, execution, monitoring）。
- 環境設定:
  - 環境変数・設定管理モジュールを実装（kabusys.config）。
    - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を探索して検出）。
    - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env ファイルのパースは export プレフィックス、クォート、インラインコメント、エスケープに対応。
    - .env.local は .env を上書き（既存 OS 環境変数は保護、protected 機能）。
    - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / システム設定等のプロパティを定義。
    - KABUSYS_ENV と LOG_LEVEL の許容値チェックを実装（不正値は ValueError）。
- データ取得・保存:
  - J-Quants API クライアントを実装（kabusys.data.jquants_client）。
    - 固定間隔のレートリミッタ（120 req/min 相当）。
    - 冪等性を考慮した DuckDB への保存関数（raw_prices/raw_financials/market_calendar）を実装、ON CONFLICT / DO UPDATE を使用。
    - ページネーション対応の fetch_* 関数（daily_quotes / statements / trading_calendar）。
    - リトライと指数バックオフ（最大 3 回）。HTTP 408/429/5xx を再試行対象に設定。429 の Retry-After を優先。
    - 401 はトークン自動リフレッシュして再試行（再帰防止のため1回のみ）。
    - モジュールレベルの ID トークンキャッシュを実装しページネーション間で共有。
    - レスポンスパース時の型安全な数値変換ユーティリティ（_to_float/_to_int）。
  - ニュース収集モジュールを実装（kabusys.data.news_collector）。
    - デフォルト RSS ソースを定義（例: Yahoo Finance）。
    - RSS 取得 → テキスト前処理 → raw_news への冪等保存ワークフローを実装。
    - defusedxml を利用して XML 関連の脆弱性対策を実施。
    - URL 正規化機能を実装（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
    - レスポンス最大サイズ制限（MAX_RESPONSE_BYTES）や受信バッファ制御でメモリ DoS を緩和。
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を保証。
    - バルク INSERT のチャンク処理を実装し SQL 文長・パラメータ数を抑制。
- リサーチ/ファクター:
  - ファクター計算モジュール（kabusys.research.factor_research）。
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（20日 ATR、相対 ATR、出来高比率等）、Value（PER/ROE）を計算。
    - DuckDB 上で SQL ウィンドウ関数等を併用して実装。データ不足時は None を返す設計。
  - 特徴量探索モジュール（kabusys.research.feature_exploration）。
    - 将来リターン calc_forward_returns（複数ホライズン対応、1/5/21 日がデフォルト）。
    - IC（Spearman ランク相関）算出 calc_ic、ランク変換 util、ファクター統計 summary を実装。
    - 外部依存を避け標準ライブラリのみで実装。
  - research パッケージの公開 API を整備（calc_momentum/calc_volatility/calc_value/zscore_normalize/calc_forward_returns/calc_ic/factor_summary/rank）。
- 特徴量エンジニアリング:
  - build_features を実装（kabusys.strategy.feature_engineering）。
    - research 側の生ファクターを取得し、ユニバースフィルタ（最小株価、20日平均売買代金）を適用。
    - 指定カラムを Z スコア正規化（zscore_normalize を使用）、±3 でクリップ。
    - features テーブルへ日付単位での置換（トランザクション + バルク挿入）により冪等性を保証。
    - DuckDB から target_date 以前の最新株価を参照してユニバース判定（休場日対応）。
- シグナル生成:
  - generate_signals を実装（kabusys.strategy.signal_generator）。
    - features テーブルと ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを算出。
    - 各コンポーネントは Z スコア → シグモイド変換等で [0,1] にマッピング。欠損コンポーネントは中立 0.5 で補完。
    - デフォルト重み（momentum 0.4, value 0.2, volatility 0.15, liquidity 0.15, news 0.1）を提供。ユーザ指定 weights は検証・正規化・再スケール。
    - Bear レジーム検知（ai_scores の regime_score 平均 < 0 かつサンプル数閾値を満たす場合）で BUY シグナルを抑制。
    - BUY シグナル閾値デフォルト 0.60、SELL はストップロス（-8%）およびスコア低下で判定。
    - positions / prices_daily / features 参照による SELL 判定を実装。SELL 優先で signals テーブルへ日付単位の置換（トランザクション）で保存。
- ロギング:
  - 各モジュールにおいて情報・警告・デバッグログを追加。

Changed
- N/A（初回リリースのため変更履歴なし）

Fixed
- N/A（初回リリースのため修正履歴なし）

Deprecated
- N/A

Removed
- N/A

Security
- news_collector で defusedxml を使用して XML パース攻撃を軽減。
- RSS URL 正規化・スキーム検証により SSRF 等の危険なスキームを制限する設計方針を明記。
- .env 読み込み時に OS 環境変数を protected として上書き不可にすることで誤上書きを防止。

Notes / Known limitations
- _generate_sell_signals 内に記載の通り、トレーリングストップ（peak_price に基づく）や時間決済（保有 60 営業日超）などはいまの実装では未実装。positions テーブルに peak_price / entry_date 等の追加が必要。
- feature_engineering ではユニバース判定に使用する avg_turnover を features テーブルには保存していない（フィルタ専用）。
- ai_scores が未登録の銘柄に対するニューススコアは補完として中立（0.5）扱い。
- DuckDB のスキーマ（tables）および外部サービス（kabu API / Slack / J-Quants）の実運用設定は本リリースでは含まず、環境変数による設定を前提とする。
- execution / monitoring パッケージは初期状態（空の __init__ 等）であり、実際の発注ロジックや監視機能は別途実装が必要。

作者注
- 各モジュールの設計文書（StrategyModel.md, DataPlatform.md 等）を参照して実装しています。運用前に環境変数（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等）を設定してください。