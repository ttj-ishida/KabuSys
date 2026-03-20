# Changelog

すべての重要な変更をここに記録します。  
このファイルは Keep a Changelog の仕様に準拠します。  

フォーマット: [バージョン] - YYYY-MM-DD

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-20
最初の公開リリース。日本株自動売買システム「KabuSys」のコア機能を実装・追加しました。

### Added
- パッケージ初期化
  - `kabusys.__version__ = "0.1.0"` を設定し、パッケージ公開用のエクスポート (`data`, `strategy`, `execution`, `monitoring`) を追加。

- 環境変数・設定管理 (`kabusys.config`)
  - `.env` / `.env.local` 自動読み込み機能を実装（プロジェクトルートは `.git` または `pyproject.toml` を探索して特定）。
  - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - `.env` 解析機能を強化：`export KEY=val` 形式、シングル/ダブルクォート内のエスケープ、インラインコメント処理などに対応するパーサ `_parse_env_line` を実装。
  - 既存のOS環境変数を保護するための `protected` 処理と、`override` オプションを持つ `_load_env_file` を実装。
  - 必須変数取得関数 `_require` と、設定値ラッパー `Settings` クラスを実装。J-Quants / kabu ステーション / Slack / DB パス / 環境フラグ（`is_live` / `is_paper` / `is_dev`）などのプロパティを提供。
  - `KABUSYS_ENV` と `LOG_LEVEL` のバリデーション（許容値チェック）を実装。

- データ取得・保存（J-Quants クライアント） (`kabusys.data.jquants_client`)
  - J-Quants API クライアントを実装：認証トークン取得 (`get_id_token`)、ページネーション対応データ取得 (`fetch_daily_quotes`, `fetch_financial_statements`, `fetch_market_calendar`) を追加。
  - レート制御用の `_RateLimiter` を実装して、120 req/min の固定間隔スロットリングを適用。
  - 再試行ロジック（指数バックオフ、最大 3 回）を実装。HTTP 408/429/5xx を再試行対象とし、429 の `Retry-After` を尊重。
  - 401 受信時の自動トークンリフレッシュを 1 回だけ行う仕組みを追加（無限再帰を防止）。
  - DuckDB への冪等保存関数を実装：
    - `save_daily_quotes`（`raw_prices` へ INSERT ... ON CONFLICT DO UPDATE）
    - `save_financial_statements`（`raw_financials` へ INSERT ... ON CONFLICT DO UPDATE）
    - `save_market_calendar`（`market_calendar` へ INSERT ... ON CONFLICT DO UPDATE）
  - レスポンスのデコード/型変換ユーティリティ `_to_float` / `_to_int` を追加。

- ニュース収集 (`kabusys.data.news_collector`)
  - RSS フィード収集基盤を実装。デフォルトソースに Yahoo Finance を追加。
  - セキュリティ対策を実装：`defusedxml` を利用した XML パース（XML Bomb 等への対策）、受信バイト上限（10 MB）によるメモリ保護、HTTP スキーム検証等。
  - URL 正規化機能 `_normalize_url` を実装（トラッキングパラメータ削除、クエリソート、スキーム/ホスト小文字化、フラグメント除去）。
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保。
  - DB へのバルク挿入はチャンク化して実行し、挿入件数を正確に把握する設計。

- 研究用ファクター計算 (`kabusys.research.factor_research`)
  - モメンタム、ボラティリティ、バリュー系ファクター計算関数を実装：
    - `calc_momentum`（mom_1m, mom_3m, mom_6m, ma200_dev）
    - `calc_volatility`（atr_20, atr_pct, avg_turnover, volume_ratio）
    - `calc_value`（per, roe：`raw_financials` の最新レコードと `prices_daily` を組合せ）
  - DuckDB のウィンドウ関数を利用した効率的な実装（期間バッファ付きのスキャン範囲設計を含む）。

- 研究支援ユーティリティ (`kabusys.research.feature_exploration`)
  - 将来リターン計算 `calc_forward_returns`（複数ホライズン対応、LEAD を利用）。
  - IC（Spearman の ρ）計算 `calc_ic` と順位付け `rank`（同順位は平均ランク、丸めによる ties 対策）。
  - ファクター統計要約 `factor_summary`（count/mean/std/min/max/median）を実装。

- 特徴量生成 (`kabusys.strategy.feature_engineering`)
  - 研究環境の生ファクターを統合・正規化して `features` テーブルへ保存する `build_features` を実装。
  - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を実装。
  - 正規化は `zscore_normalize` を利用し、対象列を ±3 でクリップして外れ値影響を抑制。
  - 日付単位の置換（DELETE → INSERT のトランザクション）で冪等性を確保。

- シグナル生成 (`kabusys.strategy.signal_generator`)
  - 正規化済み `features` と `ai_scores` を統合し、最終スコアを計算して売買シグナル（BUY/SELL）を生成する `generate_signals` を実装。
  - コンポーネントスコア算出（momentum/value/volatility/liquidity/news）とシグモイド変換を実装。
  - 重み合成（デフォルトウェイトを定義）とユーザー指定ウェイトの検証、合計が1.0でない場合の再スケールを実装。
  - Bear レジーム判定ロジック（AI の `regime_score` の平均が負 → BUY を抑制）を実装。
  - エグジット判定（売りシグナル）としてストップロス（-8%）およびスコア低下を実装。SELL 優先の取り扱いを行い、BUY ランクを再付与する。
  - シグナル保存も日付単位の置換で冪等性を確保。

- パッケージの公開 API 集約
  - `kabusys.strategy` と `kabusys.research` の主要関数を __init__ で公開（簡易インポート可能）。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Security
- ニュースパーサで `defusedxml` を採用し、XML 関連攻撃に対する対策を導入。
- ニュース収集で受信バイト数上限を設け、メモリ DoS を緩和。
- RSS の URL 正規化でトラッキングパラメータを除去し、ID を安定化して冪等性を確保。

### Notes / Implementation details
- DuckDB をデータ層に用い、各種処理は基本的に SQL（ウィンドウ関数）と最小限の Python ロジックで構築。外部依存（pandas など）は可能な限り排除している。
- API 呼び出しはレート制御・再試行・トークン管理を組み合わせて堅牢に設計。429 → `Retry-After` を尊重する実装。
- 一部仕様（例: trailing stop / 時間決済）は positions テーブルの追加情報（peak_price / entry_date 等）が未実装のため保留。
- ログ出力は各モジュールで行い、稼働時のデバッグや監査に対応する設計とした。

--- 

今後の予定（例）
- execution 層の注文送信ロジック（kabuステーション連携）の実装
- monitoring/alerting の強化（Slack 通知など）
- positions テーブルを拡張してトレーリングストップや保有期間ベースの決済を実装