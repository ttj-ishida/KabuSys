# Changelog

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従います。  

なお、本ファイルはコードベースから実装内容を推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-03-19

初回公開リリース。

### 追加 (Added)

- コア
  - パッケージエントリポイントを追加（kabusys.__init__）。公開 API として data/strategy/execution/monitoring をエクスポート。
  - バージョン情報: `__version__ = "0.1.0"` を設定。

- 設定 / 環境変数管理
  - Settings クラスを実装し、環境変数経由でアプリケーション設定を取得可能に（J-Quants / kabuAPI / Slack / DB パス /実行環境 / ログレベル 等）。
  - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。読み込み順: OS 環境 > .env.local > .env。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - .env 行パーサーを実装:
    - export プレフィックス対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメントの取り扱い（クォート外のみ、直前が空白/タブの場合はコメントとして扱う）
  - 環境値のバリデーション（KABUSYS_ENV / LOG_LEVEL の許容値チェック）、必須キー未設定時は明確なエラーを送出。

- データ取得・保存（J-Quants クライアント）
  - J-Quants API クライアントを実装（認証・ページネーション対応）。
  - レート制限管理（120 req/min）を固定間隔スロットリングで実装（内部 RateLimiter）。
  - 再試行ロジック（指数バックオフ、最大3回、408/429/5xx の再試行、429 の Retry-After 優先）。
  - 401 レスポンス時はリフレッシュトークンで自動的にトークンを更新して1回リトライ（無限再帰防止）。
  - ID トークンのモジュールレベルキャッシュを実装（ページネーション間で共有）。
  - DuckDB への保存関数を実装（冪等性を担保する ON CONFLICT / DO UPDATE を使用）:
    - save_daily_quotes -> raw_prices
    - save_financial_statements -> raw_financials
    - save_market_calendar -> market_calendar
  - データパースユーティリティ: 安全な float/int 変換関数（空値・不正値を None にするロジック）。

- ニュース収集
  - RSS フィード収集モジュールを実装（デフォルトに Yahoo Finance のカテゴリ RSS を含む）。
  - XML パースに defusedxml を使用して XML Bomb 等から保護。
  - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリをキーソート）。
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）を用いることで冪等性を担保。
  - 最大受信サイズ制限（10 MB）や HTTP スキーム検証等を導入し、メモリ DoS / SSRF 対策を考慮。
  - DB への一括 INSERT をトランザクション内で分割挿入し効率化（チャンクサイズ設定）。

- リサーチ（research）
  - ファクター計算モジュールを実装（prices_daily / raw_financials を参照）:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均は必要な行数を確認）
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio（true_range の NULL 伝播を制御）
    - calc_value: per / roe（target_date 以前の最新財務データを結合）
  - 特徴量探索モジュールを実装:
    - calc_forward_returns: 任意ホライズン（デフォルト 1,5,21 日）で将来リターンを計算
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装（サンプル不足時は None）
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算
    - rank: 同順位は平均ランクで扱うランク計算ユーティリティ
  - 研究用モジュールは外部依存（pandas 等）を使わず標準ライブラリと DuckDB の SQL で実装。

- 特徴量エンジニアリング（strategy.feature_engineering）
  - research 側で算出した生ファクターをマージ・フィルタ・正規化して features テーブルへ保存する機能を実装。
  - ユニバースフィルタを導入（最低株価 300 円、20 日平均売買代金 5 億円）。
  - Z スコア正規化（外部ユーティリティ zscore_normalize を利用）、±3 でクリップ。
  - 日付単位で既存データを削除してから挿入する形式で冪等性と原子性を確保（トランザクション）。

- シグナル生成（strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算し、BUY / SELL シグナルを生成して signals テーブルへ保存する機能を実装。
  - コンポーネントスコア:
    - momentum / value / volatility / liquidity / news を計算するユーティリティを実装（シグモイド変換など）。
  - 重み仕様: デフォルトの重みを実装し、ユーザ指定 weights は検証・正規化してマージ（合計が 1.0 になるよう再スケール）。
  - Bear レジーム判定: ai_scores の regime_score 平均が負の場合に BUY シグナルを抑制（サンプル不足時は判定しない）。
  - エグジット（SELL）条件:
    - ストップロス（終値 / avg_price - 1 < -8%）
    - final_score が閾値未満
    - 保有銘柄の価格欠損時は判定をスキップする安全策
    - （未実装だが設計に記載）トレーリングストップ・時間決済への拡張ポイントを明記
  - 日付単位で既存 signals を削除してから挿入する形式で冪等性と原子性を確保（トランザクション）。

### 修正 (Fixed)

- .env パースの堅牢化:
  - クォート内エスケープ、コメント処理、export プレフィックス対応により現場での .env 設定の誤読を低減。
- 数値変換ユーティリティの堅牢化:
  - _to_int は "1.0" のような文字列を float 経由で正しく int に変換するが、小数部がある場合は None を返すことで意図しない切り捨てを防止。

### セキュリティ (Security)

- XML パースに defusedxml を採用して XML-based attack を防止。
- ニュース収集で受信サイズ上限（10 MB）を設定し、メモリ DoS リスクを軽減。
- URL 正規化によりトラッキングパラメータを除去、また HTTP/HTTPS のみを許容することで SSRF リスクを低減。
- .env の自動ロードは明示的に無効化可能（テスト環境向け）。

### 既知の制限 / TODO

- strategy._generate_sell_signals 内で設計に記載されているトレーリングストップ / 時間決済は未実装（positions テーブルに peak_price / entry_date が必要）。
- calc_value は現在 PER / ROE のみを実装。PBR・配当利回りは未実装。
- execution パッケージは空のプレースホルダ（発注連携は別層で実装予定）。
- 一部の外部依存（例: kabusys.data.stats の zscore_normalize）は本リリースで利用されているが、実装は別ファイルで提供される想定。

---

この CHANGELOG はコードから推測して作成しています。実際のリリースノート作成時にはコミット履歴やリリース日・著者情報を追記してください。