# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

注: リポジトリ内のコードから推測して記載しています。実際のリリースノートや仕様書と差異がある場合があります。

## [Unreleased]

（なし）

---

## [0.1.0] - 2026-03-21

### Added
- パッケージ初期リリース: kabusys 0.1.0
  - kabeusys のルートパッケージ定義（__version__ = 0.1.0）。公開モジュール: data, strategy, execution, monitoring。

- 環境設定 / 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を導入。優先順位: OS 環境変数 > .env.local > .env。
  - プロジェクトルート自動検出ロジック（.git または pyproject.toml を基準）を実装。カレントワーキングディレクトリに依存しない読み込み。
  - .env パーサを実装:
    - コメント行、export プレフィックス、シングル/ダブルクォート（エスケープ含む）、インラインコメントを正しく処理。
    - 上書き制御（override）と protected キー（OS 環境変数保護）に対応。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供し、アプリケーション設定をプロパティで取得可能に:
    - 必須設定: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（未設定時は ValueError を送出）。
    - デフォルト値を持つ設定: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH。
    - KABUSYS_ENV（development / paper_trading / live）の検証、LOG_LEVEL の検証、is_live / is_paper / is_dev の利便性プロパティ。

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装（トークン取得、ページネーション対応）。
  - レート制限制御（固定間隔スロットリング: 120 req/min）。
  - 再試行ロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx およびネットワークエラーに対して）。
  - 401 レスポンス時にリフレッシュトークンで自動的にトークン更新して再試行（1 回のみ）。
  - ページネーション対応の fetch_* 関数:
    - fetch_daily_quotes（OHLCV、ページネーション）
    - fetch_financial_statements（財務データ、ページネーション）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB 保存ユーティリティ（冪等性を考慮した INSERT / ON CONFLICT DO UPDATE）:
    - save_daily_quotes -> raw_prices
    - save_financial_statements -> raw_financials
    - save_market_calendar -> market_calendar
  - 値変換ユーティリティ: _to_float / _to_int（安全なパース・欠損値処理）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集機能を実装。
  - URL 正規化（トラッキングパラメータ削除、スキーム/ホスト小文字化、フラグメント除去、クエリソート）。
  - defusedxml を利用した安全な XML パース（XML Bomb 等への対策）。
  - 受信サイズ上限（MAX_RESPONSE_BYTES）や SSRF 等への配慮。
  - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を確保。
  - raw_news へのバルク保存（チャンク化、トランザクションのまとめ挿入、ON CONFLICT DO NOTHING による重複排除）。
  - デフォルト RSS ソースとして Yahoo Finance のビジネスカテゴリを追加。

- リサーチ / ファクター計算（kabusys.research とサブモジュール）
  - factor_research モジュールで主要ファクターを実装:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日移動平均乖離）
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio（20 日ウィンドウ）
    - calc_value: per / roe（raw_financials と prices_daily を組み合わせ）
  - feature_exploration モジュール:
    - calc_forward_returns（指定ホライズンの将来リターンを一括取得）
    - calc_ic（Spearman のランク相関による IC 計算、サンプル不足時 None を返す）
    - factor_summary（count/mean/std/min/max/median を計算）
    - rank（同順位は平均ランクで処理、浮動小数丸めで ties の検出安定化）
  - research パッケージ __all__ を整理してエクスポート。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date) を実装:
    - research で計算した生ファクター（momentum / volatility / value）をマージ。
    - ユニバースフィルタ（最低株価、20 日平均売買代金）を適用。
    - 数値ファクターを Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップして外れ値影響を抑制。
    - features テーブルへ日付単位で置換（DELETE + bulk INSERT）して冪等性・原子性を確保。
    - ルックアヘッドバイアスを避けるため target_date 時点のデータのみ使用する設計。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold, weights) を実装:
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - 各コンポーネントはシグモイド変換や逆数変換を使用して [0,1] にマッピング。
    - 欠損コンポーネントは中立値 0.5 で補完し銘柄の不当な降格を防止。
    - デフォルト重みとカスタム重みのマージ、無効値のスキップ、合計が 1.0 でない場合の再スケール処理を実装。
    - Bear レジーム判定（ai_scores の regime_score 平均 < 0 かつサンプル数閾値以上）により BUY シグナルを抑制。
    - BUY シグナルは閾値超過で生成、SELL シグナルはエグジット条件（ストップロス、スコア低下）で生成。
    - positions テーブル・最新株価を参照してストップロス判定を行い、価格欠損時は判定をスキップして誤クローズを防止。
    - signals テーブルへ日付単位の置換で書き込み（冪等、トランザクションで原子性確保）。
    - 生成結果のログ出力（BUY/SELL/total）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- news_collector で defusedxml を利用し、RSS / XML パース時の安全性を考慮。
- J-Quants クライアントでトークンの取り扱いや自動リフレッシュを実装（401 ハンドリング）。
- .env 読み込み時に OS 環境変数を protected として上書きを防止する仕組みを実装。

---

## マイグレーション / セットアップノート
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 未設定の場合 Settings のプロパティ参照で ValueError が発生します。
- 任意（デフォルトあり）:
  - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
  - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
- 自動 .env 読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で利用）。

## 既知の制約 / 今後の改善候補（コード内コメントより）
- signal_generator のトレーリングストップや時間決済は positions テーブル側に peak_price / entry_date が揃っていないため未実装。
- feature_exploration は外部ライブラリ（pandas 等）を使わず標準ライブラリで実装しているため、大規模データ時のパフォーマンス改善余地あり。
- news_collector における SSRF 防止や受信バイト制限は実装されているが、追加のネットワーク堅牢化（タイムアウト/リトライ等）は今後検討。

---

（以上）