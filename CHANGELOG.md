# Changelog

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog の形式に従い、セマンティックバージョニングを使用します。

## [Unreleased]

（現時点の配布は v0.1.0 のみ。今後の変更はここに記載します）

---

## [0.1.0] - 2026-03-20

初期リリース。日本株自動売買システム「KabuSys」の基本モジュール群を実装します。主な追加機能・設計方針は下記の通りです。

### Added
- パッケージ基盤
  - src/kabusys/__init__.py にてバージョン管理と主要サブパッケージ（data, strategy, execution, monitoring）を公開。
- 設定管理
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を自動読込（プロジェクトルートは .git または pyproject.toml を起点に探索）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。
    - .env パーサ実装: export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント規則に対応。
    - 必須キー取得の簡易ラッパー _require と、各種設定プロパティ（J-Quants トークン、kabu API 情報、Slack トークン／チャンネル、DB パス、環境・ログレベル判定など）を実装。KABUSYS_ENV / LOG_LEVEL のバリデーションあり。
- データ収集／保存（J-Quants）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装（ページネーション対応）。
    - レート制限（120 req/min）を固定間隔スロットリングで管理する RateLimiter を実装。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx のハンドリング）と、401 時の自動トークンリフレッシュ（1 回）を実装。
    - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を提供。
    - DuckDB へ冪等保存する save_daily_quotes / save_financial_statements / save_market_calendar を実装（ON CONFLICT DO UPDATE を使用）。fetched_at を UTC ISO8601 で記録。
    - 入力データ変換ユーティリティ _to_float / _to_int を実装。変換ルール（空文字・不正値 → None、float 文字列の int 変換時の注意など）を明示。
- ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィードから記事を収集して raw_news に保存するロジック（デフォルトの RSS ソースを一つ含む）。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ（utm_ 等）除去、フラグメント削除、クエリソート）を実装。
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）を想定して冪等性を担保する設計方針を採用。
    - defusedxml を用いた XML パースによる安全化、受信最大バイト数制限（10MB）などの DoS / XML 攻撃対策を想定。
    - DB へのバルク挿入をチャンク化してパフォーマンスと SQL 長制限に配慮する設計。
- 研究用ファクター計算
  - src/kabusys/research/factor_research.py
    - momentum（1M/3M/6M リターン、MA200 乖離）、volatility（20日 ATR、相対 ATR、出来高比率、20日平均売買代金）、value（PER、ROE）等のファクター計算を実装。
    - DuckDB の SQL ウィンドウ関数を活用し、営業日欠損（休日等）に対応するスキャン範囲バッファを導入。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（任意ホライズン：デフォルト [1,5,21]）を提供（1クエリ取得・リード関数使用）。
    - スピアマン IC 計算（rank を利用）、ランク付けユーティリティ、ファクター統計サマリーを実装。外部ライブラリに依存せず標準ライブラリで実装。
  - research パッケージのエクスポートを __init__.py で整理。
- 戦略（特徴量作成・シグナル生成）
  - src/kabusys/strategy/feature_engineering.py
    - 研究側で算出した生ファクターをマージ、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用、指定カラム群を Z スコア正規化（外れ値は ±3 でクリップ）し features テーブルへ日付単位で置換保存する build_features を実装。DuckDB トランザクションで原子性を保証。
    - ルックアヘッドバイアス対策として target_date 時点のデータのみを使用する方針。
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合し、モメンタム / バリュー / ボラティリティ / 流動性 / ニュース のコンポーネントごとにスコアを計算。sigmoid 変換、欠損値は中立 0.5 で補完。
    - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）を持ち、ユーザー指定の weights を検証・補完・再スケールする機能を提供。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合かつ十分なサンプル数）時は BUY シグナルを抑制。
    - エグジット判定（stop_loss -8% およびスコア低下）に基づく SELL シグナル生成を実装。保有銘柄の価格欠損時は判定をスキップする安全策あり。
    - BUY/SELL を signals テーブルへ日付単位で置換（トランザクション）し、SELL 優先ポリシーで BUY を除外してランク再計算。
  - strategy パッケージは build_features / generate_signals を公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- XML パーサに defusedxml を利用（ニュース収集）し XML Bomb 等を防止する設計を採用。
- RSS などで受信するレスポンスに対して最大バイト数（10 MB）制限を想定し、メモリ DoS を軽減。
- J-Quants クライアントで 401 時のトークン自動リフレッシュの再帰防止を実装（allow_refresh フラグ）。429 の Retry-After を尊重する再試行処理。
- .env 自動読み込み時に OS 環境変数を保護（.env.local が上書き可能だが、既存 OS 環境は protected として扱う）する仕組みを導入。

### Notes / Design decisions
- DuckDB を主要なローカル時系列 DB として使用。各データ保存関数は冪等性を重視（ON CONFLICT を使用）。
- ルックアヘッドバイアス防止のため、全ての戦略・研究 API は target_date 時点以前のデータのみを参照する方針。
- 外部依存を最小化（研究モジュールは pandas 等に依存しない実装）。
- エラー時にはトランザクションで ROLLBACK を試み、失敗時はログで警告するなど堅牢性を重視。

---

今後のリリースでは、次のような拡張が想定されています（優先度順、未実装項目の例）:
- execution 層の実装（kabu API 連携による実売買）
- monitoring / alerting（Slack 通知等）の具象実装
- ニュース記事と銘柄の自動マッチング（news_symbols 連携）
- トレーリングストップや保有日数ベースの決済ルールの追加
- 単体テスト・統合テストの追加および CI 設定

（以上）