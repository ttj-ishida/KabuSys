# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

全般
- DuckDB を主要なデータストアとして利用する設計（prices_daily / features / ai_scores / raw_financials 等を前提）
- パッケージバージョン: 0.1.0（初版）

Unreleased
- （なし）

0.1.0 - 2026-03-22
Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys, バージョン 0.1.0
  - 公開 API の __all__ に data/strategy/execution/monitoring を定義（execution は現時点では空のプレースホルダ）
- 環境設定管理（kabusys.config）
  - .env ファイルと環境変数の自動読み込み機能を実装
    - プロジェクトルートの自動検出は .git または pyproject.toml を探索して判定
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能
  - .env パーサを実装
    - export KEY=val 形式対応
    - シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメントの扱いに対応
    - クォートなしでの '#' の扱いは直前が空白/タブの場合のみコメントとみなすなどの実用的ルールを実装
  - 上書き挙動（override）と protected（OS 環境変数保護）をサポート
  - 必須環境変数のチェック用 _require と Settings クラスを提供
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等のプロパティを定義
    - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL のバリデーションを実施
    - デフォルトの DB パス（DuckDB / SQLite）を設定可能
- 戦略（kabusys.strategy）
  - 特徴量エンジニアリング（feature_engineering.build_features）
    - research モジュール（calc_momentum / calc_volatility / calc_value）から生ファクターを取得して統合
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5億円）を実装
    - 正規化: 指定列を Z スコア正規化し ±3 でクリップ（外れ値抑制）
    - features テーブルへの日付単位置換（DELETE + bulk INSERT）で冪等かつ原子性を確保（トランザクション使用）
    - 欠損や非有限値を考慮した安全な処理
  - シグナル生成（signal_generator.generate_signals）
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出
    - コンポーネントの変換:
      - Z スコアをシグモイド変換して [0,1] にマップ
      - PER は 20 を基準とした変換（PER=20 → 0.5、PER→0 → 1.0、PER→∞ → 0.0）
      - volatility（atr_pct）は反転して低ボラが高スコアとなるよう変換
      - AI ニューススコアは未登録時に中立（0.5）で補完
    - 最終スコア final_score は重み付き合算（デフォルト重みを定義）で計算、weights のバリデーションおよび正規化処理を実装
    - Bear レジーム検出: ai_scores の regime_score 平均が負（かつサンプル数閾値を満たす）場合に BUY シグナルを抑制
    - SELL シグナル（エグジット）判定:
      - ストップロス（終値/avg_price - 1 < -8%）を最優先
      - final_score が閾値未満の場合にクローズ（score_drop）
      - positions テーブル参照や価格欠損時のスキップとログ出力を実装
    - signals テーブルへの日付単位置換をトランザクションで実行（冪等）
    - ログ出力により処理状況を可視化
- Research（kabusys.research）
  - ファクター計算（factor_research）
    - momentum: mom_1m/mom_3m/mom_6m、200日移動平均乖離率（ma200_dev）を DuckDB 上のウィンドウ関数で算出
    - volatility: 20日 ATR, atr_pct, 20日平均売買代金, volume_ratio を計算。true_range の NULL 伝播を適切に処理
    - value: raw_financials の最新財務データ（report_date <= target_date）と当日の株価を組み合わせて PER/ROE を算出
    - 各関数は欠損・データ不足時の安全な None 値返却を行う
  - 特徴量探索ユーティリティ（feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト 1/5/21 営業日）で将来リターンを一括取得
    - calc_ic: factor と将来リターンの Spearman の rank 相関（IC）を計算（有効サンプル数閾値あり）
    - rank / factor_summary: ランク付け（同順位は平均ランク）や基本統計量サマリーを実装。rank は丸め（round(..., 12)）で ties を安定化
  - research パッケージは外部依存（pandas 等）を使わず標準＋DuckDB で完結する設計
- バックテスト（kabusys.backtest）
  - エンジン（engine.run_backtest）
    - 本番 DuckDB から日付範囲を限定して必要テーブルをインメモリ DuckDB（:memory:）にコピーしてバックテスト用接続を作成
    - market_calendar は全件コピー、prices_daily / features / ai_scores / market_regime は date 範囲でコピー
    - 日次ループでの処理:
      1. 前日シグナルを当日の始値で約定（simulator.execute_orders）
      2. simulator の positions/cost_basis を positions テーブルに書き戻し（generate_signals の SELL 判定用）
      3. 終値で時価評価・スナップショット記録（mark_to_market）
      4. generate_signals を呼び出して当日分の signals を作成
      5. サイジングして翌日の発注リストを作成
    - get_trading_days を用いて営業日列を取得
  - ポートフォリオシミュレータ（simulator.PortfolioSimulator）
    - メモリ内で cash / positions / cost_basis / history / trades を管理
    - 約定モデル:
      - BUY は始値 × (1 + slippage_rate)、SELL は始値 × (1 - slippage_rate) を約定価格に適用
      - 手数料は約定額 × commission_rate
      - BUY は資金不足時に手数料込みで調整して購入株数を再計算
      - SELL は保有全量をクローズ（部分利確は未対応）
    - 約定記録（TradeRecord）に realized_pnl を保存（SELL 時のみ）
    - mark_to_market は終値が無い銘柄は 0 評価とし WARNING を出力
  - メトリクス（metrics.calc_metrics）
    - CAGR（暦日ベースの年率）、Sharpe（無リスク=0、年次化は sqrt(252)）、最大ドローダウン、勝率、ペイオフレシオ、総トレード数を計算
    - 計算は履歴とトレードリストのみを入力とする純粋関数
- トランザクション耐性とログ
  - features/signals への書き込みで BEGIN / COMMIT / ROLLBACK を使用。ROLLBACK 失敗時は警告ログ出力
  - 価格欠損等の異常ケースで適切に WARNING/DEBUG/INFO を出力し誤処理を回避

Fixed
- （初版のためなし）

Changed
- （初版のためなし）

Deprecated
- （初版のためなし）

Removed
- （初版のためなし）

Security
- （初版のためなし）

注意事項 / 既知の制限
- execution パッケージはプレースホルダ（__init__.py のみ）で、実際の発注 API 接続処理は実装されていません。実運用では実行層（kabu API 等）との接続実装が必要です。
- signal_generator のエグジット戦略で未実装の条件:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有日数閾値）
- 一部の計算はデータ品質（欠損値・極端値）に依存するため、前処理/データ検査が推奨されます。
- バックテストのデータコピーはテーブルスキーマ互換を前提としています。スキーマが異なる DB を使う場合は init_schema 等の調整が必要です。
- パラメータ（閾値・重み・スリッページ・手数料等）はコード内定数として固定されています。運用時は外部設定化を検討してください。

今後の予定（例、今後実装したい項目）
- execution 層の実装（kabu ステーションとの接続、注文管理）
- signal_generator の追加エグジットルール（トレーリングストップ、時間決済）
- パラメータの外部化（設定ファイル・コマンドライン・管理 UI）
- モジュール化された単体テストの整備と CI の導入

--- 
（この CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノートは運用方針に合わせて調整してください。）