# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  

- リリース日付は ISO 8601 形式（YYYY-MM-DD）で記載しています。  
- 初期リリースにおける実装の概要・設計上の意図・既知の制限点も併せて記載しています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-21

初回公開リリース。日本株自動売買システムのコアライブラリ群を実装しました。主な機能・モジュールは以下の通りです。

### Added
- パッケージ基礎
  - パッケージ初期化: kabusys.__version__ = 0.1.0、主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。
- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して自動検出。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーが以下をサポート:
    - コメント行 / 空行のスキップ、`export KEY=val` 形式、シングル/ダブルクォート内でのバックスラッシュエスケープ、インラインコメント取り扱い（クォート無しの場合は直前に空白/タブがある `#` をコメントとみなす）。
  - Settings クラスによりアプリケーション設定をプロパティで取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID が必須（未設定時は ValueError）。
    - DB パス（DUCKDB_PATH, SQLITE_PATH）、KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL 検証等を提供。
- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装（HTTP 呼び出し、ページネーション対応）。
  - レート制限遵守のための固定間隔レートリミッタ（120 req/min）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）、429 の Retry-After 処理。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）を実装。get_id_token 関数経由でリフレッシュトークンを使った取得を行う。
  - fetch_* 系関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）と、それらを DuckDB に冪等的に保存する save_* 関数（ON CONFLICT DO UPDATE）を実装。
  - レスポンスのパースと型変換ユーティリティ（_to_float / _to_int）を実装し、無効行はスキップ・警告を出力。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュースを収集・正規化して raw_news に保存する基盤を実装。
  - URL 正規化（トラッキングパラメータ削除、スキーム/ホスト小文字化、フラグメント除去、クエリソート）を実装。
  - DefusedXML を利用して XML 関連の攻撃を軽減、受信サイズ上限（10MB）でメモリ DoS を軽減、HTTP スキーム制限などセキュリティ対策を実装。
  - 挿入はバルクかつトランザクションで行い、ON CONFLICT DO NOTHING 等で冪等性を確保（INSERT チャンク化）。
- 研究用ファクター計算（kabusys.research.factor_research）
  - モメンタム（1M/3M/6M、MA200 乖離）、ボラティリティ/流動性（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB 上で計算する関数を実装。
  - SQL ウィンドウ関数を活用し、データ不足時は None を返す設計（データの健全性を保つ）。
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research で得た raw ファクターをマージ・ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
  - 数値ファクターを Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 にクリップして外れ値の影響を抑制。
  - features テーブルへの日付単位置換（DELETE + INSERT）で冪等に書き込み（トランザクションを使用して原子性を保証）。
- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して、各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し、重み付きで final_score を算出。
  - デフォルト重み・閾値を実装（デフォルト threshold=0.60、weights の補完と正規化処理あり）。無効な重みは警告を出す。
  - Bear レジーム判定（ai_scores の regime_score 平均 < 0 かつサンプル数閾値を満たす場合）により BUY シグナルを抑制。
  - 保有ポジションに対するエグジット判定（ストップロス -8% を最優先、final_score が閾値未満でのエグジット）を実装。signals テーブルへの日付置換で冪等性を確保。
- 研究支援（kabusys.research.feature_exploration）
  - 将来リターン計算（複数ホライズン、まとめて1クエリで取得）、IC（Spearman ランク相関）計算、ファクター統計サマリー、ランク関数を実装。
  - calc_forward_returns の horizons 引数に対する検証（正の整数かつ <= 252）。
- 公開 API の整理
  - strategy パッケージから build_features, generate_signals を公開。
  - research パッケージから主要な計算ユーティリティをエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### Changed
- （初版につき変更履歴なし）

### Fixed
- （初版につき修正履歴なし）

### Deprecated
- （初版につきなし）

### Removed
- （初版につきなし）

### Security
- ニュース収集で defusedxml を利用して XML の脆弱性対策を導入。
- RSS URL 正規化・スキーム検査・受信サイズ制限・IP/SSRF 関連の対策を行う設計指針を導入。
- J-Quants クライアントは 401 時にトークンリフレッシュを自動で実行するが、無限リフレッシュを防ぐため 1 回のみ行う設計。

### Known limitations / Notes
- 実運用に向けた未実装機能（今後の実装候補）:
  - ポジション管理テーブル上の peak_price / entry_date を利用したトレーリングストップや時間決済（保有 60 営業日超）などのエグジット条件は未実装（コード内に注記あり）。
  - PBR や配当利回りなどのバリューファクターは現バージョンで未実装。
- settings の必須環境変数（未設定時は ValueError が発生）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- モジュールレベルの ID トークンキャッシュを採用しているため、同一プロセス内でページネーション間はトークンが共有されます。トークンの管理は運用上注意してください。
- rate limiter は固定間隔（スロットリング）を採用。Burst を許容するトークンバケット方式ではありません。
- 外部依存:
  - DuckDB（duckdb モジュール）および defusedxml が必要。その他極力標準ライブラリで実装している。
- DB スキーマ（テーブル定義）や外部システム連携（Slack / kabu API 実行層）は別途定義・実装が必要です（本リリースはコア処理ロジックに注力）。
- .env 自動読み込みはプロジェクトルート検出に依存します。パッケージ配布環境やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを抑止できます。

---

作業上・設計上の詳細や将来の拡張（例: トレード実行の throttling、バックテスト用の追加指標、AI 統合の拡張など）は別途 RFC/イシューとして管理してください。