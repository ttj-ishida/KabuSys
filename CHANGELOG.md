# Changelog

すべての重要な変更点を記載します。フォーマットは「Keep a Changelog」に準拠します。

なお、本CHANGELOGは提供されたコードベースの内容から機能追加・設計方針・既知の制約を推測して作成しています。

## [Unreleased]

- (なし)

## [0.1.0] - 2026-03-20

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。主な追加点・設計方針は以下の通りです。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py
    - パッケージ名、version（0.1.0）および公開モジュール（data, strategy, execution, monitoring）を定義。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルと OS 環境変数を組み合わせた設定読み込み機能を実装。
    - プロジェクトルート検出（.git または pyproject.toml を起点）により CWD に依存しない自動ロードを実現。
    - export KEY=val 形式、クォート・エスケープ、行末コメント処理等を考慮した堅牢な .env パーサーを実装（_parse_env_line）。
    - 読み込み順序: OS 環境変数 > .env.local > .env、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - Settings クラスを提供し、必須環境変数取得（_require）や値検証（KABUSYS_ENV / LOG_LEVEL の許容値検査）を実装。
    - データベースパス（DuckDB/SQLite）や各種 API トークン・Slack 設定などをプロパティとして提供。

- データ収集・保存（J-Quants）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装。レート制限遵守のための固定間隔スロットリング（_RateLimiter）を実装（120 req/min）。
    - リトライ（指数バックオフ、最大 3 回）、429 の Retry-After 優先、401 時の自動トークンリフレッシュ（1 回のみ）を実装。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT による更新で重複を排除。
    - 入力変換ユーティリティ（_to_float, _to_int）を提供。
    - fetched_at を UTC で記録し、Look-ahead バイアス対策を考慮。

- ニュース収集（RSS）
  - src/kabusys/data/news_collector.py（実装の大部分）
    - RSS からの記事収集と正規化処理の基盤（URL 正規化、トラッキングパラメータ除去、記事ID生成方針）を実装。
    - defusedxml を利用した XML パースによるセキュリティ対策、受信サイズ制限（MAX_RESPONSE_BYTES）、URL スキーム制限等の安全措置を設計。
    - bulk insert のチャンク化による DB 負荷軽減や ON CONFLICT / 挿入数計測方針を記述。
    - デフォルト RSS ソース（Yahoo Finance のビジネスカテゴリ）を定義。

- リサーチ／ファクター計算
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20 日 ATR、相対 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER、ROE）等のファクター計算を実装。
    - DuckDB のウィンドウ関数を活用し、営業日欠損を吸収するためのスキャン日幅など実務的な設計を適用。
    - 関数: calc_momentum, calc_volatility, calc_value（各関数は (date, code) をキーとする dict リストを返す）。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応）を実装。
    - 情報係数（IC）計算（Spearman の ρ）および rank ユーティリティを実装。ties は平均ランクで処理。
    - factor_summary による基本統計量（count/mean/std/min/max/median）集計を実装。
    - 外部依存を使わず標準ライブラリと DuckDB のみで実装。

  - src/kabusys/research/__init__.py により主要関数を公開。

- 戦略（特徴量エンジニアリング・シグナル生成）
  - src/kabusys/strategy/feature_engineering.py
    - 研究環境で生成された生ファクターを正規化・合成して features テーブルへ保存する処理を実装（build_features）。
    - ユニバースフィルタ（最低株価300円、20日平均売買代金 >= 5億円）を実装。
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でのクリップ、日付単位のトランザクション置換挿入（冪等）を実装。
    - DuckDB を用いたトランザクションとバルク挿入で原子性を保証。

  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合して final_score を算出し、BUY/SELL シグナルを生成（generate_signals）。
    - デフォルトの重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）と閾値（0.60）を実装。ユーザー指定 weights の検証と正規化を実装。
    - component スコア算出: momentum（シグモイド平均）、value（PER を 20 を基準に変換）、volatility（低いほど高スコアへ反転）、liquidity（出来高比率のシグモイド）。
    - AI レジームスコアを元に Bear 判定を行い、Bear 時は BUY を抑制。
    - エグジット（SELL）判定: ストップロス（-8%）とスコア低下を実装。SELL 優先ポリシーを採用。
    - signals テーブルへ日付単位の置換（トランザクション/冪等）を実装。

- パッケージエクスポート（strategy）
  - src/kabusys/strategy/__init__.py で build_features / generate_signals を公開。

### Changed
- 設計方針の明文化
  - 各モジュールで Look-ahead bias を防ぐ実装方針、発注層への依存を持たせない（execution 層分離）方針を明記。
  - DuckDB をメインの分析ストレージとして使用し、読み取り・書き込みともに SQL + Python で完結する設計を採用。

### Fixed
- 初回リリースのため記載なし。

### Security
- ニュース収集にて defusedxml を利用し XML 関連攻撃を防止。
- news_collector で受信サイズ上限、URL スキーム制限、トラッキングパラメータ除去、IP/SSRF 防御等の設計方針を用意（実装の一部を含む）。
- J-Quants クライアントでトークン管理・自動リフレッシュを厳格に扱い、不正な再帰を防止（allow_refresh フラグ等）。

### Known limitations / TODO
- signal_generator に記載されている未実装条件:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有 60 営業日超の処理）
- news_collector の一部（実際の RSS フェッチ / XML パース周りの完全実装）が未掲載または未完了の可能性あり（提供コードは主要ユーティリティと方針を含む）。
- execution（発注）層はパッケージに存在するが、提供されたコード断片には実装が見当たらないため、実際の注文送信ロジックは別途実装が必要。
- 単体テスト・統合テストに関する記述・実装はコードからは確認できません。CI やテスト用フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD 等）は存在。

---

今後のリリース案（提案）
- バージョン 0.2.0: execution 層（kabu API 連携）の実装、発注ロジックと安全機構（送信前チェック、発注再試行等）。
- バージョン 0.3.0: ニュース記事の銘柄紐付け（news_symbols）、NLP によるニューススコアリングの統合、トレーリングストップ・時間決済の実装。
- テスト強化、型検査（mypy）・静的解析の導入、ドキュメント整備。

(以上)