# Changelog

すべての重要な変更点をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。

全般的な注記:
- 本リリースはパッケージの初版リリースとして想定しています（パッケージバージョン: 0.1.0）。
- ドキュメントやログメッセージは日本語で記載されています。
- DB 書き込みは可能な限り冪等性（ON CONFLICT / トランザクション）を考慮しています。

0.1.0 - 2026-03-20
------------------

Added
- パッケージ基盤
  - kabusys パッケージの公開 API を定義（kabusys.__init__ にて version="0.1.0", __all__ を設定）。
- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - プロジェクトルート自動検出: .git または pyproject.toml を基準に検索する _find_project_root。
  - .env 自動ロード機能: OS 環境変数 > .env.local > .env の優先順位で自動読み込みを実施。テスト等のため KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサー (_parse_env_line) を実装。export プレフィックス対応、引用符のエスケープ処理、インラインコメント処理などに対応。
  - .env 読み込み時に OS 環境変数を保護する protected 機能（.env.local の上書き時にも保護）。
  - 必須環境変数取得用の _require と Settings の各プロパティ（J-Quants / kabu / Slack / DB パス / 環境種別 / ログレベルなど）。
  - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装（トークン取得、ページネーション対応の fetch_*、DuckDB への保存関数 save_*）。
  - レート制限対応: 固定間隔スロットリングを行う _RateLimiter（120 req/min を想定）。
  - リトライ戦略: 指数バックオフ、最大リトライ 3 回、408/429/5xx をリトライ対象。429 の場合は Retry-After ヘッダを尊重。
  - 401 時の自動トークンリフレッシュ（1 回のみ）を実装。
  - ページネーション対応（pagination_key の共有と重複検知）。
  - DuckDB 保存関数における冪等性: raw_prices/raw_financials/market_calendar 等は ON CONFLICT DO UPDATE を使用。
  - 型変換ユーティリティ (_to_float / _to_int) を追加し安全にパース。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集し raw_news へ保存する機能を追加。
  - 記事 ID の冪等生成: 正規化 URL の SHA-256 (先頭 32 文字) を利用。
  - URL 正規化機能 (_normalize_url): スキーム/ホスト小文字化、トラッキングパラメータ除去（utm_*, fbclid 等）、フラグメント削除、クエリソート。
  - defusedxml による XML パース（XML Bomb 等への対策）。
  - 受信サイズ上限 (MAX_RESPONSE_BYTES = 10MB)、バルク挿入チャンク化 (_INSERT_CHUNK_SIZE) によるメモリ / SQL 長対策。
  - HTTP(S) スキーム検査や SSRF 等を意識した基盤設計（コメントにて方針記載）。

- 研究用ユーティリティ (kabusys.research)
  - ファクター計算モジュール (factor_research): モメンタム / バリュー / ボラティリティ / 流動性ファクターを DuckDB の prices_daily / raw_financials から算出する関数を追加。
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200 日窓を検査）。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（true range の NULL 伝播を注意深く扱う）。
    - calc_value: per, roe（target_date 以前の最新財務データを参照）。
  - 特徴量探索 (feature_exploration):
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを効率的に取得。horizons のバリデーション（1〜252 日）。
    - calc_ic: スピアマンのランク相関（IC）計算。データ不足（<3）では None を返す。
    - factor_summary: count/mean/std/min/max/median を各ファクター列に対して計算。
    - rank: 同順位は平均ランクを返すランク関数（浮動小数点の丸めにより ties 検出を安定化）。

- 戦略ロジック (kabusys.strategy)
  - 特徴量エンジニアリング (feature_engineering.build_features)
    - research で計算した raw ファクターをマージ、ユニバースフィルタ（最低株価・平均売買代金）を適用。
    - 指定カラムを z-score 正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップして外れ値を抑制。
    - features テーブルへ日付単位の置換（トランザクション + バルク挿入で原子性保証）。
  - シグナル生成 (signal_generator.generate_signals)
    - features と ai_scores を統合して各コンポーネント（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネントは欠損時に中立値 0.5 で補完、weights はデフォルト値でフォールバックし再スケール。
    - Bear レジーム検出（ai_scores の regime_score 平均が負かつ十分なサンプル数）により BUY を抑制。
    - BUY: final_score が閾値（デフォルト 0.60）以上の銘柄を採用（Bear 時は抑制）。
    - SELL: ストップロス（終値/avg_price -1 < -8%）および final_score の低下（閾値未満）を実装。SELL は BUY より優先し signals に反映。
    - signals テーブルへ日付単位の置換（トランザクション + バルク挿入で原子性保証）。

Changed
- なし（初版リリースのため変更履歴はなし）。

Fixed
- なし（初版リリース。コード内に多くの安全策/警告が記載されている）。

Security
- news_collector で defusedxml を採用し XML 関連の脆弱性へ配慮。
- URL 正規化とトラッキングパラメータ削除、受信サイズ制限により外部入力や DoS のリスクを低減。
- jquants_client の HTTP エラーやネットワーク例外に対する堅牢なリトライとトークンリフレッシュ処理を実装。

Notes / 制限事項
- DuckDB のテーブル（prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar, raw_news 等）はリリース時点で前提となっており、スキーマはコードの期待に合わせて準備する必要があります。
- 一部戦略ロジック（トレーリングストップや時間決済など）は positions テーブルに peak_price / entry_date 等の追加フィールドが必要であり、現在は未実装として明示されています。
- news_collector の RSS フィード取得では外部ネットワークへ接続するため、運用時はフェッチ頻度やタイムアウト/リトライ方針を適切に設定してください。
- settings の必須変数未設定時は ValueError を送出するため、CI/本番環境では .env の整備が必要です。

Acknowledgments
- 本 CHANGELOG は提供されたコードベースから推測した機能・設計方針に基づいて作成しています。実際のリリースノート作成時は変更差分・コミットログに基づく追記・修正を推奨します。