# CHANGELOG

このファイルは Keep a Changelog の形式に準拠しています。  
全ての注記はリポジトリ内のコードから推測して作成しています（初期リリース: v0.1.0）。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-20

初回リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを実装しました。以下はコードベースから推測した主要な追加点、設計方針、注意点です。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化: `kabusys.__init__`（バージョン `0.1.0`、エクスポート: `data`, `strategy`, `execution`, `monitoring`）。

- 設定管理
  - `kabusys.config` モジュールを追加。
    - プロジェクトルート自動検出: `.git` または `pyproject.toml` を基準に探索する `_find_project_root()` を実装。
    - `.env` / `.env.local` の自動読み込み（優先順位: OS 環境変数 > .env.local > .env）。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - `.env` パーサー: コメント・export プレフィックス・クォート（エスケープ含む）やインラインコメントを考慮する堅牢な `_parse_env_line()` を実装。
    - 必須チェック `_require()` と `Settings` クラスを提供。主要環境変数:
      - `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`
      - `KABUSYS_ENV` (`development`, `paper_trading`, `live` のみ許容)
      - `LOG_LEVEL`（`DEBUG/INFO/WARNING/ERROR/CRITICAL` の検証）
      - デフォルト DB パス: `DUCKDB_PATH`（`data/kabusys.duckdb`）／`SQLITE_PATH`（`data/monitoring.db`）

- Data レイヤー
  - `kabusys.data.jquants_client`
    - J-Quants API クライアントを実装。機能:
      - レート制限: 120 req/min を固定間隔スロットリング（_RateLimiter）で制御。
      - リトライ: ネットワーク障害および 408/429/5xx に対して指数バックオフで最大 3 回リトライ。
      - 401 応答時のトークン自動リフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュ。
      - ページネーション対応の取得関数: `fetch_daily_quotes`, `fetch_financial_statements`, `fetch_market_calendar`。
      - DuckDB への冪等保存関数: `save_daily_quotes`, `save_financial_statements`, `save_market_calendar`（`ON CONFLICT DO UPDATE` を使用）。
      - ユーティリティ `_to_float` / `_to_int` により不正な文字列を安全に None に変換。
  - `kabusys.data.news_collector`
    - RSS フィードからのニュース収集基盤。
      - URL 正規化（トラッキングパラメータ除去、クエリソート、スキーム/ホスト小文字化、フラグメント除去）。
      - defusedxml を使った安全な XML パース、防御策（XML Bomb 等）。
      - 最大受信サイズ制限（10 MB）や SSRF 対策等の設計方針。
      - 挿入はバルク＆チャンク化して DB へ冪等保存する方針（INSERT RETURNING を想定）。
      - デフォルト RSS ソースに Yahoo Finance ビジネスカテゴリを登録。
    - （注）実装は安全性やスケーラビリティを意識して設計されています。

- Research（研究）モジュール
  - `kabusys.research.factor_research`
    - ファクター計算（prices_daily / raw_financials を参照）:
      - Momentum: `calc_momentum`（mom_1m, mom_3m, mom_6m, ma200_dev）
      - Volatility: `calc_volatility`（atr_20, atr_pct, avg_turnover, volume_ratio）
      - Value: `calc_value`（per, roe — target_date 以前の最新財務データを使用）
    - 営業日不足やウィンドウ不足時の None 取り扱いなど堅牢性に配慮。
  - `kabusys.research.feature_exploration`
    - 研究用途のユーティリティ:
      - 将来リターン計算: `calc_forward_returns`（複数ホライズン対応、範囲チェックあり）
      - IC（Spearman）の計算: `calc_ic`
      - 基本統計量集計: `factor_summary`
      - ランク付けユーティリティ: `rank`（同順位は平均ランク）
    - 外部ライブラリ非依存（標準ライブラリのみ）を目指した実装。

- Strategy（戦略）モジュール
  - `kabusys.strategy.feature_engineering`
    - 研究で得た生ファクターを正規化・合成して `features` テーブルへ保存する `build_features(conn, target_date)` を実装。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - 正規化: Z スコア正規化（`kabusys.data.stats.zscore_normalize` を利用）、±3 でクリップ。
    - 日付単位での置換（DELETE→INSERT をトランザクションで行い冪等化）。
  - `kabusys.strategy.signal_generator`
    - `generate_signals(conn, target_date, threshold=0.60, weights=None)` を実装。
    - features と `ai_scores` を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - スコア処理:
      - Z スコア → シグモイド変換、欠損は中立 0.5 で補完
      - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。ユーザ提供の weights は検証後に合算して正規化
      - BUY 閾値デフォルト 0.60
      - Bear レジーム判定（`ai_scores` の regime_score 平均が負の場合、サンプル数閾値あり）では BUY を抑制
    - エグジット（SELL）判定:
      - ストップロス: PnL <= -8%（優先）
      - スコア低下: final_score < threshold
      - 未実装（注記）: トレーリングストップ、時間決済（positions に peak_price/entry_date が必要）
    - signals テーブルへの日付単位置換（トランザクションで冪等化）。

- public import
  - `kabusys.strategy.__init__` で主要関数をエクスポート (`build_features`, `generate_signals`)。
  - `kabusys.research.__init__` で研究ユーティリティをエクスポート。

### 設計上の特記事項 / 動作方針
- ルックアヘッドバイアス対策
  - 各種計算は target_date 時点の「利用可能な」データのみを参照する方針（prices/financials の最新値のみ利用）。
  - データ取得時は fetched_at を UTC で記録し、いつデータが獲得されたかトレース可能にする設計（J-Quants クライアント）。
- 冪等性とトランザクション
  - DuckDB 向け保存処理は `ON CONFLICT DO UPDATE` または 日付単位の DELETE→INSERT をトランザクションで実行して冪等性を確保。
- セキュリティ/堅牢性
  - news_collector は defusedxml、受信サイズ制限、URL 正規化、SSRF 対策などを想定。
  - HTTP クライアントは JSON 解析失敗時に詳細情報を含めて例外を投げる（デバッグ向け）。

### 既知の制限・未実装事項 (Known issues / TODO)
- ポジション関連の高度なエグジット戦略（トレーリングストップ、時間決済）は未実装。positions テーブルに `peak_price` / `entry_date` が必要で、将来的な拡張を想定。
- `kabusys.execution` / `kabusys.monitoring` はパッケージとしてエクスポートされているが、今回のコードスナップショットでは実装が見られない（プレースホルダ）。
- news_collector の ID 生成や DB への実際の挿入処理（SHA-256 トークン使用、挿入数の正確な返却）は設計方針があるが、コードスニペットは途中まで（未完成の可能性あり）。
- 一部のエラーハンドリングはロギングしてスキップする方針（例: price 欠損時の SELL 判定スキップ）であり、運用時にログ監視が必須。

### マイグレーション / デプロイ注意事項
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を設定してください。未設定時は `Settings` が ValueError を送出します。
- `.env` 自動読み込みについて:
  - パッケージ配布後もプロジェクトルート基準での自動ロードを行うため、配布方法により `.env` の配置を意識する必要があります。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DB スキーマ:
  - `prices_daily`, `raw_prices`, `raw_financials`, `features`, `ai_scores`, `signals`, `positions`, `market_calendar` 等のテーブルが呼ばれる想定です。初回導入時はスキーマ定義（DDL）を用意してください。

---

今後のリリースでは、execution 層（実際の発注ロジック）、monitoring（Slack 通知・メトリクス）、news_collector の完全実装、追加の戦略ルール・エクジットポリシーの実装を含めることが想定されます。必要であればこの CHANGELOG をベースにリリースノート（英語版や簡潔版）を作成します。