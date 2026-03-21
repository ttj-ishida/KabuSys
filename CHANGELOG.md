# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
変更の重要度はセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-21

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しています。主な追加点・設計方針は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
  - パブリック API: `data`, `strategy`, `execution`, `monitoring` をエクスポート。

- 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装（プロジェクトルートは .git / pyproject.toml を基準に探索）。
  - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` に対応。
  - .env パーサーの実装（コメント行、export プレフィックス、クォート／エスケープ、インラインコメントの扱い等に対応）。
  - Settings クラスを提供し、必須設定値（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）やデフォルト値（KABU_API_BASE_URL, データベースパス等）を安全に取得できるように実装。
  - KABUSYS_ENV / LOG_LEVEL の妥当性チェック（許容値検証）を実装。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - rate limiter（120 req/min）による固定間隔スロットリング。
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx の再試行）。429 の場合は Retry-After ヘッダを優先。
    - 401 発生時はリフレッシュトークンを使って id_token を自動更新して 1 回だけ再試行。
    - ページネーション対応（pagination_key を用いたループ）。
    - JSON デコード・エラーハンドリング。
  - API ユーティリティ関数:
    - get_id_token(refresh_token: Optional[str]) — リフレッシュトークンから id_token を取得。
    - fetch_daily_quotes(...) — 日足データ取得（ページネーション対応）。
    - fetch_financial_statements(...) — 財務データ取得（ページネーション対応）。
    - fetch_market_calendar(...) — マーケットカレンダー取得。
  - DuckDB へ冪等に保存する関数:
    - save_daily_quotes(conn, records) — raw_prices テーブルへ ON CONFLICT DO UPDATE による保存。
    - save_financial_statements(conn, records) — raw_financials テーブルへ冪等保存。
    - save_market_calendar(conn, records) — market_calendar テーブルへ冪等保存。
  - 型変換ユーティリティ: `_to_float`, `_to_int`（不正値は None に変換）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集し raw_news に冪等保存する処理を実装（デフォルトソースに Yahoo Finance を含む）。
  - セキュリティ・堅牢性:
    - defusedxml を用いた XML パース（XML Bomb 等の対策）。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を防止。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリキーでソート）。
    - 記事 ID は正規化 URL 等の SHA-256（先頭32文字）で生成し冪等性を確保。
    - HTTP/HTTPS 以外のスキームや SSRF に注意する実装方針。
  - バルク INSERT チャンクングや INSERT RETURNING を想定した性能考慮。

- 研究用モジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）を DuckDB SQL で計算。
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）を計算（true_range の NULL 伝播に注意）。
    - Value（per, roe）を raw_financials と prices_daily を組み合わせて計算。
    - 各関数は (date, code) をキーとする dict のリストを返す設計。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns(conn, target_date, horizons) — 将来リターン（horizons デフォルト: [1,5,21]）を計算。
    - calc_ic(factor_records, forward_records, factor_col, return_col) — スピアマンのランク相関（IC）を実装（有効サンプル 3 未満は None）。
    - factor_summary(records, columns) — 各ファクター列の count/mean/std/min/max/median を計算。
    - rank(values) — 同順位は平均ランクにするランク関数（丸めで ties の検出漏れを防止）。
  - 研究用ユーティリティとして zscore_normalize を外部から再エクスポート。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - research 側で計算された生ファクターを統合・正規化して features テーブルへ保存する処理を実装。
  - 処理フロー:
    1. calc_momentum, calc_volatility, calc_value から生ファクターを取得
    2. ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用
    3. 一部カラムを Z スコア正規化（±3 でクリップ）
    4. 日付単位の置換（DELETE + INSERT トランザクション）で冪等性を担保
  - public API: build_features(conn, target_date) → upsert した銘柄数を返す。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して final_score を計算し、BUY/SELL シグナルを生成して signals テーブルへ保存する処理を実装。
  - 主要ロジック:
    - コンポーネントスコア: momentum/value/volatility/liquidity/news（news は AI スコアをシグモイドで変換）
    - デフォルト重み: momentum=0.40, value=0.20, volatility=0.15, liquidity=0.15, news=0.10（与えられた weights は検証・正規化して適用）
    - BUY 閾値デフォルト: 0.60（threshold パラメータで上書き可）
    - Bear レジーム検出: ai_scores の regime_score 平均が負の場合に BUY を抑制（サンプル数不足時は Bear とみなさない）
    - SELL 条件:
      1. ストップロス（終値/avg_price - 1 < -8%）
      2. final_score が threshold 未満
      - 未実装だが想定される追加条件: トレーリングストップ、時間決済（設計コメントあり）
    - SELL 優先ポリシー: SELL 対象は BUY から除外、signals を日付単位で置換（トランザクションで原子性）
  - public API: generate_signals(conn, target_date, threshold=0.6, weights=None) → 書き込んだシグナル数を返す。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- RSS パーサで defusedxml を利用（XML パーシングの安全化）。
- ニュース収集で URL 正規化とトラッキングパラメータ除去、受信サイズ制限等を実施（SSRF・DoS 対策の基本実装）。
- J-Quants クライアントで認証リフレッシュの際の無限再帰を防止するフラグ（allow_refresh）を用意。

### 既知の制約・注意点 (Notes)
- DuckDB 接続を引数に受ける設計のため、スキーマ（テーブル定義）は呼び出し側で用意する必要があります（prices_daily, raw_financials, features, ai_scores, positions, signals, raw_prices, raw_financials, market_calendar, raw_news など）。
- 一部の高度なエグジット条件（トレーリングストップ、保持日数による決済など）は設計コメントとして残してあり、positions テーブルへの追加データ（peak_price, entry_date 等）が必要になります。
- 外部解析ライブラリ（pandas 等）には依存せず、標準ライブラリ + duckdb の組み合わせで実装されています。
- 設定は環境変数ベース（.env 自動ロードあり）。CI/テストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を推奨。

---

今後のリリースでは、以下を予定しています（非網羅）:
- execution 層（kabuステーション API を使った実際の発注ロジック）の実装
- monitoring / Slack 通知等の運用機能の追加
- トレーリングストップや時間決済などのエグジット戦略の実装
- テストカバレッジとドキュメントの拡充

--- 
（この CHANGELOG はコードベースの実装内容から推測して作成しています。）