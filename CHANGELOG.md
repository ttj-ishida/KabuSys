# Changelog

すべての重要な変更はこのファイルに記録されます。フォーマットは "Keep a Changelog" に準拠します。

※このファイルは、リポジトリ内の現行コードベースから推測して作成した初期の変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-26
最初の公開リリース。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン `0.1.0` を定義（src/kabusys/__init__.py）。
  - モジュールのエクスポート: data, strategy, execution, monitoring を __all__ に追加。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能:
    - プロジェクトルートの検出は __file__ を基点に上位ディレクトリを探索し、`.git` または `pyproject.toml` を基準とするため、CWD に依存しない実装。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - OS の既存環境変数は保護され、上書きされない（protected 機構）。
    - 自動ロードを無効化する環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env のパース機能:
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理。
    - クォートなし値のインラインコメント判定（`#` の前が空白/タブのときのみコメントとする）。
  - 必須設定の取得用 `_require` 関数 (未設定時は ValueError)。
  - Settings プロパティ:
    - J-Quants / kabu API / Slack / DB パス（duckdb/sqlite）/システム設定（env, log_level）などを提供。
    - env 値は `development`, `paper_trading`, `live` のみ有効。log_level は `DEBUG/INFO/WARNING/ERROR/CRITICAL` のみ許容。
    - is_live / is_paper / is_dev のヘルパーを提供。

- ポートフォリオ構築（src/kabusys/portfolio/）
  - portfolio_builder
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N を選択。
    - calc_equal_weights: 等金額配分の重み計算。
    - calc_score_weights: スコア加重配分。全銘柄スコアが 0 の場合は等配分にフォールバック（WARNING ログ）。
  - risk_adjustment
    - apply_sector_cap: セクター別エクスポージャーに基づき新規候補を除外（セクター集中制限）。既存保有のうち当日売却予定銘柄を除外可能。セクター不明 ("unknown") は制限対象外。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を返す（未定義レジームは警告を出し 1.0 でフォールバック）。
  - position_sizing
    - calc_position_sizes: 株数計算エンジン。複数の allocation_method をサポート:
      - "risk_based": 許容リスク率（risk_pct）、stop_loss_pct に基づく株数算出。
      - "equal"/"score": weight に基づく配分。per-position 上限、aggregate cap、lot_size（単元株丸め）、cost_buffer による保守的見積りを考慮。
    - aggregate cap 超過時はスケールダウンを行い、残余キャッシュで fractional remainders をロット単位で順次配分するロジックを実装。
    - 将来的な拡張のためのコメント（銘柄別 lot_size など）。

- ストラテジー（src/kabusys/strategy/）
  - feature_engineering
    - build_features: research モジュールの生ファクターを取得し、ユニバースフィルタ（最低株価・平均売買代金）を適用、Z スコア正規化（指定カラム）および ±3 でクリップし、features テーブルへ日付単位で置換（UPSERT）する。
    - ユニバースフィルタの閾値: 最低株価 300 円、20日平均売買代金 5 億円。Z スコア正規化のクリップ値は 3.0。
    - 正規化処理は kabusys.data.stats.zscore_normalize を利用。
    - DB への書き込みはトランザクションで原子性を担保。例外時はロールバック処理とロギング。
  - signal_generator
    - generate_signals: features と ai_scores を統合して final_score を計算し、BUY/SELL シグナルを生成して signals テーブルへ日付単位で置換。
    - スコア計算:
      - momentum/value/volatility/liquidity/news の重みをデフォルトで設定（合計 1.0 に正規化）。
      - 不正なユーザー指定 weights は無視して警告。
      - コンポーネントの欠損値は中立値 0.5 で補完。
      - final_score に対する閾値（デフォルト 0.60）で BUY 判定。
    - Bear レジーム判定: ai_scores の regime_score 平均が負かつサンプル数閾値以上の場合に BUY を抑制。
    - SELL（エグジット）判定:
      - ストップロス（終値/avg_price - 1 < -8%）が最優先。
      - final_score が閾値未満は SELL。
      - 一部未実装の条件（トレーリングストップ、時間決済）はコメントで明記（追加データが必要）。
    - BUY と SELL の優先ポリシー: SELL 対象は BUY から除外し、BUY は再ランク付け。
    - DB 書き込みはトランザクションで原子性を担保。例外時はロールバック処理とロギング。

- リサーチ / ファクター計算（src/kabusys/research/）
  - factor_research
    - calc_momentum: 1M/3M/6M リターンと 200 日移動平均乖離を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播や窓内カウントによる判定を慎重に扱う。
    - calc_value: raw_financials の最新財務データを参照して PER / ROE を計算。EPS が 0/欠損 の場合は PER を None にする。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズン検証（1〜252 営業日）あり。効率化のためスキャン範囲にバッファを設定。
    - calc_ic: ランク相関（Spearman ρ）を計算。有効サンプルが 3 未満の場合は None。
    - rank: 同順位は平均ランクを返す（浮動小数の丸めによる ties 検出漏れ対策あり）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。

- バックテスト（src/kabusys/backtest/）
  - metrics
    - BacktestMetrics dataclass と calc_metrics 関数を追加（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades を計算）。
    - 各指標の内部実装（年次化基準、営業日 252 仮定、edge-case の 0 返却など）を実装。
  - simulator
    - DailySnapshot / TradeRecord dataclass。
    - PortfolioSimulator: 擬似約定エンジン。以下の特徴を持つ:
      - 初期現金を指定してシミュレータを初期化。
      - execute_orders: signals を受け取り、当日始値での約定処理を行う。SELL を先に処理し、BUY を後で処理（資金確保のため）。
      - SELL は保有全量クローズ（部分利確・部分損切りは未対応）。
      - スリッページ（買は +、売は -）および手数料率を適用して約定価格・手数料を算出。
      - history / trades の記録を保持。

### Changed
- N/A（初期リリース）。

### Fixed
- N/A（初期リリース）。

### Notes / Known limitations / TODOs
- .env 自動読み込みはプロジェクトルート検出に依存するため、配布後やパッケージ化の環境で挙動を確認する必要がある。必要に応じて `KABUSYS_DISABLE_AUTO_ENV_LOAD` を使用して手動管理可。
- apply_sector_cap:
  - price が欠損（0.0）だとエクスポージャーを過少見積りしてしまう可能性がある旨をコメントに記載。将来的には前日終値や取得原価等のフォールバックを検討。
- position_sizing:
  - 銘柄別 lot_size をサポートしていない（将来的な拡張に言及）。
- signal_generator:
  - 一部エグジット条件（トレーリングストップ、時間決済）は未実装で、positions テーブルに peak_price / entry_date 等のデータが必要。
- research モジュールは DuckDB の prices_daily / raw_financials テーブルに強く依存する設計で、外部 API にはアクセスしない方針。
- 一部のユーティリティ（例: kabusys.data.stats.zscore_normalize）は本変更履歴参照コードで使用されているが、本ログ作成時点の別ファイル実装詳細は含まれていない。

---

今後のリリースでは、以下を想定しています（優先度順、例示）:
- 銘柄別単元株（lot_size）サポートとマスタデータ連携
- トレーリングストップ / 保有期間ベースの時間決済の実装
- execution 層（kabu API 連携）と monitoring / Slack 通知の具体実装
- テストカバレッジの追加およびエラーハンドリング改善

--- 

（この CHANGELOG はコードベースのコメント・設計文書・実装内容からの推測に基づいて作成しています。実際のコミット履歴がある場合はそちらを優先してください。）