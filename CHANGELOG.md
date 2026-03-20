# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
安定版リリースに向けた設計方針・実装の要点や既知の制約も併記しています。

なお、以下は提供されたソースコードから推測して作成した変更履歴です。

## [Unreleased]

- 今後の改善予定（ソース内コメントより推測）
  - positions テーブルに peak_price / entry_date 等を追加してトレーリングストップや時間決済を実装する。
  - strategy / execution 層のさらなる統合（発注ロジック・実口座対応）の実装。
  - テストカバレッジ強化・例外処理の細分化。
  - News 抽出とシンボル紐付けロジックの拡張（自然言語処理やマッチング改善）。

---

## [0.1.0] - 2026-03-20

初期公開リリース。日本株自動売買プラットフォームのコア機能群を実装。

### 追加 (Added)
- パッケージ基本情報
  - kabusys パッケージの初期化（src/kabusys/__init__.py）。
  - バージョン定義: `__version__ = "0.1.0"`。

- 設定管理
  - 環境変数ロードモジュール（src/kabusys/config.py）。
    - プロジェクトルート（.git または pyproject.toml）から `.env` / `.env.local` を自動検出して読み込む自動ロード機能（無効化用: `KABUSYS_DISABLE_AUTO_ENV_LOAD`）。
    - `.env` パーサ（クォート、エスケープ、inline コメント対応、`export KEY=val` 形式対応）。
    - Settings クラスによる型付きプロパティ（J-Quants トークン、kabu API、Slack、DB パス、環境モード、ログレベル等）。
    - env 値や log_level のバリデーション（許可値セットによるチェック）。

- Data 層
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）。
    - 固定間隔スロットリングによるレート制御（120 req/min）。
    - 再試行ロジック（指数バックオフ、最大試行回数、408/429/5xx ハンドリング）。
    - 401 受信時のトークン自動リフレッシュ（get_id_token）とモジュールレベルの ID トークンキャッシュ。
    - ページネーション対応の fetch 関数（daily quotes / financial statements / market calendar）。
    - DuckDB への冪等的保存関数（raw_prices / raw_financials / market_calendar）：ON CONFLICT を用いたアップサート。
    - 型変換ユーティリティ `_to_float` / `_to_int`（入力の堅牢化）。

  - ニュース収集モジュール（src/kabusys/data/news_collector.py）。
    - RSS フィード取得・記事正規化・raw_news への冪等保存。
    - 記事IDの生成（URL 正規化後の SHA-256 ハッシュ）、トラッキングパラメータ除去、URL 正規化処理。
    - defusedxml を用いた XML パースで XML Bomb 等の対策。
    - 最大受信サイズ制限（MAX_RESPONSE_BYTES）やバルク INSERT チャンク化。

- Research 層
  - ファクター計算（src/kabusys/research/factor_research.py）。
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（ATR20、atr_pct、avg_turnover、volume_ratio）、Value（per、roe）計算関数を実装。
    - DuckDB 上で SQL ウィンドウ関数を活用した効率的な実装。
  - 特徴量解析ユーティリティ（src/kabusys/research/feature_exploration.py）。
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）。
    - IC（Spearman の rho）計算、rank ユーティリティ、factor_summary（count/mean/std/min/max/median）。
  - research パッケージエクスポートを整備。

- Strategy 層
  - 特徴量生成（src/kabusys/strategy/feature_engineering.py）。
    - research の生ファクターを正規化（zscore）し ±3 でクリップ、ユニバースフィルタ（最低株価/最低売買代金）を適用。
    - features テーブルへの日付単位 UPSERT（トランザクションで原子性確保）。
    - ルックアヘッドバイアス防止を意識した実装（target_date 時点のデータのみ使用）。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）。
    - features と ai_scores を統合し、モメンタム/バリュー/ボラティリティ/流動性/ニュースのコンポーネントスコアを算出。
    - シグモイド変換、欠損コンポーネントは中立値で補完、ユーザ重みの検証・正規化（合計 1.0 に再スケール）。
    - Bear レジーム検知による BUY シグナル抑制（ai_scores の regime_score 集計に基づく）。
    - BUY/SELL シグナルを signals テーブルへ日付単位で置換（トランザクション＋バルク挿入）。
    - SELL 判定にストップロス（-8%）とスコア低下を実装。未実装のエグジット条件（トレーリングストップ・時間決済）はコメントで明示。

- パッケージ API
  - strategy パッケージで `build_features`, `generate_signals` をエクスポート。

### 変更 (Changed)
- 設計ポリシーの明文化（ソースコメント）
  - ルックアヘッドバイアス防止、発注 API への直接依存排除、DuckDB を中心としたローカル分析基盤の採用。
  - 外部依存を可能な限り抑える方針（research の実装は標準ライブラリ + DuckDB で完結）。

### 修正 (Fixed)
- データ処理の堅牢化
  - `.env` パーサで引用符内のエスケープ処理や inline コメントの扱いを改善。
  - `_to_int` の実装で "1.0" 等の文字列を安全に扱い、小数部がある場合は None を返す仕様で意図しない切り捨てを防止。
  - J-Quants API のリトライ/429（Retry-After）ハンドリングを実装し、過剰な再試行や不適切なスリープを回避。

### セキュリティ (Security)
- news_collector で defusedxml を採用して XML 攻撃を軽減。
- RSS/URL 正規化でトラッキングパラメータ除去、スキームチェック（HTTP/HTTPS 以外拒否想定）や受信サイズ制限で SSRF / メモリ DoS のリスクを低減。
- API トークンの自動リフレッシュと明示的なリフレッシュ制御により無限再帰や漏洩のリスクを軽減（allow_refresh フラグ）。

### 既知の制約・未実装事項 (Known issues / TODO)
- positions テーブルに peak_price / entry_date 等がないため、コメントで触れられているトレーリングストップや時間決済は未実装。
- execution 層は空の __init__ しか定義されておらず、実際の発注ロジック（kabu ステーション API 連携）は未実装。
- 一部のテーブルスキーマ（features, ai_scores, positions 等）の前提がコードに存在するが、スキーマ定義ファイルはリポジトリに含まれていない可能性あり。
- ai_scores の取得が空の場合は中立扱いとするため、AI スコアの取得運用が本番で必須となる場合の動作確認が必要。

---

この CHANGELOG はソースコードの実装内容・コメントから推測して作成しています。必要であれば、実際のコミット履歴やリポジトリメタデータに基づく正確な変更履歴へ整備するお手伝いをします。