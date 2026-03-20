# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトの初回リリースに相当する内容は、コードベースから推測して記載しています。

全般的な注記
- 本リポジトリは日本株の自動売買システム「KabuSys」を想定したライブラリ群です。
- 内部的に DuckDB をデータストアとして利用し、研究（research）・データ収集（data）・戦略（strategy）・実行（execution）層を分離した設計が採用されています。
- 日付はこの CHANGELOG 作成日（2026-03-20）を使用しています（実際のリリース日が異なる場合は適宜修正してください）。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-20

Added
- パッケージ初期リリース。
  - パッケージメタ情報: kabusys v0.1.0（src/kabusys/__init__.py）。
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを提供。
  - 自動 .env ロード機能（プロジェクトルート判定: .git または pyproject.toml の検出）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサーは以下をサポート:
    - コメント行・空行のスキップ、"export KEY=val" 形式の対応
    - シングル/ダブルクォート、バックスラッシュエスケープ処理
    - インラインコメントの扱い（クォートの有無に応じたコメント判別）
  - OS 環境変数の上書きを防ぐ protected オプションを使用した安全なロード処理。
  - 必須環境変数取得時の検証と適切なエラーメッセージ（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
  - env 値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）とヘルパープロパティ（is_live / is_paper / is_dev）。
- データ取得・保存（J-Quants クライアント） (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。
  - 固定間隔レートリミッタ（120 req/min 想定）を実装して API 呼び出しを制御。
  - 再試行ロジック（指数バックオフ、最大 3 回、対象ステータス: 408/429/5xx）を実装。
  - 401 応答時にリフレッシュトークンで自動的に ID トークンを更新して 1 回リトライする機能を実装（無限再帰防止あり）。
  - ページネーション対応の fetch_* 関数:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（取引カレンダー）
  - DuckDB への冪等保存用関数（ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes → raw_prices テーブルへの保存
    - save_financial_statements → raw_financials テーブルへの保存
    - save_market_calendar → market_calendar テーブルへの保存
  - データ型変換ユーティリティ: _to_float / _to_int（安全な変換・欠損値処理を行う）。
  - fetched_at を UTC ISO 8601 で記録し、いつデータを取得したかをトレース可能にする設計。
- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからニュースを収集して raw_news に保存する基本実装。
  - セキュリティおよび堅牢性対策:
    - defusedxml を用いた XML パース（XML Bomb 等の対策）。
    - 受信データ上限（MAX_RESPONSE_BYTES）を設けてメモリ DoS を軽減。
    - URL 正規化（トラッキングパラメータ除去、フラグメント削除、クエリソート）を実装し、記事 ID を冪等に生成（SHA-256 の一部を使用）。
    - SSRF を防ぐため HTTP/HTTPS のみ許容する設計を想定（コメントで明記）。
    - バルク INSERT のチャンク化とトランザクション集約による効率化。
  - デフォルトの RSS ソースに Yahoo! Finance のビジネスカテゴリを登録（DEFAULT_RSS_SOURCES）。
- 研究（research）モジュール
  - factor_research (src/kabusys/research/factor_research.py)
    - モメンタム、ボラティリティ、バリュー関連のファクター計算関数を実装:
      - calc_momentum: mom_1m/mom_3m/mom_6m / ma200_dev（200日移動平均乖離）
      - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio（ATR・出来高）
      - calc_value: per / roe（raw_financials と prices_daily を組み合わせ）
    - DuckDB のウィンドウ関数を活用した効率的な SQL 実装（営業日の欠損・範囲バッファを考慮）。
  - feature_exploration (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算: calc_forward_returns（複数ホライズン対応、データ不足時は None を返す）。
    - IC（Information Coefficient）計算: calc_ic（Spearman の ρ をランク変換で算出、サンプル不足時は None）。
    - ランク変換ユーティリティ: rank（同順位は平均ランク）。
    - factor_summary: ファクター列の基本統計量（count/mean/std/min/max/median）。
    - いずれも外部ライブラリに依存せず標準ライブラリ + DuckDB のみで設計。
  - research パッケージの __all__ に主要ユーティリティを公開。
- 戦略（strategy）モジュール
  - feature_engineering (src/kabusys/strategy/feature_engineering.py)
    - 研究側で計算した raw ファクターをマージし、ユニバースフィルタ（最低株価/最低売買代金）を適用。
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）と ±3 のクリッピング。
    - features テーブルへの日付単位の置換（BEGIN/COMMIT/ROLLBACK を用いたトランザクション）で冪等性を確保。
    - ユニバース条件（_MIN_PRICE=300円、_MIN_TURNOVER=5e8 円）を実装。
  - signal_generator (src/kabusys/strategy/signal_generator.py)
    - features と ai_scores を統合して最終スコア（final_score）を算出し、BUY / SELL シグナルを生成して signals テーブルに保存。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（シグモイド変換・補完ロジックあり）。
    - 重み指定の補完と正規化（_DEFAULT_WEIGHTS をデフォルト、ユーザー渡し重みは検証・無効値を警告して無視）。
    - Bear レジーム判定（ai_scores の regime_score の平均が負の場合）、Bear 時は BUY シグナルを抑制。
    - エグジット（SELL）ロジック:
      - ストップロス（終値が avg_price から -8% 以下）
      - final_score が閾値未満
      - 価格欠損時の SELL 判定スキップや features 未登録銘柄の扱い（score=0 と見なす）を安全に処理。
    - signals テーブルへの日付単位置換で冪等性を確保。
  - strategy パッケージは build_features, generate_signals を公開。
- データ統計ユーティリティ公開
  - kabusys.data.stats.zscore_normalize を研究 / 戦略で利用する前提で公開（参照のみ。実装ファイルはこのスナップショット上で参照される）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- news_collector で defusedxml を採用し XML 関連の脆弱性に対処。
- ニュース RSS の受信上限と URL 正規化による追跡パラメータ除去など、外部入力の安全化を実装。
- J-Quants クライアントの再試行/429 Retry-After 処理で過負荷回避を考慮。

Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - .env.example を参照して .env を作成すること（config._require のメッセージに従う）。
- 自動 .env ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時など）。
- DuckDB スキーマ（raw_prices / raw_financials / prices_daily / features / ai_scores / signals / positions / market_calendar 等）は本リリースに合わせて事前に作成しておく必要があります（スキーマ定義は別途管理）。
- signal_generator の重み (weights) をカスタム指定する場合は、既知のキー（momentum, value, volatility, liquidity, news）のみ有効で、非数値や負値は無視されます。合計が 1.0 でない場合は再スケールされます。

参考（実装上の主要挙動）
- 各種 DB 書き込みは可能な限りトランザクションで囲い、「日付単位の置換（DELETE → INSERT）」を実行して冪等性を担保しています。
- 研究モジュールは外部ライブラリに依存せず軽量に設計されているため、分析パイプラインに組み込みやすい想定です。

---

今後の予定（想定）
- execution 層の発注ロジック（kabuステーション API 統合・注文管理）の実装。
- ai_scores の生成パイプライン、news→AIスコア連携の実装強化。
- 単体テスト・統合テスト、CI の追加、ドキュメントの拡充。

（必要であれば、この CHANGELOG を実際のコミット履歴やリリース日付、変更者情報に合わせて微調整します。）