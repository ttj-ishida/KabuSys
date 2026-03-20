CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
現在のバージョン: 0.1.0

[Unreleased]
-------------

（現状のコードベースは初回リリース相当のため、未リリース差分はありません。）

[0.1.0] - 2026-03-20
-------------------

Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys、バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - export 指定: data, strategy, execution, monitoring を __all__ で公開。

- 環境変数/設定管理（src/kabusys/config.py）
  - .env ファイル自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化をサポート（テスト用途）。
  - .env 行パーサを実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメントの扱い（クォートあり/なしでの差異）
  - .env 読み込み時の override/protected 機能を実装（OS の既存環境変数を保護）。
  - Settings クラスを導入（settings インスタンスをエクスポート）。
    - J-Quants / kabu API / Slack / DB パス等のプロパティを提供。
    - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）。
    - デフォルト値（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等）を提供。

- Data 層（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。
    - レート制限制御（_RateLimiter、120 req/min 固定間隔スロットリング）。
    - リトライロジック（指数バックオフ、最大 3 回、HTTP 408/429 と >=500 を再試行対象）。
    - 401 受信時はトークンを自動リフレッシュして 1 回リトライ（無限再帰防止）。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB へ保存する save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）。
      - 保存は冪等（ON CONFLICT DO UPDATE / DO NOTHING を利用）。
      - レコードの型変換ユーティリティ (_to_float, _to_int) を実装。
    - ページネーション間で使う ID トークンのモジュールキャッシュを実装。

- Data 層（ニュース収集: src/kabusys/data/news_collector.py）
  - RSS フィードから記事収集して raw_news へ保存する機能を実装（デフォルトに Yahoo Finance の RSS を含む）。
  - セキュリティ対策:
    - defusedxml を利用して XML 関連の攻撃を軽減。
    - 受信最大バイト数（MAX_RESPONSE_BYTES = 10MB）で DoS を抑制。
    - URL 正規化実装（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）。
    - 記事ID を URL 正規化後の SHA-256（先頭32文字）で生成して冪等性を確保。
  - DB へのバルク挿入（チャンク化）とトランザクションで効率的に保存。

- Research 層
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）
    - Value（per, roe：raw_financials と prices_daily を結合）
    - DuckDB SQL を中心に実装し、営業日欠損やウィンドウ不足時の None ハンドリング
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）：LEAD を用いた一括取得、horizons 検証
    - IC 計算（calc_ic）：Spearman（ランク相関）を実装（ties は平均ランク）
    - factor_summary：count/mean/std/min/max/median を計算
    - rank ユーティリティ：同順位は平均ランク（round(v,12) による丸めで ties を安定化）
  - 研究用 API をまとめてエクスポート（src/kabusys/research/__init__.py）。

- Strategy 層
  - 特徴量作成（src/kabusys/strategy/feature_engineering.py）
    - research の生ファクターを取得して統合・ユニバースフィルタ・正規化を行い features テーブルへ日付単位で置換（冪等性）。
    - ユニバースフィルタ:
      - 最低株価 _MIN_PRICE = 300 円
      - 20日平均売買代金 _MIN_TURNOVER = 5e8（5 億円）
    - Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップ、トランザクションを使った原子的な差し替え。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合して final_score を計算し signals テーブルへ保存（冪等）。
    - コンポーネント: momentum, value, volatility, liquidity, news（AI スコア）。
    - デフォルト重みとしきい値（weights デフォルト、threshold=0.60）。
    - AI レジームスコアの平均が負であれば Bear レジームと判定して BUY を抑制（サンプル閾値あり）。
    - SELL 条件実装:
      - ストップロス: 終値/avg_price - 1 < -8%
      - スコア低下: final_score < threshold
      - （未実装のエグジットロジックはコード内に明記：トレーリングストップ・時間決済 等）
    - 保有銘柄の features 欠損時の扱い（保有銘柄が features に無ければ final_score=0 として SELL 判定）。
    - DB 書き込みは日付単位で DELETE→INSERT をトランザクションで行い原子性を保証。
  - strategy API をまとめてエクスポート（src/kabusys/strategy/__init__.py）。

Changed
- （初回リリースのため過去からの変更はなし）

Fixed
- （初回リリースのため修正履歴はなし）

Security
- news_collector で defusedxml を使用、受信サイズ制限、URL 正規化等の対策を実装。
- jquants_client の HTTP レスポンス処理において JSON デコード失敗時の例外通知や Retry-After ヘッダ対応を実装。

Notes / Known limitations
- 一部のエグジット条件（トレーリングストップ、時間決済）は未実装。positions テーブルに peak_price / entry_date 等の追加が必要。
- news_collector 内の SSRF/IP フィルタや外部接続の厳格な検証はコードの設計で考慮されているが、運用時のネットワークポリシーやホワイトリスト設定を併用することを推奨。
- DuckDB のスキーマ（テーブル名やカラム）への依存が強いため、既存の DB スキーマが想定と異なる場合はマイグレーションが必要。
- Settings の必須環境変数が未設定の場合は ValueError を送出するため、デプロイ前に必須環境変数の設定が必要:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - （オプション）KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL

参考ドキュメント（コード内参照）
- StrategyModel.md（戦略仕様）
- DataPlatform.md（データ設計）
- Research 用ドキュメント（research ディレクトリ内の設計方針）

Repository 管理者向け補足
- 自動 .env 読み込みはパッケージ配布後も __file__ を起点にプロジェクトルートを探索する実装になっているため、CI/コンテナ環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して明示的に制御することを推奨します。
- jquants_client のトークン自動リフレッシュは 401 時に 1 回のみ行われ、無限ループにならない設計です。トークン周りの障害が発生した場合はログを確認してください。

--- End of CHANGELOG.md ---