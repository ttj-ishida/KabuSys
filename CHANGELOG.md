# CHANGELOG

全ての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

最新: [0.1.0] - 2026-03-19

## [0.1.0] - 2026-03-19
初回公開リリース。本バージョンでは日本株自動売買システム「KabuSys」のコア機能群を実装しました。主要な追加・設計方針は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - src/kabusys/__init__.py にてパッケージバージョンと公開 API を定義（data, strategy, execution, monitoring）。

- 環境設定読み込み・管理
  - src/kabusys/config.py
    - プロジェクトルート（.git または pyproject.toml）から自動で .env/.env.local を読み込む自動ロード機能を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - .env の行パースロジックを実装（コメント・export プレフィックス・クォート・エスケープ処理対応）。
    - Settings クラスを導入し、J-Quants トークン、kabu API 設定、Slack、DB パス、実行環境フラグ（development/paper_trading/live）等の取得インターフェースを提供。バリデーション（env, log_level 等）を実装。

- データ取得/保存（J-Quants API クライアント）
  - src/kabusys/data/jquants_client.py
    - API レート制御 (120 req/min) を固定間隔スロットリングで実装（_RateLimiter）。
    - HTTP リクエストの共通処理を実装し、ページネーション対応。
    - リトライ（指数バックオフ、最大 3 回）と 401 時の ID トークン自動リフレッシュを実装。再試行ポリシーで 408/429/5xx を考慮。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar のページネーション対応関数を追加。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を追加し、冪等性（ON CONFLICT DO UPDATE）を担保。
    - 値変換ユーティリティ _to_float / _to_int を追加して堅牢なデータハンドリングを実現。

- ニュース収集モジュール
  - src/kabusys/data/news_collector.py
    - RSS からの記事収集、本文前処理、URL 正規化（トラッキングパラメータ削除、ソート、フラグメント削除）を実装。
    - defusedxml を使った XML パースで XML Bomb 等の攻撃対策。HTTP スキーム検査と受信サイズ上限（MAX_RESPONSE_BYTES）で SSRF/DoS 対策を計上。
    - 記事 ID を正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成して冪等性を保証。
    - raw_news へのバルク INSERT をトランザクション内で行い、INSERT チャンクサイズ制御により SQL 長制限に対応。

- リサーチ（因子計算・探索）
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20 日 ATR、相対 ATR、出来高関係）、バリュー（PER, ROE）等のファクター計算関数（calc_momentum / calc_volatility / calc_value）を実装。DuckDB の prices_daily / raw_financials テーブルのみを参照。
    - 実務上の欠損・不正値に対する堅牢性（NULL 伝播やカウント閾値による None 返却）を考慮。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）：指定ホライズンに対する将来終値を LEAD で取得しリターンを計算。
    - IC（Information Coefficient）計算（calc_ic）：factor と forward を code で結合し Spearman（ランク相関）を算出。サンプル不足時は None。
    - ランク付けユーティリティ（rank）と factor_summary（count/mean/std/min/max/median）を実装。外部依存なしで標準ライブラリのみで実装。

  - src/kabusys/research/__init__.py で主要関数をエクスポート。

- 特徴量エンジニアリング
  - src/kabusys/strategy/feature_engineering.py
    - research モジュールの生ファクターを統合し、ユニバースフィルタ（最低株価、20 日平均売買代金）を適用。
    - 数値ファクターの Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへの日付単位での置換（DELETE + INSERT をトランザクションで行い原子性を保証）。
    - ルックアヘッドバイアス回避のため target_date 時点のデータのみを使用。

- シグナル生成
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合して各種コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネントはシグモイド変換や反転処理を行い最終スコア final_score を重み付きで算出（デフォルト重みは StrategyModel.md Section 4.1 相当）。
    - weights の入力検証・フォールバック・正規化ロジックを実装（無効なキーや負値、非数値を無視し、合計が 1 でなければ再スケール）。
    - Bear レジーム判定（AI の regime_score 平均が負かつサンプル数閾値を満たす場合に BUY を抑制）。
    - BUY シグナルは閾値（デフォルト 0.60）超過で生成、SELL シグナルはストップロス（-8%）やスコア低下で判定。
    - positions / prices_daily / ai_scores を参照し、SELL 優先ポリシーで BUY から除外、signals テーブルへ日付単位の置換で書き込み（原子性確保）。

- Strategy パッケージエクスポート
  - src/kabusys/strategy/__init__.py で build_features と generate_signals を公開。

### 変更 (Changed)
- なし（初回リリースのため既存変更はありません）

### 修正 (Fixed)
- なし（初回リリース）

### セキュリティ (Security)
- news_collector で defusedxml の使用、受信バイト数制限、URL スキーム検査、トラッキングパラメータ削除などを導入し、XML インジェクション／SSRF／DoS への耐性を高めました。
- jquants_client でトークン管理と HTTP リトライの制御、Retry-After ヘッダ考慮により誤ったリトライや無限ループのリスクを低減。

### 既知の制限 / 未実装の機能 (Known issues / Not implemented)
- signal_generator のトレーリングストップや時間決済条件は未実装（positions テーブルに peak_price / entry_date 等が必要）。feature_engineering / strategy 内にコメントで残しています。
- 一部ユーティリティ（例: kabusys.data.stats.zscore_normalize）は本リリース前提で参照されています。実装は同パッケージ内に存在する想定です（本 CHANGELOG 作成対象コードからは詳細ファイルが省略されている可能性があります）。
- execution / monitoring パッケージの具体的な発注 API 連携や実行監視実装は本リリースでは含まれていません（パッケージ構成でのプレースホルダ）。

---

今後のリリースでは、execution 層（実際の発注統合）、監視・アラート強化、追加のファクターやバックテスト用ユーティリティ、より詳細なドキュメントやテストカバレッジの拡充を予定しています。