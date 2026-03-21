# Changelog

すべての注目すべき変更点をこのファイルに記載します。  
このプロジェクトは Keep a Changelog の慣習に従っています。  

なお、この CHANGELOG はリポジトリのコード内容から推測して作成した初回リリース向けの要約です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-21

初回公開リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。主な追加点は以下のとおりです。

### Added
- パッケージ基盤
  - パッケージエントリポイント `kabusys`（__version__ = 0.1.0）を追加。
  - サブパッケージ構成: data, strategy, execution, monitoring をエクスポート。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルまたは OS 環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート探索ロジック（.git または pyproject.toml を起点）を追加し、カレントワーキングディレクトリに依存せずに .env を検出可能に。
  - .env のパーサを実装。下記に対応:
    - コメント行・空行の無視
    - `export KEY=val` 形式のサポート
    - シングル/ダブルクォートで囲まれた値、バックスラッシュエスケープの解釈
    - クォートなし値のインラインコメント処理（直前が空白/タブの場合）
  - 自動ロード無効化オプション: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
  - 設定クラス `Settings` を提供。必須項目取得時に未設定であれば `ValueError` を送出するユーティリティ `_require` を実装。
  - 設定項目:
    - J-Quants: `JQUANTS_REFRESH_TOKEN`
    - kabu API: `KABU_API_PASSWORD`, `KABU_API_BASE_URL`（デフォルト: http://localhost:18080/kabusapi）
    - Slack: `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`
    - DB パス: `DUCKDB_PATH`（デフォルト: data/kabusys.duckdb）, `SQLITE_PATH`（デフォルト: data/monitoring.db）
    - 環境 (`KABUSYS_ENV`) のバリデーション（development, paper_trading, live）
    - ログレベル (`LOG_LEVEL`) のバリデーション

- データ取得・保存 (`kabusys.data.jquants_client`)
  - J-Quants API クライアントを実装。
    - レート制限（120 req/min）を守る固定間隔スロットリング（RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 受信時にリフレッシュトークンで id_token を自動更新して 1 回リトライする機能。
    - ページネーション対応。
    - 取得時刻（fetched_at）を UTC ISO8601 形式で記録し、ルックアヘッドバイアスを防止。
  - データ取得関数:
    - fetch_daily_quotes (日足)
    - fetch_financial_statements (財務データ)
    - fetch_market_calendar (JPX カレンダー)
  - DuckDB 保存関数（冪等化）:
    - save_daily_quotes -> raw_prices テーブルへ ON CONFLICT DO UPDATE
    - save_financial_statements -> raw_financials テーブルへ ON CONFLICT DO UPDATE
    - save_market_calendar -> market_calendar テーブルへ ON CONFLICT DO UPDATE
  - 型変換ユーティリティ `_to_float` / `_to_int` を実装（安全なパース・空値処理）。

- ニュース収集 (`kabusys.data.news_collector`)
  - RSS フィードからニュースを収集して raw_news に保存する機能を実装（research/data platform 向け）。
  - セキュリティ / 安全性対応:
    - defusedxml を用いた XML パースで XML-Bomb 等に対する防御。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）。
    - HTTP/HTTPS スキーム以外を拒否する設計（SSRF 対策に向けた方針）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）を設定。
  - 挿入はバルクチャンク化（チャンクサイズ）して効率化。挿入済み件数を正確に返すことを想定。

- リサーチ（研究）モジュール (`kabusys.research`)
  - ファクター計算ロジックを実装（DuckDB を用いた SQL+Python）。
  - 提供 API:
    - calc_momentum: mom_1m/mom_3m/mom_6m/ma200_dev を計算（200日MA のデータ不足は None）
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算（ATR のデータ不足は None）
    - calc_value: per, roe を計算（raw_financials と prices_daily を結合）
    - calc_forward_returns: 将来リターン（デフォルト horizons=[1,5,21]）をまとめて取得
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装（有効サンプル 3 未満は None）
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算
    - rank: 同順位は平均ランクとするランク付けユーティリティ
  - 設計方針として外部ライブラリ（pandas 等）に依存しない実装を目指し、prices_daily / raw_financials のみを参照する点を明示。

- 戦略（Strategy）モジュール (`kabusys.strategy`)
  - feature_engineering.build_features:
    - research モジュールの calc_* 関数から生ファクターを取得し、ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）し ±3 でクリップ。
    - features テーブルへ日付単位で置換（トランザクション + バルク挿入で原子性を保証）。
  - signal_generator.generate_signals:
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）、閾値デフォルト 0.60。
    - Ai レジームスコアから Bear 判定を行い（サンプル閾値あり）、Bear 時は BUY シグナル抑制。
    - BUY シグナル生成・SELL（エグジット）判定を実装:
      - SELL 条件としてストップロス（-8%）と final_score の閾値割れを実装。
      - SELL 優先ポリシー（SELL 対象は BUY から除外し、BUY はランク再付与）。
    - signals テーブルへ日付単位で置換（トランザクション + バルク挿入で原子性を保証）。
    - weights のバリデーション・フォールバック・再スケール処理を実装（無効値はログでスキップ）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- news_collector: defusedxml による XML パースと受信サイズ上限により XML-Bomb / メモリ DoS に対処する方針を採用。
- jquants_client: トークン自動リフレッシュ処理において無限再帰を防ぐため allow_refresh フラグの導入。

### Notes / Migration / Requirements
- このリリースでは必要な環境変数（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）が未設定だと Settings のプロパティアクセス時に `ValueError` が発生します。`.env.example` を参考に適切に設定してください。
- DuckDB 側に想定されるテーブル（raw_prices, raw_financials, prices_daily, raw_financials, features, ai_scores, positions, signals, market_calendar, raw_news など）が必要です。スキーマはプロジェクトドキュメント（DataPlatform.md / StrategyModel.md）に従って作成してください。
- research モジュールや strategy モジュールはルックアヘッド・バイアスを防ぐ設計になっています — target_date 時点のデータのみを使用します。
- 外部依存は最小限（defusedxml を使用）。他は標準ライブラリと DuckDB を想定。

---

今後のリリースでは以下の拡張が想定されています:
- strategy の追加エグジット条件（トレーリングストップ・時間決済）
- execution 層の実装（kabu API への発注ロジック）
- monitoring / Slack 通知連携の実装強化
- テストカバレッジ・ドキュメントの充実

（以上）