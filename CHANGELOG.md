# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-03-22
初回公開リリース。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__init__、バージョン "0.1.0"）。
  - public API のエクスポートを整理（strategy / execution / monitoring / data 等を __all__ に設定）。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートは .git または pyproject.toml を上位ディレクトリから探索して決定（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサー実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォートのエスケープ処理をサポート。
    - インラインコメントやクォート無しの # の扱い（スペース直前をコメントと判断）に対応。
  - Settings クラス提供:
    - J-Quants / kabu ステーション / Slack / DB パス等の設定プロパティを定義（必須項目は未設定時に例外を投げる）。
    - KABUSYS_ENV の値検証（development/paper_trading/live）。
    - LOG_LEVEL の値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - パス類は Path オブジェクトで返す（expanduser 実施）。

- 戦略（kabusys.strategy）
  - feature_engineering.build_features:
    - research モジュールの生ファクター（momentum/volatility/value）を取得し、ユニバースフィルタ（最低株価・平均売買代金）を適用。
    - 指定カラムを Z スコア正規化し ±3 にクリップ。
    - features テーブルへ日付単位で置換（DELETE→INSERT、トランザクションで原子性確保）。
    - 欠損や異常値を考慮した堅牢な実装。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネントスコアは未定義値を中立 0.5 で補完。
    - final_score を重み付き和で算出。ユーザー指定の weights は検証・補完・再スケールされる（合計が 1.0 でない場合も正規化）。
    - Bear レジーム判定（ai_scores の regime_score の平均 < 0 かつサンプル数閾値以上）で BUY を抑制。
    - BUY／SELL の生成、signals テーブルへ日付単位の置換（トランザクション）で書き込み。
    - エグジット判定（ストップロス、スコア低下）を実装（positions と最新価格参照）。価格欠損時の挙動はログ出力して判定をスキップまたは保護的判定。

- リサーチ（kabusys.research）
  - factor_research:
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（20日 ATR、相対 ATR、出来高関連）、Value（PER、ROE）を DuckDB クエリで計算する関数を提供。
    - prices_daily / raw_financials のみ参照し、ルックアヘッドを防ぐ設計。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns、任意ホライズン、バリデーション付）。
    - IC（Spearman の ρ）計算（rank/同順位は平均ランク処理）。
    - factor_summary（count/mean/std/min/max/median）を標準ライブラリのみで実装。
  - 研究用ユーティリティ（zscore_normalize を data.stats から再利用可能にするエクスポート）。

- バックテスト（kabusys.backtest）
  - simulator:
    - PortfolioSimulator によるメモリ内ポートフォリオ管理、擬似約定ロジックを実装。
    - BUY: alloc に基づき始値＋スリッページで約定、手数料考慮、資金不足時のリサイズ、平均取得単価更新。
    - SELL: 保有全量をクローズ（部分利確非対応）、スリッページと手数料を考慮、realized_pnl を計算して記録。
    - mark_to_market で終値評価し DailySnapshot を記録。終値欠損時は 0 と評価して WARNING ログを出力。
    - TradeRecord / DailySnapshot の dataclass を定義。
  - metrics:
    - バックテスト評価指標の計算（CAGR、Sharpe（無リスク 0 と仮定）、Max Drawdown、Win Rate、Payoff Ratio、トレード数）。
  - engine.run_backtest:
    - 本番 DuckDB から日付範囲をコピーしてインメモリ DuckDB を作成（signals/positions を汚染しない）。
    - 日次ループ: 前日シグナルの約定 → positions 書き戻し → mark-to-market → generate_signals → ポジションサイジング → 次日の発注 という流れを実装。
    - デフォルトパラメータ（初期資金、スリッページ、手数料、1銘柄最大比率）を提供。
    - データコピー時の例外を寛容に扱い（テーブルごとにコピー失敗をログでスキップ）。

- DB 操作の堅牢化
  - features / signals への書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で行い、ROLLBACK に失敗した場合は警告ログ出力。

### Changed
- 初期リリースのため該当なし。

### Fixed
- 初期リリースのため該当なし。

### Removed
- 初期リリースのため該当なし。

### Known issues / Limitations / TODO
- エグジット条件の一部（トレーリングストップ、保有期間による時間決済）は positions に peak_price / entry_date 等のカラムが必要で、現状未実装（コード内に TODO コメントあり）。
- PortfolioSimulator の SELL は常に「全量クローズ」。部分利確／部分損切りはサポートしていない。
- feature_exploration は pandas 等に依存せず標準ライブラリのみで実装しているため非常に軽量だが、大量データでの使い勝手は実運用でのベンチマークが推奨される。
- env パーサーは一般的な .env フォーマットをサポートするが、複雑なシェル展開（$(...) や ${VAR} 展開等）は行わない。
- run_backtest のデータコピーは日付フィルタされたテーブルを用いるため、start_date より古い履歴を必要とする特殊なリサーチでは不足する可能性がある（しかし start_date - 300 日分を確保する設計）。
- generate_signals は ai_scores 未登録の銘柄に対してはニューススコアを中立（0.5 相当）で補完するため、AI スコアが無い場合の振る舞いに注意。

### Security
- 初回リリースのため特記すべきセキュリティ修正はなし。

---

リリースに関する追加情報や具体的な API 使用例、マイグレーション手順が必要な場合は、該当モジュール（特に config / strategy / backtest）の使用方法や期待される DB スキーマについて追記します。必要であれば CHANGELOG に「Contributors」や「References（設計ドキュメント）」の節も追加できます。