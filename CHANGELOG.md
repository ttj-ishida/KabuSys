# CHANGELOG

すべての注目すべき変更履歴を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

履歴はセマンティックバージョニングに従います。  
現在のリリース: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-20
最初の公開リリース。日本株向け自動売買プラットフォームのコア機能群を実装しました。主な追加点・設計上の考慮事項は以下のとおりです。

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys.__init__、バージョン "0.1.0"）。
  - サブパッケージ公開: data, strategy, execution, monitoring（execution は空のパッケージとしてプレースホルダ）。

- 設定管理 (kabusys.config)
  - .env ファイルや環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml を探索）から .env を読み込み、.env.local で上書き（OS 環境変数を保護）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env 行パーサの強化: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、コメント取り扱いの細かい仕様。
  - 必須値チェック (_require) と設定値バリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。
  - DB パス（DuckDB / SQLite）を Path オブジェクトで返すユーティリティ。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - レート制限 (120 req/min) を守る固定間隔スロットリング実装（_RateLimiter）。
    - 冪等での DuckDB 保存（ON CONFLICT による upsert）を提供する save_* 関数:
      - save_daily_quotes: raw_prices への保存
      - save_financial_statements: raw_financials への保存
      - save_market_calendar: market_calendar への保存
    - ページネーション対応、pagination_key 管理。
    - 再試行ロジック（指数バックオフ、最大3回）および HTTP ステータスに基づく待機 (Retry-After 優先)。
    - 401 Unauthorized 受信時のトークン自動リフレッシュ（1 回のみ）とトークンキャッシュ。
    - 安全で堅牢な JSON デコードエラーハンドリングとネットワークエラー処理。
    - 型変換ユーティリティ (_to_float, _to_int)。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからのニュース収集モジュールを実装（デフォルトソースに Yahoo Finance）。
  - セキュリティ対策:
    - defusedxml を用いた XML パースで XML-Bomb 等を防止。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES）を設けメモリ DoS を防止。
    - HTTP/HTTPS 以外のスキームの拒否や潜在的 SSRF 緩和の考慮（設計記載）。
  - 冪等性: 記事ID は正規化 URL の SHA-256 ハッシュ先頭を用いる案内（ドキュメントに記載）。
  - バルク INSERT のチャンク処理、トランザクションまとめ、挿入件数の正確な算出（INSERT RETURNING 想定）。

- リサーチ / ファクター計算 (kabusys.research)
  - ファクター計算モジュール群を実装:
    - factor_research:
      - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev を計算（ウィンドウサイズやスキャンバッファ考慮）。
      - calc_volatility: atr_20、atr_pct、avg_turnover、volume_ratio を計算（true_range 処理における NULL 制御）。
      - calc_value: per / roe（raw_financials の最新財務データと結合）。
    - feature_exploration:
      - calc_forward_returns: 複数ホライズンの将来リターンを一度のクエリで取得（LEAD を利用）。
      - calc_ic: Spearman（ランク）相関（IC）を実装（同順位は平均ランク処理）。
      - factor_summary: count/mean/std/min/max/median を計算する統計サマリ。
      - rank: タイの平均ランク処理（丸めを行い浮動小数点誤差を抑制）。
    - research パッケージ __init__ に主要ユーティリティを公開。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - 研究側で計算した生ファクターを統合して features テーブルへ保存する build_features 実装。
    - ユニバースフィルタ（最低株価、20日平均売買代金）適用。
    - Z スコア正規化（zscore_normalize を利用）、±3 でクリップ。
    - 日付単位で削除→挿入するトランザクションベースの置換（冪等性確保）。
    - DuckDB を利用した価格取得の最適化（target_date 以前の最新価格取得）。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して最終スコアを算出し、BUY/SELL シグナルを生成する generate_signals 実装。
    - コンポーネントスコア: momentum/value/volatility/liquidity/news（AI スコア）を計算。
    - スコア正規化: Z スコアをシグモイド変換し [0,1] にマッピング。
    - 重み付けの受け入れと正規化（不正入力の検証、既定値へのフォールバック、合計の再スケーリング）。
    - Bear レジーム検知（AI の regime_score 平均 < 0、サンプル数による抑制）。
    - BUY は閾値超え銘柄、SELL はポジションのストップロスおよびスコア低下で判定。SELL を BUY より優先して排除。
    - signals テーブルへの日付単位置換（トランザクション＋バルク挿入で原子性を保証）。
    - 実装済みの制御パラメータ: デフォルト閾値 0.60、ストップロス -8%。

- ロギング / エラーハンドリング
  - 各モジュールで詳細なログ（info/warning/debug）を出力。
  - トランザクション失敗時はROLLBACKを試行し、その失敗も警告ログに残す。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- RSS パースに defusedxml を採用し XML 攻撃対策を実施。
- ニュースの URL 正規化とトラッキングパラメータ除去により、冪等性と情報漏洩リスクを低減。
- .env 読み込み時に OS 環境変数を保護する仕組みを導入（protected set）。

### 既知の制限 / 未実装な点 (Known limitations / TODO)
- signal_generator のいくつかのエグジット条件はドキュメントに言及されているが未実装:
  - トレイリングストップ（peak_price を positions テーブルで管理する必要あり）
  - 時間決済（保有 60 営業日超過）
- news_collector の実装は設計に沿った安全性・正規化を記載しているが、記事ID生成や銘柄紐付け(news_symbols)の具体的な SQL スキーマ周りは実行環境に依存。
- 外部依存:
  - duckdb、defusedxml 等の導入が必要。
- AI スコア（ai_scores）がない場合は中立値（0.5）で補完している点により、AI スコアが存在する環境との結果差が発生する。

### 互換性 / マイグレーション (Compatibility / Migration)
- 本バージョンは初回リリースのため破壊的変更はなし。
- DuckDB スキーマ（raw_prices/raw_financials/features/ai_scores/positions/signals 等）が前提。既存データベースを利用する場合はスキーマ互換性を確認してください。

---

貢献・バグ報告・改善提案は issue を通してお願いします。