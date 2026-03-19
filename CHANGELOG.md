CHANGELOG
=========

すべての変更は "Keep a Changelog" の形式に従い、セマンティックバージョニングを使用します。
日付はリリース日です。

[Unreleased]
------------

なし。

0.1.0 - 2026-03-19
------------------

Added
- 初回リリース。パッケージ名: kabusys (バージョン 0.1.0)。
  - パッケージのトップレベルでは data, strategy, execution, monitoring を公開。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み（OS 環境変数 > .env.local > .env の優先順位）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env のパース処理を実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理を考慮）。
  - Settings クラスを導入し、必須値取得時の検証を提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - 環境変数検証: KABUSYS_ENV（development/paper_trading/live のみ許容）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許容）。
  - データベースパスの既定値: DUCKDB_PATH= data/kabusys.duckdb、SQLITE_PATH= data/monitoring.db。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - レート制限(120 req/min) を守る固定間隔スロットル実装（RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大3回）。再試行対象ステータス: 408, 429, 5xx。
    - 401 応答時はリフレッシュトークンから自動で id_token を更新し1回リトライ。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar 実装。
    - レスポンス JSON デコードエラー時の例外処理。
  - DuckDB への保存ユーティリティを実装（冪等性を重視）。
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE による保存。
    - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE による保存。
    - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE による保存。
    - 保存時に fetched_at を UTC ISO8601 で記録。
    - PK 欠損レコードはスキップしログ警告を出力。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュースを収集し raw_news に保存するためのユーティリティを実装。
  - セキュリティ配慮:
    - defusedxml を用いた XML パース（XML Bomb 等の防御）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）。
    - URL 正規化時にトラッキングパラメータ（utm_*, fbclid 等）を除去。
    - 記事IDは正規化 URL の SHA-256（先頭32文字）を用いることで冪等性を確保。
    - SSRF 等を意識したスキーム検証など（実装方針に記載）。
  - バルク INSERT のチャンク化・トランザクション集約でパフォーマンス向上。

- リサーチ（kabusys.research）
  - ファクター計算モジュール（kabusys.research.factor_research）
    - モメンタム: mom_1m / mom_3m / mom_6m, ma200_dev（200日移動平均乖離率）。
    - ボラティリティ/流動性: 20日 ATR（atr_20 / atr_pct）、20日平均売買代金、volume_ratio。
    - バリュー: per / roe（raw_financials と prices_daily を組み合わせて算出）。
    - データ不足時は None を返す仕様（安全に扱えるように実装）。
  - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト: [1,5,21]）の将来リターンを一括取得。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算。サンプル不足（<3）や定数系列は None を返す。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクで処理（丸めで ties 検出の安定化）。
  - 研究用 API は外部ライブラリに依存せず標準ライブラリ＋duckdb で実装。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features: research の生ファクターを統合・正規化して features テーブルへ UPSERT（日付単位で置換）するワークフローを実装。
    - ユニバースフィルタ: 株価 >= 300 円、20日平均売買代金 >= 5億円。
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップして外れ値の影響を抑制。
    - トランザクションで DELETE→INSERT を行い日付単位で冪等性・原子性を保証。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals: features と ai_scores を統合して銘柄ごとの final_score を計算し、BUY / SELL シグナルを signals テーブルへ保存（日付単位の置換）。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（AIスコア）。
    - スコア変換: Z スコアを sigmoid で [0,1] に変換。欠損コンポーネントは中立 0.5 で補完。
    - 重み: デフォルト重みを採用し、ユーザー指定 weights は検証（無効値は無視）して合計を1.0にスケール。デフォルト閾値: 0.60。
    - Bear レジーム判定: ai_scores の regime_score 平均が負の場合は BUY を抑制（サンプル数閾値あり）。
    - SELL 判定:
      - ストップロス: 終値 / avg_price - 1 < -8%（優先）。
      - スコア低下: final_score < threshold。
      - 価格欠損時は SELL 判定をスキップして誤クローズを防止。
    - SELL 優先ポリシー: SELL 対象は BUY から除外し、BUY のランクを再付与。
    - トランザクションで DELETE→INSERT により冪等性・原子性を保証。

- 共通ユーティリティ
  - 入出力変換ユーティリティ（_jquants_client の _to_float/_to_int 等）。
  - ロギングによる詳細な警告/情報出力を充実。

Security
- defusedxml を利用した RSS パースで XML を安全に処理。
- J-Quants クライアントはトークンリフレッシュ/レートリミッティング/Retry-After 尊重などレジリエンス設計を含む。
- RSS 処理で受信サイズを制限し、トラッキングパラメータ削除・URL 正規化でデータ整合性と冪等性を確保。

Known issues / Limitations
- generate_signals の未実装項目（コメントに記載）:
  - トレーリングストップ（peak_price / entry_date が positions テーブルに必要）。
  - 時間決済（保有 60 営業日超過）などの追加エグジット条件は未実装。
- news_collector のネットワーク/URL の追加厳格チェック（例: 完全な SSRF 防止ルールセット）は基本実装方針を含むが、運用に応じた追加検証が推奨される。
- research モジュールは pandas 等に依存しない設計のため、大量データ処理のチューニングは今後の改善対象。
- AI スコアが未登録の銘柄はニューススコアを中立に補完（0.5）。AI スコア統合の運用方針はユーザ側で調整可能。

Migration notes
- 初回リリースのため変更履歴アップグレード手順はなし。
- DuckDB スキーマ（raw_prices / raw_financials / prices_daily / features / ai_scores / signals / positions 等）は本リポジトリの別途スキーマ定義を参照してください。機能を利用する前に必要なテーブルを作成してください。

Contributing
- バグ報告・改善提案歓迎。セキュリティ問題は直接報告してください（公開リポジトリの ISSUE/PR フロー等）。

References
- パッケージバージョン: kabusys.__version__ == "0.1.0"