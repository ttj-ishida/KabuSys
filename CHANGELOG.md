# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
このファイルはコードベースから推測して作成した変更履歴です。

全般:
- パッケージバージョンは src/kabusys/__init__.py の __version__ に従っています。

[0.1.0] - 2026-03-20
--------------------

Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring（src/kabusys/__init__.py）

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ロード機能を実装
    - プロジェクトルートを .git または pyproject.toml から探索して自動的に .env/.env.local を読み込む
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
    - .env.local は .env の上書き（override）として扱い、OS 環境変数は保護（protected）される
  - .env 行パーサの実装
    - export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメント処理などを考慮
  - Settings クラスを提供し、必要な環境変数をプロパティ経由で取得（J-Quants トークン、kabu API、Slack、DB パス、env/log_level 判定等）
  - 入力検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）とユーティリティプロパティ（is_live/is_paper/is_dev）

- データ取得・保存機能（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
    - レート制限（120 req/min）を固定間隔スロットリングで遵守する RateLimiter を実装
    - 再試行ロジック（最大 3 回、指数バックオフ、408/429/5xx を対象）
    - 401 受信時にリフレッシュトークンから id_token を再取得して1回リトライ
    - id_token のモジュールレベルキャッシュを実装（ページネーション間で共有）
    - JSON パースおよびエラーラップ
  - DuckDB への冪等保存ユーティリティを実装
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - ON CONFLICT を利用した upsert（重複時は更新）
    - PK 欠損行のスキップ、変換ユーティリティ（_to_float/_to_int）
    - fetched_at を UTC ISO8601 で記録（look-ahead bias を可追跡にする設計）
  - 設計注記: API レート・リトライ・トークン再取得を考慮した堅牢な実装

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事収集ワークフローを設計（RSS 取得、前処理、DB 保存、銘柄紐付け）
  - 安全対策を組み込んだ実装方針
    - defusedxml を利用して XML 関連攻撃を緩和
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）を設定しメモリ DoS を防止
    - URL 正規化（トラッキングパラメータ除去、スキームホスト小文字化、フラグメント削除、クエリソート）
    - 記事 ID は URL 正規化後の SHA-256 等で冪等性を確保する方針（コメントに明記）
  - デフォルト RSS ソース定義（Yahoo Finance ビジネスカテゴリ等）
  - バルク挿入のチャンク化等パフォーマンス配慮

- 研究用ファクター計算（src/kabusys/research/*）
  - calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials を参照）
    - Momentum: mom_1m / mom_3m / mom_6m、ma200_dev（200 日移動平均乖離）
    - Volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率
    - Value: per, roe（target_date 以前の最新財務データを取得）
    - SQL を中心とした高性能な実装（DuckDB の window 関数を活用）
  - 解析ユーティリティを追加
    - calc_forward_returns: 指定ホライズン（既定 [1,5,21]）の将来リターンを計算
    - calc_ic: スピアマンのランク相関（IC）を計算。サンプル不足時は None を返す
    - factor_summary: count/mean/std/min/max/median を算出
    - rank: 同順位の平均ランク処理（round で丸めて tie を検出）

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - research の生ファクターを取り込み、ユニバースフィルタ・正規化・クリッピングを行い features テーブルへ UPSERT
    - ユニバースフィルタ: 最低株価（300 円）・20 日平均売買代金 >= 5 億円 を適用
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）と ±3 でクリップ
    - 日付単位の置換（DELETE + bulk INSERT）で冪等性と原子性を確保
    - 価格参照は target_date 以前の最新価格を使用（ルックアヘッド回避・休場日対応）

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合し final_score を計算、BUY / SELL シグナルを生成して signals テーブルへ保存
    - コンポーネントスコア: momentum/value/volatility/liquidity/news（news は AI スコアをシグモイド変換）
    - 重み付け合算（デフォルト重みを定義）。ユーザ指定 weights を受け付け、検証・スケーリングを行う
    - Bear レジーム判定: ai_scores の regime_score 平均が負なら BUY を抑制（サンプル数閾値あり）
    - BUY 閾値（デフォルト 0.60）以上を BUY、SELL はストップロス（-8%）やスコア低下で判定
    - SELL が優先され、BUY から除外してランクを再付番
    - 日付単位の置換で signals を冪等に更新（トランザクション + bulk insert）
  - ロバストネス考慮
    - 欠損コンポーネントは中立値 0.5 で補完（不当な降格を回避）
    - 無効な weights の警告ログ出力

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Deprecated
- （初版のため該当なし）

Security
- ニュース収集で defusedxml を使用し XML 攻撃に対処
- RSS レスポンスのサイズ上限、URL 正規化、トラッキングパラメータ排除等により外部データ取り込みの安全性を向上
- J-Quants クライアントは認証トークンの安全な再取得とレート制御、リトライポリシーを備える

Notes / Known limitations
- Signal モジュール内でコメントされているいくつかのエグジット条件は未実装（例：トレーリングストップ、時間決済）。これらは positions テーブルに peak_price / entry_date 等の追加が必要。
- news_collector の一部実装（記事 ID 生成や SSRF 除去の詳細）は設計方針としてコメントで明記されているが、ファイル末尾までコードが提示されていないため、細部実装状況は要確認。
- DuckDB を主要な依存として使用（外部ライブラリへの依存を抑えた実装）。pandas など高レベルライブラリには依存していない設計。
- J-Quants のエンドポイントレスポンスのスキーマやエラー挙動に依存するため、実運用時は API 仕様変更に注意が必要。

以上。必要であれば各機能ごとにより詳細な変更点（関数単位のチェンジログや実装上の注意点）を追記します。