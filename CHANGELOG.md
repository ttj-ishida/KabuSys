Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

注: リリース日はコードベースから推測して記載しています。

Unreleased
----------

- 特になし

0.1.0 - 2026-03-19
------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージメタ情報: __version__ = "0.1.0"、パブリックモジュールとして data / strategy / execution / monitoring を公開。

- 環境設定
  - .env ファイルと環境変数を統合して読み込む自動ローダを実装。
    - プロジェクトルートは .git または pyproject.toml を起点に探索（CWD 非依存）。
    - 読み込み順序: OS 環境 > .env.local > .env。
    - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途）。
  - 高度な .env パーサを実装:
    - export プレフィックス対応、シングル／ダブルクォート対応（バックスラッシュエスケープ考慮）、インラインコメント処理。
  - Settings クラスにより設定値をプロパティ経由で取得:
    - J-Quants, kabu ステーション, Slack, データベースパスなどを提供。
    - 必須環境変数のチェック（未設定時に ValueError）。
    - KABUSYS_ENV / LOG_LEVEL の許容値チェックとヘルパープロパティ（is_live / is_paper / is_dev）。

- データ取得・保存 (data)
  - J-Quants API クライアント (jquants_client):
    - 固定間隔のレートリミッタ実装（120 req/min 想定）。
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx 再試行）。
    - 401 受信時の自動トークンリフレッシュ (1 回のみ)。
    - ページネーション対応の fetch_* 関数（daily_quotes, financial_statements, trading_calendar）。
    - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE による上書き/更新。
    - 取得時の fetched_at を UTC ISO8601 で記録し、look-ahead バイアスの追跡を可能に。
    - 入力変換ユーティリティ (_to_float / _to_int) により安全に型変換。
  - news_collector:
    - RSS フィード取得と記事保存の基盤実装。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ削除、フラグメント削除、クエリキーソート）。
    - 記事IDは正規化 URL の SHA-256 ハッシュ（先頭32文字）を利用して冪等性を確保。
    - defusedxml を用いた安全な XML パース、受信サイズ制限（10MB）、HTTP スキーム制限などセキュリティ対策。
    - バルク挿入のチャンク化、トランザクションによる効率的・安全な DB 保存。

- リサーチ (research)
  - factor_research:
    - モメンタム、ボラティリティ、バリュー関連ファクター算出関数を実装:
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均のカウントチェック）。
      - calc_volatility: 20日 ATR、atr_pct、avg_turnover、volume_ratio（true_range 計算の NULL 伝播制御）。
      - calc_value: target_date 以前の最新財務データを用いて PER / ROE を計算。
    - DuckDB のウィンドウ関数を活用した実装（営業日欠損を考慮したスキャン範囲のバッファ）。
  - feature_exploration:
    - calc_forward_returns: LEAD を用いた複数ホライズン（デフォルト [1,5,21]）の将来リターン計算。
    - calc_ic: ファクターと将来リターン間の Spearman ランク相関（IC）を計算。ties に対して平均ランクを採用し、サンプル不足時は None を返す。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を標準ライブラリのみで算出。
    - rank: 丸め（round(..., 12)）による安定した同順位処理を行うランク関数。

- 戦略 (strategy)
  - feature_engineering.build_features:
    - research の生ファクターを統合して features テーブルへ書き込み。
    - ユニバースフィルタ（最低株価300円・20日平均売買代金5億円）を適用。
    - 指定列の Z スコア正規化（kabusys.data.stats の zscore_normalize 利用）と ±3 でのクリップ。
    - 日付単位の置換（DELETE + bulk INSERT）をトランザクションで実行し冪等性と原子性を保証。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して各銘柄の final_score を算出（デフォルト重みと閾値を採用）。
    - component スコア算出ロジック（momentum/value/volatility/liquidity/news）と sigmoid/平均化ユーティリティを実装。
    - AI レジームスコア集計による Bear 判定（サンプル閾値あり）。Bear 時は BUY シグナルを抑制。
    - BUY シグナル（閾値超え）と SELL シグナル（ストップロス -8% / スコア低下）を生成。
    - 保有銘柄の SELL を優先し、signals テーブルへ日付単位で置換して保存（トランザクション + bulk insert）。
    - weights の検証・補完・正規化処理、無効値に対するログ警告処理。

Changed
- （初回リリースのため変更履歴は無し）

Fixed
- （初回リリースのため修正履歴は無し）

Security
- RSS パーサに defusedxml を利用して XML 関連の攻撃を緩和。
- news_collector で受信サイズ上限・HTTP スキーム制限・トラッキングパラメータ除去を実装し SSRF やメモリ DoS を考慮。
- J-Quants クライアントで 401 ハンドリングとリトライ・レート制限を実装し、安定した認証と API 利用を支援。

Known limitations / TODO
- signal_generator の SELL 条件の一部（トレーリングストップ、時間決済）は未実装。positions テーブルに peak_price / entry_date 等の拡張が必要。
- news_collector の記事→銘柄マッピング（news_symbols との紐付け等）は実装想定だが、コード中では主な正規化・保存ロジックが中心。
- 一部処理は DuckDB のテーブル定義（カラム名 / PK / インデックス）に依存するため、利用前にスキーマ整備が必要。

Authors
- kabusys 開発チーム（コードベースより推測）

License
- 明示的なライセンスファイルはコードからは特定できません。配布時に LICENSE を確認してください。