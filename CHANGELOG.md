CHANGELOG
=========
すべての注目すべき変更点を記録します。  
このファイルは「Keep a Changelog」の書式に従い、セマンティックバージョニングを採用しています。

フォーマットについて
- https://keepachangelog.com/（概念的準拠）
- バージョンは semver に従います。

Unreleased
----------
（なし）

[0.1.0] - 2026-03-19
-------------------

Added
- 基本パッケージを追加
  - パッケージ名: kabusys（__version__ = 0.1.0）
  - モジュール構成: data, research, strategy, execution（execution は初期プレースホルダ）

- 環境設定/読み込み（kabusys.config）
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml）から自動検出して読み込む自動ロード機能を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env の行パーサ実装（コメント、export プレフィックス、単／二重引用符、バックスラッシュエスケープに対応）。
  - Settings クラスを提供し、各種必須設定をプロパティ経由で取得（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス、実行環境判定、ログレベル等）。
  - env 値のバリデーション（KABUSYS_ENV, LOG_LEVEL）を実装し、不正値で例外を投げる。

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - レートリミット制御（120 req/min）を固定間隔スロットリングで実装（_RateLimiter）。
  - リトライ・指数バックオフロジック（最大 3 回、408/429/5xx を再試行対象）。429 時は Retry-After ヘッダを優先。
  - 401 応答時にリフレッシュトークンから id_token を自動取得して 1 回だけ再試行（無限再帰対策あり）。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB へ冪等に保存する save_* 関数（ON CONFLICT DO UPDATE を使用し重複を排除）。fetched_at を UTC ISO8601 で記録。
  - レスポンス JSON デコード時のエラーやネットワークエラーの扱いを明確化。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィード収集の骨格実装を提供（デフォルトで Yahoo Finance のビジネス RSS を登録）。
  - 安全設計: defusedxml を利用して XML 攻撃を防ぐ。受信サイズ上限（10MB）を設定してメモリ DoS を緩和。
  - URL 正規化機能（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）。
  - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を確保。
  - DB へのバルク挿入（チャンク化）を念頭に置いた実装。

- 研究用モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）計算を実装（DuckDB SQL ベース）。
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）計算を実装。
    - Value（per, roe）計算を実装（raw_financials と prices_daily の組合せ）。
    - 営業日ベースのウィンドウ処理・スキャン範囲バッファを考慮。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns、ホライズンの検証、単一クエリで効率的に取得）。
    - IC（Spearman の ρ）計算（calc_ic）。ランク計算・同順位は平均ランクで処理。
    - ファクター統計サマリー（factor_summary）とランク変換ユーティリティ（rank）。
  - 依存最小化: pandas 等の外部ライブラリに依存しない設計（標準ライブラリ + DuckDB）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - 研究で計算した raw factor をマージ・ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）適用。
  - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）と ±3 のクリップ。
  - features テーブルへ日付単位での置換（DELETE→BULK INSERT、トランザクションにより原子性を保証）。
  - ルックアヘッドバイアス防止のため target_date 時点のみのデータを使用。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して最終スコア（final_score）を計算。
  - コンポーネントスコア: momentum, value, volatility, liquidity, news（AI）を計算するユーティリティを実装（シグモイド変換、NaN/Inf/None の扱い）。
  - 重み（weights）を受け付け、検証・補完・再スケーリングを行う。既知キーのみ受付。
  - Bear レジーム検知（ai_scores の regime_score 平均が負かつ十分なサンプル数）で BUY シグナルを抑制するロジックを実装。
  - BUY（閾値デフォルト 0.60）と SELL（ストップロス -8% / スコア低下）を生成し、signals テーブルへ日付単位で置換して保存（トランザクション）。
  - 保有銘柄（positions テーブル）に対するエグジット判定を実装（価格欠損時の判定スキップ、保有銘柄が features にない場合は警告して final_score を 0 と見なす等）。

Changed
- （初回リリースにつき該当なし）

Fixed
- input の堅牢化・誤データ対策を実装
  - .env パーサで引用符中のバックスラッシュエスケープや inline コメントの扱いに対応。
  - J-Quants の save_* 関数で PK 欠損行をスキップしログ警告を出すようにした（データ整合性向上）。
  - fetch 系のページネーション処理で pagination_key 重複防止。

Security
- 複数のセキュリティ対策を導入
  - ニュース XML パースに defusedxml を使用し XML 本体攻撃への耐性を確保。
  - ニュース取得で受信サイズ上限を設けメモリ DoS を軽減。
  - J-Quants API の認証トークン自動リフレッシュ時の再帰防止ロジックを実装。

Known issues / TODO
- signal_generator に記載の未実装条件
  - トレーリングストップ（peak_price が positions に存在することが前提）および時間決済（保有 60 営業日超）については未実装。positions テーブルに peak_price / entry_date が必要。
- news_collector の SSRF / IP ホワイトリスト等のさらなる厳緻化（モジュールは IP/スキーマ検査用のインポートを行っているが、外部呼び出しの完全検証ロジックは将来的拡張想定）。
- kabusys.data.stats の実装は本変更ログ作成時点のコード抽出には含まれていない（zscore_normalize の提供元として参照）。
- 自動テスト・CI に関する記述は本リポジトリのコードからは確認できず、今後の整備が望まれる。

Database / Schema notes
- 本実装は以下のテーブルを前提に動作する（主な想定カラム）
  - raw_prices(date, code, open, high, low, close, volume, turnover, fetched_at)
  - raw_financials(code, report_date, period_type, eps, roe, fetched_at, ...)
  - market_calendar(date, is_trading_day, is_half_day, is_sq_day, holiday_name)
  - prices_daily / features / ai_scores / positions / signals（各モジュール内 SQL 参照）
- save_* 関数は ON CONFLICT DO UPDATE を用いるため、既存データの上書き挙動がある。マイグレーションやスキーマ定義は導入時に確認すること。

開発・運用メモ
- ログ出力は各モジュールで行われ、異常時にスタックトレースが発生する箇所はトランザクションのロールバック等の対処が入っている。
- 設定は環境変数優先。.env.local は .env を上書きする形で読み込まれる（OS 環境変数は保護される）。

クレジット
- 初期実装（0.1.0）

----  
（以上）