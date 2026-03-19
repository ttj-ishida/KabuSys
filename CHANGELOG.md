# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従って記載しています。  
本ファイルはコードベースから推測される機能・振る舞いをもとに作成した初回リリース向けの変更履歴です。

## [Unreleased]

- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-03-19

初回公開リリース。日本株自動売買システム「KabuSys」ライブラリの基本機能を実装しました。下記はコードベースから推測される主要な追加点・設計方針・既知制約です。

### 追加 (Added)
- パッケージ基礎
  - パッケージエントリポイント `kabusys` を追加。バージョンは `0.1.0`。
  - サブモジュール公開: data, strategy, execution, monitoring（execution は空の初期モジュール）。

- 設定管理 (kabusys.config)
  - 環境変数/`.env` ファイル自動読み込み機能を実装。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）により CWD に依存しない自動読込を実現。
    - 読込優先順位: OS 環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能（テスト等で利用）。
  - .env パーサーは export 形式、クォート、エスケープ、インラインコメント等に対応。
  - 必須環境変数取得時に未設定なら明示的に例外を投げる `_require` を提供。
  - 設定アクセス用 `Settings` クラスを提供（J-Quants トークン、kabu API 設定、Slack、データベースパス、環境種別・ログレベル等）。

- データ取得・保存 (kabusys.data)
  - J-Quants API クライアント（jquants_client）を実装。
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（RateLimiter）。
    - 再試行（指数バックオフ、最大 3 回）実装。リトライ対象の HTTP ステータスやネットワークエラーを考慮。
    - 401 を検知した場合はリフレッシュトークンから ID トークンを再取得して 1 回リトライ。
    - ページネーション対応の fetch 系関数: 日足（fetch_daily_quotes）、財務データ（fetch_financial_statements）、マーケットカレンダー（fetch_market_calendar）。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。冪等性のため ON CONFLICT DO UPDATE を使用。
    - データ変換ユーティリティ `_to_float` / `_to_int` を提供し不正値の扱いを明確化。
    - 取得時の fetched_at を UTC 形式で記録し、Look-ahead バイアスのトレースを可能に。

  - ニュース収集モジュール（news_collector）を実装（RSS ベース）。
    - RSS 取得、記事正規化、トラッキングパラメータ除去、記事ID生成（URL 正規化後の SHA-256 先頭 32 文字）等を実装。
    - セキュリティ対策: defusedxml を使用して XML 攻撃を緩和、URL スキーム検査（HTTP/HTTPS のみ許可）、受信サイズ上限（10 MB）でメモリ DoS を防止。
    - DB 挿入はバルクかつチャンクサイズ制御（デフォルト 1000 件）で実行。INSERT RETURNING を想定した冪等操作。
    - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを登録。

- リサーチ機能（kabusys.research）
  - ファクター計算モジュール（factor_research）を実装。
    - Momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均乖離）。データ不足時は None を返す。
    - Volatility: 20 日 ATR / atr_pct、20 日平均売買代金、volume_ratio を算出。true_range の NULL 伝播制御で集計精度を担保。
    - Value: PER（EPS が 0 または欠損なら None）、ROE（raw_financials から取得）。
    - 全関数は prices_daily / raw_financials のみを参照し、外部 API に依存しない設計。
  - 特徴量探索（feature_exploration）を実装。
    - 将来リターン計算（calc_forward_returns）：指定ホライズン（デフォルト [1,5,21]）の将来終値リターンを計算。
    - IC（Information Coefficient）計算（calc_ic）：ファクターと将来リターンのスピアマンランク相関を計算（有効データが 3 件未満なら None）。
    - factor_summary（基本統計量）と rank（同順位は平均ランク）を提供。pandas に依存しない純 Python 実装。

- 戦略（kabusys.strategy）
  - 特徴量エンジニアリング（feature_engineering.build_features）
    - research モジュールの生ファクターを取得し、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化し ±3 でクリップ。
    - 日付単位で features テーブルへ置換（トランザクション + バルク挿入で原子性を保証）。
  - シグナル生成（signal_generator.generate_signals）
    - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネントはシグモイド変換や逆スケール等で [0,1] に整形。欠損は中立 0.5 で補完。
    - デフォルト重みを定義（momentum 0.40 / value 0.20 / volatility 0.15 / liquidity 0.15 / news 0.10）、ユーザ重みを受け付け合計を 1.0 に再スケール。
    - Bear レジーム判定（AI の regime_score の平均が負の場合）で BUY シグナルを抑止。
    - BUY シグナル閾値デフォルト 0.60。
    - エグジット条件（SELL）としてストップロス（-8%）およびスコア低下を実装。既存ポジションに対して SELL シグナルを生成。
    - signals テーブルへ日付単位の置換（トランザクション + バルク挿入）。
    - エグジット判定の一部（トレーリングストップ、時間決済）は未実装（positions テーブルに peak_price / entry_date が必要）。

### 変更 (Changed)
- 初期リリースのため過去バージョンからの変更はありません（新規実装）。

### 修正 (Fixed)
- 初回リリースのため修正履歴はありません。

### セキュリティ (Security)
- RSS パーサで defusedxml を利用、XML 関連攻撃軽減。
- ニュース URL 正規化によりトラッキングパラメータを除去、SSRF 対策としてスキームチェックを想定。
- J-Quants クライアントでのトークン自動リフレッシュ実装により認証エラーの安全な復旧を実現。

### 仕様メモ / 設計上の注意
- DuckDB に依存した設計。主要に参照/更新するテーブル:
  - prices_daily, raw_prices, raw_financials, features, signals, ai_scores, positions, market_calendar
- ルックアヘッドバイアス対策として「target_date 時点の利用可能データのみ」を原則に実装。
- 外部ライブラリへの依存を最小化（research モジュール等は標準ライブラリのみを使用）。
- エラー発生時はトランザクションのロールバックを試み、失敗した場合にログ出力。
- ニュース記事の ID は URL 正規化＋ハッシュで生成し冪等性を保証。

### 既知の制限・未実装の機能 (Known issues / TODO)
- ポジション管理の一部（ピーク価格保持、entry_date）やトレーリングストップ、時間決済は未実装であり positions テーブルの拡張が必要。
- execution 層 (発注処理) は空実装または未実装のため、signals テーブルへの書き込みから実際の発注に至るパスは別実装が必要。
- 一部入力の検証やエッジケース処理（極端な欠損データや特異な市場状況）については追加の堅牢化が望まれる。

---

参照: パッケージ内の docstring と関数実装（modules: config, data.jquants_client, data.news_collector, research.*, strategy.*）をもとに作成。実際の利用時には README / ドキュメントおよびマイグレーション方針に従って運用してください。