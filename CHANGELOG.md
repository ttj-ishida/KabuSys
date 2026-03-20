Keep a Changelog に準拠した変更履歴

すべての注目すべき変更点をこのファイルに記載します。フォーマットは Keep a Changelog に従います。
このリリースは、コードベースから推測した初期公開（機能実装）内容をまとめたものです。

0.1.0 - 2026-03-20
=================

Added
-----
- パッケージ初期化
  - kabusys パッケージを導入。__version__ = "0.1.0"。
  - パッケージ外部 API として data / strategy / execution / monitoring を __all__ に公開。

- 設定（kabusys.config）
  - .env ファイルまたは環境変数からの設定読み込みを実装。
    - プロジェクトルート判定ロジック（.git または pyproject.toml を探索）により、CWD に依存しない自動ロードを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ実装: コメント/引用符/エスケープ/inline コメント処理、"export KEY=val" 形式対応。
  - 環境変数保護機構（protected set）を用いた .env 上書き制御。
  - Settings クラスを実装し、以下のプロパティを提供（必須環境変数は未設定時に ValueError を送出）:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV (development / paper_trading / live の検証)
    - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL の検証)
    - ヘルパー: is_live / is_paper / is_dev

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - 固定間隔スロットリングによるレート制限管理（120 req/min）。
    - リトライ（最大 3 回） + 指数バックオフ、HTTP 429 の Retry-After 考慮、408/429/5xx をリトライ対象。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）と再試行処理。ID トークンのモジュールレベルキャッシュを提供。
    - ページネーション対応の fetch_* 関数:
      - fetch_daily_quotes
      - fetch_financial_statements
      - fetch_market_calendar
    - DuckDB への保存関数（冪等）:
      - save_daily_quotes -> raw_prices（ON CONFLICT DO UPDATE）
      - save_financial_statements -> raw_financials（ON CONFLICT DO UPDATE）
      - save_market_calendar -> market_calendar（ON CONFLICT DO UPDATE）
    - 数値変換ユーティリティ: _to_float / _to_int（文字列や None を安全に変換）
    - UTC の fetched_at を記録し、Look-ahead バイアス追跡に対応。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news に保存する処理を実装。
    - デフォルト RSS ソース登録（例: Yahoo Finance のビジネス RSS）。
    - defusedxml を利用した安全な XML パース（XML Bomb 等の防御）。
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ除去（utm_ など）、フラグメント除去、クエリソート。
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を担保。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を緩和。
    - バルク INSERT のチャンク処理で DB 側制約を回避。
    - セキュリティ対策: HTTP/HTTPS 以外のスキーム拒否や SSRF を想定した検討（実装上の留意あり）。

- 研究系（kabusys.research）
  - factor_research: モメンタム / ボラティリティ / バリューのファクター計算を実装。
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日 MA の欠損扱い等に注意）
    - calc_volatility: atr_20, atr_pct（ATR の NULL 伝播制御）, avg_turnover, volume_ratio
    - calc_value: per, roe（raw_financials の最新レコードを参照）
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンをまとめて取得
    - calc_ic: スピアマンのランク相関（IC）計算（有効レコード 3 件未満は None）
    - factor_summary: count/mean/std/min/max/median の統計要約
    - rank: 同順位に平均ランクを割り当てるランク換算ユーティリティ
  - research パッケージ __all__ に主要 API を公開。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date) を実装:
    - research の calc_momentum/calc_volatility/calc_value を呼び出して素ファクターを取得。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）適用。
    - 正規化: zscore_normalize を使用し、対象カラムを Z スコア化した後 ±3 でクリップ。
    - features テーブルに date 単位で置換（DELETE + INSERT をトランザクションで実行、冪等性）。
    - ルックアヘッドバイアス防止の設計（target_date 時点のデータのみ使用）。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装:
    - features, ai_scores, positions を参照して最終スコア(final_score) を計算。
    - コンポーネントスコア: momentum/value/volatility/liquidity/news を計算（シグモイド変換・平均化等）。
    - 重みのマージと再スケール（デフォルト重みを提供、無効値は無視）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾上なら Bear と判定）による BUY 抑制。
    - BUY（final_score >= threshold）と SELL（ストップロス、score_drop）の判定。SELL 優先ポリシーにより BUY から除外。
    - signals テーブルへ date 単位で置換して保存（DELETE + INSERT をトランザクションで実行）。
    - 内部での安全措置: 重複・欠損値処理や価格欠損時の SELL 判定スキップ・警告ログ。

- モジュールエクスポート
  - strategy パッケージで build_features / generate_signals を __all__ に公開。
  - research でも主要ユーティリティを __all__ に公開。

Changed
-------
- （初回リリースのため該当なし）

Fixed
-----
- （初回リリースのため該当なし）

Security
--------
- ニュース RSS パースに defusedxml を使用し、XML 関連の攻撃に備える実装を追加。
- ニュース収集でのレスポンスサイズ制限、URL のトラッキング除去・正規化、HTTP/HTTPS スキーム検証等による安全対策を実施。

Notes / Known limitations
-------------------------
- _generate_sell_signals 内で記載された未実装のエグジット条件:
  - トレーリングストップ（peak_price の追跡が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
  これらは将来的な実装候補。現状ではストップロス（-8%）とスコア低下のみでエグジット判定を行う。

- DB スキーマ期待値:
  - 上位モジュールは以下のテーブルを参照／更新することを前提とする:
    - raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals, raw_news, etc.
  - 実際のスキーマ（カラム名や PK/制約）は実装で想定されているため、既存データベースと組み合わせる際はスキーマ互換性に注意してください。

- 外部依存:
  - 実行には duckdb と defusedxml（ニュース解析）を使用。
  - 他は基本的に標準ライブラリのみで実装を意図。

- 設定必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須。
  - KABUSYS_ENV は development / paper_trading / live のいずれかである必要があり、不正値は起動時に例外を投げます。
  - LOG_LEVEL は大文字の標準レベルで検証されます。

Upgrade / Migration notes
-------------------------
- 初回公開のため特別な移行手順はありませんが、上記の DB テーブル・環境変数の準備を行ってください。
- .env 自動読み込みを利用する場合、プロジェクトルート（.git または pyproject.toml）が存在することを確認してください。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

Acknowledgements / Implementation remarks
-----------------------------------------
- 多くの設計コメント（StrategyModel.md / DataPlatform.md 等）に準拠した実装方針がコード中に記載されています。実運用前に戦略パラメータ（閾値、重み、ユニバース定義など）のチューニングと検証を推奨します。
- ロギングが各所に挿入されており、運用時の監視やデバッグに利用可能です。

（本 CHANGELOG は与えられたコード内容から推測して作成しています。実際のリリースノート作成時はコミット履歴・リリース日・実装担当者等の情報を追記してください。）