# CHANGELOG

すべての注目すべき変更点はこのファイルに記載します。  
このプロジェクトは Keep a Changelog の慣習に従っています。

注意: 以下は提供されたコードベースの内容・コメントから推測してまとめた変更履歴です。

## [Unreleased]

(なし)

## [0.1.0] - 2026-03-21

### Added
- パッケージ初期リリースとして kabusys モジュール群を追加。
  - パッケージメタ情報: __version__ = "0.1.0"、公開 API を __all__ で定義。
- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env の行パース機能を実装（コメント／export 形式／クォート／インラインコメント等を考慮）。
  - 環境変数取得用 Settings クラスを実装（必須変数チェック、既定値、型変換、検証ロジック）。
  - KABUSYS_ENV と LOG_LEVEL のバリデーション（許容値チェック）。
- データ取得・保存（kabusys.data）
  - J-Quants API クライアント (jquants_client)
    - レート制限（120 req/min）を守る固定間隔レートリミッタを実装。
    - 再試行ロジック（指数バックオフ、最大リトライ回数）を実装（408/429/5xx 等を対象）。
    - 401 受信時の ID トークン自動リフレッシュ（1 回のみ）とキャッシュ機構。
    - ページネーション対応の fetch_* 関数（株価・財務・カレンダー）を実装。
    - DuckDB への冪等保存関数を実装（ON CONFLICT による upsert）。
    - 型安全な変換ユーティリティ _to_float / _to_int を提供。
  - ニュース収集モジュール (news_collector)
    - RSS フィード取得と記事正規化のフローを実装（デフォルトソース: Yahoo Finance）。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）を実装。
    - 受信サイズ制限（最大 10MB）や INSERT チャンク化などの保護策を追加。
    - defusedxml を利用した XML パースにより XML Bomb 等の脆弱性対策を考慮。
    - 記事 ID を正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を確保する設計（コメント）。
- 研究・ファクター計算（kabusys.research）
  - factor_research: Momentum / Volatility / Value の計算関数を実装。
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200 日移動平均乖離）。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（20 日ウィンドウ）。
    - calc_value: per, roe（raw_financials から最近の財務データを取得）。
    - 各関数は DuckDB の prices_daily / raw_financials を参照し、(date, code) 形式の辞書リストを返す。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、情報係数 IC 計算（calc_ic）、ファクター統計サマリー（factor_summary）、ランク変換（rank）を実装。
    - calc_forward_returns は複数ホライズンを同時に取得可能で、入力検証（horizons の制約）あり。
    - calc_ic は Spearman の ρ をランク変換経由で計算し、データ不足時は None を返す。
- 戦略層（kabusys.strategy）
  - feature_engineering.build_features
    - research の生ファクターを統合し、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化、±3 でクリップし features テーブルへ日毎 upsert（トランザクションで原子性保証）。
    - 価格参照は target_date 以前の最新価格を使用（ルックアヘッドバイアス対策）。
  - signal_generator.generate_signals
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - 最終スコア final_score を重み付き合算で計算（デフォルト重みを提供、ユーザ指定重みは検証・再スケーリング）。
    - Bear レジーム判定を実装（ai_scores の regime_score の平均が負 → BUY を抑制）。
    - BUY（デフォルト閾値 0.60）および SELL シグナル生成（ストップロス -8% / スコア低下）を実装。
    - positions / prices を参照してエグジット判定を行い、signals テーブルへ日付単位で置換挿入（トランザクションで原子性保証）。
    - SELL 優先ポリシー（SELL 対象は BUY から除外しランクを再付与）。
  - signal_generator 内での未実装部分はコメントで明示（例: トレーリングストップ、時間決済には peak_price/entry_date が必要）。
- 共通ユーティリティとロギング
  - 各モジュールで詳細なログメッセージ（info/warning/debug）を出力する設計。
  - 例外発生時のロールバック処理、失敗時の警告出力を導入。

### Changed
- 初版のため既存リリースからの変更はなし（初期実装）。

### Fixed
- 初版のため既存バグ修正履歴はなし。

### Security
- news_collector は defusedxml を使用し XML パースの安全性を高める。
- RSS 取得でのレスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）によりメモリ DoS 対策を実装。
- J-Quants クライアントは認証トークンの自動更新ロジックを実装し、401 ハンドリングを行うことで認証の安定性を向上。
- .env 読み込み時に OS 環境変数を保護する protected パラメータを導入（.env.local の上書き制御を安全に実行）。

### Known issues / Limitations
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装（コメントで明示）。positions テーブルに peak_price / entry_date 等の追加が必要。
- news_collector の一部（IP ベースの SSRF 緩和、受信 URL のホスト/IP 検査等）は TODO（設計コメントはいくつか存在するが実装の有無はコードの抜粋に依存）。
- 外部依存を最小化する設計だが、大量データ処理時のパフォーマンス調整（DuckDB クエリの最適化等）は今後の改善余地あり。
- calc_forward_returns は営業日カウントを内部で仮定しており、カレンダー日→営業日マッピングが前提の実装になっていることに注意。

---

参考: 各モジュールの詳細な設計意図・制約はソース内のドキュメント文字列（docstring）に記載されています。必要であれば各機能ごとにリリースノート（利用方法・注意点・サンプル）を追加で作成します。