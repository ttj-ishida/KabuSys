# Changelog

すべての注目すべき変更をこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。  

既知の互換性レベルはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-03-20

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。以下の主要機能・設計方針・注意点を含みます。

### Added
- パッケージの基本構成
  - パッケージ名: kabusys、バージョン 0.1.0
  - public API エントリポイント: kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring を __all__ で公開。

- 環境設定管理 (kabusys.config)
  - .env ファイルあるいは環境変数からの設定自動読み込み機能を実装。
    - プロジェクトルート判定は .git または pyproject.toml を基準に行い、CWD に依存しない安全な検出を実装。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能（テスト向け）。
  - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート、バックスラッシュによるエスケープ、行末コメント処理を考慮）。
  - 環境変数の保護（protected set）により OS 環境変数を上書きしない制御を実装。
  - 必須変数チェック用の _require() と Settings クラスを提供。以下の設定プロパティが利用可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト）、SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV（検証あり: development/paper_trading/live）, LOG_LEVEL（検証あり）。
  - 環境値の妥当性検査（env/log_level の候補チェック）を実装。

- Data モジュール (kabusys.data.jquants_client)
  - J-Quants API クライアント実装（取得・保存ロジック、ページネーション対応）。
  - レート制限制御: 固定間隔スロットリング（120 req/min）による RateLimiter を実装。
  - 再試行ロジック: 指数バックオフ（最大 3 回）。HTTP 408/429/5xx に対するリトライ。429 の場合は Retry-After ヘッダを優先。
  - 401 Unauthorized 受信時の自動トークンリフレッシュ（1 回のみ）と再試行の実装。
  - ページネーション対応の fetch_* API:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（取引カレンダー）
  - DuckDB への冪等保存関数:
    - save_daily_quotes: raw_prices に ON CONFLICT DO UPDATE で保存（PK 欠損行はスキップして警告）。
    - save_financial_statements: raw_financials に同様の冪等保存（PK 欠損行はスキップ）。
    - save_market_calendar: market_calendar に冪等保存。
  - JSON デコードエラーやネットワークエラーに対する例外メッセージ改善。
  - 型変換ユーティリティ: _to_float / _to_int（空値や不正フォーマットを安全に None に変換）。

- News モジュール (kabusys.data.news_collector)
  - RSS ベースのニュース収集機能を実装。
  - デフォルト RSS ソース（yahoo_finance）を指定。
  - セキュリティ・堅牢性対策:
    - defusedxml を用いて XML Bomb 等を回避。
    - 受信最大バイト数制限（MAX_RESPONSE_BYTES=10MB）でメモリ DoS を抑止。
    - URL 正規化機能を実装（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
    - 記事 ID を URL 正規化後の SHA-256（先頭32文字）で生成し、冪等性を担保。
    - SSRF 対策（HTTP/HTTPS 以外のスキーム拒否等の方針/実装を想定）。
  - raw_news へのバルク INSERT をチャンク化して実行し、パフォーマンスと SQL 長制限に対応。
  - news_symbols 等で銘柄紐付けを行う設計。

- 研究・ファクター計算 (kabusys.research)
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を DuckDB（prices_daily）から計算。200日未満は None。
    - calc_volatility: 20日 ATR / atr_pct / avg_turnover / volume_ratio を計算。データ不足は None。
    - calc_value: raw_financials と prices_daily を組み合わせて per / roe を計算（EPS=0 は None）。
    - 各関数は営業日 (連続レコード数) を前提にウィンドウを扱う（カレンダーバッファを確保）。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で計算。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装（ペア数 < 3 は None）。
    - factor_summary: count/mean/std/min/max/median を算出。
    - rank: 同順位は平均ランクとするランク関数（丸めによる ties 対応）。

- 戦略層 (kabusys.strategy)
  - feature_engineering.build_features:
    - research モジュールから生ファクターを取得しマージ。
    - ユニバースフィルタ（最低株価 _MIN_PRICE=300 円、20日平均売買代金 _MIN_TURNOVER=5e8 円）を実装。
    - 正規化: zscore_normalize を呼び出し、対象カラムを ±3 でクリップして外れ値影響を抑制。
    - features テーブルへ日付単位で置換（DELETE + bulk INSERT をトランザクション内で実行し原子性を保証）。
  - signal_generator.generate_signals:
    - features と ai_scores を統合し、component スコア（momentum/value/volatility/liquidity/news）を算出。
    - スコア変換にシグモイドを利用。欠損コンポーネントは中立値 0.5 で補完。
    - final_score の重み付け（デフォルト weights は momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。ユーザー指定 weights は正当性検査後に合計が 1.0 となるよう再スケール。
    - Bear レジーム判定: ai_scores の regime_score 平均が負のとき Bear（サンプル数閾値あり）。
    - BUY シグナル閾値デフォルト: 0.60（_DEFAULT_THRESHOLD）。Bear 時は BUY を抑制。
    - SELL シグナル（エグジット）判定:
      - ストップロス: 現在終値 / avg_price - 1 < -0.08（-8%）
      - スコア低下: final_score < threshold
      - SELL 判定は保有ポジション（positions テーブル）を参照し処理。価格欠損時は判定をスキップして安全性を確保。
      - （未実装）トレーリングストップ、時間決済は将来の拡張想定（positions に peak_price / entry_date が必要）。
    - signals テーブルへ日付単位の置換（トランザクション＋バルク挿入で原子性を保証）。
    - ロギングと警告メッセージを充実させ、欠損データや異常値を通知。

- DB と処理全体の設計方針
  - DuckDB を分析・一時保存層として利用する設計を前提。
  - データ保存は可能な限り冪等化（ON CONFLICT / DO UPDATE 等）して再実行可能性を担保。
  - ルックアヘッドバイアスを防ぐため、各処理は target_date 時点のデータのみを参照する方針。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- XML パースに defusedxml を採用し、RSS の脆弱性を軽減。
- ニュース URL 正規化および受信サイズ制限で SSRF / DoS リスクを低減。
- J-Quants クライアントでトークン管理と自動リフレッシュを実装し、不正な認証状態からの復旧を図る。

### Notes / Known limitations
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装。positions テーブルの拡張を予定。
- news_collector の SSRF 関連チェックの詳細（IP ブロックや DNS 追跡）については実装方針がコメントにあるが、運用時の追加検討が必要。
- 外部依存は極力少なくする設計だが、J-Quants API のレスポンス仕様変更や DuckDB スキーマの前提変更は破壊的な影響を与える可能性があるため、運用時のスキーマ管理を推奨。

---

貢献・バグ報告・改善提案は issue / PR を通じて歓迎します。