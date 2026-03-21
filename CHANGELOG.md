# Changelog

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

## [Unreleased]

- 予定 / 未実装（コードから推測）
  - execution 層（発注ロジック）や監視（monitoring）の実装が不足。現状は strategy 層までで、発注 API への橋渡しは別実装が必要。
  - ニュース収集のフェッチ実装（RSS パース〜DB保存のフロー）は設計が整っているが、完全な公開API呼び出し・挿入結果の検証や細かな例外処理の追加が今後の改善候補。
  - より詳細なテスト（単体／統合）とエラーハンドリングの強化（特にネットワーク・DB周り）。

---

## [0.1.0] - 2026-03-21

### Added
- パッケージ初期リリースとして主要モジュールを追加。
  - kabusys.config
    - .env ファイルおよび環境変数の自動読み込み機構を実装。
    - プロジェクトルート検出（.git / pyproject.toml）に基づく自動ロード。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
    - .env の堅牢なパースロジックを実装（export プレフィックス対応、クォートとエスケープ、インラインコメント処理）。
    - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / システム環境（env, log_level）等のプロパティを取得・検証。
  - data パッケージ
    - jquants_client
      - J-Quants API クライアントを実装（ページネーション対応）。
      - レート制限管理（固定間隔スロットリング）を実装し 120 req/min を遵守。
      - リトライ（指数バックオフ、最大3回）、HTTP 429 の Retry-After 優先処理、401 時の自動トークンリフレッシュ（1回のみ）を実装。
      - fetch_* 系関数: 日足、財務、マーケットカレンダーの取得ロジックを実装。
      - save_* 系関数: raw_prices / raw_financials / market_calendar への冪等保存（ON CONFLICT DO UPDATE）を実装。
      - データ型変換ユーティリティ（_to_float, _to_int）を実装。
    - news_collector（収集設計とユーティリティ）
      - RSS 収集の設計方針とユーティリティを追加（URL正規化、トラッキングパラメータ除去、受信バイト上限、XML パースに defusedxml を使用など）。
      - デフォルトRSSソース設定、ID生成（正規化 URL の SHA-256）などの仕様を盛り込む。
  - research パッケージ
    - factor_research
      - モメンタム（1/3/6ヶ月, MA200乖離）、ボラティリティ（ATR20, 相対 ATR, 出来高指標）、バリュー（PER, ROE）などのファクター計算関数を実装。
      - DuckDB の SQL ウィンドウ関数を利用し、欠損・データ不足に対する扱いを明確化。
    - feature_exploration
      - 将来リターン calc_forward_returns（複数ホライズン対応）、Spearman ランク相関による IC 計算 calc_ic、ファクター統計 summary を実装。
      - ランク計算における同順位処理（平均ランク）を実装。
    - research パッケージ __all__ を整備。
  - strategy パッケージ
    - feature_engineering.build_features
      - research 側で計算した生ファクターをマージし、ユニバースフィルタ（最低株価・平均売買代金）を適用、Z スコア正規化（指定列）→ ±3 でクリップ、features テーブルへ日付単位で置換（トランザクション）する処理を実装。
      - DuckDB を利用した原子性ある置換（DELETE + bulk INSERT）を実装。
    - signal_generator.generate_signals
      - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
      - デフォルト重み（momentum 0.40 等）を用いた重み付け合算、ユーザー指定 weights の検証・正規化・リスケールに対応。
      - Bear レジーム判定（ai_scores の regime_score 平均が負の場合。ただしサンプル閾値を設定）により BUY シグナル抑制。
      - BUY シグナルは閾値（デフォルト 0.60）超過銘柄をランク付けして出力。SELL シグナルは保有ポジションに対してストップロス（-8%）やスコア低下で判定。
      - signals テーブルへ日付単位で置換（トランザクション）を実装。
  - パッケージ構成
    - kabusys.__init__ に public API リスト（data, strategy, execution, monitoring）・バージョンを定義。

### Changed
- (初回リリースのため該当なし)

### Fixed
- (初回リリースのため該当なし)

### Security
- ニュースパーシングで defusedxml を使用して XML 関連攻撃（XML Bomb 等）を軽減。
- news_collector は受信バイト数上限を設け、HTTP スキームチェック等で SSRF / 大量受信対策を考慮。
- jquants_client におけるトークン自動リフレッシュは無限再帰を避けるため allow_refresh フラグを導入。

### Known limitations / Notes
- execution（発注）層は実装ファイルが空であり、実際の発注は未実装。signals → 発注の橋渡しは別実装が必要。
- ニュース収集モジュールは設計・ユーティリティ（正規化等）が実装済みだが、RSS のフェッチ全体フロー（DB保存・シンボル紐付けの一連の実行）が完成するまで追加実装・検証が必要。
- 一部関数は DuckDB の特定テーブル構造（prices_daily, raw_financials, features, ai_scores, positions 等）を前提としており、スキーマ整備が必須。
- 外部依存は最小限を目指すが、defusedxml と duckdb は必須。

---

（この CHANGELOG はコードベースから推測して作成しています。実際の変更履歴や公開日付はプロジェクトの正式記録に基づいて更新してください。）