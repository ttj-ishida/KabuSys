# Changelog

すべての重要な変更は Keep a Changelog の慣例に従って記載しています。  
リリース日付はリポジトリ内のバージョン（src/kabusys/__init__.py の __version__）に基づいています。

全般的な方針:
- DuckDB を中心としたローカルデータレイク（prices_daily / raw_prices / raw_financials / features / ai_scores / signals 等）を前提とした設計
- ルックアヘッドバイアス回避（target_date 時点の情報のみ参照）を重視
- 冪等性（日付単位での置換、ON CONFLICT / INSERT/DELETE の組合せによる実装）
- 本番の発注層（execution）や外部口座に直接アクセスしない戦略/研究レイヤの分離

---

## [0.1.0] - 2026-03-19

### Added
- パッケージ基盤
  - kabusys パッケージを初期実装。パッケージバージョンを 0.1.0 として公開。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に定義。

- 設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git / pyproject.toml を基準に探索）。
  - .env パーサーの実装:
    - export プレフィックス対応、シングル/ダブルクォートのエスケープ処理、インラインコメント処理、無効行のスキップ。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - protected（既存 OS 環境変数）を考慮した .env.local の上書き処理。
  - Settings クラスを提供し、以下の設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live の検証）、LOG_LEVEL（検証）
    - is_live / is_paper / is_dev のブール判定

- Data 層（kabusys.data）
  - J-Quants API クライアント (data/jquants_client.py)
    - 固定間隔スロットリングによるレート制限実装（120 req/min、_RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx に対応）。
    - 401 の際の自動トークンリフレッシュ（1 回のみ）を実装。トークン取得 API を get_id_token() で提供。
    - ページネーション対応の fetch_* 関数:
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - DuckDB への保存関数（冪等）:
      - save_daily_quotes（raw_prices へ ON CONFLICT DO UPDATE）
      - save_financial_statements（raw_financials へ ON CONFLICT DO UPDATE）
      - save_market_calendar（market_calendar へ ON CONFLICT DO UPDATE）
    - 入出力パース用ユーティリティ: _to_float, _to_int
    - fetched_at を UTC ISO タイムスタンプで記録（Look-ahead トレーサビリティ）

  - ニュース収集モジュール (data/news_collector.py)
    - RSS フィード収集フローを実装。デフォルトソースに Yahoo Finance RSS を登録。
    - セキュリティ考慮:
      - defusedxml を使用して XML 攻撃を防止
      - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）
      - URL 正規化時にトラッキングパラメータ（utm_* 等）を除去
      - URL スキーマ制限（HTTP/HTTPS のみ想定）
    - 記事 ID は正規化後の URL の SHA-256 を用いる方針（冪等性確保）
    - バルク INSERT のチャンク処理とトランザクション集約（パフォーマンスと安全性向上）

- Research 層（kabusys.research）
  - ファクター計算 (research/factor_research.py)
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を計算
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio を計算（true_range の NULL 伝播注意）
    - calc_value: raw_financials から最新の財務データを参照し per / roe を計算
    - 各関数は DuckDB の prices_daily / raw_financials のみを参照し、欠損時は None を返す挙動
  - 特徴量探索 (research/feature_exploration.py)
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括で計算（LEAD を使用）
    - calc_ic: Spearman の ρ（ランク相関）を実装（同順位は平均ランク）
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算
    - rank ユーティリティ（同順位は平均ランク、丸めによる tie 対応）
  - research パッケージの __all__ に主要関数をエクスポート

- Strategy 層（kabusys.strategy）
  - 特徴量エンジニアリング (strategy/feature_engineering.py)
    - build_features(conn, target_date): research モジュールの生ファクターを取り込み、ユニバースフィルタ（最低株価300円、20日平均売買代金5億円）を適用、選定ファクターを Z スコア正規化（±3 でクリップ）して features テーブルへ日付単位で置換（トランザクションで原子性確保）
    - 正規化に zscore_normalize（kabusys.data.stats）を使用
  - シグナル生成 (strategy/signal_generator.py)
    - generate_signals(conn, target_date, threshold=0.60, weights=None):
      - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
      - コンポーネントはシグモイド変換／逆転等で 0..1 にスケール
      - final_score = 重み付き合算（デフォルト重みを実装）、外部指定 weights は検証・正規化して適用
      - Bear レジーム判定（ai_scores の regime_score 平均が負なら Bear、サンプル数閾値あり）
      - BUY（threshold 以上）・SELL（ストップロス / スコア低下）を判定し signals テーブルへ日付単位で置換（トランザクション）
      - SELL 優先ポリシー（SELL 対象は BUY から除外しランクを再付与）
    - 内部ユーティリティ:
      - _sigmoid, _avg_scores, 各コンポーネント計算、_is_bear_regime、_generate_sell_signals（stop_loss=-8% 等）
    - 未実装機能（docstring にて明示）:
      - トレーリングストップ（peak_price が positions に必要）
      - 時間決済（保有 60 営業日超過）
  - strategy パッケージの __all__ に build_features / generate_signals をエクスポート

- その他
  - 複数モジュールで DuckDB 接続（duckdb.DuckDBPyConnection）を想定した API 設計
  - ロギング（logger）を各モジュールに導入して情報/警告/デバッグを出力

### Changed
- 初版リリースのため「変更」はありません（初期導入機能の一覧）。

### Fixed
- 初版リリースのため「修正」はありません。

### Security
- RSS パーシングで defusedxml を使用、受信サイズ制限を実装。
- ニュース URL 正規化でトラッキングパラメータ除去、HTTP スキーマ制限を考慮。
- J-Quants クライアントで 401 リフレッシュおよびリトライポリシー、RateLimiter によるレート制御を実装。

### Known limitations / TODO
- execution パッケージは空のプレースホルダ（発注層の具体実装は未提供）。
- monitoring についてはパッケージ名が __all__ に含まれるが、実装ファイルの有無や機能は限定的（今後拡張予定）。
- シグナル生成の一部エグジット条件（トレーリングストップ、時間決済）は positions テーブルへの追加フィールド（peak_price / entry_date 等）が必要で未実装。
- news_collector の RSS -> raw_news の銘柄紐付け（news_symbols）等、完全自動運用に向けた追加処理は今後実装予定。
- データ整合性（prices_daily / raw_prices / raw_financials のスキーマ・インデックス設定）は利用側での準備が必要。

---

今後の予定（例）
- execution 層の実装（kabu API との接続・注文実行）
- monitoring / alerting の実装（Slack通知等）
- news とシグナルの統合（AI スコア生成ワークフロー）
- 単体テスト・統合テストの充実と CI 設定

もし CHANGELOG のスタイルや記載粒度（もっと詳細なモジュール毎の変更履歴や、リリースノートに含めたい具体的な項目）がご希望であれば、対象とするリリース日や重要視する観点を教えてください。