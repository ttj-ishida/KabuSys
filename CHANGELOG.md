# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
リリース日はコードベースから推測して記載しています。

## [Unreleased]
- 今後の変更点をここに記載します。

## [0.1.0] - 2026-03-20
初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。以下はコードベースから推測した主な追加点・設計方針です。

### Added
- パッケージ基盤
  - pakage 初期化: `kabusys.__init__` にバージョン情報と公開モジュール一覧を追加。
  - モジュール構成: data / research / strategy / execution / monitoring 等の名前空間を整備。

- 設定・環境変数管理 (`kabusys.config`)
  - .env 自動読み込み機能を実装（プロジェクトルートの検出: `.git` または `pyproject.toml` を基準）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードの無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD` に対応。
  - 高機能な .env パーサ: `export KEY=val` 形式、シングル/ダブルクォート内のエスケープ・コメント処理を考慮したパーシング。
  - 環境設定クラス `Settings` を提供（J-Quants / kabuAPI / Slack / DB パス / 実行環境判定 / ログレベル等のプロパティ）。
  - 必須キー未設定時は明確な例外メッセージを送出。

- データ取得・保存（J-Quants クライアント） (`kabusys.data.jquants_client`)
  - API クライアント実装: ページネーション対応の fetch 系関数（株価・財務・カレンダー）。
  - レート制限管理: 固定間隔スロットリング（120 req/min）を実装した `_RateLimiter`。
  - 再試行ロジック: 指数バックオフ、最大 3 回、408/429/5xx を対象。
  - 401 応答時トークン自動リフレッシュ機構（1 回のみリトライ）とトークンキャッシュ。
  - JSON デコード失敗 / ネットワークエラー時の明確なエラーハンドリング。
  - DuckDB への保存ユーティリティ（`save_daily_quotes`, `save_financial_statements`, `save_market_calendar`）:
    - 冪等性確保のため ON CONFLICT（UPSERT）を使用。
    - fetched_at を UTC ISO で記録（Look-ahead バイアス対策）。
    - PK 欠損行のスキップとログ警告。
    - 型変換ユーティリティ `_to_float` / `_to_int` を実装。

- ニュース収集 (`kabusys.data.news_collector`)
  - RSS フィードの収集・前処理・保存機能を実装（デフォルトソースに Yahoo Finance）。
  - URL 正規化: トラッキングパラメータ除去（utm_/fbclid/gclid 等）、スキーム/ホストの小文字化、フラグメント削除、クエリソート。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等対策）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を防止。
    - SSRF を意識した URL/スキーム制御（HTTP/HTTPS 想定）。
  - バルク挿入のチューニング（チャンクサイズ）とトランザクション最適化。
  - 記事 ID を正規化 URL のハッシュで生成し冪等性を確保。

- 研究系ユーティリティ (`kabusys.research`)
  - ファクター計算: `calc_momentum`, `calc_volatility`, `calc_value` を提供（prices_daily / raw_financials を使用）。
  - 特徴量探索:
    - 将来リターン計算 `calc_forward_returns`（複数ホライズン、営業日ベースの計算）。
    - IC（Spearman の ρ）計算 `calc_ic` とランク変換 `rank`（同順位は平均ランク）。
    - ファクター統計サマリー `factor_summary`（count/mean/std/min/max/median）。
  - 外部依存を避け、標準ライブラリと DuckDB で完結する設計。

- 特徴量エンジニアリング (`kabusys.strategy.feature_engineering`)
  - 研究環境の生ファクターを取り込み、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
  - Z スコア正規化（`zscore_normalize` を利用）、±3 でクリップ。
  - 日付単位で features テーブルへ置換（DELETE + INSERT、トランザクションで原子性保証）。
  - ルックアヘッドバイアスを防ぐため target_date 時点のデータのみを利用。

- シグナル生成 (`kabusys.strategy.signal_generator`)
  - features と ai_scores を統合し、コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
  - シグモイド変換や欠損時の中立補完（0.5）を用いて final_score を計算。
  - デフォルト重みと閾値を実装（デフォルト final BUY 閾値 0.60、重みは momentum 0.40 等）。
  - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数十分時）で BUY を抑制。
  - エグジット判定（SELL）:
    - ストップロス: 終値 / avg_price - 1 < -8%（最優先）
    - スコア低下: final_score < threshold
    - 価格欠損・features 未存在時の安全策（判定スキップや score=0 扱い）を実装。
  - signals テーブルへの日付単位置換（トランザクション + バルク挿入で原子性）。
  - 重み入力の検証・正規化（未知キー・非数値・負値を排除、合計が 1.0 でない場合に再スケール）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- XML パースに defusedxml を採用（ニュース収集での XML 攻撃対策）。
- ニュース URL の正規化 / トラッキング除去によりクエリパラメータ由来の情報漏洩リスクを低減。
- ネットワーク通信部でのタイムアウト・再試行・RateLimit の実装により過負荷や API レート超過のリスクを低減。

### Performance
- J-Quants クライアントで固定間隔スロットリングを導入し、API レート制限を遵守。
- DuckDB へのバルク挿入とトランザクションを用いた日付単位の置換で I/O オーバーヘッドを削減。
- ニュースのバルク挿入をチャンク化して SQL 長・パラメータ上限を回避。

### Design / Notes
- ルックアヘッドバイアス防止を設計方針として一貫して重視（fetched_at の記録、target_date のみ参照等）。
- 発注層（execution）への依存を排し、strategy 層はシグナル生成に専念する構造。
- 多くの処理で冪等性（UPSERT / 日付単位置換）を担保。
- 型注釈・ロギングを多用し可観測性とデバッグ性を向上。

---

（この CHANGELOG はソースコードの実装内容から推測して作成したものであり、実際のリリースノートとして使用する際は運用者による確認・追記をお願いします。）