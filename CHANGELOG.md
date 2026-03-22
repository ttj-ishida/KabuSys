# Changelog

すべての変更は Keep a Changelog のフォーマットに従っています。  
このプロジェクトはセマンティックバージョニング (https://semver.org/) を採用しています。

## [Unreleased]

（現在なし）

## [0.1.0] - 2026-03-21

初回リリース。日本株自動売買システムのコアライブラリを提供します。主な追加点・設計方針は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージを導入。バージョンは 0.1.0。
  - パブリック API: data, strategy, execution, monitoring をエクスポート。

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local ファイルまたは OS 環境変数から設定を自動ロード（プロジェクトルートは .git または pyproject.toml を探索）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用途）。
  - .env パーサーはコメント、export 形式、クォートおよびエスケープに対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境等のプロパティを安全に取得。
  - 必須環境変数未設定時は明確なエラーメッセージを送出。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）。

- データ取得・保存（J-Quants クライアント） (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装（トークン取得、ページネーション、日足・財務・カレンダー取得）。
  - レートリミッタ実装（120 req/min 固定間隔スロットリング）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx などに対応）。
  - 401 受信時はリフレッシュトークンを用いてトークン自動更新を行い 1 回リトライ。
  - 取得時刻 (fetched_at) を UTC で記録し、ルックアヘッドバイアスのトレースを可能に。
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）するユーティリティ:
    - save_daily_quotes: raw_prices テーブルへ保存（PK 欠損行はスキップして警告）。
    - save_financial_statements: raw_financials テーブルへ保存。
    - save_market_calendar: market_calendar テーブルへ保存。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を取得して raw_news へ保存する仕組みを実装（デフォルトに Yahoo Finance の RSS を含む）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除、スキーム/ホスト小文字化）を実装。
  - defusedxml を使用して XML Attack を防止、受信サイズ上限（10MB）でメモリ DoS を防ぐ対策を実装。
  - 記事 ID を正規化 URL の SHA-256 で生成して冪等性を確保。
  - DB へのバルク挿入はチャンク処理で行う（パフォーマンスと SQL 長制約に配慮）。

- リサーチ（研究）モジュール (src/kabusys/research/)
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials を参照）。
    - Momentum: 1M/3M/6M リターン、200 日移動平均乖離率を計算。
    - Volatility: 20 日 ATR（相対 ATR）、20 日平均売買代金、出来高比率を計算。
    - Value: PER / ROE を計算（最新財務データを target_date 以前から取得）。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（デフォルト: 1, 5, 21 営業日）を一括取得。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算。
    - factor_summary / rank: 基本統計量やランク変換ユーティリティを提供。
  - 研究用 API は外部ライブラリに依存せず、DuckDB + 標準ライブラリのみで実装。

- 戦略モジュール (src/kabusys/strategy/)
  - feature_engineering.build_features:
    - research の生ファクターを読み込み、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 数値ファクターを Z スコア正規化（zscore_normalize を使用）、±3 でクリップ。
    - features テーブルへ日付単位で置換（トランザクション＋バルク挿入で原子性を保障）。
  - signal_generator.generate_signals:
    - features と ai_scores を統合し、モメンタム/バリュー/ボラティリティ/流動性/ニュースのコンポーネントスコアを計算。
    - スコアはシグモイド変換や反転処理を行い、欠損コンポーネントは中立値 0.5 で補完。
    - final_score を重み付きで合成（デフォルト重みを定義）。重みはユーザ指定で補完・正規化可能。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合、サンプル閾値あり）により BUY を抑制。
    - BUY／SELL シグナルを生成し、signals テーブルへ日付単位で置換して保存（冪等）。
    - 保有ポジションのエグジット判定（ストップロス -8%、スコア低下）を実装。

### 変更 (Changed)
- （初回リリースのため過去変更はなし）

### 修正 (Fixed)
- （初回リリースのため過去修正はなし）

### セキュリティ (Security)
- ニュースパーサで defusedxml を採用して XML 関連の脆弱性を緩和。
- ニュース収集で外部 URL のスキーム検証や受信サイズ制限を導入し SSRF / DoS 対策の設計方針を反映。
- J-Quants クライアントは Authorization ヘッダ管理とトークン自動リフレッシュを実装。

### 設計ノート / 制限事項 (Notes / Limitations)
- positions テーブルに peak_price / entry_date がないため、トレーリングストップや時間決済の一部条件は未実装としてコメントで残されています。
- calc_value は PER / ROE を提供するが、PBR や配当利回りは未実装。
- ai_scores が未登録の銘柄はニューススコアを中立（0.5）で補完する設計。Bear 判定はサンプル数不足（デフォルト 3 件未満）では行わない。
- zscore の正規化は ±3 にクリップして外れ値の影響を抑制。
- DuckDB のテーブルスキーマ（raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar 等）は本ログやコードのコメントで参照されるが、スキーマ定義自体はリリースに含まれていないため、運用では適切なテーブル定義が事前に必要。
- NewsCollector は既知のトラッキングパラメータプレフィックスを除去するが、未知のパラメータや非常に特殊な URL パターンは追加対応が必要な可能性あり。
- 外部依存は最小限（defusedxml を使用）で、リサーチ系は pandas に依存せず純 Python / DuckDB で実装しているため、データボリュームやパフォーマンス要件によっては最適化が必要。

---

著者・貢献者はコード内のロギングや docstring を参照してください。将来的なリリースでは、実運用向けの追加検証・監視・テスト・ドキュメント強化を予定しています。