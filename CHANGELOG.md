Keep a Changelog
=================

すべての重要な変更はこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

[0.1.0] - 2026-03-22
-------------------

Added
- パッケージ基盤
  - 初期バージョンを追加。パッケージ名: kabusys、バージョン: 0.1.0。
  - パブリック API エクスポートを定義 (kabusys.__all__)。

- 環境設定管理 (kabusys.config)
  - .env / .env.local ファイルまたは OS 環境変数から設定を読み込む自動ロード機能を追加。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定（配布後も CWD に依存しない）。
  - .env パーサーの強化:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント判定ルールを実装。
    - 無効行（コメント／空行／不正フォーマット）は無視。
  - .env 読み込み時の上書き制御:
    - override フラグ、OS 環境変数を保護する protected セットをサポート。
    - ファイル読み込み失敗時は警告を出す。
  - Settings クラスを実装し、アプリケーションで使用する主要設定プロパティを提供（J-Quants / kabu API / Slack / DB パス / 環境・ログレベル判定等）。
    - KABUSYS_ENV / LOG_LEVEL の値チェック（許容値以外は ValueError）。

- 戦略: 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - research 側で計算した生ファクターを正規化・合成して features テーブルへ保存する build_features(conn, target_date) を実装。
  - 処理の主な特徴:
    - calc_momentum / calc_volatility / calc_value からファクターを取得してマージ。
    - ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5 億円）を適用。
    - 指定列を Z スコア正規化後 ±3 でクリップ（外れ値抑制）。
    - 日付単位で既存レコードを削除してからのトランザクション＋バルク挿入により冪等性と原子性を保証。
    - DuckDB を使用した SQL ベースの価格取得に対応（直近の価格参照で休場日対応）。

- 戦略: シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold, weights) を実装し、features / ai_scores / positions を基に BUY / SELL シグナルを作成して signals テーブルに保存。
  - 主要なロジック:
    - momentum/value/volatility/liquidity/news のコンポーネントスコア計算（シグモイド変換・補完ルール）。
    - AI スコア（ai_scores）を統合。レジーム（regime_score）の平均が負のときは Bear レジームと判定し BUY を抑制。
    - weights の入力検証・フォールバック・正規化を実装（未知キーや非数値は無視、合計が 1 になるよう再スケール）。
    - SELL はエグジット条件（ストップロス -8% / final_score < threshold）で判定。price 欠損時は判定をスキップして警告を出力。
    - signals テーブルへ日付単位で置換挿入（トランザクション処理、ROLLBACK 失敗時の警告ログあり）。
    - SELL 優先ポリシー: SELL 対象は BUY から除外してランク再付与。

- Research ユーティリティ (kabusys.research)
  - ファクター計算モジュール (factor_research):
    - calc_momentum(conn, target_date): mom_1m/3m/6m・ma200_dev を計算。データ不足時は None。
    - calc_volatility(conn, target_date): ATR(20)、相対ATR(atr_pct)、20日平均売買代金、volume_ratio を計算。NULL の伝播制御に注意。
    - calc_value(conn, target_date): raw_financials から最新財務を取って PER・ROE を計算（EPS=0/欠損は PER=None）。
  - 特徴量探索 (feature_exploration):
    - calc_forward_returns(conn, target_date, horizons): 指定ホライズンの将来リターンを一括で取得。horizons のバリデーション（1〜252 日）。
    - calc_ic(factors, forwards, factor_col, return_col): スピアマンのランク相関（IC）を計算。サンプル数 3 未満では None。
    - rank(values): 同順位は平均ランクを返す。丸め（round 12）で ties 検出漏れを抑制。
    - factor_summary(records, columns): 各カラムの count/mean/std/min/max/median を算出（None を除外）。
  - research パッケージ __all__ を整備。

- バックテストフレームワーク (kabusys.backtest)
  - PortfolioSimulator 実装:
    - 日次スナップショット DailySnapshot、約定記録 TradeRecord を定義。
    - execute_orders: SELL を先に処理、BUY は alloc に基づき始値で約定（スリッページ・手数料考慮）。BUY の場合は手数料込みで株数を再計算して調整。
    - _execute_buy/_execute_sell: 平均取得単価の更新、cash の調整、TradeRecord 生成。
    - mark_to_market: 終値で時価評価し DailySnapshot を記録。終値欠損は 0 として警告。
  - backtest.metrics: バックテスト評価指標を計算する calc_metrics と内部関数群を実装（CAGR, Sharpe, MaxDrawdown, WinRate, PayoffRatio, total_trades）。
  - run_backtest(conn, start_date, end_date, ...):
    - 本番 DB から In-memory DuckDB へ必要テーブルをコピーする _build_backtest_conn（signals/positions を汚さない）。
    - データコピーの範囲は start_date - 300 日のバッファを使用。
    - 日次ループの主要処理フロー実装: 約定 → positions 書き戻し → 時価評価 → generate_signals（bt_conn 上で）→ ポジションサイジング → 次日の注文生成。
    - _fetch_open_prices/_fetch_close_prices/_write_positions/_read_day_signals 等のユーティリティを追加。

- 安全性・ロギング
  - 主要箇所でのエラーハンドリングとログ出力（warning/info/debug）を充実させ、ROLLBACK 失敗時に警告を出す等の保険措置を追加。

Changed
- なし（初期リリースのため変更履歴はなし）。

Fixed
- なし（初期リリース）。

Deprecated
- なし。

Removed
- なし。

Security
- 環境変数の自動ロードで OS 環境変数を上書きしないデフォルト挙動、保護キーセットを導入。自動ロードの無効化オプションを提供。

Notes / Known limitations / TODOs
- execution パッケージは存在するが実際の発注 API との接続実装は含まれていない（本バージョンでは execution 層への依存を持たない設計）。
- signal_generator のエグジット条件で未実装の項目:
  - トレーリングストップ（peak_price が必要）
  - 時間決済（保有日数に基づくクローズ）
- calc_value: PBR・配当利回りは未実装。
- PortfolioSimulator の SELL は全量クローズのみ（部分利確・部分損切りは未対応）。
- 外部依存を極力排しているため、DataFrame ベースの高速探索等は未採用（今後の拡張候補）。
- run_backtest の日次ループは主要ロジックを実装済みだが、上位の実運用フローやエッジケースの追加検証が必要。

開発者向けメモ
- DuckDB を前提とした SQL 実行を多用しているため、テーブルスキーマ（prices_daily, features, ai_scores, positions, raw_financials, market_calendar 等）が正しく初期化されていることを前提とする。
- Settings の必須環境変数が未設定だと ValueError を送出するため、テスト/CI 環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を使うか必要な環境変数を整備すること。

---