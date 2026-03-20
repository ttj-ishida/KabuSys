CHANGELOG
=========

すべての注目すべき変更はここに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

（現在のところ未リリースの変更はありません）

0.1.0 — 2026-03-20
------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージエントリポイントを追加
    - src/kabusys/__init__.py: バージョン定義と主要サブパッケージの公開（data, strategy, execution, monitoring）
  - 環境設定管理
    - src/kabusys/config.py
      - .env/.env.local をプロジェクトルートから自動読み込み（.git または pyproject.toml を探索）
      - export KEY=val 形式やクォート付き値、インラインコメント等に対応した堅牢なパース実装
      - OS 環境変数を保護する protected オプション、.env.local による上書きサポート
      - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
      - 必須設定取得ヘルパーとバリデーション（KABUSYS_ENV / LOG_LEVEL 等）
      - 主要環境変数名（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH）
  - J-Quants API クライアント
    - src/kabusys/data/jquants_client.py
      - 固定間隔レートリミッタ（120 req/min）
      - リトライ（指数バックオフ、最大 3 回）、429 の場合は Retry-After を優先
      - 401 受信時はリフレッシュトークンで自動的にトークンを更新して 1 回再試行
      - ページネーション対応の fetch_ 関数群（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）
      - DuckDB への冪等保存（save_daily_quotes, save_financial_statements, save_market_calendar）を実装（ON CONFLICT / DO UPDATE を使用）
      - トークンキャッシュ（モジュールレベル）と get_id_token 実装
      - レスポンスの fetched_at を UTC で記録（ルックアヘッドバイアス対策）
      - 型変換ユーティリティ（_to_float, _to_int）
  - ニュース収集モジュール
    - src/kabusys/data/news_collector.py
      - RSS フィード収集と raw_news への冪等保存
      - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）
      - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を担保
      - defusedxml による XML パースで XML Bomb 等の防御
      - HTTP レスポンスサイズ制限（MAX_RESPONSE_BYTES=10MB）など SSRF/DoS 緩和策
      - デフォルト RSS ソース（Yahoo Finance）を定義
      - バルク INSERT のチャンク処理によるパフォーマンス配慮
  - リサーチ（因子計算・探索）
    - src/kabusys/research/factor_research.py
      - Momentum（1M/3M/6Mリターン、MA200乖離）、Volatility（20日ATR、ATR/終値）、Value（PER/ROE）、Liquidity（20日平均売買代金、出来高比率）を DuckDB ベースで計算
      - データ欠損時の安全な None 処理やウィンドウ最小行数チェックを実装
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算（複数ホライズン、カレンダーバッファでスキャン領域を限定）
      - スピアマン IC 計算（rank を内部実装、同順位は平均ランク）
      - ファクターの統計サマリー（count/mean/std/min/max/median）
    - research パッケージの公開 API を整備
  - 戦略（特徴量作成・シグナル生成）
    - src/kabusys/strategy/feature_engineering.py
      - research で計算した生ファクターをマージ、ユニバースフィルタ（最低株価/最低売買代金）を適用
      - 指定列の Z スコア正規化（zscore_normalize を利用）、±3 でクリップ
      - DuckDB の features テーブルへ日付単位での置換（DELETE + INSERT、トランザクション）
      - ルックアヘッドバイアス防止の設計
    - src/kabusys/strategy/signal_generator.py
      - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出
      - 最終スコア final_score を重み付き和で計算（デフォルト重みを定義、ユーザ重みの検証と正規化を実装）
      - Bear レジーム（AI の regime_score による平均が負）では BUY シグナル抑制
      - BUY（threshold ベース）および SELL（ストップロス、スコア低下）条件を実装
      - positions が存在する銘柄のエグジット判定と、features が欠けている場合の扱い（欠損時は中立/score=0扱いなど）
      - signals テーブルへ日付単位で置換（トランザクション）
  - 公開 API の統合
    - src/kabusys/strategy/__init__.py で build_features / generate_signals を公開
  - その他
    - DuckDB を用いた分析ワークフローを前提にした実装（外部 heavy 依存を避ける設計）
    - ロギングを各モジュールに導入し処理の可観測性を確保

Fixed
- ルックアヘッドバイアスへの配慮を各所で実装
  - データ取得タイムスタンプ（fetched_at）を UTC で記録
  - シグナル/ファクター計算は target_date 時点のデータのみ参照するよう設計
- データ保存時の冪等性強化
  - raw_* / market_calendar / raw_financials の INSERT を ON CONFLICT DO UPDATE で実装
  - raw データの PK 欠損行をスキップしてログ出力
- 環境変数読み込みの堅牢化
  - export 構文やクォート・エスケープ、インラインコメント対応を追加
  - OS 環境変数を保護するため .env の上書き制御と protected キーセットを導入
- API リクエストの堅牢化
  - transient エラーでのリトライ、429 の Retry-After 尊重、401 の一回のみのトークンリフレッシュ
- 型変換ユーティリティの改善
  - _to_int/_to_float が不正な入力を安全に None に変換

Security
- news_collector で defusedxml を使用して XML の脆弱性を緩和
- RSS URL 正規化とトラッキングパラメータ除去により冪等性とプライバシーに配慮
- HTTP レスポンス最大バイト数を制限してメモリ DoS を抑制
- news_collector における SSRF 阻止のためスキームチェック等（実装方針として明記）

Known issues / Limitations
- 一部エグジット条件（トレーリングストップ、時間決済）は未実装（signal_generator に注記あり）。これらは positions テーブルに peak_price / entry_date が必要。
- execution（発注）層は空のパッケージ/モジュールとして残されており、本リリースでは発注 API への直接依存はない（戦略層は signals テーブルまで書き込むのみ）。
- news_collector のデフォルト RSS は限定的（現状は Yahoo Finance のビジネスカテゴリのみ）。複数ソース設定は可能だが拡張が必要。
- 外部解析ライブラリ（pandas など）には依存せず実装しているため、大量データ・高度な統計処理では最適化の余地あり。

Migration notes
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- デフォルト DB パス:
  - DUCKDB_PATH = data/kabusys.duckdb
  - SQLITE_PATH = data/monitoring.db
- 自動 .env 読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかでなければなりません。
- LOG_LEVEL は "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL" のいずれかでなければなりません。

Acknowledgements
- 本リリースはベータ段階の初期実装です。運用前にテスト環境での検証、特に API レート制限やデータ欠損/トランザクションエラーの挙動確認を推奨します。