# Changelog

すべての注目すべき変更を一元管理します。フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-03-20

初回リリース — 日本株自動売買システム「KabuSys」の基盤機能を実装しました。以下はコードベースから推測される主な追加点と設計上の重要な振る舞いの概要です。

### Added
- パッケージ基盤
  - パッケージエントリポイント: kabusys.__init__（バージョン 0.1.0、公開 API の一覧設定）。
- 設定管理
  - kabusys.config
    - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を探索して検出）。
    - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .env と .env.local の優先順位と .env.local による上書き実装。
    - .env パーサーの強化: export プレフィックス対応、シングル/ダブルクォート、エスケープ、インラインコメント処理、無効行スキップ。
    - protected（OS 環境変数）の概念を用いた安全な上書きロジック。
    - Settings クラスによる型付けされたプロパティ（J-Quants トークン、kabu API 設定、Slack トークン/チャンネル、DB パス、環境／ログレベル検証、is_live/is_paper/is_dev ヘルパー）。
    - 環境変数未設定時の明確なエラー（_require）。
- データ取得 / 保存（Data レイヤ）
  - kabusys.data.jquants_client
    - J-Quants API クライアントの実装（ページネーション対応）。
    - 固定間隔レートリミッタ（120 req/min ベース）を実装。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx の再試行と 401 のトークン自動リフレッシュをサポート）。
    - id_token のモジュールレベルキャッシュ、get_id_token 実装。
    - fetch_* 系関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を実装。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装し、冪等（ON CONFLICT DO UPDATE / DO NOTHING）を採用。
    - データ変換ユーティリティ（_to_float, _to_int）を追加。
    - 取得時刻（fetched_at）を UTC ISO8601 で記録し、Look-ahead バイアス追跡可能に。
  - kabusys.data.news_collector
    - RSS フィードからニュースを収集して raw_news に保存する処理（記事 ID = 正規化 URL の SHA-256 ハッシュ短縮）。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）。
    - セキュリティ対策: defusedxml を使用した XML パース、受信サイズ上限（10 MB）、HTTP スキーム検証、SSRF 緩和の工夫。
    - バルク挿入チャンク処理やトランザクション単位での保存、INSERT RETURNING による正確な挿入数取得を想定。
- リサーチ（研究用）モジュール
  - kabusys.research.factor_research
    - Momentum / Volatility / Value のファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB のウィンドウ関数を活用した高性能な SQL ベース計算。
    - 各ファクターでデータ不足時に None を扱う方針（安全な欠損処理）。
  - kabusys.research.feature_exploration
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応・入力検証）。
    - IC（Information Coefficient）計算（calc_ic、Spearman の ρ をランクで計算、サンプル不足は None を返す）。
    - ランク付けユーティリティ（rank）とファクター統計サマリー（factor_summary）。
  - kabusys.research.__init__ に主要関数をエクスポート。
- 戦略（Strategy）
  - kabusys.strategy.feature_engineering
    - build_features: research の生ファクターを取得、ユニバースフィルタ（最低株価・最低平均売買代金）適用、Zスコア正規化、±3 クリップ、features テーブルへ日付単位で置換（トランザクションによる原子性）。
    - ユニバース基準の定義（_MIN_PRICE=300 円、_MIN_TURNOVER=5e8 円）。
  - kabusys.strategy.signal_generator
    - generate_signals: features と ai_scores を統合し最終スコア（final_score）を算出、BUY/SELL シグナルを生成して signals テーブルへ日付単位で置換（冪等）。
    - 統合重みのデフォルト（momentum/value/volatility/liquidity/news）と閾値（デフォルト 0.60）を実装。外部から weights を渡せるが妥当性チェックと自動正規化を行う。
    - ストップロス（-8%）やスコア低下による SELL 条件を実装（positions テーブル参照）。
    - Bear レジーム判定（ai_scores の regime_score を集計、サンプル数閾値を考慮して判定）に基づく BUY 抑制。
    - 欠損コンポーネントは中立値 0.5 で補完するポリシー。
- データ変換 / 統計ユーティリティ
  - kabusys.data.stats.zscore_normalize（明示的に import して利用されていることを確認）。

### Changed
- （初版のため歴史的差分なし）ただし各モジュールは以下の設計ガイドラインに従って構築:
  - ルックアヘッドバイアス回避（target_date 時点のデータのみ使用、fetched_at を記録）。
  - 発注 / execution 層への依存排除（戦略モジュールは発注 API に依存しない）。
  - DuckDB を単一の真理ソース（prices_daily, raw_financials, features, ai_scores, positions, signals 等）として利用。
  - 冪等性と原子性を重視した DB 操作（DELETE→INSERT、トランザクション管理、ON CONFLICT）。

### Fixed
- （初版のため既知のバグ修正履歴なし）しかし次のような堅牢化が施されています:
  - ネットワーク/HTTP エラーや JSON デコード失敗、トークン期限切れに対する明示的な例外処理とリトライロジック。
  - .env 読み込み時のファイル I/O エラーは警告で扱いプロセスを停止させない。
  - DB 保存時の PK 欠損行はスキップしてログ出力。

### Security
- news_collector: defusedxml による XML の安全な解析、受信サイズ制限、URL 正規化による追跡パラメータ除去など SSRF / DoS / XML Bomb 対策を導入。
- jquants_client: Authorization ヘッダ管理とトークン自動更新、HTTP エラーハンドリングにより不正・例外状態を適切に扱う。

### Notes / Known limitations
- execution 層（実際の発注ロジック）はパッケージに含まれていないか、空の __init__ に留められており、直接の発注実装は別実装を想定。
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装で、positions テーブルに追加情報（peak_price / entry_date）が必要。
- news_collector のRSS取得・パースの詳細実装（HTTP ヘッダ/タイムアウト扱いの微調整や記事→銘柄紐付けロジックの実装）はコメントベースで設計指針が存在するが、実際の紐付け詳細は要実装/確認。
- 一部関数は外部 DB スキーマ（テーブル/カラム）に依存しており、運用前に DuckDB スキーマの作成が必要。

---

今後のリリースでは以下を想定しています（優先度順）:
- execution 層の発注ロジック実装（kabu API 経由の売買実行、安全確認、注文管理）。
- モニタリング / アラート（Slack 通知やメトリクス収集）の実装。
- news_collector の記事→銘柄マッチング、自然言語処理による sentiment/ai_score 生成パイプライン。
- 戦略のパラメータ最適化用のテストスイートとバックテスト機能の整備。

--- 

(この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートは開発履歴や Git コミットログを基に補完してください。)