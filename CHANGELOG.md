# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠しています。  
このリポジトリはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-21
初回リリース

### 追加 (Added)
- パッケージ基盤
  - パッケージのバージョンを `kabusys.__version__ = "0.1.0"` として追加。
  - パッケージ公開 API (`__all__`) に data、strategy、execution、monitoring を追加。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート検出ロジック `_find_project_root()` を実装（.git または pyproject.toml を基準）。
  - .env の自動ロードを追加（優先順位: OS 環境変数 > .env.local > .env）。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パース機能 `_parse_env_line()` を実装し、export プレフィックス・シングル/ダブルクォート・エスケープ・インラインコメントに対応。
  - .env 読み込み関数 `_load_env_file()` は既存 OS 環境変数を保護する `protected` 引数と上書きフラグ `override` を実装。
  - 必須環境変数取得 `_require()` を実装し、未設定時に明示的なエラーを出す。
  - 設定プロパティ（J-Quants、kabu API、Slack、DB パス、実行環境判定、ログレベル等）を提供。
  - KABUSYS_ENV と LOG_LEVEL の値検証を実装。

- データ取得・保存: J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API 用クライアントを実装（株価・財務データ・マーケットカレンダー取得）。
  - 固定間隔レートリミッタ `_RateLimiter` を実装し、120 req/min の制限を守る。
  - 冪等性を考慮した DuckDB 保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。INSERT ... ON CONFLICT DO UPDATE を利用。
  - ネットワーク＆HTTP リトライロジックを実装（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）。429 の場合は Retry-After を考慮。
  - 401 Unauthorized を検出しトークン自動リフレッシュ（get_id_token）を行って 1 回だけ再試行する仕組みを導入。
  - ページネーション対応（pagination_key を用いたループ）を実装。
  - レスポンス JSON デコード失敗時の明示的エラー、型変換ユーティリティ `_to_float` / `_to_int` を実装。
  - fetch_*/save_* 系 API を公開。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集して raw_news に保存するモジュールを追加。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除、小文字化）機能を実装して、記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を保証。
  - defusedxml を用いた XML パースで XML Bomb 等の脆弱性対策を実装。
  - SSRF 対策（HTTP/HTTPS スキーム以外の拒否、IP 判定の方針を含む設計）、受信サイズ上限（MAX_RESPONSE_BYTES=10MB）によるメモリ DoS 対策を導入。
  - バルク INSERT のチャンク化、INSERT RETURNING を意識した設計。

- リサーチ・ファクター計算 (src/kabusys/research/*.py)
  - ファクター計算モジュール群を実装:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率（データ不足時は None を返す）。
    - calc_volatility: 20 日 ATR / atr_pct、20 日平均売買代金、出来高比率。
    - calc_value: target_date 以前の最新財務データと株価から PER / ROE を計算。
  - Feature 探索ユーティリティを実装:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度に取得する SQL 実装（LEAD を使用、カレンダーバッファ採用）。
    - calc_ic: スピアマンランク相関（IC）計算を実装。サンプル不足（<3）や ties を考慮。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ機能。
    - rank: 同順位は平均ランクを返すランク付けユーティリティ（丸めにより ties 判定の安定化）。
  - DuckDB の prices_daily / raw_financials のみを参照する方針で実装（本番 API へアクセスしない）。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - research モジュールで計算した生ファクターを統合・正規化して features テーブルに保存する `build_features()` を実装。
  - 処理フロー:
    - calc_momentum / calc_volatility / calc_value を呼び出して原始ファクターを取得。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラムに対して Z スコア正規化（kabusys.data.stats.zscore_normalize）を適用し ±3 でクリップ。
    - 日付単位で既存レコードを削除→トランザクション内でバルク挿入（冪等）。
  - ルックアヘッドバイアス対策: target_date 時点のデータのみ参照。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - `generate_signals()` を実装し features / ai_scores / positions を参照して売買シグナルを生成し signals テーブルへ保存。
  - 各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。シグモイド変換・欠損値は中立 0.5 で補完。
  - デフォルト重みセットを実装（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。ユーザ提供 weights は検証・正規化して合計が 1.0 になるようスケール。
  - Bear レジーム判定（ai_scores の regime_score の平均が負でかつサンプル数閾値以上で判定）により BUY シグナルを抑制。
  - SELL 条件（ストップロス -8% / final_score が閾値未満）を実装。保有ポジションの価格欠損時は SELL 判定をスキップして誤クローズを防止。
  - BUY / SELL を日付単位で置換してトランザクション内で保存（冪等）。

- 公開モジュールエクスポート
  - strategy/__init__.py にて build_features, generate_signals を公開。
  - research/__init__.py で主要ユーティリティを再エクスポート。

### 変更 (Changed)
- なし（初回リリース）。

### 修正 (Fixed)
- なし（初回リリース）。

### 削除 (Removed)
- なし（初回リリース）。

### セキュリティ / 安全性に関する注記
- RSS パースに defusedxml を使用し XML 攻撃を想定した防御を行っています。
- ニュース取得時は受信サイズ制限を設け、トラッキングパラメータ除去や URL 正規化を行って冪等性・誤マッチを低減しています。
- J-Quants クライアントはトークン管理（自動リフレッシュ）やレート制御・リトライ戦略を備えています。

---

今後の予定（例）
- execution 層（kabu ステーション API との注文送信・状態管理）の実装。
- モニタリング・アラート（Slack 統合）の強化。
- tests と CI の整備、型チェックとリントの自動化。

（必要に応じて日付・項目の詳細化や追加修正を行います。）
