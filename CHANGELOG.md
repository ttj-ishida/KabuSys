# Changelog

すべての重要な変更をここに記録します。フォーマットは "Keep a Changelog" に準拠します。

現在のリリース履歴は下記の通りです。

## [0.1.0] - 2026-03-20

初回リリース。日本株自動売買システム「KabuSys」のコアライブラリを追加しました。主な機能はデータ収集・保存、ファクター計算、特徴量作成、シグナル生成、環境設定管理、およびリサーチ補助ツール群です。

### 追加 (Added)
- パッケージ基礎
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
  - 公開 API: data, strategy, execution, monitoring モジュールのエクスポート定義。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - プロジェクトルート検出機能: .git または pyproject.toml を基準に自動検出。
  - .env パース実装: export プレフィックス、クォート・エスケープ、インラインコメント処理などに対応。
  - 自動ロード優先度: OS 環境変数 > .env.local > .env。テスト等で自動ロードを無効にする KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / env/log_level 判定等のプロパティ）。

- データ収集・保存 (src/kabusys/data)
  - J-Quants API クライアント (jquants_client.py)
    - レートリミッタ（120 req/min 固定間隔スロットリング）を実装。
    - 冪等性とページネーション対応のデータ取得（fetch_* 関数）。
    - リトライロジック（指数バックオフ、最大試行回数、HTTP 408/429/5xx の再試行）、および 401 受信時のトークン自動リフレッシュを実装。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装し、ON CONFLICT DO UPDATE による冪等保存を行う。
    - 型変換ユーティリティ (_to_float / _to_int) を提供。
  - ニュース収集モジュール (news_collector.py)
    - RSS フィードからの記事収集と前処理の実装。
    - URL 正規化（トラッキングパラメータ除去・ソート・小文字化・フラグメント除去）を実装。
    - defusedxml を利用した安全な XML パース、防御策（SSRF 回避のためのスキームチェック想定）や最大受信サイズ制限を導入。
    - 挿入効率化のためのバルクチャンク処理・INSERT RETURNING を想定した設計。

- リサーチ / ファクター計算 (src/kabusys/research)
  - factor_research.py
    - モメンタム（calc_momentum）: 1M/3M/6M リターン、200 日移動平均乖離率を計算。
    - ボラティリティ・流動性（calc_volatility）: 20 日 ATR、相対ATR (atr_pct)、20 日平均売買代金、出来高比率を計算。
    - バリュー（calc_value）: raw_financials と当日の株価を組み合わせて PER / ROE を算出。
    - DuckDB と SQL ウィンドウ関数を用いた効率的な実装。
  - feature_exploration.py
    - 将来リターン計算 (calc_forward_returns): 指定ホライズン（デフォルト 1,5,21 営業日）へのリターンを一括取得。
    - IC 計算 (calc_ic): スピアマンランク相関（Information Coefficient）を実装。サンプル数不足時は None を返す。
    - ランク関数 (rank)、ファクター統計サマリー (factor_summary) を提供。
  - research パッケージの __init__ で主要関数を再エクスポート。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - build_features(conn, target_date): research モジュールから取得した生ファクターを結合し、
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用、
    - 指定列の Z スコア正規化（zscore_normalize を利用）と ±3 クリップ、
    - features テーブルへ日付単位で置換（トランザクション + バルク挿入で原子性確保）する処理を実装。
  - ルックアヘッドバイアス対策: target_date 時点のみのデータを使用。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - generate_signals(conn, target_date, threshold=0.60, weights=None): features と ai_scores を統合して最終スコアを算出し、BUY / SELL シグナルを生成して signals テーブルへ保存。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news を計算。
    - AI レジームスコア集計による Bear 判定（サンプル閾値あり）。Bear 時は BUY を抑制。
    - BUY は閾値超え銘柄をスコア降順で選出。SELL はポジション情報（positions テーブル）に基づくストップロスやスコア低下で判定。
    - 重みの入力検証と合計スケーリング機能を実装。
    - 日付単位の置換で冪等性を確保。
  - 設計と実装は StrategyModel.md に定義された仕様（コメント）に従うよう記載。

- その他
  - strategy パッケージ __init__ にて build_features / generate_signals を公開。
  - ロギング（各主要処理での info/debug/warning 出力）を充実。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 非推奨 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- news_collector: defusedxml を使用して XML パースの安全性を高め、XML Bomb 等への対策を実装。
- J-Quants クライアント: ネットワークエラー・HTTP エラーに対する堅牢なリトライ・トークンリフレッシュ処理を導入。

---

注記:
- ソース内の docstring にて多くの設計意図（ルックアヘッドバイアス対策、冪等性、トランザクション処理、ログ出力方針等）を明示しています。
- DuckDB スキーマ（tables: raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar 等）はコード利用を前提に存在することを期待しています（スキーマ定義は本変更ログの範囲外）。
- 実運用前に .env 設定、DuckDB ファイル配置、J-Quants/Slack API トークンの準備が必要です。