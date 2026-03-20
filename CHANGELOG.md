CHANGELOG
=========

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-03-20
------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージエクスポート:
    - kabusys.__version__ = "0.1.0"
    - __all__ に data, strategy, execution, monitoring を公開

- 環境変数 / 設定管理 (kabusys.config)
  - .env ファイルまたは OS 環境変数から設定を自動読み込み
    - プロジェクトルートを .git または pyproject.toml で検出
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env の行パーサ実装
    - コメント行、export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - クォートなしの場合は「#」をインラインコメントとして扱うルール（直前がスペース／タブの場合）
  - .env 読み込みの保護キー機能（protected）により OS 環境変数を上書きしない挙動を実装
  - Settings クラスを提供（settings インスタンスで利用可能）
    - 必須項目取得（未設定時は ValueError を送出）
    - 提供プロパティ（主なもの）:
      - jquants_refresh_token (JQUANTS_REFRESH_TOKEN 必須)
      - kabu_api_password (KABU_API_PASSWORD 必須)
      - kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
      - slack_bot_token (SLACK_BOT_TOKEN 必須)
      - slack_channel_id (SLACK_CHANNEL_ID 必須)
      - duckdb_path (デフォルト: data/kabusys.duckdb)
      - sqlite_path (デフォルト: data/monitoring.db)
      - env (KABUSYS_ENV: development/paper_trading/live のみ有効)
      - log_level (LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL)
      - ヘルパー: is_live / is_paper / is_dev

- データ取得 / 保存 — J-Quants クライアント (kabusys.data.jquants_client)
  - HTTP リクエストユーティリティと堅牢なエラーハンドリング
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）
    - 再試行（最大 3 回、指数バックオフ）、対象ステータス: 408/429/5xx
    - 401 受信時は ID トークン自動リフレッシュを 1 回行い再試行
    - ページネーション対応（pagination_key）
    - JSON デコードエラーやネットワークエラーに対する明確なエラー報告
    - ID トークンのモジュールレベルキャッシュ（ページネーション間で共有）
  - API 用ラッパー関数:
    - get_id_token(refresh_token: Optional[str]) -> str
    - fetch_daily_quotes(...)
    - fetch_financial_statements(...)
    - fetch_market_calendar(...)
  - DuckDB への保存関数（冪等性: ON CONFLICT DO UPDATE / DO NOTHING）
    - save_daily_quotes(conn, records) -> 挿入・更新件数
      - fetched_at は UTC ISO8601 で記録
      - PK 欠損レコードはスキップして警告出力
    - save_financial_statements(conn, records) -> 挿入・更新件数
    - save_market_calendar(conn, records) -> 挿入・更新件数
  - ユーティリティ変換関数: _to_float / _to_int（入力バリデーション厳格化）

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード収集の実装
    - デフォルト RSS ソース: Yahoo Finance のビジネスカテゴリ
    - 受信最大バイト数制限（10 MB）によりメモリ DoS を軽減
    - defusedxml を使った XML パース（XML Bomb 等の保護）
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ除去（utm_*/fbclid/gclid 等）、フラグメント除去、クエリパラメータをキーでソート
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）を利用して冪等性を担保
    - HTTP スキーム以外拒否・SSRF 対策・受信サイズ制限・チャンク化したバルク INSERT（_INSERT_CHUNK_SIZE）
    - raw_news / news_symbols などへの保存を想定（ON CONFLICT DO NOTHING）

- リサーチモジュール (kabusys.research)
  - factor_research: 主要ファクター計算を実装
    - calc_momentum(conn, target_date) -> mom_1m, mom_3m, mom_6m, ma200_dev
      - 1M/3M/6M リターン、200 日移動平均乖離（データ不足時は None）
    - calc_volatility(conn, target_date) -> atr_20, atr_pct, avg_turnover, volume_ratio
      - ATR 計算は true_range を NULL 伝播で厳密に扱う（部分窓は None）
    - calc_value(conn, target_date) -> per, roe
      - raw_financials の target_date 以前の最新レポートと当日株価を組み合わせて算出
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=[1,5,21]) — 将来リターンを一度の SQL で取得
    - calc_ic(factor_records, forward_records, factor_col, return_col) — Spearman の ρ（ランク相関）実装
      - 有効レコード < 3 の場合は None を返す
    - factor_summary(records, columns) — count/mean/std/min/max/median を算出（None 値除外）
    - rank(values) — 同順位は平均ランクにするランク付け（丸めで ties 検出安定化）

- 戦略モジュール (kabusys.strategy)
  - 特徴量エンジニアリング (feature_engineering.build_features)
    - research モジュールの生ファクターから features テーブル用の特徴量を構築
    - ユニバースフィルタ: 価格 >= 300 円、20 日平均売買代金 >= 5e8（円）
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）
    - 正規化値を ±3 でクリップ（外れ値対策）
    - 日付単位で削除→挿入のトランザクション処理により冪等性を担保
    - build_features(conn, target_date) -> upsert した銘柄数を返す
  - シグナル生成 (signal_generator.generate_signals)
    - features と ai_scores を統合して final_score を計算
    - デフォルト重みと閾値:
      - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10
      - デフォルト閾値: BUY = 0.60
      - ストップロス: -8%（_STOP_LOSS_RATE）
    - 重みのバリデーションと再スケール（合計が 1.0 になるよう補正）
    - コンポーネントスコアの計算（シグモイド変換、欠損は中立 0.5 で補完）
    - Bear レジーム判定: ai_scores の regime_score 平均が負でサンプル数 >= 3 の場合 BUY を抑制
    - エグジット判定（保有ポジションに対する SELL）
      - 実装済み: ストップロス（終値 / avg_price - 1 < -8%）、final_score が閾値未満
      - 未実装（コメント）: トレーリングストップ、時間決済（positions テーブルに peak_price/entry_date が必要）
    - SELL 優先ポリシー: SELL 対象は BUY から除外し、BUY ランクを再付与
    - こちらも日付単位で削除→挿入のトランザクション処理で冪等性を担保
    - generate_signals(conn, target_date, threshold=None, weights=None) -> signals テーブルに書き込んだシグナル数を返す

Changed
- （新規リリースのため該当なし）

Fixed
- （新規リリースのため該当なし）

Deprecated
- （なし）

Removed
- （なし）

Security
- ニュース XML パースに defusedxml を使用（XML 脅威対策）
- RSS URL 正規化や受信サイズ制限、スキーム検査により SSRF / DoS リスクを軽減

注意事項 / マイグレーション
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- KABUSYS_ENV は "development", "paper_trading", "live" のいずれかでなければ ValueError を送出
- LOG_LEVEL は大文字で "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL" のいずれか
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行う。配布後やテストで抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB 側では以下テーブル/スキーマが期待される（実運用ではスキーマ準備が必要）
  - raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals, raw_news, news_symbols など
- J-Quants API の呼び出しはレート制限や再試行ロジックが組み込まれているが、プロダクション運用時は API 利用上限やトークン管理に注意してください。

補足
- 実装はルックアヘッドバイアス回避を重視しており、多くの集計・結合は target_date 時点までのデータのみを参照するよう設計されています。システム統合時はこの前提を崩さないようご注意ください。