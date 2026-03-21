Keep a Changelog
=================

すべての重要な変更をここに記録します。  
このファイルは「Keep a Changelog」フォーマットに準拠します。

フォーマット:
- 年-月-日形式の日付を使用しています。
- バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に対応します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-21

初回公開リリース。以下の機能群を実装しました。

### Added
- パッケージ基礎
  - パッケージルートと公開 API の定義（kabusys.__init__）。
  - strategy、execution、data、research、monitoring などのモジュール構成。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 自動ロードの優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートを .git または pyproject.toml から探索（__file__ 起点）。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env の高度なパース実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のエスケープ対応、インラインコメント処理。
  - 必須環境変数取得時の検証（_require）と設定値プロパティを提供（J-Quants, kabu ステーション, Slack, DB パス, ログレベル, 環境種別など）。
  - 設定値の妥当性チェック（KABUSYS_ENV / LOG_LEVEL の許容値検査）。

- データ取得・保存: J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しラッパーを実装（JSON パース、ページネーション対応）。
  - レート制限器（固定間隔スロットリング）を実装して 120 req/min を順守。
  - 再試行ロジック（指数バックオフ、最大 3 回）を実装。429/408/5xx を再試行対象に含む。
  - 401 受信時のリフレッシュトークンによる自動 ID トークン再取得を実装（1 回のリフレッシュでリトライ）。
  - ページネーション間で利用するモジュールレベルのトークンキャッシュを実装。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等保存を行う。
  - 型変換ユーティリティ（_to_float / _to_int）を実装し、不正データの堅牢な取り扱いを提供。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事収集パイプラインを実装。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリのソート）機能を実装。
  - セキュリティ対策: defusedxml を利用した XML パース、受信サイズ上限（MAX_RESPONSE_BYTES）、HTTP/HTTPS スキーム制限、SSRF を意識した実装方針。
  - 記事 ID は正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を確保。
  - raw_news へのバルク保存を想定したチャンク処理実装（INSERT チャンクサイズ制御）。

- リサーチ（研究）モジュール（src/kabusys/research/*）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）計算を実装（DuckDB SQL ベース）。
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）計算を実装。true_range の NULL 伝播を明示的に制御。
    - Value（per, roe）計算を実装。raw_financials から target_date 以前の最新財務データを取得して算出。
    - スキャン範囲・ウィンドウ幅は実務に合わせて定数化（例: ma200=200, atr=20 等）。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns（任意ホライズン、1/5/21 日がデフォルト）を実装。1 クエリでまとめて取得。
    - スピアマンランク相関（IC）calc_ic を実装（ランク付け、同順位の平均ランク処理）。
    - rank、factor_summary（count/mean/std/min/max/median）を実装。
  - すべて外部ライブラリに依存せず、DuckDB 接続を受け取る設計。

- 特徴量構築（src/kabusys/strategy/feature_engineering.py）
  - research モジュールで計算した raw ファクターをマージして features テーブルへ保存する処理を提供（build_features）。
  - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を実装。
  - 指定カラムに対する Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）と ±3 でのクリップを実施。
  - 日付単位での置換（DELETE + bulk INSERT）により冪等性・原子性を保証。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合し final_score を計算して売買シグナルを生成（generate_signals）。
  - コンポーネントスコア（momentum / value / volatility / liquidity / news）の計算ロジックを実装（シグモイド変換、PER ベースの value スケーリング等）。
  - デフォルト重み・閾値を実装（デフォルト閾値: 0.60、デフォルト重みは StrategyModel.md の値に基づく）。
  - user から渡された weights の検証・補完・リスケール機構を実装（未定義キー・負値・非数は無視）。
  - Bear レジーム判定（ai_scores の regime_score 平均が負の場合。ただしサンプル数が最低 3 件未満の場合は Bear 判定を抑制）を実装し、Bear 時は BUY を抑制。
  - SELL（エグジット）判定ロジックを実装:
    - ストップロス: 終値 / 平均取得価格 - 1 < -8%（優先）
    - スコア低下: final_score が閾値未満
    - 価格欠損時は SELL 判定をスキップして誤クローズを防止
  - BUY/SELL の日付単位置換（DELETE + bulk INSERT）で signals テーブルへ書き込み、冪等性確保。
  - BUY と SELL の競合解決（SELL を優先し BUY から除外、ランクの再付与）を実装。

- データ統合 / ユーティリティ
  - DuckDB を前提とした SQL 実装により、データ取得・集約・バルク挿入が可能。
  - ロギング（logger）を各モジュールへ導入し運用時の可観測性を低コストで提供。

### Known / Not Implemented
- エグジット条件（signal_generator）で触れられている未実装項目:
  - トレーリングストップ（peak_price / entry_date が positions テーブルへ格納されれば実装可能）
  - 時間決済（保有 60 営業日超過など）
- Value ファクターにおける PBR・配当利回りは現バージョンでは未実装。
- news_collector / raw_news → news_symbols の紐付け処理（記事と銘柄の紐付けロジック）は本実装で明示的には実装していない（将来追加予定）。
- 一部の挙動は DuckDB のテーブルスキーマに依存（prices_daily, raw_financials, features, ai_scores, positions, signals, raw_prices, raw_financials, market_calendar 等）。スキーマが適切に用意されている前提。

### Security
- XML パースに defusedxml を使用し XML ベース攻撃（XML Bomb 等）を抑止。
- RSS / HTTP 取得時に受信サイズ上限を設けメモリ DoS を軽減。
- ニュースの URL 正規化によりトラッキングパラメータ除去と一貫性を担保。

### Notes / Implementation Decisions
- ルックアヘッドバイアス回避: features / signals / financials 等の計算は target_date 時点で利用可能なデータのみを使用する方針を徹底。
- 冪等性: データ保存は基本的に ON CONFLICT（または日付単位での DELETE + INSERT）で同一日付の再実行に耐える。
- ネットワーク呼び出しはモジュールレベルのトークンキャッシュとレート制御で安定化。
- 外部依存（pandas 等）を避け、標準ライブラリ + duckdb のみで記述。

## バージョン履歴
- 0.1.0 - 初回リリース（2026-03-21）

---

貢献・修正提案歓迎。README / ドキュメントに記載された環境変数例（.env.example）と DuckDB テーブルスキーマを参照してセットアップしてください。