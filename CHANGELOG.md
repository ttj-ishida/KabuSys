# CHANGELOG

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

- リリースは後方互換性を意識して記載しています。  
- 各項目はコードベースから推測してまとめた「実装された機能」「設計上の決定」「既知の制限／TODO」を含みます。

## [Unreleased]
- （現状なし）

## [0.1.0] - 2026-03-20
最初の公開バージョン。日本株自動売買システムのコア機能群を実装。

### 追加
- 基本パッケージ構成
  - パッケージ識別子: `kabusys`、バージョン `0.1.0`
  - パッケージ公開 API（__all__）に `data`, `strategy`, `execution`, `monitoring` を含む

- 環境変数・設定管理（kabusys.config）
  - .env ファイル自動ロード機能（プロジェクトルートは `.git` または `pyproject.toml` を探索）
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化するフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD`
  - .env 行パーサの実装（コメント/クォート、export プレフィックス、インラインコメント等に対応）
  - 環境変数取得ユーティリティ `Settings`（以下のプロパティを提供）
    - J-Quants: `jquants_refresh_token`
    - kabu API: `kabu_api_password`, `kabu_api_base_url`（デフォルト: http://localhost:18080/kabusapi）
    - Slack: `slack_bot_token`, `slack_channel_id`
    - DB パス: `duckdb_path`（デフォルト data/kabusys.duckdb）, `sqlite_path`（デフォルト data/monitoring.db）
    - システム設定: `env`（development|paper_trading|live の検証）、`log_level`（検証済み）、および便利なプロパティ `is_live`, `is_paper`, `is_dev`
  - 必須設定が欠けている場合は明確なエラーメッセージで ValueError を送出

- Data 層（kabusys.data）
  - J-Quants API クライアント（kabusys.data.jquants_client）
    - レート制限対応（120 req/min 固定間隔スロットリング）を行う _RateLimiter を実装
    - リトライロジック（指数バックオフ、最大試行回数 3 回、HTTP 408/429/5xx を対象）
    - 401 受信時は id_token を自動リフレッシュして 1 回リトライ
    - ページネーション対応のデータ取得（fetch_daily_quotes、fetch_financial_statements）
    - JPX マーケットカレンダー取得（fetch_market_calendar）
    - DuckDB への冪等保存関数（ON CONFLICT を用いた save_daily_quotes / save_financial_statements / save_market_calendar）
    - 取得時刻を UTC で記録し（fetched_at）、ルックアヘッドバイアスのトレースに対応
    - ユーティリティ `_to_float`, `_to_int` を実装（型安全な変換）

  - ニュース収集（kabusys.data.news_collector）
    - RSS フィード収集の骨格を実装（デフォルトソース: Yahoo Finance のビジネス RSS）
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、クエリソート、フラグメント除去）
    - XML パースに defusedxml を使用しセキュリティ対策（XML Bomb 等を防止）
    - 受信サイズ制限（10 MB）、SSRF 等へ配慮した設計
    - 記事IDを正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成して冪等性を確保
    - raw_news へのバルク保存を想定（チャンク化、1 トランザクションでの挿入、ON CONFLICT DO NOTHING を前提）

- Research 層（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日平均乖離）計算（営業日ベースのラグ）
    - Volatility: ATR (20 日)、atr_pct、avg_turnover（20 日平均売買代金）、volume_ratio（出来高比率）
    - Value: per、roe（raw_financials と prices_daily を結合）
    - 各関数は DuckDB の SQL ウィンドウ関数を活用して高速集計
    - データ不足時は None を返す（安全に扱える設計）
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns: 複数ホライズン対応、1/5/21 日がデフォルト）
    - IC（Information Coefficient）計算（Spearman の ρ：rank を内部実装）
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を算出
    - rank: 同順位は平均ランクとするアルゴリズムを実装（丸め処理で tie を安定化）
  - データ依存を prices_daily / raw_financials に限定（本番 API へはアクセスしない設計）

- Strategy 層（kabusys.strategy）
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
    - 研究環境の生ファクターを取り込み、ユニバースフィルタ・正規化（Z スコア）・クリッピング（±3）して features テーブルへ UPSERT（日単位で置換）
    - ユニバース定義（最低株価 300 円、20 日平均売買代金 >= 5 億円）
    - 正規化対象カラムの指定・欠損処理・トランザクションでの原子性保証
  - シグナル生成（kabusys.strategy.signal_generator）
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出
    - コンポーネントスコアの結合は重み付け平均（デフォルト重みを実装、ユーザ指定の weights を検証して再スケール）
    - Z スコア → シグモイド変換で [0,1] にマッピング
    - BUY シグナル閾値デフォルト 0.60（threshold）、Bear レジーム検知時は BUY を抑制
    - SELL（エグジット）条件を実装
      - ストップロス: 終値/avg_price - 1 < -8%
      - スコア低下: final_score が threshold 未満
      - SELL は BUY 優先ルールに基づき BUY から除外、signals テーブルへ日単位で置換（トランザクション）
    - AI ニューススコアは未登録時は中立（0.5）で補完
    - 最終的に signals テーブルへ冪等的に書き込み（DELETE + bulk INSERT をトランザクションで実行）
  - 戦略設計に関する多数の設計注記（ルックアヘッド回避、非依存設計、欠損補完ポリシー等）

- パッケージ初期化（モジュールの __init__）
  - 主要 API をトップレベルで公開（build_features / generate_signals 等）

### 変更
- （初版のため変更履歴なし）

### 修正
- （初版のため修正履歴なし）

### 既知の制限 / TODO（コード内コメントより）
- 売却条件の未実装項目（将来の実装候補）
  - トレーリングストップ（peak_price を positions テーブルに保持する必要あり）
  - 時間決済（保有 60 営業日超過）
- news_collector の具体的な RSS パース・DB スキーマへのマッピングは骨格実装（詳細実装・マッピングロジックは追加が想定される）
- monitoring モジュールが __all__ に含まれているが、今回のスナップショットでは具体的実装ファイルが含まれていない（プレースホルダ）
- execution パッケージは空の __init__ のみで、発注ロジック（kabu/発注APIとの統合）は別途実装が必要
- 外部依存／環境
  - DuckDB を前提としたテーブル構成（raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar 等）が必要
  - defusedxml を利用（XML セキュリティ依存）
- 一部のバリデーション／境界条件はログ警告で扱う設計（例: 無効な weights をスキップ・フォールバック）

### セキュリティおよび堅牢性に関する設計事項
- API クライアントにてレート制限とリトライ（429 の Retry-After を尊重）を実装
- XML パースに defusedxml を使用して XML 攻撃対策
- ニュース収集における受信サイズ制限・URL 検査で SSRF/DoS を軽減
- 環境変数ロードにおいて OS 環境変数を保護するロジックを実装（.env.local は上書き可だが OS 環境は保護）

---

今後のリリースでは以下のような拡張が想定されます（参考）:
- execution 層の具体的発注ロジック / kabu API 統合
- monitoring（Slack 通知等）の実装
- news_collector の記事→銘柄紐付けロジックの強化（NLP・シンボル抽出）
- Sell 条件の追加（トレーリングストップ、時間決済）
- 単体テスト・統合テストの追加（KABUSYS_DISABLE_AUTO_ENV_LOAD を活用したテスト向けフックの利用）

---

参考: 実装ファイル一覧（本バージョンで確認できる主要ファイル）
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/data/jquants_client.py
- src/kabusys/data/news_collector.py
- src/kabusys/research/factor_research.py
- src/kabusys/research/feature_exploration.py
- src/kabusys/research/__init__.py
- src/kabusys/strategy/feature_engineering.py
- src/kabusys/strategy/signal_generator.py
- src/kabusys/strategy/__init__.py
- src/kabusys/execution/__init__.py

（以上、コードベースから推測して作成した CHANGELOG です。実際のリリースノート作成時はコミット履歴・Issue を参照して更新してください。）