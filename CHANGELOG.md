CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠します。  
このファイルはコードベースの内容から推測して作成した初期リリースの変更履歴です。

フォーマットルール:
- 重大な変更（破壊的変更）は Breaking Changes として明示します。
- 日付はリリース日を示します（推定：本ファイル作成日）。

[Unreleased]
------------

- （現時点では未リリースの変更はありません）

[0.1.0] - 2026-03-19
-------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - 高レベル概要: 日本株の自動売買・リサーチ用ユーティリティ群を提供。
- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - 複雑な .env 行のパース対応（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ処理）。
  - 環境変数の保護（OS 環境変数を保護する protected set）と override ロジック。
  - Settings クラスによりアプリケーション設定を集中管理（J-Quants トークン、kabu API、Slack、DB パス、環境モード、ログレベル判定等）。
  - env / log_level のバリデーション（許容値セットのチェック）。
- データ取得・保存（kabusys.data）
  - J-Quants API クライアント (jquants_client)
    - レート制限制御（_RateLimiter、120 req/min のスロットリング）。
    - リトライ付き HTTP 呼び出し（指数バックオフ、最大試行回数、408/429/5xx をリトライ対象）。
    - 401 受信時の自動トークンリフレッシュ（1 回まで）とモジュールレベルの ID トークンキャッシュ。
    - ページネーション対応の fetch_* API（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - DuckDB への冪等保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）— ON CONFLICT を用いて重複更新を防止。
    - 型変換ユーティリティ (_to_float / _to_int) を実装。
  - ニュース収集モジュール (news_collector)
    - RSS フィード収集の実装方針（デフォルト RSS ソース含む）。
    - 記事 ID の冪等性確保（URL 正規化 + SHA-256 ベースのハッシュ）やトラッキングパラメータ除去。
    - XML パースに defusedxml を利用しセキュリティ対策を実装。
    - 受信サイズ上限や SSRF 対策方針などの設計方針を導入。
- リサーチ・ファクター計算（kabusys.research）
  - ファクター計算モジュール (factor_research)
    - Momentum（1M/3M/6M リターン、ma200 乖離率）、Volatility（20 日 ATR、相対 ATR、出来高比率、平均売買代金）、Value（PER, ROE）を DuckDB の prices_daily / raw_financials を参照して計算。
    - 営業日ベースの窓や走査バッファを考慮した SQL 実装。
  - 特徴量探索 (feature_exploration)
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応、入力検証）。
    - IC（Information Coefficient）計算（calc_ic、Spearman の ρ 相当のランク相関）。
    - ランク化ユーティリティ（rank）と統計サマリー（factor_summary）。
  - 研究用ユーティリティのエクスポートを整備（__init__）。
- 戦略層（kabusys.strategy）
  - 特徴量エンジニアリング (feature_engineering)
    - research の生ファクターを統合・ユニバースフィルタリング（最低株価、平均売買代金）・Z スコア正規化・±3 クリップして features テーブルへ UPSERT（トランザクションによる日付単位置換）。
    - build_features(conn, target_date) を公開。
  - シグナル生成 (signal_generator)
    - features と ai_scores を統合して最終スコア final_score を計算（momentum/value/volatility/liquidity/news コンポーネント、デフォルト重みを実装）。
    - Sigmoid 変換、欠損コンポーネントの中立補完（0.5）、重みの合成と再スケール処理。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合、最小サンプル検証あり）による BUY 抑制。
    - BUY（閾値デフォルト 0.60）および SELL（ストップロス -8% とスコア低下）ロジックの実装。保有ポジション判定は positions テーブル参照。
    - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入）。
    - generate_signals(conn, target_date, threshold=..., weights=...) を公開。
- パッケージエクスポート
  - kabusys.__init__ にてバージョン管理（__version__ = "0.1.0"）と公開モジュールリストを設定。

Changed
- n/a（初回リリースのため変更履歴無し）

Fixed
- n/a（初回リリースのため修正履歴無し）

Deprecated
- n/a

Removed
- n/a

Security
- ニュース RSS の XML パースに defusedxml を採用し XML Bomb 等の攻撃を防止。
- news_collector での URL 正規化・スキーム検査・受信バイト上限等により SSRF やメモリ DoS に対する対策を明示。
- J-Quants クライアントはトークン処理とエラーハンドリングを慎重に実装し、不要な再帰的リフレッシュを防止。

Known limitations / Notes
- signal_generator の未実装項目:
  - トレーリングストップ（直近最高値からの閾値）や時間決済（保有期間による自動決済）は未実装。positions テーブルに peak_price / entry_date が必要。
- calc_forward_returns は営業日欠損時の取り扱いを SQL の LEAD で実装しており、ホライズンに対応するデータがない場合は None を返す。
- 一部の機能は duckdb と defusedxml に依存します（標準ライブラリ以外の依存に注意）。
- .env パーサは多くのケースを扱うが、極端に非標準な .env 書式は想定外となる可能性あり。
- J-Quants API のレート/再試行ポリシーは実装済みだが、実運用でのパフォーマンス調整や回線・API 側の挙動に応じたチューニングが必要。

Credits
- 本 CHANGELOG はコード内の docstring、関数名、コメント、実装ロジックから推測して作成しました。実際のリリースノートはプロジェクトの公式履歴に合わせて調整してください。