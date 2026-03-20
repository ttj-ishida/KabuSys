# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  

現在のバージョンは 0.1.0 です (初回公開)。リリース日は 2026-03-20 です。

## [0.1.0] - 2026-03-20

### Added
- パッケージ基盤
  - kabusys パッケージの公開 API を追加。
    - __all__ に data, strategy, execution, monitoring を設定。
    - パッケージバージョンを "0.1.0" に設定。

- 設定 / 環境変数読み込み (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - プロジェクトルート検出: __file__ を起点に .git または pyproject.toml を探索して自動的にプロジェクトルートを特定。
  - 自動ロード優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化オプション: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサーの強化:
    - export プレフィックス対応（`export KEY=val`）。
    - シングル/ダブルクォート内のエスケープ処理対応。
    - コメント処理（クォート内無視、クォート外の '#' は直前が空白/tab の場合のみコメントとして扱う）。
  - 設定プロパティを提供（必須キーは未設定時に ValueError を送出）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など。
  - 環境値検証:
    - KABUSYS_ENV は (development, paper_trading, live) のみ許可。
    - LOG_LEVEL は (DEBUG, INFO, WARNING, ERROR, CRITICAL) のみ許可。
  - デフォルトの DB パス (duckdb/sqlite) の取り扱いを提供。

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar）。
    - 認証: リフレッシュトークンからの ID トークン取得機能 (get_id_token) を実装（/token/auth_refresh へ POST）。
    - モジュールレベルの ID トークンキャッシュを実装しページネーション間で共有。
  - レート制御:
    - 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
  - リトライ/エラーハンドリング:
    - 指数バックオフ付きリトライ（最大 3 回）。対象ステータスコードに 408, 429 と 5xx を含む。
    - 401 を受けた場合はトークンを一度リフレッシュして再試行（再帰防止）。
    - 429 の場合は Retry-After ヘッダを優先。
  - DuckDB への保存ユーティリティ:
    - save_daily_quotes, save_financial_statements, save_market_calendar を実装。挿入は冪等化（ON CONFLICT DO UPDATE / DO NOTHING）される。
    - レコードの PK 欠損時スキップ、挿入件数のログ出力。
  - データ変換ユーティリティ (_to_float / _to_int) を実装し、安全に None を取り扱う。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news に保存する処理を実装（設計とユーティリティを追加）。
  - セキュリティ/堅牢性対策:
    - defusedxml を用いた XML パース（XML Bomb 等の対策）。
    - URL 正規化（スキーム/ホストの小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）。
    - トラッキングパラメータリスト（utm_*, fbclid 等）を除去。
    - バルク INSERT のチャンク化（_INSERT_CHUNK_SIZE）。
  - デフォルト RSS ソースを定義（例: Yahoo Finance ビジネス RSS）。

- 研究用ファクター計算 (kabusys.research.*)
  - factor_research モジュール:
    - モメンタムファクター (calc_momentum): mom_1m/mom_3m/mom_6m、MA200 乖離率（200 行未満は None）。
    - ボラティリティ/流動性ファクター (calc_volatility): 20日 ATR（atr_20/atr_pct）、20日平均売買代金、volume_ratio。
    - バリューファクター (calc_value): raw_financials から最新財務データを参照して PER/ROE を計算。
    - 各関数は DuckDB の prices_daily / raw_financials テーブルのみを参照。
  - feature_exploration モジュール:
    - 将来リターン計算 (calc_forward_returns): 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - IC 計算 (calc_ic): Spearman のランク相関（ランクは同順位平均ランク、値は round(..., 12) で ties の誤判定を低減）。
    - rank, factor_summary (count/mean/std/min/max/median) を実装。
  - research パッケージの公開 API を整備。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features を実装:
    - research モジュールの calc_momentum/calc_volatility/calc_value を呼び、レコードをマージ。
    - ユニバースフィルタを適用（最小株価 300 円、20日平均売買代金 >= 5 億円）。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）し、±3 でクリップ。
    - features テーブルへ日付単位で置換（DELETE → INSERT をトランザクションで行い冪等性を保証）。
    - 欠損や非有限値は None として扱う。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals を実装:
    - features / ai_scores / positions テーブルを参照し、各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - シグモイド変換、コンポーネントの平均化、欠損は中立値 0.5 で補完。
    - デフォルト重みと閾値を実装（デフォルト weights や threshold=0.60）。
    - 重みの検証・正規化（未知キーや負値・NaN/Inf を除外し、合計を 1.0 に再スケール）。
    - Bear レジーム判定: ai_scores の regime_score 平均が負なら BUY を抑制（サンプル数が不足 < 3 件 の場合は Bear とみなさない）。
    - BUY シグナル: final_score >= threshold。
    - SELL シグナル生成 (_generate_sell_signals):
      - ストップロス: 現在終値 / avg_price - 1 < -8%（優先判定）。
      - スコア低下: final_score が threshold 未満。
      - 価格欠損時は SELL 判定をスキップして警告ログを出力。
      - 未実装だがコメントでトレーリングストップや時間決済の拡張を示唆。
    - signals テーブルへ日付単位で置換（トランザクションで原子性を保証）。
    - 実行結果のログ出力（BUY/SELL 件数）。

### Security
- news_collector で defusedxml を使用して XML パースの安全性を確保。
- news_collector は URL の正規化・トラッキング除去・最大レスポンスサイズ制限等の対策を講じている（SSRF・DoS 対策の方針が設計に明記されている）。
- jquants_client でのトークン管理・リトライ/レート制御により異常時の暴走を抑止。

### Documentation / Logging
- 各モジュールに詳細な docstring と設計方針・処理フロー・注記を追加。開発者向けの振る舞いと注意点（ルックアヘッドバイアス回避等）を明記。
- 多数の箇所で logger による情報/警告/デバッグ出力を追加。

### Notes / Known limitations
- execution パッケージはインターフェースのみ（__init__ が存在）で実際の発注 API 統合はこのリリースでは含まれていない。
- signal_generator のトレーリングストップや時間決済など、いくつかのエグジット条件は未実装（位置情報に peak_price / entry_date が必要）。
- news_collector の記事 ID 生成や銘柄紐付けの詳細実装は設計に記載されているが、実装の一部は今後の拡張対象。
- データベーススキーマ（テーブル定義: raw_prices/raw_financials/prices_daily/features/ai_scores/positions/signals 等）は本 CHANGELOG に含まれていないため、運用前にスキーマ整備が必要。

--- 

今後のリリースでは以下を想定しています:
- execution 層の実装（kabu API との連携・注文送信ロジック）。
- news_collector の記事→銘柄マッチング処理強化とインデックス最適化。
- signal_generator の追加エグジット条件・ポートフォリオ制約の導入。
- テストカバレッジ拡充と CI/CD ワークフローの整備。