# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
ここでは、リポジトリの初期実装（バージョン 0.1.0）で導入された主要な機能・設計判断・既知の制約をまとめます。なお、日付は本リリース作成日です。

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-03-20

### 追加 (Added)
- パッケージ初期構成
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"`、トップレベルのエクスポート `__all__ = ["data", "strategy", "execution", "monitoring"]` を追加。

- 設定・環境変数管理 (`kabusys.config`)
  - プロジェクトルート自動検出: `.git` または `pyproject.toml` を基準にパッケージ位置から探索する `_find_project_root()` を実装。
  - .env ロード: 自動で `.env` → `.env.local` の順に読み込み（OS 環境変数を保護）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能。
  - .env パーサー: `export KEY=val`、クォート文字列、インラインコメント処理、トラッキングされた値のエスケープ処理に対応する `_parse_env_line()` を実装。
  - 必須キー取得ヘルパ: `_require()` を実装し、未設定時に明確な例外を送出。
  - Settings クラス: J-Quants / kabuステーション / Slack / DB パス 等のプロパティ実装（デフォルト値やバリデーションを含む）。
    - `env`（development/paper_trading/live）と `log_level` のバリデーション。
    - `is_live` / `is_paper` / `is_dev` プロパティ。

- Data（J-Quants クライアント） (`kabusys.data.jquants_client`)
  - API リクエスト共通実装 `_request()`：
    - レートリミット（120 req/min）を満たす固定間隔スロットリング `_RateLimiter` を導入。
    - 自動リトライ（指数バックオフ）、対象ステータスコードの指定（408/429/5xx）と最大リトライ回数。
    - 401 受信時のリフレッシュトークンによる ID トークン再取得処理（1 回リトライ）。
    - ページネーション対応の fetch 系関数（`fetch_daily_quotes`、`fetch_financial_statements`、`fetch_market_calendar`）。
  - DuckDB への冪等保存関数：
    - `save_daily_quotes`：`raw_prices` テーブルへ ON CONFLICT DO UPDATE により保存。
    - `save_financial_statements`：`raw_financials` テーブルへ ON CONFLICT DO UPDATE により保存。
    - `save_market_calendar`：`market_calendar` テーブルへ ON CONFLICT DO UPDATE により保存。
  - 入出力ユーティリティ `_to_float` / `_to_int` 実装（変換失敗時は None）。
  - データ取得時の fetched_at を UTC で記録し、Look-ahead バイアスの追跡を可能に。

- News（RSS ニュース収集） (`kabusys.data.news_collector`)
  - RSS フィード収集パイプラインの基礎実装（デフォルトに Yahoo Finance の RSS を設定）。
  - URL 正規化 `_normalize_url()` 実装（トラッキングクエリパラメータ削除、スキーム/ホスト小文字化、フラグメント削除、クエリパラメータソート）。
  - セキュリティ対策:
    - XML 解析に defusedxml を使用（XML Bomb 等の防止）。
    - 受信サイズ制限（最大 10MB）。
    - HTTP/HTTPS スキーム以外の拒否、SSRF の配慮（IP 検査等の実装方針が示唆されている）。
  - DB へのバルク挿入はチャンク処理・トランザクションで実行し、挿入件数を正確に返す方針。

- Research（研究用ユーティリティ） (`kabusys.research`)
  - ファクター計算モジュール群を公開 (`calc_momentum`, `calc_volatility`, `calc_value`)。
  - 特徴量探索ユーティリティ:
    - 将来リターン計算 `calc_forward_returns`（複数ホライズン対応、SQL ベースの効率的取得）。
    - IC（Information Coefficient）計算 `calc_ic`（スピアマン ρ を計算、サンプル不足時 None を返す）。
    - 基本統計量サマリー `factor_summary` とランク変換 `rank`。
  - 研究モジュールは DuckDB の `prices_daily` / `raw_financials` のみ参照し、本番の発注 API にはアクセスしない設計。

- Strategy（戦略） (`kabusys.strategy`)
  - 特徴量エンジニアリング `build_features`：
    - research 側で計算した生ファクターをマージし、ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 正規化に `zscore_normalize` を使用、Z スコアは ±3 でクリップ。
    - features テーブルへ日付単位の置換（トランザクション + バルク挿入で冪等性）。
  - シグナル生成 `generate_signals`：
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - コンポーネントはシグモイド変換・補完（欠損は中立値 0.5）を行う。
    - デフォルト重みは StrategyModel.md の仕様に合わせ実装（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。ユーザ指定重みはバリデーションの上で正規化。
    - BUY 閾値のデフォルトを 0.60 に設定。Bear レジーム（AI の regime_score 平均が負）では BUY を抑制。
    - SELL（エグジット）条件:
      - ストップロス（終値/avg_price - 1 <= -8%）を優先。
      - final_score が閾値未満の場合のスコア低下によるエグジット。
    - signals テーブルへ日付単位置換（冪等）。

- execution / monitoring パッケージスケルトン（名前空間の確立）

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 注意事項 / 既知の制限 (Notes / Known limitations)
- 一部のエグジット条件は未実装（`positions` テーブルに peak_price / entry_date 等が必要）：
  - トレーリングストップ（直近最高値から -10%）
  - 時間決済（保有 60 営業日超過）
- feature_engineering 内でユニバース判定に利用する `avg_turnover` はフィーチャ保存時に保存されない（フィルタ用のみ）。
- NewsCollector の一部の低レベル安全チェック（IP ブラックリスト等）は実装方針として示されているが、運用時の追加強化が想定される。
- Research モジュールは外部ライブラリ（pandas 等）に依存しない軽量実装を優先しているため、既存の研究ツールと比べて機能性/利便性で差異がある可能性がある。

### セキュリティ (Security)
- RSS（XML）処理に defusedxml を採用して XML 関連攻撃を軽減。
- J-Quants API クライアントでのトークン管理と自動リフレッシュ、再試行・レート制御を実装して API 利用の堅牢性を向上。
- HTTP レスポンスのサイズ制限や URL 正規化により、リソース消費やトラッキング、SSRF リスクを軽減する配慮を導入。

---

今後の作業候補:
- execution 層（kabu/発注ロジック）の実装とテスト
- monitoring（監視・アラート）の実装
- NewsCollector のシンボルリンク（news_symbols）と詳細な SSRF 防御の実装
- CI / テスト（DuckDB を利用した統合テスト）とドキュメント補強

（必要であれば、この CHANGELOG をリポジトリの実際のコミット履歴に合わせて更に詳細化できます。）