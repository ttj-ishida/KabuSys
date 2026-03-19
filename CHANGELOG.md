CHANGELOG
=========

すべての変更は Keep a Changelog の形式に概ね準拠して記載しています。

[0.1.0] - 2026-03-19
--------------------

Added
- 初回リリース。日本株自動売買システムのコア機能群を追加。
  - パッケージ基点
    - src/kabusys/__init__.py
      - パッケージのバージョン (0.1.0) と公開モジュールを定義（data, strategy, execution, monitoring）。
  - 設定・環境変数管理
    - src/kabusys/config.py
      - .env ファイルおよび環境変数からの設定読み込みを実装。
      - プロジェクトルートの自動検出（.git または pyproject.toml を探索）。
      - .env パースの堅牢化：コメント、export プレフィックス、シングル/ダブルクォート内のエスケープ処理、行末コメント取り扱いを考慮。
      - 自動ロード順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロード無効化可能。
      - 必須環境変数取得時の検証とエラーメッセージ化（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_* 等）。
      - 一部設定値のバリデーション（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）。
      - DB パスを Path 型で返すユーティリティ（duckdb/sqlite の既定パス）。
  - データ取得 / 保存（J-Quants API クライアント）
    - src/kabusys/data/jquants_client.py
      - J-Quants API への HTTP クライアントを実装。
      - レート制限（120 req/min）を守る固定間隔スロットリング実装（内部 RateLimiter）。
      - リトライ戦略（指数バックオフ、最大 3 回）を実装。対象ステータスコード・ネットワークエラーに対応。
      - 401 Unauthorized を検知した場合の自動トークンリフレッシュ（1 回）処理。
      - ページネーション対応（pagination_key）で全ページ取得。
      - データ整形ユーティリティ (_to_float, _to_int) と安全なパース/スキップロジック。
      - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装し、ON CONFLICT DO UPDATE による冪等性を確保。
      - fetched_at を UTC ISO8601（Z）で記録し、データ取得タイミングのトレースを可能に。
  - ニュース収集
    - src/kabusys/data/news_collector.py
      - RSS フィード取得と記事保存の基礎を実装。
      - URL 正規化（トラッキングパラメータ除去、クエリソート、fragment 削除、小文字化など）。
      - 記事IDは正規化URLの SHA-256（先頭32文字）を利用して冪等性を担保。
      - defusedxml による安全な XML パース（XML Bomb 等への対策）。
      - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 対策。
      - HTTP スキームチェックや SSRF 暗黙防止のための注意点を設計に明記。
      - DB バルク挿入のチャンク化（_INSERT_CHUNK_SIZE）による効率化。
  - リサーチ / ファクター計算
    - src/kabusys/research/factor_research.py
      - モメンタム（1M/3M/6M）、200日移動平均乖離（ma200_dev）、ATR（20日）、avg_turnover / volume_ratio、PER/ROE を DuckDB の prices_daily / raw_financials から計算する関数を実装（calc_momentum / calc_volatility / calc_value）。
      - 営業日ベースの窓長とカレンダーバッファを採用し、休日を吸収する設計。
      - データ不足時は None を返すことで欠損を明示。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算（calc_forward_returns）、IC（スピアマンランク相関）計算（calc_ic）、統計サマリー（factor_summary）、ランク関数（rank）を実装。
      - 外部依存を用いず標準ライブラリと DuckDB のみで計算可能。
  - 戦略（特徴量作成・シグナル生成）
    - src/kabusys/strategy/feature_engineering.py
      - 研究環境で計算した raw ファクターを正規化・統合して features テーブルへ UPSERT する build_features を実装。
      - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を実装。
      - Z スコア正規化（zscore_normalize を利用）と ±3 のクリップによる外れ値対策。
      - 日単位の置換（削除→挿入）をトランザクションで行い原子性を確保。
    - src/kabusys/strategy/signal_generator.py
      - features と ai_scores を統合して final_score を計算し、BUY/SELL シグナルを生成する generate_signals を実装。
      - モメンタム / バリュー / ボラティリティ / 流動性 / ニュース の重み付け集約（デフォルト重みを提供）。
      - weights 入力の検証・補完・再スケーリング処理。
      - Bear レジーム検知（ai_scores の regime_score 平均が負）時は BUY を抑制。
      - SELL 条件: (1) ストップロス（終値が取得できる場合に avg_price に対して -8% 以下）、(2) 最終スコアが閾値未満。
      - 保有銘柄に対する価格欠損時は SELL 判定をスキップして誤クローズを回避。
      - signals テーブルへの日付単位の置換処理をトランザクションで実施。
  - モジュールエクスポート
    - src/kabusys/research/__init__.py, src/kabusys/strategy/__init__.py
      - 主要 API 関数をパッケージの公的 API としてエクスポート。

Security
- データ取得・ニュース収集で以下の安全対策を実装/設計に反映。
  - defusedxml による安全な XML パース（news_collector）。
  - 受信バイト数制限（news_collector）。
  - URL 正規化とトラッキングパラメータ除去により一意性を担保し、外部参照の取り扱いを明確化。
  - J-Quants クライアントでのトークン管理と自動リフレッシュにより認証失敗時の取り扱いを安全に実装。

Performance
- DuckDB に対する集計はできるだけウィンドウ関数＋単一クエリでまとめ、必要なスキャン範囲をカレンダーバッファで限定して効率化（factor_research, feature_exploration）。
- jquants_client のページネーション収集と rate limiter によるスロットリングで API への過負荷を回避。
- news_collector のバルク挿入チャンク化で DB オーバーヘッドを抑制。

Known limitations / TODO
- signal_generator の SELL 条件のうち、トレーリングストップ（peak_price に基づく）と時間決済（保有60営業日超）は未実装。positions テーブルに peak_price / entry_date を追加する必要あり（コメントで明記済）。
- data.stats モジュール（zscore_normalize など）は参照されているが本差分にコードを含まず、外部に存在することを前提としている。
- execution パッケージは空の初期プレースホルダ（発注処理層の実装は別途）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Notes / Usage hints
- .env 自動読み込みは CWD に依存せずパッケージファイル位置からプロジェクトルートを探索するため、パッケージ配布後も安定して動作します。テスト等で自動読み込みを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API の利用には JQUANTS_REFRESH_TOKEN が必須です（settings.jquants_refresh_token を参照）。
- generate_signals / build_features は DuckDB 接続（DuckDBPyConnection）を受け取りテーブルを直接操作します。運用前にスキーマ（prices_daily, raw_financials, features, ai_scores, positions, signals 等）を準備してください。