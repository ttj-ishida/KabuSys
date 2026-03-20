# Changelog

すべての重要な変更点をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従います。SemVer を採用します。

## [Unreleased]

## [0.1.0] - 2026-03-20
初回公開リリース。

### Added
- 基本パッケージ構成を追加
  - パッケージ名: `kabusys`
  - バージョン: `0.1.0`
  - public API: `kabusys.data`, `kabusys.strategy`, `kabusys.execution`, `kabusys.monitoring`

- 環境設定管理 (`kabusys.config`)
  - `.env` / `.env.local` の自動ロード機能（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）
  - コメント・クォート・エスケープ対応の .env パーサ実装
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD`
  - 必須環境変数チェック `_require()` と `Settings` クラスを提供
    - 主なプロパティ:
      - J-Quants: `jquants_refresh_token`
      - kabuステーション: `kabu_api_password`, `kabu_api_base_url`（デフォルト: `http://localhost:18080/kabusapi`）
      - Slack: `slack_bot_token`, `slack_channel_id`
      - DB パス: `duckdb_path`（デフォルト `data/kabusys.duckdb`）, `sqlite_path`（デフォルト `data/monitoring.db`）
      - 環境種別 `env`（development/paper_trading/live）、`log_level` 等のバリデーション
  - OS 環境変数の保護（`.env.local` の override 時に既存 OS 環境変数は上書きしない）

- Data — J-Quants API クライアント (`kabusys.data.jquants_client`)
  - API から日足・財務データ・マーケットカレンダーを取得するクライアントを実装
  - レート制御（120 req/min）を固定間隔スロットリングで実装（_RateLimiter）
  - 再試行ロジック（指数バックオフ、最大 3 回）と 408/429/5xx 対応
  - 401 発生時のトークン自動リフレッシュ（1 回のみ）と ID トークンキャッシュ
  - ページネーション対応（pagination_key）
  - DuckDB への冪等保存ユーティリティ:
    - save_daily_quotes → `raw_prices`（ON CONFLICT DO UPDATE）
    - save_financial_statements → `raw_financials`（ON CONFLICT DO UPDATE）
    - save_market_calendar → `market_calendar`（ON CONFLICT DO UPDATE）
  - 型安全な変換ヘルパ: `_to_float`, `_to_int`

- Data — ニュース収集 (`kabusys.data.news_collector`)
  - RSS フィードから記事を収集・正規化して `raw_news` へ保存するモジュール
  - デフォルト RSS ソース（例: Yahoo Finance）
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）
  - 記事 ID を URL 正規化後の SHA-256 の先頭 32 文字で生成して冪等性を確保
  - defusedxml による XML パース（XML Bomb 対策）
  - HTTP 応答サイズ上限（10 MB）や SSRF 対策の考慮
  - バルク INSERT チャンク処理、トランザクションまとめての挿入

- Research（研究用ユーティリティ群） (`kabusys.research`)
  - ファクター計算モジュール (`factor_research`)
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio を計算
    - calc_value: per / roe を計算（raw_financials と prices_daily 組合せ）
    - DuckDB のウィンドウ関数・行数チェックを用いた堅牢な実装
  - 特徴量探索 (`feature_exploration`)
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得
    - calc_ic: Spearman（ランク相関）で IC を計算
    - factor_summary: count/mean/std/min/max/median を算出
    - rank: 同順位は平均ランク扱い（丸めによる ties 対応を含む）
  - zscore_normalize は `kabusys.data.stats` を通して再公開（__init__ にエクスポート）

- Strategy（特徴量整備・シグナル生成） (`kabusys.strategy`)
  - 特徴量エンジニアリング (`feature_engineering.build_features`)
    - research の raw ファクター（momentum/volatility/value）を取得してマージ
    - ユニバースフィルタ（最小株価 300 円、20日平均売買代金 >= 5 億円）
    - Z スコア正規化（対象カラム指定）と ±3 でクリップ
    - 日付単位の置換（DELETE + INSERT）をトランザクションで行い冪等化
  - シグナル生成 (`signal_generator.generate_signals`)
    - features と ai_scores を統合して各銘柄の final_score を算出
    - コンポーネント: momentum / value / volatility / liquidity / news（デフォルト重みを定義）
    - スコア正規化: z → sigmoid( z )、欠損コンポーネントは中立値 0.5 で補完
    - Bear レジーム判定（AI の regime_score 平均が負の場合。ただしサンプル数が閾値未満なら Bear と判定しない）
    - BUY シグナル生成は閾値（デフォルト 0.60）を使用。Bear 時は BUY を抑制
    - SELL シグナル（エグジット）:
      - ストップロス: 現在終値が平均取得単価から -8% 以下
      - スコア低下: final_score < threshold
      - 保有銘柄の価格欠損時は SELL 判定をスキップ（誤クローズ防止）
    - signals テーブルへの日付単位置換（トランザクションで冪等化）

- misc
  - ロギングと警告メッセージを各所に整備（入力パラメータ警告やトランザクション失敗時のログ等）
  - DuckDB をデータ処理の主な永続層として利用する前提の SQL 実装

### Known limitations / Not implemented
- Signal generator の SELL 条件のうち以下は未実装（備考に記載）
  - トレーリングストップ（peak_price / entry_date が positions に必要）
  - 時間決済（保有 60 営業日超過）
- NewsCollector の詳細な銘柄紐付けロジック（news_symbols へのマッピング）は実装想定だが、このリリースでの完全実装箇所は要確認
- 外部ライブラリ依存最小化方針により、Research の統計処理は標準ライブラリで実装（pandas 等を利用していない）
- execution / monitoring パッケージはスケルトン（このリリースでは発注層や監視ルーティンは未実装または限定実装）

### Security
- defusedxml を使用した XML パースで RSS 関連の XML 攻撃を軽減
- NewsCollector で受信上限バイト数を設定（メモリ DoS 対策）
- HTTP クライアントでのトークン取り扱いはモジュール内キャッシュ＋リフレッシュで管理（ただし運用上の秘密情報取り扱いは .env 管理に依存）

---

注意:
- 本 CHANGELOG は該当コードベースの実装内容から推測して作成しています。実際のリリースノートや運用ドキュメントとして利用する場合は、実際のリリース手順・マイグレーション（DB スキーマ・テーブル作成等）を合わせて確認してください。