Keep a Changelog に準拠した CHANGELOG.md（日本語）
※コードベースから推測して作成しています（初回リリース v0.1.0）。

All notable changes to this project will be documented in this file.
このプロジェクトの重要な変更点はすべてこのファイルに記録します。

フォーマットは Keep a Changelog に準拠しています。
https://keepachangelog.com/ja/1.0.0/

## [Unreleased]


## [0.1.0] - 2026-03-20
最初の公開リリース。以下の主要機能群・実装を含みます。

### 追加 (Added)
- パッケージ初期構成
  - kabusys パッケージ（__version__ = 0.1.0）
  - エントリポイントとして data, strategy, execution, monitoring モジュールを公開。

- 環境変数/設定管理 (src/kabusys/config.py)
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする機能を実装。
  - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用途）。
  - .env パーサーは以下をサポート:
    - 空行・コメント行（#）の無視
    - export KEY=val の形式
    - 単一/二重クォート内のバックスラッシュエスケープ処理
    - クォート無し値のインラインコメント処理（直前がスペース/タブの場合はコメントと扱う）
  - .env 読み込みの優先順位: OS 環境 > .env.local（override=True） > .env（override=False）。OS 環境は保護される。
  - Settings クラスを提供（プロパティ経由で設定取得）
    - 必須設定の検証（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）
    - デフォルト値: KABUSYS_ENV=development, LOG_LEVEL=INFO, KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV / LOG_LEVEL の入力検証（許容値チェック）
    - ヘルパー is_live / is_paper / is_dev を提供

- データ取得・保存 (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアント実装：
    - ページネーション対応の fetch_* 系関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を再試行対象）
    - 401 受信時は自動的にリフレッシュトークンで ID トークンを更新して 1 回再試行
    - ページングキーの二重取得防止
    - 取得時刻 fetched_at を UTC ISO8601 で記録（Look-ahead バイアス回避とトレーサビリティ）
  - DuckDB への保存関数:
    - save_daily_quotes/save_financial_statements/save_market_calendar：冪等な保存（ON CONFLICT DO UPDATE / ON CONFLICT DO NOTHING）
    - PK 欠損レコードのスキップとログ警告
    - 型変換ユーティリティ (_to_float, _to_int) を実装し不正データに寛容に対応

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィード収集・正規化機能を実装
    - URL 正規化（スキーム・ホスト小文字化、トラッキングパラメータ削除、フラグメント削除、クエリソート）
    - 記事ID を正規化後 URL の SHA-256（先頭32文字）で生成して冪等性を確保
    - defusedxml を用いた安全な XML パース（XML Bomb 等への対策）
    - 受信サイズ上限（MAX_RESPONSE_BYTES=10MB）によるメモリ DoS 対策
    - HTTP スキーム以外の URL 排除など SSRF 対策を想定（実装方針）
    - raw_news へのバルク挿入をチャンク化して実行（パフォーマンスと SQL 長対策）
    - デフォルト RSS ソース（Yahoo Finance のビジネスカテゴリ）を用意

- 研究用ファクター計算（src/kabusys/research/*.py）
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を prices_daily から計算
    - calc_volatility: ATR(20)、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算
    - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を計算（最新報告を銘柄ごとに取得）
    - SQL ベースで営業日欠損やウィンドウサイズ未満を適切に扱う
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得
    - calc_ic: スピアマンのランク相関（IC）を計算（必要なサンプル数チェック）
    - rank: 同順位は平均ランクとするランク変換（丸め処理で ties の検出改善）
    - factor_summary: count/mean/std/min/max/median の統計サマリを返す
  - 研究モジュールは pandas 等の外部依存を使わず標準ライブラリ＋DuckDB で実装

- 戦略関連（src/kabusys/strategy/*.py）
  - feature_engineering.py:
    - research モジュールで計算された raw ファクターを統合し features テーブルへ書き込み
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を実装
    - 正規化は zscore_normalize を利用し ±3 でクリップ（外れ値対策）
    - 日付単位で DELETE → INSERT をトランザクションで行い原子性を保証（冪等性）
  - signal_generator.py:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出
    - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完
    - デフォルト重みとし合成して final_score を計算（重みのバリデーション・リスケールを実装）
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）
    - BUY シグナルは閾値（デフォルト 0.60）以上。Bear 時は BUY 抑制。
    - SELL シグナル（エグジット）実装:
      - ストップロス（現行: 終値/avg_price - 1 < -8%）
      - final_score が閾値未満への降格
      - 価格欠損時は SELL 判定をスキップ（誤クローズ防止）
    - positions/price の最新行を参照して判定。signals テーブルへ日付単位で置換（トランザクション）

- logging / デバッグ情報
  - 各モジュールで適切な logger 呼び出しを追加（info/warning/debug）

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- news_collector で defusedxml を使用して XML パースの脆弱性に対処
- ニュース URL 正規化とスキームチェックによる SSRF リスク低減
- J-Quants クライアントでネットワークエラーや 429 の Retry-After を考慮した安全な再試行を実装
- .env 読み込みは OS 環境を保護する仕組みを導入（override/protected）

### 既知の制限 / 未実装の機能 (Known issues / TODO)
- signal_generator の一部エグジット条件は未実装:
  - トレーリングストップ（peak_price が positions に必要）
  - 時間決済（保有日数に関する判定）
- research / strategy はルックアヘッドバイアス回避を意識しているが、DB に格納するデータの fetched_at / 日付運用には注意が必要
- news_collector の SSRF や接続に関する細かいネットワーク制約は実運用での追加検証を推奨
- 外部依存:
  - DuckDB、defusedxml 等が必要（requirements に明示）

### マイグレーション / 運用上の注意 (Migration / Operational notes)
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings で必須
- 自動 .env ロードはプロジェクトルート検出に依存（.git または pyproject.toml）するため、パッケージ配布後に動作させる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定するか、適切に環境変数をセットしてください。
- DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, features, ai_scores, positions, signals, raw_news 等）を事前に用意すること。INSERT の ON CONFLICT 句はそれらの PK/ユニーク制約に依存します。

---

今後のリリースでは以下を優先して追加予定（推測）:
- エグジット条件の追加（トレーリングストップ、時間決済）
- execution 層との統合（発注 API 実行の実装）
- monitoring モジュールの実装（Slack 通知・ヘルスチェック）
- より詳細なテスト・例外ハンドリングの拡充

[0.1.0]: https://example.org/changes/0.1.0  <!-- 実際のリリースURLがあれば置換してください -->