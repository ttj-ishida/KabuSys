# CHANGELOG

このプロジェクトの変更履歴は「Keep a Changelog」形式に従います。  
Semantic Versioning に準拠します。

- リリース日付は YYYY-MM-DD 形式で記載しています。
- ここに記載されている内容は、与えられたコードベースから推測してまとめたものです。

## [Unreleased]

### Added
- 開発中の機能・ドキュメントや追加予定のユニットテスト、CI ワークフロー等をここに記載してください。

---

## [0.1.0] - 2026-03-21

初回公開リリース。日本株自動売買システムのコアライブラリを提供します。主な追加点は以下の通りです。

### Added
- パッケージ基礎
  - kabusys パッケージの初期版を追加。バージョンは 0.1.0。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ としてエクスポート。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルと環境変数の統合ロード機能を実装（プロジェクトルートを .git または pyproject.toml から自動検出）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ: コメント行 / export プレフィックス / シングル・ダブルクォートとエスケープ対応 / インラインコメントの扱い等に対応する堅牢なパーサを実装。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス等の設定をプロパティ経由で取得できるようにした。
  - KABUSYS_ENV と LOG_LEVEL の入力値検証（許容値セットによるバリデーション）を実装。

- データ取得・保存 (kabusys.data)
  - J-Quants クライアント (data.jquants_client)
    - API 呼び出し用の汎用 _request 実装（JSON デコード、ページネーション対応）。
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回）。408/429/5xx に対する再試行、429 の Retry-After 優先対応。
    - 401 受信時はリフレッシュトークンによる ID トークン自動更新を 1 回のみ行う仕組みを実装。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を追加（ページネーション対応）。
    - DuckDB への保存ユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT（冪等性）で重複を排除。
    - 型変換ユーティリティ _to_float / _to_int を実装。欠損や変換失敗を安全に扱う。

  - ニュース収集 (data.news_collector)
    - RSS フィード収集機能を追加（デフォルト RSS: Yahoo Finance のビジネスカテゴリ）。
    - URL 正規化（追跡パラメータ削除、スキーム/ホスト小文字化、フラグメント削除、クエリソート）と記事 ID を SHA-256 ハッシュで生成して冪等性を確保。
    - defusedxml による XML パースで XML 関連攻撃を軽減。受信サイズ上限を設定してメモリ DoS を防止。
    - SSRF 対策（HTTP/HTTPS スキーム限定など）やトラッキングパラメータ除去などセキュリティ上の配慮を実装。
    - DB へのバルク挿入はチャンク化して実行し、INSERT RETURNING で挿入数を正確に得られることを想定。

- 研究（Research）モジュール (kabusys.research)
  - factor_research: モメンタム / ボラティリティ / バリューなどのファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - 各関数は DuckDB の prices_daily / raw_financials を参照し、date/code 単位で結果を返す。
    - 移動平均、ATR、出来高平均、PER 計算などを SQL と Python の組み合わせで実装。
  - feature_exploration: 将来リターンの計算（calc_forward_returns）、IC（スピアマン ρ）計算（calc_ic）、ファクター統計サマリー（factor_summary）、rank 関数を提供。
    - calc_forward_returns は複数ホライズンを一度に取得する効率的な SQL 実装。
    - calc_ic はランク相関（Spearman）を実装し、サンプル数が不足する場合は None を返す。
    - factor_summary は count/mean/std/min/max/median を計算。

  - 研究用ユーティリティ zscore_normalize を data.stats 経由で公開（re-export）。

- 戦略 / シグナル (kabusys.strategy)
  - 特徴量エンジニアリング (strategy.feature_engineering)
    - research で計算された生ファクターを取り込み、ユニバースフィルタを適用（最低株価・平均売買代金の閾値）。
    - 指定されたカラムを Z スコア正規化し ±3 でクリップ。結果を features テーブルへ日付単位で UPSERT（トランザクションで置換）する build_features を実装。
    - ルックアヘッドバイアス対策として target_date 時点のデータのみ使用することを明記。

  - シグナル生成 (strategy.signal_generator)
    - features と ai_scores を統合して各銘柄の final_score を計算し、BUY / SELL シグナルを生成する generate_signals を実装。
    - momentum/value/volatility/liquidity/news の重み付けによる最終スコア計算（デフォルト重みを実装）と、外部からの重み上書き時の妥当性チェック・再スケーリング処理。
    - シグモイド変換、欠損コンポーネントの中立補完（0.5）処理、スコアのソート・ランク付けを実装。
    - Bear レジーム判定（ai_scores の regime_score の平均が負の場合に BUY を抑制）を実装。
    - エグジット（SELL）判定ロジックを実装（ストップロス -8% とスコア低下）。SELL 判定は BUY より優先しランクを再計算。
    - signals テーブルへの日付単位置換（トランザクション + バルク挿入）で冪等性を保証。

### Changed
- n/a（初期リリースのため過去変更なし）

### Fixed
- n/a（初期リリースのためバグ修正履歴なし）

### Security
- ニュース収集で defusedxml を利用し、XML 関連脆弱性を軽減。
- URL 正規化と追跡パラメータ除去、受信サイズ制限、スキーム制限等で SSRF/DoS リスクに配慮。
- J-Quants クライアントは認証トークンの自動リフレッシュを実装し、不正な 401 後の誤動作を減らすよう設計。

### Known issues / Limitations
- signal_generator のエグジット条件に未実装のルール（トレーリングストップ、時間決済）に関する注記あり。positions テーブルに peak_price / entry_date の情報が必要。
- news_collector の詳細な URL 検証（IP アドレスの内部アドレス回避等）や一部のエッジケースは更なる強化が可能。
- 一部のユーティリティや DB スキーマ（tables の定義）はこのリリースに含まれるコードスナップショットでは明示されておらず、導入時に適切なスキーマ定義が必要。
- 外部依存（duckdb, defusedxml 等）についてはバージョン管理と互換性検証が必要。

---

参考: Keep a Changelog — https://keepachangelog.com/（英語）