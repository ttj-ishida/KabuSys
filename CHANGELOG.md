# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買システム「KabuSys」の基盤機能を追加しました。主要な追加点・設計方針は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化: kabusys.__version__ = 0.1.0、主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。
- 設定管理
  - 環境変数・設定読み込みモジュール (kabusys.config)
    - プロジェクトルート探索ロジックを実装（.git または pyproject.toml を基準）。
    - .env / .env.local の自動ロード（優先順: OS 環境 > .env.local > .env）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサ実装（export 形式、クォート文字列、インラインコメントの扱いに対応）。
    - Settings クラスでアプリケーション設定をプロパティとして提供（J-Quants トークン、kabu API 設定、Slack トークン、DB パス、実行環境判定など）。
    - env と log_level の値チェックを実装（許容値以外は ValueError を送出）。
- データ取得・保存 (kabusys.data)
  - J-Quants API クライアント (jquants_client)
    - 固定間隔スロットリングによるレート制御（120 req/min を想定）。
    - 冪等なデータ保存関数（DuckDB へ ON CONFLICT DO UPDATE を使用する save_* 系関数）。
    - ページネーション対応のフェッチ関数（fetch_daily_quotes, fetch_financial_statements）。
    - リトライロジック（最大3回、指数バックオフ）と 401 時のトークン自動リフレッシュ処理。
    - トークンキャッシュ（モジュールレベル _ID_TOKEN_CACHE）を導入してページネーション間で共有。
    - 型変換ユーティリティ (_to_float, _to_int) による堅牢な入力正規化。
  - ニュース収集モジュール (news_collector)
    - RSS フィード取得・正規化・前処理・DB 保存の一連処理を実装。
    - デフォルト RSS ソース一覧を提供（例: Yahoo Finance）。
    - 記事IDを正規化 URL の SHA-256 先頭32文字で生成し冪等性を確保。
    - URL 正規化でトラッキングパラメータ（utm_* 等）を除去、クエリをソート。
    - SSRF 対策: スキーム検証、ホストのプライベートIPチェック、リダイレクト時の検査ハンドラを実装。
    - XML パースは defusedxml を使用して安全に処理。
    - レスポンスサイズ上限（10 MB）や gzip 解凍後のサイズ検査、最大読み込みバイト数制限を実装（DoS対策）。
    - DB 保存: INSERT ... RETURNING を用いたチャンク挿入、トランザクション・ロールバック処理、news_symbols の一括保存ユーティリティを実装。
    - 銘柄コード抽出 (extract_stock_codes): 本文から 4 桁コードを抽出して known_codes と照合。
- データスキーマ (data.schema)
  - DuckDB 用スキーマ定義を追加（Raw / Processed / Feature / Execution 層を想定）。
  - raw_prices, raw_financials, raw_news などの DDL を定義（NOT NULL / 型制約 / PRIMARY KEY 等を含む）。
- リサーチ用機能 (kabusys.research)
  - ファクター計算モジュール (factor_research)
    - Momentum, Value, Volatility（および一部 Liquidity 指標）を DuckDB の prices_daily / raw_financials を用いて計算する関数を提供。
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均乖離）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（atr_20）、atr_pct、平均売買代金、出来高比率を計算。欠損時は None を返す。
    - calc_value: 最新財務（report_date <= target_date）と当日の株価を組み合わせて PER / ROE を計算。
  - 特徴量探索モジュール (feature_exploration)
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト: 1,5,21 営業日）における将来リターンを一度のクエリで取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。データ不足（有効レコード < 3）の場合は None を返す。
    - rank: 同順位の平均ランクを扱うランク化ユーティリティ（浮動小数の丸めで ties の誤検出を防止）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリーを提供。
  - 研究用ユーティリティとして kabusys.data.stats.zscore_normalize を re-export。
- 仕様・設計文書参照
  - 各モジュールの docstring に設計方針や参考ドキュメント（DataPlatform.md, StrategyModel.md 等）を記載。

### 変更 (Changed)
- （初回リリースのためなし）

### 修正 (Fixed)
- （初回リリースのためなし）

### セキュリティ (Security)
- RSS 収集部で以下のセキュリティ対策を導入:
  - defusedxml による XML の安全なパース。
  - URL スキーム/ホストの検証、リダイレクト先の検査により SSRF を防止。
  - レスポンスサイズ上限・gzip 解凍後のサイズチェックによるリソース消費攻撃対策。
- J-Quants API クライアントの認証処理でトークンリフレッシュ時の無限再帰を回避する制御を追加（allow_refresh フラグ）。

### パフォーマンス (Performance)
- J-Quants の API 呼び出しは固定間隔レートリミッタを実装し、リクエスト間隔を制御（120 req/min 想定）。
- DuckDB へのバルク挿入はチャンク処理とトランザクションでまとめて実行しオーバーヘッドを低減。
- calc_forward_returns 等の集計は必要な最小範囲のカレンダー日でスキャンするよう設計（ホライズンのバッファを用いる）。

### 互換性に関する注意 (Notes / Breaking Changes)
- 環境変数の自動ロードはデフォルト ON。テストや特殊環境で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Settings.env / log_level に対する入力検証が厳密に行われます。既存の環境変数が許容値外の場合、ValueError が発生します。
- J-Quants クライアントは内部で同期的にスリープする（rate limiter）ため、外部スケジューラ等と併用する場合は待ち時間の影響を考慮してください。

### 既知の制約・今後の予定 (Known issues / Roadmap)
- 一部モジュール（strategy、execution、monitoring）はパッケージ階層に存在しますが、実装の詳細や API は今後追加予定です。
- research モジュールは外部ライブラリ（pandas 等）には依存しない純粋 Python 実装が優先されているため、大規模データでの高速化や並列処理は今後の課題です。
- DuckDB スキーマは Raw 層の主要テーブルを定義していますが、Processed / Feature / Execution 層の詳細な DDL 拡張は今後行う予定です。

---

今後のリリースでは、戦略実行（発注・約定・ポジション管理）、監視・アラート基盤、バックテスト/シミュレーション機能の強化、並列/非同期化（特にネットワークリクエストと DB 書込周り）の改善を予定しています。