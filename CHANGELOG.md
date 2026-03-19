# Changelog

すべての重要な変更履歴はこのファイルで管理します。  
フォーマットは Keep a Changelog に準拠します。  

---

## [Unreleased]
（なし）

---

## [0.1.0] - 2026-03-19

初回リリース。本リポジトリの主要機能を実装した初版です。

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリーポイント `kabusys` を追加。公開 API として `data`, `strategy`, `execution`, `monitoring` をエクスポート。
  - バージョン番号を `0.1.0` に設定。

- 設定管理 (kabusys.config)
  - 環境変数管理モジュールを実装。
  - プロジェクトルート（.git または pyproject.toml）を起点に `.env` / `.env.local` を自動読み込み（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
  - .env パーサを実装（`export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、コメント扱いの細かなルールに対応）。
  - OS 環境変数を保護するための上書き制御（`.env.local` は既存 OS 環境を除外して上書き可能）。
  - `Settings` クラスを提供し、必須環境変数をプロパティ経由で取得（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル等）。
  - DB パス（DuckDB / SQLite）や `KABUSYS_ENV` / `LOG_LEVEL` の検証・デフォルト処理、環境判定（is_live / is_paper / is_dev）を実装。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - 固定間隔スロットリングによるレート制限（120 req/min）を実装する `RateLimiter` を導入。
  - リトライ制御（指数バックオフ、最大3回）、ステータスコード別の扱い（408/429/5xx をリトライ候補）、429 の `Retry-After` を考慮。
  - 401 受信時はリフレッシュトークンから ID トークンを自動更新して 1 回だけリトライするロジックを実装（無限再帰対策あり）。
  - ページネーション対応の取得関数を実装（`fetch_daily_quotes`, `fetch_financial_statements`, `fetch_market_calendar`）。
  - DuckDB への冪等保存関数を実装（`save_daily_quotes`, `save_financial_statements`, `save_market_calendar`）し、`ON CONFLICT DO UPDATE` により重複を排除。
  - レスポンスからの型変換ユーティリティ（`_to_float`, `_to_int`）を実装。
  - モジュールレベルで ID トークンをキャッシュしてページネーション間で共有。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからニュースを収集して `raw_news` へ保存するモジュールを追加。
  - URL 正規化（スキーム/ホストの小文字化、トラッキングパラメータ削除、フラグメント除去、クエリソート）を実装。
  - defusedxml を用いた安全な XML パース、受信サイズ上限、SSRF 回避などセキュリティ対策を考慮した設計（ドキュメントとしての設計方針を明示）。
  - 記事 ID の一意化（URL 正規化後のハッシュ）やバルク INSERT のチャンク処理など、冪等性・効率性を考慮した保存方針を採用。

- リサーチ機能 (kabusys.research)
  - 要素ファクター計算群を実装・エクスポート（`calc_momentum`, `calc_volatility`, `calc_value`）。
  - 特徴量探索ユーティリティを実装：将来リターン計算 `calc_forward_returns`（複数ホライズン対応）、IC 計算 `calc_ic`（Spearman の ρ）、基本統計サマリー `factor_summary`、ランク付けユーティリティ `rank`。
  - すべて DuckDB の `prices_daily` / `raw_financials` テーブルのみを参照する設計（外部 API や発注処理には依存しない）。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - 研究環境から得た生ファクターを正規化・合成して `features` テーブルへ保存する `build_features(conn, target_date)` を実装。
  - ユニバースフィルタ（価格 >= 300 円、20日平均売買代金 >= 5 億円）を実装。
  - 指数・外れ値対策として Z スコア正規化（`zscore_normalize` を利用）および ±3 でのクリップを実施。
  - 日付単位の置換（削除→挿入）をトランザクションで行い冪等性と原子性を担保。

- シグナル生成 (kabusys.strategy.signal_generator)
  - 正規化済み特徴量と AI スコアを統合して最終スコアを算出し、BUY/SELL シグナル（`signals` テーブル）を生成する `generate_signals(conn, target_date, ...)` を実装。
  - コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算するユーティリティを実装（シグモイド変換、欠損は中立値で補完）。
  - デフォルト重みと閾値を導入し、ユーザー指定の weights のバリデーションと再スケーリング処理を実装。
  - Bear レジーム判定（AI の regime_score 平均が負の場合）により BUY を抑制する仕組みを実装。
  - エグジット判定（ストップロス -8%、スコア低下）による SELL シグナル生成を実装。保有銘柄の価格欠損時は判定をスキップ・ログ出力。
  - signals テーブルへの日付単位置換をトランザクションで実施し冪等性を担保。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### セキュリティ (Security)
- ニュース XML パースに defusedxml を採用し XML バッファ攻撃等のリスクを低減。
- ニュース収集時の受信サイズ制限や URL 正規化・トラッキングパラメータ除去など、外部入力に対する安全対策を設計ドキュメントに明示。

### 既知の制限 / 今後の課題 (Known issues / Future work)
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は positions テーブルに追加情報（peak_price / entry_date 等）が必要なため未実装。
- news_collector の実装断片（本体 fetch / insert の完全実装や SSRF の詳細チェック）が今後の実装対象となる可能性あり（ドキュメントで設計方針を示している）。
- execution / monitoring モジュールはパッケージに含まれているが、実ロジックは未実装（将来的に発注連携・監視機能を追加予定）。

---

履歴は今後のリリースで逐次更新します。各変更は可能な限り後方互換性を保つ方針で進めますが、重大な API 変更を行う場合は Breaking change として明示します。