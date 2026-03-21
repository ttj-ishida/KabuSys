Changelog
=========

すべての注目すべき変更をここに記載します。  
このファイルは "Keep a Changelog" の形式に準拠しています。

[0.1.0] - 2026-03-21
-------------------

Added
- 初回リリース。日本株自動売買システム "KabuSys" の基礎機能を実装。
- パッケージ構造（kabusys）とバージョン定義を追加（src/kabusys/__init__.py）。
- 環境変数 / 設定管理（src/kabusys/config.py）:
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサ実装（export プレフィックス、クォート処理、インラインコメント対応など）。
  - Settings クラスでアプリ設定をプロパティとして提供（J-Quants トークン、kabu API、Slack トークン/チャンネル、DBパス、環境・ログレベルの検証など）。
  - 必須設定が未定義の場合は ValueError を送出。

- データ取得・保存（src/kabusys/data/）:
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）:
    - レート制限（120 req/min）の固定間隔スロットリング実装。
    - 冪等なページネーション対応の fetch_* 関数（daily_quotes / financial_statements / market_calendar）。
    - リトライ（指数バックオフ、最大3回）、特定ステータス（408/429/5xx）でリトライ、429 の Retry-After 優先。
    - 401 受信時はリフレッシュトークンで自動的にトークンを再取得して1回リトライ。
    - 取得時刻（fetched_at）を UTC ISO 形式で記録（ルックアヘッドバイアスのトレーサビリティ確保）。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）は ON CONFLICT を使って冪等に保存。
    - 型変換ユーティリティ（_to_float / _to_int）で入力整形。
  - ニュース収集モジュール（src/kabusys/data/news_collector.py）:
    - RSS 取得 → テキスト前処理 → raw_news へ冪等保存のワークフロー。
    - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保。
    - defusedxml を利用して XML 攻撃対策、HTTP スキーム検査で SSRF 対策、受信サイズ上限（10MB）でメモリ DoS を軽減。
    - トラッキングパラメータ除去、URL 正規化、バルク INSERT のチャンク処理などを実装。

- 研究・ファクター計算（src/kabusys/research/）:
  - factor_research.py:
    - Momentum（1M/3M/6M、MA200乖離）、Volatility（ATR20、相対ATR、出来高比率・20日平均売買代金）、Value（PER、ROE）を DuckDB の prices_daily / raw_financials を参照して計算。
    - ウィンドウサイズ／スキャン範囲考慮、データ不足時は None を返す安全設計。
  - feature_exploration.py:
    - 将来リターン計算（horizons デフォルト [1,5,21]、営業日ベース）、IC（Spearman の ρ）計算、ファクター統計サマリーを実装。
    - rank 関数は同順位を平均ランクで処理し、浮動小数点丸めで ties の誤判定を回避。
  - research パッケージの __all__ に主要ユーティリティを公開。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）:
  - research 側で計算した raw factor を取得してマージ、ユニバースフィルタ（価格 >= 300 円、20日平均売買代金 >= 5億円）を適用。
  - Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップ。
  - features テーブルへ日付単位の置換（DELETE → INSERT、トランザクションで原子性確保）。
  - 冪等な実行を想定（target_date のデータを置換）。

- シグナル生成（src/kabusys/strategy/signal_generator.py）:
  - features と ai_scores を統合してコンポーネントスコア（momentum / value / volatility / liquidity / news）を計算。
  - スコア変換関数（シグモイド）、欠損コンポーネントは中立値 0.5 で補完。
  - final_score を重み付き合算（デフォルト重みを実装、ユーザ指定 weights を検証・正規化）。
  - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）により BUY シグナルを抑制。
  - BUY（閾値 0.60）/ SELL（ストップロス -8% / final_score が閾値未満）を生成し、signals テーブルへ日付単位置換で保存。
  - 保有ポジション（positions テーブル）に対するエグジット判定を実装。未実装のエグジット条件（トレーリングストップ、時間決済）を明記。

Changed
- n/a（初回リリースのため変更履歴なし）。

Fixed
- n/a（初回リリースのため修正履歴なし）。

Deprecated
- n/a。

Removed
- n/a。

Security
- News collector で defusedxml を使用、RSS の受信サイズ上限や URL スキーム検査により XML Bomb / SSRF / メモリ DoS のリスクに配慮。
- J-Quants クライアントでリトライ制御、トークンリフレッシュの際の無限再帰防止フラグ（allow_refresh）を実装。

Notes / 制約・既知の問題
- positions テーブルに peak_price / entry_date 等がないため、トレーリングストップや時間決済の一部ロジックは未実装（signal_generator の docstring に注記あり）。
- research モジュールは外部依存を避け、標準ライブラリ + duckdb で動作する設計。pandas 等は依存しない。
- settings が要求する必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 未設定時は Settings の対応プロパティアクセスで ValueError が発生します。
- DuckDB / defusedxml 等のパッケージが必要（実行環境に応じてインストールしてください）。
- Python の型ヒント（| 記法等）を使用しているため、Python 3.10 以上を想定しています。

アップグレード / マイグレーションノート
- 本バージョンは初回リリースのため、移行は不要。新規導入時は .env.example を参照して必須環境変数を設定してください。
- 自動 .env ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

開発者向け
- 研究機能と実行（execution）層は明確に分離されています。strategy 層は発注 API への直接アクセスを持たず、signals テーブルに出力することで execution 層が発注を担当する想定です。
- ログレベルや環境（development / paper_trading / live）は Settings.env, Settings.log_level で検証され、不正値はエラーとなります。

Contributors
- 初回実装: コードベースから推測してドキュメント作成。

--- End of CHANGELOG ---