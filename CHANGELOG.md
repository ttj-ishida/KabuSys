# Changelog

すべての主な変更点は Keep a Changelog の形式に従って記録します。互換性のある公開リリースはセマンティックバージョニングに従います。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システムのコアライブラリ群を実装。

### Added
- パッケージ初期化
  - kabusys パッケージの導入（__version__ = 0.1.0）。
  - public API: kabusys.{data,strategy,execution,monitoring} を __all__ に公開。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび OS 環境変数から設定を自動読み込み。
  - プロジェクトルート判定: .git または pyproject.toml を基準に自動検出（CWD 非依存）。
  - .env/.env.local の読み込み優先度実装（OS 環境変数保護、.env.local は上書き）。
  - パース機能: export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - Settings クラス実装（必須環境変数のチェック、デフォルト値、検証）
    - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等の必須取得メソッド。
    - env（development/paper_trading/live）の検証、LOG_LEVEL の検証、パス型の DB 設定取得。

- データ取得・保存（kabusys.data）
  - J-Quants API クライアント（data.jquants_client）
    - 固定間隔スロットリングによるレート制限実装（120 req/min）。
    - リトライ/指数バックオフ（最大3回）、HTTP 408/429/5xx に対する再試行。
    - 401 受信時の自動トークンリフレッシュ（1回のみ）とモジュールレベルでの ID トークンキャッシュ。
    - ページネーション対応の fetch_* 系（株価日足、財務データ、カレンダー）。
    - DuckDB へ冪等に保存する save_* 系（raw_prices / raw_financials / market_calendar）。
    - データ変換ユーティリティ (_to_float/_to_int)。
    - レスポンス JSON のデコードエラーハンドリング、ログ出力。
  - ニュース収集モジュール（data.news_collector）
    - RSS フィード収集処理の基礎実装（既定ソースに Yahoo Finance を登録）。
    - 記事 ID に URL 正規化＋SHA-256 を用いる冪等性設計。
    - 受信サイズ制限（MAX_RESPONSE_BYTES）や defusedxml による XML 攻撃対策。
    - トラッキングパラメータ除去、URL 正規化、SSRF 対策方針を実装。
    - バルク INSERT チャンク処理と DB トランザクションで効率的かつ安全に保存。

- リサーチ（kabusys.research）
  - ファクター計算（research.factor_research）
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）計算（窓・LAG を用いた SQL 実装）。
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）計算（true_range の NULL 伝播を考慮）。
    - Value（per, roe）計算（raw_financials の最新レコード結合）。
    - DuckDB を用いた SQL ベースの実装で外部 API に依存しない設計。
  - 特徴量探索ユーティリティ（research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）：複数ホライズン（デフォルト 1/5/21 営業日）。
    - IC（Information Coefficient）計算（スピアマンのランク相関 calc_ic）。
    - factor_summary による基本統計量集計（count/mean/std/min/max/median）。
    - rank 関数（同順位は平均ランク、丸めによる ties 考慮）。
    - 外部ライブラリに依存しない標準ライブラリのみの実装方針。

- 戦略（kabusys.strategy）
  - 特徴量エンジニアリング（strategy.feature_engineering）
    - research モジュールで計算された raw factor をマージしてユニバースフィルタ適用（最低株価・平均売買代金閾値）。
    - 指定カラムを Z スコア正規化し ±3 でクリップ。
    - features テーブルへの日付単位の置換（DELETE→INSERT をトランザクションで行い原子性を確保）。
    - Z スコア正規化は kabusys.data.stats の zscore_normalize を利用。
  - シグナル生成（strategy.signal_generator）
    - features と ai_scores を統合して final_score を計算（momentum/value/volatility/liquidity/news の重み付け）。
    - デフォルト重みと閾値（threshold=0.60）を実装、ユーザー重みの検証とリスケーリングを実装。
    - Sigmoid 等のスコア変換、欠損コンポーネントの中立値（0.5）補完。
    - Bear レジーム判定（AI レジームスコアの平均が負の場合、サンプル閾値あり）により BUY を抑制。
    - エグジット判定（ストップロス -8%、スコア低下）を実装。SELL 優先のポリシー（SELL 対象は BUY から除外）。
    - signals テーブルへの日付単位の置換をトランザクションで実行。
  - strategy パッケージで build_features / generate_signals を公開。

### Changed
- （初回リリースのため過去変更なし）
- 設計上の注記（README/Docstring に明記）
  - ルックアヘッドバイアス対策として、target_date 時点のデータのみを参照する方針を明確化。
  - DB 操作は原子性を保つためトランザクション + バルク挿入で行う設計。

### Fixed
- （初版リリースにつき修正履歴なし）

### Security
- news_collector: defusedxml の利用、最大レスポンスバイト数制限、URL サニタイズにより XML Bomb / SSRF / メモリ DoS に対する基本対策を実装。
- jquants_client: ID トークンの取り扱いは内部キャッシュ化し、401 に対する安全なリフレッシュロジックを実装（無限ループ防止フラグあり）。

### Known limitations / TODO
- execution パッケージは空で、発注層（kabuステーション連携等）は未実装。
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装（positions テーブルに peak_price / entry_date が必要）。
- research モジュールは DuckDB の prices_daily/raw_financials テーブルを前提としているため、データ整備が必要。
- ニュースの銘柄紐付け処理（news_symbols への登録や NLP に基づくマッチング）は今後の拡張対象。

---

補足:
- 各モジュールには詳細な docstring と設計方針が含まれており、研究（research）環境と運用（execution）環境の役割分離を重視しています。