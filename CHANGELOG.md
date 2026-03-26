# Changelog

すべての注記は Keep a Changelog 準拠です。  
このファイルではコードベースから推測される変更点・機能をまとめています。

## [Unreleased]

- （現時点の変更はありません）

---

## [0.1.0] - 2026-03-26

初回リリース — 日本株自動売買ライブラリ "KabuSys" の基礎機能を実装。

### 追加 (Added)

- パッケージ基盤
  - pakage 初期化: kabusys パッケージ（__version__ = 0.1.0）。
  - 明示的な公開 API 定義（__all__）により主要サブパッケージをエクスポート（data, strategy, execution, monitoring 等を意図）。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートの検出: .git または pyproject.toml を基準に __file__ から親ディレクトリを探索（CWD に依存しない）。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ実装:
    - コメント行、空行、export KEY=val 形式、シングル/ダブルクォートとバックスラッシュによるエスケープをサポート。
    - クォートなしの場合のインラインコメント判定（直前がスペース/タブの場合に '#' をコメントとみなす）。
  - Settings クラスによる型付きプロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須取得（未設定時は ValueError を送出）。
    - DUCKDB_PATH / SQLITE_PATH の既定値と Path 変換。
    - KABUSYS_ENV（development, paper_trading, live の検証）と LOG_LEVEL の検証。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定:
    - select_candidates: score 降順、同点時は signal_rank 昇順によるタイブレーク。
  - 重み計算:
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（合計スコアが 0 の場合は等重にフォールバック、警告出力）。
  - リスク調整:
    - apply_sector_cap: セクター集中制限。既存保有時価を計算し、1 セクター比率が閾値を超える場合に同セクターの新規候補を除外する。unknown セクターは制限対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバック（警告）。
  - ポジションサイズ決定:
    - calc_position_sizes: allocation_method に応じた発注株数計算を実装（"risk_based", "equal", "score" をサポート）。
    - risk_based: 許容リスク率(risk_pct) と stop_loss_pct を用いた株数算出。
    - equal/score: weight に基づく割当、max_position_pct / max_utilization 等の上限を考慮。
    - lot_size による単元丸め、cost_buffer による手数料・スリッページの保守的見積もり、aggregate cap 超過時のスケーリング（残差処理・lot 単位での再配分）を実装。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features: research モジュールで計算した生ファクターを結合し、ユニバースフィルタ（最低株価・最低平均売買代金）を適用、Z スコア正規化、±3 でクリップして features テーブルへ日付単位の置換（DELETE→INSERT、トランザクションで原子性確保）。
  - DuckDB 経由で prices_daily / raw_financials を参照。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals: features と ai_scores を統合して final_score を算出し、BUY/SELL シグナルを生成して signals テーブルへ日付単位の置換。
    - コンポーネントスコア: momentum, value, volatility, liquidity, news（AI）を計算。
    - デフォルト重みと外部指定重みのマージ・正規化（不正なキーや値は無視し、合計が 1 でない場合は再スケール）。
    - AI スコアは未登録の場合中立（0.5）を補完。
    - Bear レジーム判定（ai_scores の regime_score の平均が負かつ十分なサンプル数がある場合）で BUY を抑制。
    - SELL 条件:
      - ストップロス（終値 / avg_price - 1 < -8%）
      - スコア低下（final_score < threshold）
    - 保有ポジションの価格欠損時の安全策（価格取得不能なら SELL 判定をスキップ）。
    - signals テーブルへの原子置換（トランザクション + バルク挿入）。
    - 欠落機能/未実装のエグジット（トレーリングストップ・時間決済）は明示的にコメントあり。

- リサーチ（kabusys.research）
  - ファクター計算:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日移動平均乖離）。
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio（20 日 ATR / 20 日平均売買代金等）。
    - calc_value: per / roe（raw_financials の最新レコードと当日の価格を組み合わせて計算）。
  - 特徴量解析:
    - calc_forward_returns: 指定ホライズン（既定 [1,5,21]）の将来リターンを LEAD を使って一括取得。
    - calc_ic: ランク相関（Spearman ρ）を計算する機能（有効レコードが 3 未満なら None）。
    - factor_summary / rank: 基本統計量・ランク付けユーティリティ。
  - 研究向け設計: DuckDB 接続を受け、prices_daily / raw_financials のみを参照。標準ライブラリのみで実装（pandas などに依存しない）。

- バックテスト（kabusys.backtest）
  - ポートフォリオシミュレータ:
    - PortfolioSimulator: メモリ内での保有株数・コスト基準の管理、シグナル実行（SELL を先に処理、SELL は保有全量クローズ）、約定ロジック（スリッページ・手数料適用）。
    - DailySnapshot / TradeRecord dataclass。
  - メトリクス:
    - calc_metrics: cagr, sharpe_ratio, max_drawdown, win_rate, payoff_ratio, total_trades を計算する統括関数と内部実装。

### 変更 (Changed)

- .env 読み込みロジックを堅牢化:
  - OS 環境変数保護（読み込み時に protected set を用いて既存 OS 変数を上書きしない）。
  - ファイル読み込み失敗時に警告を発す（warnings.warn）。
- シグナル生成側での重み取り扱いを堅牢化:
  - 無効値（非数値・NaN/Inf・負値・未知キー）を除外し、合計が 1 でない場合に再スケール。合計が 0 以下ならデフォルトへフォールバック。
- position_sizing の aggregate cap 処理を改善:
  - cost_buffer を用いて約定コストを保守的に見積もり、スケーリング後に lot_size 単位で残差を再配分する実装を追加。

### 修正 (Fixed)

- calc_score_weights: 全銘柄スコア合計が 0 の場合は等金額配分にフォールバックし警告を出す（スコアが0の挙動に対する安全弁）。
- generate_signals:
  - features が空の場合に BUY を生成しない（警告出力）ように調整。
  - SELL 対象は BUY から除外し、ランクを再付与（SELL 優先ポリシーの適用）。

### 既知の制約・TODO（注意事項）

- apply_sector_cap:
  - price が欠落（0.0）だとエクスポージャーが過小評価されブロックが外れる可能性がある。将来的には前日終値や取得原価などのフォールバックを検討する旨の TODO コメントあり。
  - "unknown" セクターはセクターキャップの対象外。
- 売却ルールで未実装の項目:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
- 一部の設計は将来的な拡張を想定（銘柄ごとの lot_size を持たせる等の TODO）。
- AI スコア / レジーム判定は ai_scores テーブルの有無・サンプル数に依存するため、実運用では ai_scores の供給が必要。

### セキュリティ (Security)

- 初期リリースのため既知のセキュリティ問題はコードから明示されていないが、環境変数の取り扱い（自動ロード）に注意。OS 環境変数はデフォルトで上書かれない挙動になっている。

---

作成: KabuSys コードベース（ソースコード解析に基づく推定 CHANGELOG）。ソース内の docstring / TODO コメントを尊重して記載しています。