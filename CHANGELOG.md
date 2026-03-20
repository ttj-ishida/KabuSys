Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

0.1.0 - 2026-03-20
------------------

Added
- パッケージ初期リリース。
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - エントリポイント: src/kabusys/__init__.py （公開モジュール: data, strategy, execution, monitoring）

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に探索する _find_project_root を提供（CWD に依存しない）。
  - .env パーサーを実装（コメント、export プレフィックス、シングル/ダブルクォート・エスケープ処理、インラインコメントの扱いなどに対応）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化サポート。
  - Settings クラスを提供し、J-Quants / kabu / Slack / DB パス / システム設定（KABUSYS_ENV, LOG_LEVEL）をプロパティ経由で参照。必須キー未設定時は ValueError を送出。
  - 有効な env 値と log level のバリデーションを実装。

- データ取得・保存: J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - API クライアントを実装。
  - レートリミット制御: 固定間隔スロットリングで 120 req/min を遵守する _RateLimiter。
  - 再試行ロジック: 指数バックオフ、最大試行回数 3、408/429/5xx をリトライ対象に。429 の場合は Retry-After を優先。
  - 401 応答時の自動トークンリフレッシュ（1 回まで）とモジュールレベルの ID トークンキャッシュを実装。
  - 汎用 HTTP リクエストユーティリティ _request、JSON デコードエラーハンドリング。
  - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
  - DuckDB への冪等保存用ユーティリティ: save_daily_quotes / save_financial_statements / save_market_calendar（ON CONFLICT / DO UPDATE を使用）。
  - 入力値変換ユーティリティ _to_float / _to_int（堅牢な変換ロジックと欠損処理）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集し raw_news に保存する処理を実装。
  - セキュリティ対策: defusedxml を使用して XML 脆弱性対策、受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）、HTTP/HTTPS のみ許可、SSRF 対策を想定した設計。
  - URL 正規化: トラッキングパラメータ（utm_* 等）の除去、スキーム/ホストの小文字化、フラグメント削除、クエリソートなど。
  - 記事ID は URL 正規化後の SHA-256（先頭 32 文字）で生成して冪等性を確保。
  - デフォルト RSS ソース（yahoo_finance）とバルク挿入チャンク処理を備える。

- 研究用ファクター計算 (src/kabusys/research/factor_research.py)
  - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）を計算。
  - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。
  - calc_value: raw_financials から直近財務データを取得し PER / ROE を計算（EPS が 0 または欠損時は None）。
  - DuckDB SQL を活用したウィンドウ関数中心の実装（性能を考慮したスキャン範囲バッファあり）。
  - 研究向けユーティリティ zscore_normalize を data.stats から利用。

- 研究用探索・解析ツール (src/kabusys/research/feature_exploration.py)
  - calc_forward_returns: 指定日から複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。ホライズンは最大 252 営業日までバリデーション。
  - calc_ic: ファクターと将来リターンのスピアマン順位相関（IC）を計算。サンプル不足（<3）や ties 処理を考慮。
  - rank / factor_summary を実装（平均順位同順の平均ランク処理、基本統計量: count/mean/std/min/max/median）。
  - pandas 等外部依存を避け、標準ライブラリ + DuckDB で実装。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - research 側で計算された生ファクターを統合・正規化して features テーブルへ保存する build_features を実装。
  - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を導入。
  - Z スコア正規化（zscore_normalize）と ±3 のクリップ、日付単位での置換（DELETE + bulk INSERT、トランザクションによる原子性）を実装。
  - ルックアヘッドバイアス回避のため target_date 時点のデータのみを使用。

- シグナル生成エンジン (src/kabusys/strategy/signal_generator.py)
  - features と ai_scores を統合して final_score を算出し BUY/SELL シグナルを生成する generate_signals を実装。
  - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）と閾値（DEFAULT_THRESHOLD = 0.60）を実装。ユーザー重みは検証・正規化して扱う。
  - コンポーネントスコア計算:
    - momentum: momentum_20/60 と ma200_dev をシグモイド平均で算出
    - value: PER を 20 を基準にスケール（PER が正でない場合は欠損扱い）
    - volatility: atr_pct の Z スコアを反転してシグモイド変換
    - liquidity: volume_ratio をシグモイドで変換
    - news: ai_score をシグモイドで変換（未登録は中立）
  - Bear レジーム判定: ai_scores の regime_score 平均が負かつサンプル数 >= 3 の場合に BUY を抑制。
  - エグジット判定（_generate_sell_signals）:
    - ストップロス: 現在終値が平均取得単価から -8% 以下
    - final_score が閾値未満
    - positions / prices の欠測時の挙動（警告出力・安全側の扱い）を明示
  - signals テーブルへの日付単位置換（トランザクション + bulk insert）で冪等性を保証。

- モジュールエクスポート
  - strategy と research の __init__.py で主要関数を公開（build_features, generate_signals, calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / Implementation details
- 多くの処理で「ルックアヘッドバイアス防止」を設計方針として明示（target_date 時点のデータのみ参照、fetched_at に UTC タイムスタンプを記録等）。
- DuckDB を中心に SQL ウィンドウ関数を活用することで大規模銘柄群にも対応可能な設計。
- ロギングを広く利用して運用時の可観測性を確保（情報・警告・デバッグメッセージを適所に出力）。
- セキュリティや頑健性に配慮（XML パース安全化、ネットワーク再試行、トークン自動更新、入力値の厳密な変換ルールなど）。

今後の予定（例）
- execution 層の実装（kabu ステーション API 経由の発注処理）。
- backtest / ポートフォリオ最適化ツールの追加。
- ニュースと銘柄紐付け（news_symbols テーブル）や自然言語処理を用いたニューススコアの強化。
- monitoring モジュールの実装／拡充（Slack 通知等）。

-----