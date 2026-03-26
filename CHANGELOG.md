# Changelog

すべての重要な変更点をここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

なお、この CHANGELOG はコードベースから推測して作成した初期リリース向けの要約です。

## [0.1.0] - 2026-03-26

### 追加 (Added)
- 初期リリース。パッケージメタ情報:
  - パッケージ名: KabuSys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
- 環境設定管理 (src/kabusys/config.py)
  - .env/.env.local ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に探索（__file__ を起点）。
  - 複雑な .env パース実装:
    - export KEY=val 形式の対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメント判定（クォートなしでは '#' の直前が空白/タブの場合のみコメントとみなす）
  - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - Settings クラス提供（プロパティ経由で設定値にアクセス）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - データベースパスの取得: DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV 値検証（development / paper_trading / live）
    - LOG_LEVEL 値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - ヘルパー: is_live / is_paper / is_dev
- ポートフォリオ構築 (src/kabusys/portfolio)
  - 銘柄選定と重み計算 (portfolio_builder.py)
    - select_candidates: スコア降順、同点は signal_rank でタイブレークして上位 N を選択
    - calc_equal_weights: 等金額配分
    - calc_score_weights: スコア加重配分（全銘柄スコアが 0 の場合は等分にフォールバックし WARNING を出力）
  - リスク調整 (risk_adjustment.py)
    - apply_sector_cap: セクター集中制限ロジック（当日売却予定の銘柄は除外、"unknown" セクターは制限対象外）
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear→1.0/0.7/0.3、未知はフォールバック 1.0）
  - 株数決定・サイズ計算 (position_sizing.py)
    - allocation_method = "risk_based" / "equal" / "score" をサポート
    - risk_based: risk_pct と stop_loss_pct に基づく株数算出
    - equal/score: 重みと max_utilization を用いた配分、portfolio_value*weight を基に算出
    - 単元株（lot_size）で丸め、1銘柄上限・aggregate cap（available_cash）に基づくスケールダウン処理を実装
    - cost_buffer による手数料・スリッページ考慮（保守的コスト見積もり）
    - スケールダウン時に残差（fractional remainder）順で lot 単位の追加配分を行う再現性のあるアルゴリズム
- 戦略（feature / signal） (src/kabusys/strategy)
  - 特徴量エンジニアリング (feature_engineering.py)
    - research モジュールの生ファクターを取得（calc_momentum / calc_volatility / calc_value）
    - ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）
    - 指定列の Z スコア正規化（zscore_normalize を利用）、±3 でクリップ
    - DuckDB を用いた日付単位の置換（DELETE + INSERT）で冪等に features テーブルを更新
  - シグナル生成 (signal_generator.py)
    - features と ai_scores を統合しコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
    - コンポーネントのシグモイド変換、欠損値は中立 0.5 で補完
    - final_score の重み付け合成（デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）
    - 買い閾値（デフォルト 0.60）、Bear レジーム判定時は BUY を抑制
    - エグジット（SELL）判定:
      - ストップロス（終値/avg_price - 1 < -8%）
      - スコア低下（final_score < threshold）
      - 価格欠損時の SELL 判定スキップや、features に存在しない保有銘柄の扱い（score=0 と見なす）などの安全処理
    - signals テーブルへの日付単位置換で冪等性を保証
- 研究ツール (src/kabusys/research)
  - calc_momentum / calc_volatility / calc_value: prices_daily / raw_financials を用いたファクター計算
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト 1,5,21）で将来リターンを一括取得
    - calc_ic: スピアマン順位相関（IC）計算（有効サンプルが 3 未満なら None）
    - factor_summary: 基本統計量（count/mean/std/min/max/median）
    - rank: 同順位は平均ランクを返す安定したランク付け
  - 研究用実装は外部ライブラリに依存せず標準ライブラリと DuckDB で完結
- バックテスト (src/kabusys/backtest)
  - PortfolioSimulator: 擬似約定ロジック（SELL 先行・BUY 後処理、スリッページ/手数料考慮、保有全量クローズ）
  - DailySnapshot / TradeRecord データクラスを提供
  - metrics: バックテスト評価指標を計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades）
  - metrics の内部実装は安全性のため入力サイズやゼロ除算を考慮したデフォルト値を返す設計

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 既知の制限・注意事項 (Notes / Known limitations)
- .env の自動読み込みはプロジェクトルートの検出に依存するため、パッケージ配布後や特殊なディレクトリ構成では無効化が必要な場合がある（KABUSYS_DISABLE_AUTO_ENV_LOAD を設定）。
- position_sizing の price フォールバックは未実装（price が欠損 = 0.0 の場合にエクスポージャーが過小見積られる可能性あり）。将来的に前日終値や取得原価でフォールバックすることを検討中。
- signal_generator のトレーリングストップや時間決済は未実装（positions テーブルに peak_price / entry_date 情報が必要）。
- calc_regime_multiplier は未知レジームを 1.0 にフォールバックするが、Bear レジームでは generate_signals 側で BUY シグナル非生成の方針を採用している（multiplier は追加の安全弁）。
- バックテストの約定モデルは現状シンプル（SELL: 全量クローズ、部分利確/部分損切り非対応）。

### 開発者向けメモ
- 多くの処理は DuckDB に依存（features / prices_daily / raw_financials / ai_scores 等のテーブルが前提）。
- トランザクションは DELETE + INSERT のパターンで日付単位の置換（冪等性を確保）。エラー時はロールバックを試行し警告を出力する実装になっている。
- ロガーを各モジュールに配置し、警告・デバッグ情報を明示的に出力する方針。
- 将来的な拡張点はコード内の TODO コメントに記載（例: 銘柄別 lot_size マスタ、価格フォールバック、トレーリングストップ等）。

---

（この CHANGELOG はコードベースの内容を解析して作成した推測に基づく文書です。実際のリリースノートとして利用する際は、変更点・日付・バージョン情報をプロジェクトの実運用に合わせて調整してください。）