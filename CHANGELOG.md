# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

- リリース方針: 主要な機能追加は Added、バグ修正は Fixed、互換性のある改善は Changed、破壊的変更は Removed、セキュリティ修正は Security に記載します。

## [Unreleased]
（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-20

### Added
- パッケージ基本構成
  - kabusys パッケージ初期版本を追加。パッケージバージョンは `0.1.0`。
  - エクスポートモジュール: data, strategy, execution, monitoring を公開（execution は空のパッケージとしてプレースホルダ）。

- 設定管理 (.env) / 環境変数読み込み
  - 環境変数・設定管理モジュール `kabusys.config` を追加。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を探索）。これにより CWD に依存せず .env 自動読み込みが可能。
  - .env/.env.local の自動ロード機能を実装。優先順位は OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化するフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` に対応。
  - .env の行パーサを堅牢化（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いをサポート）。
  - Settings クラスを提供し、J-Quants / kabu / Slack / DB パス等の設定をプロパティで取得可能に。
  - 設定値の妥当性チェック（KABUSYS_ENV は development/paper_trading/live のみ、LOG_LEVEL は標準レベルのみ）。

- Data 層: J-Quants API クライアント
  - `kabusys.data.jquants_client` を追加。
  - レートリミッタ実装（120 req/min、固定間隔スロットリング）。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。429 の場合は Retry-After を尊重。
  - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライする仕組みを実装（無限再帰防止）。
  - ページネーション対応の取得関数を追加:
    - fetch_daily_quotes (日足 OHLCV)
    - fetch_financial_statements (財務データ)
    - fetch_market_calendar (市場カレンダー)
  - DuckDB への保存関数を追加（冪等性を考慮した ON CONFLICT / DO UPDATE 実装）:
    - save_daily_quotes -> raw_prices
    - save_financial_statements -> raw_financials
    - save_market_calendar -> market_calendar
  - 取得日時（fetched_at）を UTC ISO 形式で記録し、Look-ahead バイアス対策を考慮。
  - _to_float / _to_int 等の堅牢な型変換ユーティリティを実装。

- Data 層: ニュース収集
  - `kabusys.data.news_collector` を追加。
  - RSS フィード収集、記事正規化、raw_news への冪等保存機能を実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等の対策）。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 対策。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）。
    - 記事 ID は URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を確保。
    - SSRF 対策や不正なスキームの排除（実装方針に準拠）。
  - バルク INSERT のチャンク化を行い、DB 書き込みの安定性を向上。

- Research 層
  - `kabusys.research.factor_research`:
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離率の計算。
    - calc_volatility: 20 日 ATR、相対 ATR (atr_pct)、20 日平均売買代金、出来高比率を計算。
    - calc_value: PER / ROE（raw_financials と prices_daily の組合せ）。
    - SQL + Window 関数を利用し DuckDB 接続を直接参照する設計。
    - 外部ライブラリに依存せず標準ライブラリ + duckdb で実装。
  - `kabusys.research.feature_exploration`:
    - calc_forward_returns: 指定日からの将来リターン（任意ホライズン）を計算。ホライズンは営業日ベースで検証。
    - calc_ic: スピアマンランク相関（IC）を実装。サンプル不足（<3）や定数分散のケースは None を返す。
    - factor_summary: 各ファクターの基本統計量（count, mean, std, min, max, median）を計算。
    - rank: 同順位の平均ランクを返す実装（丸め処理で ties の誤判定を抑制）。
  - これらを研究用 API として再エクスポート (`kabusys.research.__all__`)。

- Strategy 層
  - `kabusys.strategy.feature_engineering`:
    - build_features(conn, target_date): research で計算した生ファクターを統合・正規化して features テーブルへ UPSERT（日付単位で削除→挿入の置換）する。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を実装。
    - Z スコア正規化（kabusys.data.stats に依存）および ±3 でのクリップを実施し外れ値影響を抑制。
    - トランザクション（BEGIN/COMMIT/ROLLBACK）で原子性を保証。ROLLBACK の失敗は logger.warning で捕捉。
  - `kabusys.strategy.signal_generator`:
    - generate_signals(conn, target_date, threshold=0.60, weights=None): features と ai_scores を統合して最終スコアを算出し、BUY/SELL シグナルを生成して signals テーブルへ保存（同様に日付単位の置換で冪等性を保証）。
    - コンポーネントスコア計算（momentum/value/volatility/liquidity/news）を実装。Z スコアをシグモイドで [0,1] に変換するユーティリティを持つ。
    - 重みのバリデーションと正規化ロジックを実装（未知キーや非数値は無視、合計が 1 でなければ再スケール）。
    - Bear レジーム判定: ai_scores の regime_score の平均が負かつサンプル数 >= 3 の場合に BUY を抑制。
    - SELL 条件:
      - ストップロス（終値 / avg_price - 1 < -8%）
      - final_score が閾値未満（score_drop）
    - SELL 優先ポリシー: SELL 対象は BUY から除外し、BUY のランクは再付与。
    - features が空の場合は BUY をスキップして SELL 判定のみ行う旨のログを出力。
    - いくつかのエグジット条件（トレーリングストップ、時間決済）は未実装で、positions テーブルに追加情報（peak_price / entry_date 等）が必要である旨をコメントで明示。

- ロギング・診断
  - 主要処理で logger による情報/警告/デバッグ出力を整備（例: build_features, generate_signals, fetch/save 系）。
  - DB トランザクション失敗時の挙動やデータ欠損時の警告ログを充実。

### Changed
- （初回リリースのため、該当なし）

### Fixed
- （初回リリースのため、該当なし）

### Removed
- （初回リリースのため、該当なし）

### Security
- RSS パーサに defusedxml を採用して XML 関連攻撃を緩和。
- ニュース取得時の受信サイズ制限、URL 正規化、SSRF 対策方針を導入。
- API クライアントでトークン管理・再取得を慎重に扱い、不適切なトークン再帰呼び出しを防止。

### Known limitations / TODO
- signal_generator の一部のエグジット戦略（トレーリングストップ、時間決済）は未実装。positions テーブルに peak_price / entry_date の保持が必要。
- execution パッケージはまだ実装されていない（発注ロジック・kabu API 連携は未実装）。
- monitoring パッケージの実装状況は未記載（__all__ に含まれるが内容は今後追加予定）。
- NewsCollector の RSS フィードリストは最小構成（デフォルト: Yahoo Finance）で、追加フィードやより厳密なセキュリティフィルタは今後拡張予定。

---

（注）この CHANGELOG は提供されたコード内容からの推測に基づいて作成しています。実際のリリース履歴や日付はプロジェクトの運用方針に合わせて調整してください。