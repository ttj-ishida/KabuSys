# CHANGELOG

すべての重要な変更をここに記録します。本ファイルは Keep a Changelog の形式に準拠しています。

現在のバージョン: 0.1.0 - 2026-03-21

## [Unreleased]
（次のリリースに向けた変更はここに記載）

## [0.1.0] - 2026-03-21
初回リリース。日本株自動売買システム "KabuSys" の基本機能群を実装しました。

### Added
- パッケージ基盤
  - `kabusys` パッケージ初期化（`src/kabusys/__init__.py`）
    - バージョン番号 `0.1.0`
    - エクスポート: `data`, `strategy`, `execution`, `monitoring`（`execution` は空パッケージ、`monitoring` は将来的な実装想定）
- 環境設定 / ロード
  - `kabusys.config`（`src/kabusys/config.py`）
    - .env ファイルおよび環境変数から設定読み込みを自動化（プロジェクトルート判定：`.git` または `pyproject.toml` を探索）
    - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD`
    - .env パーサ実装（コメント、export プレフィックス、クォート/エスケープ、インラインコメントの扱いに対応）
    - 環境値検証（`KABUSYS_ENV`、`LOG_LEVEL` の有効値チェック）
    - `Settings` クラスで主要設定をプロパティとして提供（J-Quants トークン、kabuステーションパスワード、Slack トークン/チャンネル、DB パス等）
- データ収集 / 保存
  - `kabusys.data.jquants_client`（`src/kabusys/data/jquants_client.py`）
    - J-Quants API クライアント
    - 固定間隔によるレート制御（120 req/min）
    - リトライ戦略（指数バックオフ、最大 3 回、408/429/5xx を対象）
    - 401 発生時にリフレッシュトークンで自動再取得して 1 回リトライ
    - ページネーション対応のデータ取得（株価・財務・マーケットカレンダー）
    - DuckDB への冪等保存関数（`save_daily_quotes`, `save_financial_statements`, `save_market_calendar`）: ON CONFLICT による更新
    - データ変換ユーティリティ（安全な float/int 変換）
    - fetched_at は UTC で記録（look-ahead bias 対策）
  - `kabusys.data.news_collector`（`src/kabusys/data/news_collector.py`）
    - RSS フィードからニュース収集（デフォルトソースに Yahoo Finance を設定）
    - XML パースに defusedxml を利用（XML 攻撃対策）
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）
    - レスポンスサイズ上限、SSRF リスク低減の考慮、記事ID を正規化 URL の SHA-256 ハッシュで生成して冪等性を保証
    - DB へバルク挿入（チャンク化）して効率的に保存
- 研究モジュール（Research）
  - `kabusys.research.factor_research`（`src/kabusys/research/factor_research.py`）
    - モメンタム (1M/3M/6M, MA200 乖離)、ボラティリティ（ATR20 / 相対ATR）、流動性（20日平均売買代金、volume_ratio）、バリュー（PER / ROE）を DuckDB 上で計算する関数群
    - DuckDB のウィンドウ関数を活用した実装、欠損/データ不足時の安全な None 処理
  - `kabusys.research.feature_exploration`（`src/kabusys/research/feature_exploration.py`）
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）
    - IC（Spearman の ρ）計算（ランク付け実装、同順位は平均ランク）
    - ファクター統計サマリー（count/mean/std/min/max/median）
    - pandas 等に依存せず、標準ライブラリと DuckDB のみで実装
  - `kabusys.research.__init__` で主要 API を公開
- 戦略層（Strategy）
  - `kabusys.strategy.feature_engineering`（`src/kabusys/strategy/feature_engineering.py`）
    - research の生ファクターを統合し、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用
    - 正規化（z-score）と ±3 でのクリップ、features テーブルへの日付単位の置換（トランザクション + バルク挿入で冪等）
    - 正規化対象列等の定数化
  - `kabusys.strategy.signal_generator`（`src/kabusys/strategy/signal_generator.py`）
    - features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを生成
    - コンポーネントスコア: momentum/value/volatility/liquidity/news（news は AI スコア）
    - 重み合成（デフォルト重みを持ち、カスタム重みは検証・正規化して適用）
    - Bear レジーム検知（AI の regime_score 平均が負なら BUY を抑制、サンプル閾値あり）
    - SELL 判定（ストップロス -8%、スコア低下など）、保有ポジション情報を参照して判定
    - signals テーブルへ日付単位置換（冪等）
  - `kabusys.strategy.__init__` で主要 API を公開（`build_features`, `generate_signals`）
- その他
  - DuckDB 接続を前提とした設計（prices_daily / raw_financials / raw_prices / features / ai_scores / positions 等のテーブル想定）
  - ログ出力（各モジュールで適切な logger 呼び出し）

### Security
- defusedxml を用いた XML パース（news_collector）により XML ベースの攻撃を低減
- RSS URL 正規化およびスキーム検証により SSRF リスクを低減
- J-Quants クライアントは認証トークンの自動リフレッシュ処理を行うが、トークン管理には注意（Settings が環境変数依存）
- .env ファイル読み込みでは OS 環境変数を保護（既存の OS 環境変数は上書きされない、.env.local は上書き）

### Known issues / Limitations
- execution 層は未実装（`src/kabusys/execution/__init__.py` は空）。実際の発注連携は今後実装予定。
- monitoring モジュールはパッケージ公開に含まれるが、本リリースに具体的実装は含まれていない。
- 一部のロジック（トレーリングストップ、時間決済など）は未実装（signal_generator のコメント参照）。
- 外部依存（duckdb, defusedxml）が必要。環境構築時にインストールが必要。
- ai_scores の生成・モデル本体は含まれない（外部で算出して ai_scores テーブルへ格納する想定）。
- zscore_normalize は `kabusys.data.stats` に依存しているが、本差分ではその実装ファイルは表示されていない（プロジェクトに含まれる想定）。

### Notes for users / Operators
- 自動で .env をルート（.git または pyproject.toml）から読み込むため、実行ディレクトリに依存せず設定が適用されます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のテーブルスキーマは本 changelog に含まれません。スキーマ準備（raw_prices, raw_financials, prices_daily, features, ai_scores, positions, market_calendar, raw_news 等）は導入手順に従ってください。
- J-Quants の利用には `JQUANTS_REFRESH_TOKEN` の設定が必須です（`Settings.jquants_refresh_token` が未設定だと ValueError を送出します）。
- `KABUSYS_ENV` と `LOG_LEVEL` は有効な値であるか検証されます。無効値はエラーになります。

---

今後の予定（例）
- execution 層での kabuステーション連携（注文送信 / 約定管理）
- monitoring / alerting 機能の実装（Slack 通知自動化）
- AI スコア生成パイプラインの統合と学習モジュールの追加
- テストカバレッジの拡充と CI 導入

（以上）