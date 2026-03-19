# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースの内容から推測して作成しています（実際のコミット履歴ではありません）。

## [Unreleased]
-（なし）

## [0.1.0] - 2026-03-19
初期リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。以下の主要コンポーネントを含みます。

### 追加（Added）
- パッケージ初期化
  - `kabusys.__init__` に __version__ = 0.1.0 を追加。
  - public API として "data", "strategy", "execution", "monitoring" をエクスポート。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を実装。
  - プロジェクトルート検出ロジック: `.git` または `pyproject.toml` を起点に探索（CWD 非依存）。
  - .env の行パーサーを実装（コメント行、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いを考慮）。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - Settings クラスを追加し、アプリ設定（J-Quants トークン、kabu API、Slack、DB パス、環境名、ログレベル等）をプロパティ経由で提供。
  - 環境値の検証（KABUSYS_ENV の有効値チェック、LOG_LEVEL の有効値チェック）と必須環境変数未設定時の例外（ValueError）を実装。

- Data 層（kabusys.data）
  - J-Quants API クライアント（jquants_client）
    - 固定間隔スロットリングによるレート制限制御（120 req/min, _RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx の再試行、Retry-After を尊重）。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ。
    - ページネーション対応のデータフェッチ（株価日足 / 財務データ / 市場カレンダー）。
    - DuckDB への保存関数（raw_prices, raw_financials, market_calendar）を実装。INSERT の冪等化（ON CONFLICT DO UPDATE）。
    - 型変換ユーティリティ（_to_float, _to_int）による安全な変換ロジック。
  - ニュース収集モジュール（news_collector）
    - RSS フィード収集機能（デフォルトに Yahoo Finance のビジネス RSS を設定）。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホストの小文字化、フラグメント除去、クエリソート）。
    - XML パースに対する安全対策（defusedxml を使用）。
    - SSRF 回避（HTTP/HTTPS スキームのみ想定）、受信サイズ制限（最大 10MB）、挿入時のバルクチャンク処理。
    - 記事ID は正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を保証する設計（説明記述あり）。

- Research 層（kabusys.research）
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算を DuckDB の prices_daily / raw_financials テーブルを参照して実装。
    - モメンタム: 1M/3M/6M リターン、MA200 乖離率（必要データ不足時は None）。
    - ボラティリティ: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、volume_ratio。
    - バリュー: PER（EPS が 0 または欠損の場合は None）、ROE（最新の財務データを target_date 以前で取得）。
    - スキャン範囲やウィンドウサイズは実務的なバッファを考慮して実装（カレンダー日でバッファを取る設計）。
  - feature_exploration: 将来リターン計算（複数ホライズン、範囲チェック）、IC（スピアマンランク相関）計算、ファクター統計サマリー、ランク関数を実装。
    - calc_forward_returns: LEAD を使った一括取得、ホライズンチェック、horizons の検証（正の整数かつ <= 252）。
    - calc_ic: 3 件未満で None を返す安全な実装、同順位処理は平均ランクで対応。
    - factor_summary: count/mean/std/min/max/median を計算（None を除外）。

- Strategy 層（kabusys.strategy）
  - feature_engineering: 研究環境で計算した生ファクターを正規化・合成して features テーブルへ保存する処理を実装。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）。
    - Z スコア正規化（外部ユーティリティ zscore_normalize を利用）および ±3 でクリップ。
    - 日付単位での置換（DELETE + バルク INSERT をトランザクションで実行し原子性を保証）。
    - 冪等性（target_date の既存レコードを削除してから挿入）を確保。
  - signal_generator: features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを生成。
    - コンポーネントスコア: momentum, value, volatility, liquidity, news を計算（シグモイド変換など）。
    - 重み合成ロジック（デフォルト重みを用意、ユーザ指定は検証・スケーリングして統合）。
    - Bear レジーム判定（AI の regime_score の平均が負の場合かつサンプル数閾値を満たすと Bear と判定、Bear 時は BUY 抑制）。
    - SELL 生成ロジック: ストップロス（終値/avg_price - 1 < -8%）およびスコア低下（final_score < threshold）。
    - BUY/SELL を signals テーブルへ日付単位で置換（トランザクションで原子性を保証）。
    - 欠損値補完方針: コンポーネント None は中立 0.5 で補完、features に存在しない保有銘柄は final_score = 0.0 扱い（SELL 対象）。

- パッケージ公開 API の整理
  - strategy と research の __init__ で主要関数を再エクスポート（build_features, generate_signals, calc_momentum, ...）。

### 変更（Changed）
- 初期リリースのため、既存コードの変更項目はなし。

### 修正（Fixed）
- 初期リリースのため、既存バグ修正はなし（実装時点でハンドリングやログ出力による安全対策を多数追加）。

### セキュリティ（Security）
- news_collector で defusedxml を用いた XML パース、安全な URL 正規化、応答サイズ制限、SSRF に対する考慮を追加。
- J-Quants クライアントでトークン管理時に無限再帰を防ぐため allow_refresh フラグを導入。

### 注意事項 / 備考（Notes）
- 環境変数について:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings の _require によって未設定で例外）。
  - 自動 .env ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB を前提とした設計（prices_daily / raw_prices / raw_financials / features / ai_scores / positions / signals 等のテーブルが必要）。
- 一部機能は将来的に拡張予定（例: signal_generator のトレーリングストップ、時間決済は未実装で注記あり）。
- research モジュールは外部ライブラリに依存せず標準ライブラリと DuckDB で完結する方針。

---

この CHANGELOG はコードから推測して作成したため、実際の開発履歴やコミットメッセージとは異なる場合があります。必要であれば、各モジュールの実装箇所ごとにさらに詳細な変更点や既知の制約を追加できます。