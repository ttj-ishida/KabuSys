# Changelog

すべての重要な変更を記録します。フォーマットは Keep a Changelog に準拠しています。

- 該当リポジトリバージョン: 0.1.0
- 初版作成日: 2026-03-20

## [Unreleased]

（現在未リリースの変更はここに記載します）

---

## [0.1.0] - 2026-03-20

初回公開リリース。日本株自動売買システム「KabuSys」の基本モジュール群を実装しました。設計方針として、DuckDB を中心にデータ処理を行い、ルックアヘッドバイアスの抑制、冪等性、堅牢な外部 API 呼び出し、研究用ユーティリティの分離を重視しています。

### 追加 (Added)
- 基本パッケージ構成
  - パッケージエントリポイント: kabusys.__version__ = "0.1.0"、公開モジュール: data, strategy, execution, monitoring。
- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数からの自動ロード（プロジェクトルートは .git または pyproject.toml を探索して判定）。
  - .env / .env.local の優先読み込み (OS 環境変数を保護)。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途）。
  - .env 行パーサ（export 前置、クォート、エスケープ、インラインコメント処理対応）。
  - Settings クラスで必須環境変数の取得・検証（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - env / log_level の検証とユーティリティプロパティ（is_live / is_paper / is_dev）。
- Data 層 (kabusys.data)
  - J-Quants API クライアント (jquants_client)
    - API レートリミット遵守（120 req/min 固定間隔スロットリング）。
    - 汎用 HTTP リクエスト処理: ページネーション対応、JSON デコード、リトライ（指数バックオフ、最大 3 回）、特定ステータス（408, 429, 5xx）の再試行。
    - 401 時の自動トークンリフレッシュ（1 回）とトークンキャッシュ共有。
    - 取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）。
    - DuckDB への保存関数: save_daily_quotes / save_financial_statements / save_market_calendar（ON CONFLICT を用いた冪等保存）。
    - 値変換ユーティリティ: _to_float / _to_int（安全な変換規則）。
    - ログ出力により取得件数やスキップ件数を通知。
  - ニュース収集モジュール (news_collector)
    - RSS フィード収集の基本実装（デフォルトに Yahoo Finance を含む）。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、クエリソート、フラグメント排除）。
    - XML パースに defusedxml を使用（XML BOM 等の脆弱性対策）。
    - 受信サイズ制限（10MB）や SSRF 対策に配慮した実装設計。
    - raw_news への冪等保存方針（SHA-256 による記事 ID 生成など、処理方針をコメントで明記）。
- 研究用モジュール (kabusys.research)
  - factor_research
    - Momentum, Volatility, Value, Liquidity 等のファクター計算実装:
      - calc_momentum (mom_1m, mom_3m, mom_6m, ma200_dev)
      - calc_volatility (atr_20, atr_pct, avg_turnover, volume_ratio)
      - calc_value (per, roe) — raw_financials からの最新財務データ参照
    - 営業日ベースの窓とスキャン範囲バッファを考慮したクエリ実装（DuckDB SQL を活用）。
  - feature_exploration
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターン一括取得。
    - calc_ic: スピアマンランク相関（Information Coefficient）計算。サンプル不足時は None を返す。
    - factor_summary: 各ファクター列の統計量（count, mean, std, min, max, median）。
    - rank ユーティリティ: 同順位は平均ランクを返す実装（round で丸めて tie を扱う）。
- 戦略層 (kabusys.strategy)
  - feature_engineering
    - research 由来の生ファクターをマージしてユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - 正規化: zscore_normalize を利用、Z スコアを ±3 でクリップ。
    - features テーブルへの日付単位 UPSERT（トランザクション＋バルク挿入で原子性を保証）。
  - signal_generator
    - features と ai_scores を統合して final_score を計算（デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。
    - スコア変換: Z スコア -> sigmoid -> コンポーネント平均 -> 重み付け和。
    - Bear レジーム判定: ai_scores の regime_score 平均が負 (かつサンプル >= 3) の場合 BUY を抑制。
    - BUY シグナル閾値デフォルト 0.60、SELL はストップロス（-8%）とスコア低下で判定。
    - signals テーブルへの日付単位置換（トランザクション + バルク挿入）。
    - ユーザー提供の weights を受け入れつつ検証／リスケーリングを行う（無効値はスキップ）。
- API エクスポート
  - kabusys.strategy.__all__ に build_features / generate_signals を公開。
  - kabusys.research.__all__ に主要関数群を公開。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### 非推奨 (Deprecated)
- （初版のため該当なし）

### 削除 (Removed)
- （初版のため該当なし）

### セキュリティ (Security)
- J-Quants クライアント:
  - トークン管理と自動リフレッシュの実装により認証失敗からの回復を考慮。
  - ネットワーク異常や 429 等のレート制限時に適切なリトライとログを出力。
- news_collector:
  - defusedxml の使用、受信サイズ制限、トラッキングパラメータ除去、HTTP スキーム制限などセキュリティ設計を明確化。

### 既知の制限・注意点 (Known issues / Notes)
- signal_generator の未実装部分:
  - Trailing stop（ピーク価格に基づくトレール）と時間決済（保有 60 営業日超過）は positions テーブルに peak_price / entry_date 等の情報が必要で未実装。コメントで将来実装を示唆。
- calc_value:
  - PBR / 配当利回り 等は現バージョンで未実装（コメントで明記）。
- execution パッケージは空のプレースホルダ（発注ロジックは別途実装予定）。
- .env 自動ロードはプロジェクトルートの検出に依存するため、配布後や特殊環境下では KABUSYS_DISABLE_AUTO_ENV_LOAD による制御が必要な場合があります。
- J-Quants API 呼び出しは外部サービスに依存するため、API 仕様変更やレート制限ポリシーの変更に注意してください。

---

変更履歴のフォーマットや内容について修正・追記が必要であればお知らせください。