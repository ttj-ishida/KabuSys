# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」準拠です。

## [0.1.0] - 2026-03-26

初回公開リリース。日本株自動売買システムのコアライブラリを提供します。  
主な機能は環境設定管理、ポートフォリオ構築、戦略用特徴量・シグナル生成、リサーチユーティリティ、バックテストシミュレータおよびメトリクス計算です。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージの初期公開。トップレベルエクスポート: data, strategy, execution, monitoring。
  - バージョン: 0.1.0（src/kabusys/__init__.py）

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルと OS 環境変数を統合する自動読み込み機構を追加（優先順: OS 環境 > .env.local > .env）。
  - プロジェクトルート検出: .git または pyproject.toml を基準に __file__ から探索（CWD 非依存）。
  - .env パーサを実装:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - クォートなし値の行内コメント判定（直前が空白/タブの場合のみ）
  - 自動ロード無効化用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - 必須環境変数取得用 _require() と Settings クラスを実装（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - 設定値の検証: KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL の許容値チェック。

- ポートフォリオ構築 (src/kabusys/portfolio/)
  - 候補選定:
    - select_candidates: score 降順、同点は signal_rank 昇順で上位 N 件を選択。
  - 配分重み:
    - calc_equal_weights: 等金額配分
    - calc_score_weights: スコア加重配分（合計スコアが 0 の場合は等金額にフォールバックし WARN 出力）
  - リスク調整:
    - apply_sector_cap: セクター集中制限の適用（売却予定銘柄はエクスポージャー計算から除外、"unknown" セクターは制限対象外）
    - calc_regime_multiplier: 市場レジームに応じた資金乗数（bull=1.0, neutral=0.7, bear=0.3、未知レジームは 1.0 にフォールバックと警告出力）
  - 株数決定・単元丸め:
    - calc_position_sizes: allocation_method により "risk_based"/"equal"/"score" をサポート。単元(lot_size)丸め、1 銘柄上限・aggregate cap（available_cash）でスケーリング、cost_buffer による保守的見積もり、残差（fractional）を基に lot 単位で再配分するアルゴリズムを実装。

- 戦略: 特徴量作成・シグナル生成 (src/kabusys/strategy/)
  - feature_engineering.build_features:
    - research モジュールの生ファクター（momentum / volatility / value）を統合し、ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5億円）を適用。
    - 指定カラムを Z スコア正規化し ±3 でクリップ、DuckDB に対して日付単位の置換（DELETE + INSERT）で冪等処理。
  - signal_generator.generate_signals:
    - features と ai_scores を統合し、複数コンポーネント（momentum/value/volatility/liquidity/news）を重み付き合算して final_score を算出。
    - sigmoid によるスコア変換、PER の値変換、ボラティリティは反転してスコア化。
    - Bear レジーム検知（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）で BUY を抑制。
    - BUY の閾値（デフォルト 0.60）を超えた銘柄を BUY、保有ポジションに対してはストップロス（-8%）またはスコア低下で SELL。
    - weights の入力検証（未知キーや非数値は無視）、合計が 1 でない場合は正規化。
    - signals テーブルへ日付単位の置換で冪等書き込み。

- リサーチユーティリティ (src/kabusys/research/)
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を実装（DuckDB の prices_daily / raw_financials を参照）。
    - MA200, ATR20, 1/3/6 ヶ月リターン、20日平均出来高等を算出。
  - feature_exploration:
    - calc_forward_returns: LEAD を用いた将来リターン計算（デフォルト horizons=[1,5,21]）。
    - calc_ic: Spearman のランク相関（IC）計算（有効レコードが 3 未満の場合 None）。
    - factor_summary: count/mean/std/min/max/median を返す集計ユーティリティ。
    - rank: 同順位は平均ランクとなるランク関数（丸め処理による ties 対応）。
  - zscore_normalize を data.stats から利用する公開 API を整備。

- バックテスト (src/kabusys/backtest/)
  - simulator:
    - DailySnapshot / TradeRecord の dataclass を定義。
    - PortfolioSimulator: メモリ内でポートフォリオ状態を管理し、signals を open 価格で約定（SELL を先に処理、SELL は保有全量クローズ、スリッページ・手数料モデルを適用）。
  - metrics:
    - バックテスト評価指標を計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total trades）。

### 変更 (Changed)
- （新規リリースのため該当なし）

### 修正 (Fixed)
- （新規リリースのため該当なし）

### 注意事項 / 既知の制限 (Notes)
- .env パーサは多くの一般的ケースに対応していますが、極端に複雑なシェル式や改行・ネスト引用の全てのケースは保証しません。
- apply_sector_cap 内の価格取得が 0.0 の場合、エクスポージャーが過小評価されてしまう可能性があり、コード内に TODO コメントで前日終値や取得原価等のフォールバック導入を検討する旨が記載されています。
- calc_position_sizes の将来的拡張 TODO:
  - 銘柄ごとの単元サイズを渡して銘柄別 lot_map に対応する予定（現状はグローバル lot_size）。
- _generate_sell_signals では現時点で未実装のエグジット条件がある（トレーリングストップ、時間決済）。これらは positions テーブルに peak_price / entry_date 等の情報が必要。
- signal_generator は Bear レジーム時に BUY を抑制する設計（StrategyModel.md に準拠）であり、Bear レジームで BUY シグナルがまったく出ないことは仕様です（ただし calc_regime_multiplier は中間的な絞り込み用として 0.3 を返す）。
- バックテストの約定ロジックは現状で SELL を全量クローズとする設計（部分利確／部分損切りは未対応）。
- 一部の実装で例外発生時にトランザクションの ROLLBACK を試みるが、ROLLBACK に失敗した場合は警告を出して例外を再送出します。

### セキュリティ (Security)
- 環境変数の読み込みに際して OS の既存環境変数は保護され、.env による上書きを防ぐ仕組みを導入（protected set）。
- 重要なトークンや API パスワードは Settings 経由で必須チェックを行い、未設定時は ValueError を送出。

---

今後の予定:
- 銘柄別 lot_size サポート、エグジット条件（トレーリング/時間決済）追加、価格フォールバックロジックの強化、execution 層との統合強化（注文送信・約定確認）などを検討しています。