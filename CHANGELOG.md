# Changelog

すべての重要な変更は Keep a Changelog のフォーマットに従って記載します。  
このファイルはコードベースから推測して作成した初期の変更履歴（初回リリース相当）です。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 初回リリース
リリース日: 未設定

### 追加 (Added)
- パッケージ骨組みを実装
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring を想定（execution パッケージは空の __init__ を含む）

- 環境設定管理モジュール (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサ実装（コメント、export プレフィックス、クォート・エスケープ処理、インラインコメントの扱い等に対応）。
  - override と protected オプションをサポートした .env 読み込み（.env.local が .env を上書き）。
  - Settings クラスを実装（必須環境変数の検証を含む）：
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パス設定: DUCKDB_PATH, SQLITE_PATH（デフォルトを提供）
    - 環境とログレベルの検証: KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（DEBUG/INFO/...）
    - ヘルパープロパティ: is_live / is_paper / is_dev

- データ取得・保存モジュール (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装（fetch_* / save_* のセット）:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）
    - save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB への冪等保存：ON CONFLICT や重複排除）
  - レートリミッタ実装（固定間隔スロットリング、120 req/min を基準）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）、429 の Retry-After を考慮。
  - 401 を受信した際のトークン自動リフレッシュを 1 回だけ行う仕組み（モジュールレベルの ID トークンキャッシュ）。
  - ページネーション中にトークンを共有するためのキャッシュ利用。
  - 取得データのパースと型変換ユーティリティ (_to_float / _to_int) を提供。
  - fetched_at を UTC ISO8601 で記録し、データ取得時刻を明確化（look-ahead bias のトレーサビリティ向上）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード収集と raw_news テーブル向けの冪等保存処理（ON CONFLICT DO NOTHING 想定）。
  - URL 正規化処理（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
  - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）や defusedxml による XML 攻撃対策。
  - 記事 ID を正規化 URL のハッシュで生成する方針（冪等性確保）。
  - RSS ソースのデフォルト設定（例: Yahoo Finance のビジネスカテゴリ）。
  - バルク挿入のチャンク化実装想定（INSERT チャンクサイズ制御）。

- リサーチ系モジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算（200日移動平均の存在チェック等）
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算（true range の NULL 伝播に配慮）
    - calc_value: per, roe を計算（raw_financials の最新レコードを取得して株価と組合せ）
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 複数ホライズンの将来リターン計算（デフォルト [1,5,21]）
    - calc_ic: スピアマンのランク相関（ties は平均ランク）で IC を計算
    - factor_summary: count/mean/std/min/max/median を算出
    - rank: 同順位は平均ランクを割り当てるランク関数
  - research パッケージの __all__ で主要関数を公開

- ストラテジー系モジュール (kabusys.strategy)
  - 特徴量エンジニアリング (feature_engineering.build_features)
    - research の calc_* 関数を呼び出して生ファクターを取得、ユニバースフィルタ適用、Zスコア正規化（_NORM_COLS を対象）、±3でクリップ、DuckDB の features テーブルへ日付単位で置換（BEGIN/DELETE/INSERT/COMMIT）する冪等処理を提供。
    - ユニバース制約: 最低株価 = 300 円、20日平均売買代金 >= 5億円。
  - シグナル生成 (signal_generator.generate_signals)
    - features と ai_scores を統合して component score（momentum/value/volatility/liquidity/news）を計算、重みづけ合算で final_score を生成。
    - デフォルト重みと閾値: momentum=0.40, value=0.20, volatility=0.15, liquidity=0.15, news=0.10、BUY 閾値 = 0.60。
    - Z スコアをシグモイドで [0,1] に変換、欠損コンポーネントは中立値 0.5 で補完。
    - Bear レジーム検知（ai_scores の regime_score 平均が負・サンプル数閾値あり）時は BUY を抑制。
    - SELL（エグジット）条件を実装:
      - ストップロス: 終値 / avg_price - 1 < -8%（優先）
      - final_score が threshold 未満
      - 価格欠損や avg_price の無効値は処理をスキップする安全策
    - SELL 優先ポリシー（SELL 対象は BUY から除外）と日付単位の置換で signals テーブルへ保存（トランザクションで原子性確保）。

- データ統計ユーティリティ (kabusys.data.stats への依存を想定)
  - zscore_normalize を利用して正規化処理を行う設計。

### 変更 (Changed)
- （初回リリースのため「変更」は特になし。設計上の留意点をドキュメント的に反映）
  - SQL クエリは DuckDB 向けに最適化され、ウィンドウ関数や LEAD/LAG/AVG を多用する形で実装。
  - NULL 伝播やデータ不足時の挙動に細かな配慮（例: true_range の計算で high/low/prev_close のいずれかが NULL の場合は NULL とする等）。

### 修正 (Fixed)
- （初回リリースのため「修正」は特になし）

### セキュリティ (Security)
- RSS パースに defusedxml を利用して XML Bomb 等の攻撃緩和を図る設計。
- news_collector で受信サイズ上限を設定（MAX_RESPONSE_BYTES）してメモリ DoS を防止。
- ニュース URL の正規化でトラッキングパラメータを除去、SSRF 緩和のためスキームの検査を想定。

### 既知の制限 / 未実装 (Known Issues / Not Implemented)
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装で、positions テーブルに peak_price / entry_date が必要になる旨が注記されている。
- news_collector の記事 ID 生成やシンボル紐付けの詳細実装は設計方針として述べられているが、該当コード断片は部分的に提示されているため実装の完全性は実環境での確認が必要。
- research モジュールは外部依存（pandas 等）を使わない設計だが、大規模データセットでのパフォーマンス検証が必要。

### 移行 / 利用時の注意 (Migration / Usage Notes)
- 必須環境変数（JQUANTS_REFRESH_TOKEN 等）を設定しないと Settings プロパティが ValueError を投げます。 .env.example を参考に .env を作成してください。
- 自動で .env を読み込むため、テスト時や特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読込を無効化してください。
- DuckDB のスキーマは各 save_* / build_features / generate_signals の SQL が前提となるため、スキーマ整備（raw_prices/raw_financials/prices_daily/features/ai_scores/positions/signals/market_calendar 等）を実行前に準備してください。
- J-Quants API の利用にはレート制限・リトライの挙動が組み込まれていますが、実運用では API キーの権限・使用量を確認してください。

---

（この CHANGELOG はソースコードからの推測に基づいて作成しました。実際のリリースノート作成時はリリース日やコミット単位の変更点、影響範囲の確認を推奨します。）