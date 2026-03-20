Keep a Changelog
=================

このファイルは Keep a Changelog の形式に従っており、セマンティックバージョニングを使用します。
https://keepachangelog.com/ja/1.0.0/

0.1.0 - 2026-03-20
------------------

初回公開リリース。本リポジトリの主要機能・モジュールを実装しています。

Added
- パッケージ初期化
  - kabusys パッケージのバージョン定義: __version__ = "0.1.0"
  - パブリック API のエクスポート設定 (__all__) を整備（data, strategy, execution, monitoring）。

- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途）。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索して行うため、CWD に依存しない。
  - .env パーサーを実装（コメント・export 形式・クォート内のエスケープ処理・インラインコメント取り扱い対応）。
  - .env ファイル読み込み時の保護キー（OS 環境変数が上書きされないようにする）と override オプションを実装。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能に。
    - J-Quants / kabu ステーション / Slack / DB パス等の設定をカプセル化。
    - KABUSYS_ENV（development / paper_trading / live）および LOG_LEVEL（DEBUG/INFO/...）のバリデーションを実装。
    - 必須 env が未設定の場合は _require() により ValueError を送出。

- Data 層（kabusys.data）
  - J-Quants API クライアント (kabusys.data.jquants_client)
    - 固定間隔の RateLimiter 実装（120 req/min を遵守）。
    - HTTP リクエストラッパーでリトライ（指数バックオフ、最大 3 回）、特定ステータス(408/429/5xx)での再試行、429 の Retry-After 対応。
    - 401 受信時は自動でリフレッシュトークンから ID トークンを再取得して 1 回リトライする仕組み。
    - ページネーション対応のデータ取得（fetch_daily_quotes / fetch_financial_statements）。
    - DuckDB への冪等的保存関数を提供（save_daily_quotes / save_financial_statements / save_market_calendar）。ON CONFLICT による更新で重複を排除。
    - データ変換ユーティリティ (_to_float / _to_int) を実装し、入力の安全なパースを行う。
    - データ取得時に fetched_at を UTC ISO8601 で記録し、Look-ahead Bias のトレーサビリティを保持。
  - ニュース収集モジュール (kabusys.data.news_collector)
    - RSS フィード収集ワークフローを実装（既定ソースに Yahoo Finance を含む）。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）実装。
    - セキュリティ対策: defusedxml の使用（XML Bomb 対策）、受信バイト上限（10MB）、HTTP/HTTPS スキームのみ許可、IP/SSRF への配慮。
    - 挿入はバルクでチャンク化し、DB へ冪等的に保存（ON CONFLICT DO NOTHING 等を想定）。記事ID は正規化 URL の SHA-256 ハッシュを用いる設計（冪等性確保）。

- Research 層（kabusys.research）
  - ファクター計算モジュール (kabusys.research.factor_research)
    - モメンタム（calc_momentum）: 1m/3m/6m リターン、200日移動平均乖離等を DuckDB SQL で計算。
    - ボラティリティ/流動性（calc_volatility）: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を算出。true_range の NULL 伝播を適切に制御。
    - バリュー（calc_value）: raw_financials から最新財務データを参照し PER / ROE を計算。
    - 各関数は prices_daily / raw_financials のみ参照し、本番 API 等にはアクセスしない設計。
  - 特徴量探索・解析 (kabusys.research.feature_exploration)
    - 将来リターン計算 (calc_forward_returns): 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得。
    - IC（calc_ic）: Spearman ランク相関（ランク処理は同順位を平均ランクで扱う）を実装。サンプル不足（<3）では None を返す。
    - 統計サマリー (factor_summary) / ランク関数 (rank) を実装。
    - 実装は外部依存を持たず標準ライブラリのみで行う方針。

- Strategy 層（kabusys.strategy）
  - 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
    - research で算出した生ファクターをマージ・ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）適用・Z スコア正規化・±3 でクリップし、features テーブルへ冪等的に upsert（トランザクションによる日付単位置換）。
    - 正規化対象カラムの明示（mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev）。
  - シグナル生成 (kabusys.strategy.signal_generator)
    - features と ai_scores を統合し、各コンポーネントスコア（momentum, value, volatility, liquidity, news）を計算、重み付けして final_score を算出。
    - デフォルト重みと閾値を実装（デフォルト threshold=0.60）。
    - 重みの入力検証と正規化（未知キー・非数値・負値の無視、合計が 1.0 に再スケール）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負でかつ十分なサンプルがある場合のみ BUY を抑制）。
    - SELL シグナル生成（ストップロス -8% 及びスコア低下）を実装。保有銘柄の価格欠損時の判定スキップなど安全対策あり。
    - signals テーブルへ日付単位の置換（トランザクション＋バルク挿入で原子性を保証）。
    - ルックアヘッドバイアス回避のため、target_date 時点のデータのみ参照。

- その他
  - モジュール間の公共関数（build_features, generate_signals 等）をパッケージレベルでエクスポート。
  - ロギングや例外ハンドリングに配慮した実装（例: トランザクション失敗時の ROLLBACK ログ、読み込み失敗の警告）。

Security
- ニュース収集で defusedxml を採用し XML パース攻撃を防止。
- RSS/HTTP に対して受信サイズ制限（10MB）を設定しメモリ DoS を軽減。
- ニュース URL の正規化でトラッキングパラメータ除去、記事 ID にハッシュを使うことで冪等性確保とトラッキング排除。
- J-Quants の API 呼び出しでトークン管理・リフレッシュを実装し、不正なリクエストループを防止。

Known issues / Missing / TODO
- signal_generator のトレーリングストップや時間決済は positions テーブルに peak_price / entry_date 等の情報が必要であり現状未実装（コメントで未実装箇所を明示）。
- feature_engineering の features テーブル挿入は現状 SQL 側のスキーマに依存。マイグレーションやスキーマ検証ロジックは未提供。
- ニュース収集における記事と銘柄の紐付け（news_symbols）の具体的ロジックは設計文書に基づくが、実装の詳細は今後の拡張領域。
- research モジュールは pandas 等に依存しない実装だが、大規模データでの性能チューニング（メモリ・クエリ最適化）は今後対応予定。

Notes
- DuckDB を主要な OLAP / 一時 DB として利用する設計。各種計算・保存処理は DuckDB 接続を引数に取り、SQL と Python の組み合わせで実装されています。
- ルックアヘッドバイアス防止の設計方針を全体で徹底しており、target_date 時点のみを参照する実装が各所に存在します。

今後のリリースに向けて
- positions テーブルの拡張（peak_price / entry_date）とそれに基づくトレーリングストップ等の追加実装。
- monitoring / execution 層の実装強化（運用監視・実注文インターフェース）。
- パフォーマンス測定に基づく DuckDB クエリ最適化および並列処理対応。