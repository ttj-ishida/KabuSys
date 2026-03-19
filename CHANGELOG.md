Keep a Changelog
=================

すべての注目すべき変更点を時系列で記録します。  
このファイルは「Keep a Changelog」仕様に準拠します。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-03-19
-------------------

初回リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを実装しました。主な追加点は以下のとおりです。

Added
- パッケージ基礎
  - パッケージ初期化: kabusys.__init__ にバージョン (0.1.0) と公開 API を定義。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml で探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。既存 OS 環境は保護される。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ実装: コメント・export プレフィックス・クォート・エスケープ・インラインコメントに対応。
  - Settings クラスでアプリケーション設定をプロパティ経由で提供:
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（未設定時は ValueError を送出）
    - オプション/デフォルト: KABU_API_BASE_URL、DUCKDB_PATH（data/kabusys.duckdb）、SQLITE_PATH（data/monitoring.db）
    - 環境検証: KABUSYS_ENV は {development, paper_trading, live} のみ許容、LOG_LEVEL は標準ログレベルのみ許容
    - is_live / is_paper / is_dev の短縮プロパティを提供

- データ取得・保存（J-Quants API） (kabusys.data.jquants_client)
  - J-Quants API クライアント実装
    - レート制限 (120 req/min) を固定間隔スロットリングで実装（_RateLimiter）
    - リトライロジック（指数バックオフ、最大 3 回）を実装（408/429/5xx を想定）
    - 401 受信時は自動トークンリフレッシュを一度行って再試行（無限再帰を回避）
    - ID トークンのモジュールレベルキャッシュを実装（ページネーション間で共有）
    - fetch_* 系: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）
    - save_* 系: save_daily_quotes, save_financial_statements, save_market_calendar
      - DuckDB への保存は冪等性を担保（ON CONFLICT DO UPDATE / DO NOTHING を利用）
      - fetched_at は UTC タイムスタンプ（Z 形式）で記録
    - 入力データ変換ユーティリティ: _to_float / _to_int（堅牢な変換・空値処理）
    - 詳細なログ出力を追加（取得件数・スキップ件数等）

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード収集・正規化・DB保存機能
    - デフォルト RSS ソースに Yahoo Finance を登録
    - 記事 ID を URL 正規化後の SHA-256（先頭 32 文字）で生成し冪等性を確保
    - URL 正規化: スキーム/ホストの小文字化、トラッキングパラメータ（utm_*, fbclid 等）の除去、フラグメント削除、クエリパラメータのソート
    - defusedxml を用いた安全な XML パース（XML bomb 等を考慮）
    - 最大受信サイズ制限（MAX_RESPONSE_BYTES = 10 MB）によりメモリ DoS を軽減
    - HTTP スキーム検証や SSRF 回避の考慮（設計コメント）
    - DB 挿入はチャンク化して実行（_INSERT_CHUNK_SIZE）し、トランザクション単位で効率的に保存
    - 挿入したレコード数の正確な返却を設計

- 研究用ファクター実装 (kabusys.research)
  - factor_research:
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均のデータ不足時は None）
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（ATR/window チェックで None を扱う）
    - calc_value: per, roe（raw_financials の最新財務データを target_date 以前から取得）
    - SQL + DuckDB を用いた効率的なデータ取得・計算（スキャン範囲のバッファを確保）
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算
    - calc_ic: スピアマンランク相関（IC）を計算。ties の平均ランク処理、サンプル不足時は None を返す
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー
    - rank ユーティリティ: 同順位は平均ランクで扱う（round(..., 12) による tie の安定化）

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features 実装:
    - research モジュールから生ファクターを取得しマージ
    - ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を適用
    - 指定カラムの Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）と ±3 でクリップ
    - features テーブルへ日付単位の置換（削除→挿入）をトランザクションで実施し冪等性を確保
    - 休場日や当日欠損に対応するため target_date 以前の最新価格を参照

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals 実装:
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントを計算
    - コンポーネントスコア計算:
      - momentum: 複数シグナルのシグモイド平均
      - value: PER に基づく逆数スコア（PER=20 で 0.5）
      - volatility: ATR の Z スコアを反転してシグモイド変換
      - liquidity: volume_ratio をシグモイド変換
      - news: ai_score をシグモイド変換（未登録は中立）
    - 欠損コンポーネントは中立値 0.5 で補完
    - 重み (weights) の入力を検証・補完し、合計が 1.0 になるよう正規化（不正値はスキップ）
    - Bear レジーム検出: ai_scores の regime_score の平均が負でかつサンプル数が閾値以上であれば BUY を抑制
    - BUY シグナル閾値デフォルト: 0.60（カスタム可能）
    - SELL シグナル（エグジット）:
      - ストップロス: 終値 / avg_price - 1 < -8%
      - スコア低下: final_score < threshold
      - 保有銘柄の価格が取得できない場合は SELL 判定をスキップ（誤クローズ防止）
      - SELL 優先ポリシー: SELL の対象は BUY から除外、BUY は再ランク付け
    - signals テーブルへ日付単位の置換（トランザクション＋バルク挿入）で冪等性を担保
    - 詳細ログ出力（BUY/SELL 件数等）

- 共通・運用面
  - DuckDB をコアデータレイヤに採用し、conn（DuckDB 接続）を受け取る設計でサンプルとテストが容易
  - ログ出力を各処理に配置（info/debug/warning）、失敗時の ROLLBACK のログも実装
  - ルックアヘッドバイアス対策: 各処理は target_date 時点のデータのみ参照し、fetched_at を記録することで「システムがいつデータを知り得たか」を追跡可能に

Changed
- 初回リリースのため該当なし

Fixed
- 初回リリースのため該当なし

Deprecated
- 初回リリースのため該当なし

Removed
- 初回リリースのため該当なし

Security
- news_collector で defusedxml を使用し XML 周りの攻撃を軽減
- URL 正規化とトラッキングパラメータ除去により、外部リンク処理の一貫性を向上
- J-Quants クライアントで 401 発生時にトークンを安全にリフレッシュ（無限再帰防止のガードあり）

Notes / Requirements
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- DuckDB / defusedxml などの依存が必要（実行環境にインストールしてください）
- 本リリースでは一部の戦術（トレーリングストップ、時間決済、PBR/配当利回り等）は未実装（コード中に注記あり）

開発者向け補足
- 設計ドキュメント参照箇所（ソース内コメント）:
  - StrategyModel.md, DataPlatform.md, Research 関連ドキュメントへの言及が多く、仕様に従った実装が行われています
- 単体テストを行う際は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを抑止できます

-------------------
（以降のリリースでは機能追加・改善・バグ修正をこのファイルに追記します）