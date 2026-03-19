# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従っています。

※本 CHANGELOG は提示されたコードベースの内容から推測して作成しています。実際のリリースノート作成時は必要に応じて日付・表現を調整してください。

## [Unreleased]
- 次回リリースに向けた変更点はここに記載します。

---

## [0.1.0] - 2026-03-19
初回リリース（推定）。以下の主要機能と設計方針を実装しています。

### 追加 (Added)
- 基本パッケージ構成
  - パッケージ初期化（kabusys.__init__ にて __version__ = "0.1.0" を定義）。(src/kabusys/__init__.py)

- 設定・環境読み込み (src/kabusys/config.py)
  - .env 自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサーは export プレフィックス、クォート（シングル/ダブル）内のエスケープ、行末コメント処理など多彩な形式に対応。
  - Settings クラスを導入し、必要な環境変数を型的に提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV（validation: development/paper_trading/live）、LOG_LEVEL（検証: DEBUG/INFO/...）
  - 環境値の検証（不正値は ValueError を送出）。

- データ取得・保存（J-Quants） (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。主な機能:
    - 固定間隔スロットリングによるレート制御（120 req/min）を実装（内部 RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回）、408/429/5xx をリトライ対象に指定。429 の Retry-After を尊重。
    - 401 発生時の ID トークン自動リフレッシュを 1 回だけ行う仕組み（無限再帰防止）。
    - ページネーション対応で fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を提供。
    - DuckDB へ冪等に保存する save_daily_quotes / save_financial_statements / save_market_calendar を実装（ON CONFLICT DO UPDATE を使用）。
    - 取得時刻（fetched_at）は UTC で記録し、Look-ahead バイアス解析に利用可能。
    - 型変換ユーティリティ _to_float/_to_int を提供し、不正データを安全に処理。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を取得・正規化して raw_news へ保存するモジュールを実装。
  - デフォルト RSS ソース（Yahoo Finance の business カテゴリ）を設定。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除、スキーム/ホスト小文字化）。
  - defusedxml を利用した安全な XML パース、受信サイズ上限（10MB）や SSRF を意識した設計。
  - バルク INSERT のチャンク化や記事 ID の SHA-256（先頭32文字）生成による冪等性を想定。

- 研究用ファクター計算（research） (src/kabusys/research/*.py)
  - ファクター計算モジュール提供:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日移動平均）を計算。
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio を計算（true_range の NULL 伝播管理含む）。
    - calc_value: raw_financials の最新財務データを用いて per / roe を計算。
  - 特徴量探索モジュール:
    - calc_forward_returns: 複数ホライズンの将来リターンを一括取得（LEAD を使用、ホライズン検証）。
    - calc_ic: スピアマンのランク相関（IC）を計算（ties を平均ランクで処理）。
    - factor_summary: count/mean/std/min/max/median を計算。
    - rank: 同順位を平均ランクにするランク変換（round(..., 12) による ties 対策）。
  - 研究用 API をパッケージレベルでエクスポート（kabusys.research.__init__）。

- 特徴量エンジニアリング（strategy） (src/kabusys/strategy/feature_engineering.py)
  - build_features(conn, target_date) を実装:
    - research の calc_momentum / calc_volatility / calc_value を組み合わせて raw factor を取得。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 数値ファクターを Z スコア正規化（kabusys.data.stats.zscore_normalize）し ±3 でクリップ。
    - features テーブルへ日付単位の置換（トランザクション + バルク挿入で原子性確保）。
    - 欠損・非有限値の扱いを明文化。

- シグナル生成（strategy） (src/kabusys/strategy/signal_generator.py)
  - generate_signals(conn, target_date, threshold=0.6, weights=None) を実装:
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算。
    - Z スコア→sigmoid 変換、欠損コンポーネントは中立値 0.5 で補完。
    - デフォルト重みとユーザ指定 weights の検証・正規化（負値/NaN/Inf/未知キーは無視、合計で再スケール）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつ十分なサンプル数）で BUY を抑制。
    - BUY シグナル閾値（デフォルト 0.60）に基づく BUY 生成。SELL はストップロス（-8%）やスコア低下で判定。
    - SELL 優先ポリシー（SELL 対象は BUY から除外）と signals テーブルへの日付単位置換で冪等性を確保。
    - 戻り値は書き込んだシグナル数（BUY+SELL）。

- strategy パッケージに公開エントリ（build_features, generate_signals）を追加 (src/kabusys/strategy/__init__.py)

- 実行層・モニタリング
  - execution と monitoring のパッケージプレースホルダを含む（将来的な拡張ポイント）。(src/kabusys/execution/__init__.py, monitoring は __all__ に記載されるが実装ファイルは提示範囲で限定的)

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- news_collector で defusedxml を用いた安全な XML パースを採用し XML 攻撃を緩和。
- news_collector は受信バイト数上限・HTTP スキーム検証など SSRF/DoS 対策を考慮。
- jquants_client はトークン自動リフレッシュ周りで無限再帰を回避する設計を採用。

### 既知の制限・設計上の注記 (Notes)
- ルックアヘッドバイアス対策: 多くの処理で target_date 時点のデータのみを利用し、fetched_at を記録することで「システムがいつそのデータを入手できたか」を追跡可能にしています。
- generate_signals の SELL 条件ではトレーリングストップや時間決済（保有 60 営業日超）などはいくつか未実装のまま（コード内に TODO として明示）。
- AI（ニュース）スコアが未登録の場合は中立値（0.5）で補完する設計のため、AI がない環境でも安定して動作します。
- 外部依存を最小化する方針（DuckDB と defusedxml 以外の重量級ライブラリに依存しない設計）を採用。
- positions テーブルに peak_price / entry_date 等の拡張が必要な機能が一部存在（トレーリングストップ等）。
- .env パーサーは多くの一般的ケースに対応しますが、極端な構文や非標準フォーマットでは想定どおり動作しない可能性があります。

### マイグレーション / 設定
- 必須環境変数（少なくとも以下をセットする必要があります）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- データベースパスは環境変数で調整可能:
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト data/monitoring.db）

---

（以上）