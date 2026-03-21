0.1.0 - 2026-03-21
------------------

注: このリリースはコードベースの初期リリース相当と想定し、ソースコード内の実装・コメントから機能・設計上の決定を推測してまとめています。

Added
- パッケージ基盤
  - kabusys パッケージを公開。トップレベルで data, strategy, execution, monitoring を __all__ に設定。
  - バージョン: 0.1.0

- 設定管理
  - 環境変数/設定読み込みモジュールを追加（kabusys.config）。
  - .env / .env.local ファイルの自動ロード機能を提供（プロジェクトルート(.git または pyproject.toml) を基準に探索）。
  - 行パースの堅牢化: export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント処理に対応。
  - 自動ロード無効化フラグ(KABUSYS_DISABLE_AUTO_ENV_LOAD)をサポート。
  - Settings クラスを導入し、J-Quants / kabuステーション / Slack / DB パス / 環境種別 等のアクセサとバリデーションを提供。
  - 環境値検証: KABUSYS_ENV と LOG_LEVEL の許容値チェック。

- データ取得・保存（J-Quants）
  - J-Quants API クライアントを実装（kabusys.data.jquants_client）。
    - 固定間隔レートリミッタ（120 req/min 相当）を実装。
    - リトライ戦略（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 受信時の自動トークンリフレッシュと 1 回リトライを実装。
    - ページネーション対応の fetch_* 関数を提供: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB へ冪等保存関数を追加: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を使用）。
    - レスポンス JSON デコードエラー・ネットワークエラーのハンドリング、ログ出力を実装。
    - データ取得時の fetched_at を UTC ISO8601 で記録し、Look-ahead バイアス追跡に配慮。

- ニュース収集
  - RSS 収集モジュールを追加（kabusys.data.news_collector）。
    - RSS 取得・XML パース（defusedxml で XML 脆弱性対策）。
    - URL 正規化（tracking パラメータ削除、スキーム/ホスト正規化、フラグメント除去、クエリソート）。
    - 記事ID の SHA-256 ベース生成（先頭32文字）による冪等性。
    - レスポンス受信サイズ上限 (10MB) や SSRF 防止の考慮、バルク INSERT チャンク化などの安全対策。
    - raw_news / news_symbols への保存設計（ON CONFLICT DO NOTHING 等を想定）。

- ファクター計算（Research）
  - factor_research モジュールを実装（kabusys.research.factor_research）。
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev を DuckDB の prices_daily から計算。
    - calc_volatility: 20 日 ATR / 相対 ATR (atr_pct), 20 日平均売買代金 (avg_turnover), volume_ratio を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（最新財務レコードを report_date <= target_date から選択）。
    - データ欠損時は None を返す設計、営業日・ウィンドウサイズに対するスキャンバッファを確保。

  - feature_exploration モジュールを実装（kabusys.research.feature_exploration）。
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: Spearman のランク相関（IC）計算。
    - factor_summary: 各ファクター列の基本統計量(count/mean/std/min/max/median) を計算。
    - rank: 平均ランク（同順位は平均）を返すユーティリティ。

  - research パッケージの __all__ を整備し、主要ユーティリティを再エクスポート。

- 特徴量エンジニアリング（Strategy）
  - feature_engineering モジュールを実装（kabusys.strategy.feature_engineering）。
    - build_features(conn, target_date): research の生ファクターを結合、ユニバースフィルタ（最低株価300円、20日平均売買代金 >= 5億円）を適用。
    - 正規化: 指定カラム群を zscore_normalize で標準化、±3 でクリップ。
    - features テーブルへ日付単位で置換（DELETE→INSERT をトランザクションで行い原子性を確保）。
    - 休場日や当日の欠損へ対応するため target_date 以前の最新価格を用いる等、ルックアヘッド対策。

- シグナル生成（Strategy）
  - signal_generator モジュールを実装（kabusys.strategy.signal_generator）。
    - generate_signals(conn, target_date, threshold=0.60, weights=None):
      - features と ai_scores を統合して各銘柄のコンポーネントスコア(momentum/value/volatility/liquidity/news) を算出。
      - コンポーネントの欠損は中立値 0.5 で補完。
      - 最終スコア final_score は重み付き和（デフォルト重みを定義）で計算。重みは渡された辞書で上書き可能（入力検証・再スケーリングあり）。
      - Bear レジーム（ai_scores の regime_score 平均が負）検知時は BUY シグナルを抑制。
      - BUY: threshold 超過銘柄を採用（Bear 時は抑制）。
      - SELL: positions テーブルの保有ポジションに対してストップロス（終値基準 -8%）または final_score < threshold を判定して SELL を生成。価格欠損時は SELL 判定をスキップ。
      - SELL が出た銘柄は BUY から除外（SELL 優先）。
      - signals テーブルへ日付単位で置換（トランザクション + バルク挿入）。
    - 設計上の注意点をコードコメントで明示（ルックアヘッド防止、execution 層に依存しない等）。

- DB・数値ユーティリティ
  - duckdb を前提とした SQL/Python 混合の実装。トランザクション制御（BEGIN/COMMIT/ROLLBACK）やエラーロギングを導入。
  - 型変換ユーティリティ (_to_float / _to_int) を追加（save_* 内で利用）。

Changed
- N/A（初期リリース相当のため既存機能の変更履歴は無し）

Fixed
- N/A（初期リリース相当）

Deprecated
- N/A

Removed
- N/A

Security
- RSS の XML パースに defusedxml を使用して XML ベースの攻撃を軽減。
- ニュース収集で受信サイズ上限を設ける等、メモリ DoS 対策を導入。
- HTTP 呼び出し時に SSRF や不正 URL を避けるためのチェックを設計に含める（news_collector のコメントより）。

Notes / Known limitations / TODO
- signal_generator の SELL 条件について、トレーリングストップや時間決済（保有 60 営業日超）などは未実装（positions テーブルに peak_price / entry_date が必要）。コードコメントで未実装として明記。
- 一部の安全・正確性処理は設計コメントとして記載されているが、運用面（例: Retry-After の多様な形式、外部 API の変化）では追加のテスト／強化が必要。
- execution パッケージは存在するが、今回のコードベースでは未実装（空の __init__）。発注ロジックは別層として設計されている模様。
- 外部依存を最小限にする設計（標準ライブラリ中心）だが、実行環境では duckdb と defusedxml のインストールが必要。

参考
- 各モジュール内の docstring に設計方針・意図・参照ドキュメント（StrategyModel.md, DataPlatform.md 等）が記載されており、実装はそれら仕様に準拠することを意図しています。