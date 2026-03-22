# Changelog

すべての注目すべき変更をまとめます。フォーマットは「Keep a Changelog」に準拠しています。

※このファイルはコードベースから推測して作成しています。実際の変更履歴やリリース日付・細部は実実装に合わせて調整してください。

---

## [Unreleased]

- 現時点で未リリースの変更はありません。

---

## [0.1.0] - 2026-03-22

初回公開リリース。日本株の自動売買フレームワークのコア機能を実装。

### 追加 (Added)

- パッケージメタ情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - __all__ に主要サブパッケージをエクスポート（data, strategy, execution, monitoring）

- 環境設定 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用途）。
  - .env パーサ実装（export プレフィックス対応、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの取り扱い）。
  - 読み込み時、OS 環境変数を保護するための protected キー集合を使用して .env.local の上書きを制御。
  - Settings クラスを提供し、必要な環境変数をプロパティ経由で取得（必須キー未設定時は ValueError を送出）。
  - 既定値とバリデーション:
    - KABUSYS_ENV: 有効値 ("development", "paper_trading", "live") の検証
    - LOG_LEVEL: 有効ログレベルの検証 ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
    - データベースパス: DUCKDB_PATH / SQLITE_PATH のデフォルト値を用意

- 研究用ファクター計算 (src/kabusys/research/factor_research.py)
  - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率 (ma200_dev) の計算
  - calc_volatility: 20日 ATR、atr_pct（ATR/終値）、20日平均売買代金、出来高比率の計算
  - calc_value: raw_financials から直近財務データを取得して PER / ROE を計算
  - DuckDB の SQL とウィンドウ関数を使用し、営業日欠損やデータ不足時の取り扱いを実装

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - build_features(conn, target_date): research モジュールの生ファクターを統合し features テーブルへ書き込み
  - 処理フロー:
    1. calc_momentum / calc_volatility / calc_value から raw factor を取得
    2. ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用
    3. Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ
    4. date 単位で DELETE → INSERT の置換（トランザクションで原子性を保証）
  - 欠損や異常値に対する安全対策とログ出力を備える

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - generate_signals(conn, target_date, threshold=0.60, weights=None)
  - 正規化済みファクター（features）と ai_scores を統合して final_score を計算
  - スコア計算の特徴:
    - コンポーネントスコア: momentum, value, volatility, liquidity, news（AI スコア）
    - Z スコアをシグモイド変換して [0,1] へマッピング
    - 欠損コンポーネントは中立値 0.5 で補完
    - 重みはデフォルト値にフォールバックし、ユーザ指定は妥当性検証・正規化してマージ
    - デフォルト閾値: 0.60（BUY 判定）
  - Bear レジーム判定（AI の regime_score 平均が負の場合、サンプル数閾値あり）による BUY の抑制
  - SELL（エグジット）判定:
    - ストップロス: 終値 / avg_price - 1 < -8%（優先）
    - スコア低下: final_score < threshold
    - 価格が欠損する銘柄は SELL 判定処理をスキップし警告ログを出力
  - signals テーブルへ date 単位で置換（トランザクションで原子性を保証）
  - SELL 対象は BUY から除外し、BUY ランクを再付与（SELL 優先）

- 特徴量探索ユーティリティ (src/kabusys/research/feature_exploration.py)
  - calc_forward_returns(conn, target_date, horizons=[1,5,21]): 複数ホライズンの将来リターンを一度のクエリで取得
  - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマン順位相関（IC）を実装、データ不足時は None を返す
  - rank(values): 同順位は平均ランクで扱うランク関数（丸めを使い ties 検出の安定化）
  - factor_summary(records, columns): count/mean/std/min/max/median を計算

- バックテストフレームワーク (src/kabusys/backtest/)
  - PortfolioSimulator (simulator.py)
    - メモリ内でのポートフォリオ管理、約定シミュレーション（SELL を先に処理、BUY は割当に従い購入）
    - スリッページ・手数料を反映した約定価格・手数料計算
    - BUY 時は手数料込みで購入可能な株数へ再計算して調整
    - SELL は保有全量クローズ（部分利確・部分損切りは未対応）
    - mark_to_market() により DailySnapshot を記録（終値欠損時は 0 評価で警告）
  - metrics.py
    - バックテスト指標計算: CAGR, Sharpe ratio（年次化、無リスク=0）, 最大ドローダウン, 勝率, Payoff ratio, 総クローズトレード数
  - engine.py
    - run_backtest: 本番 DB からインメモリ DuckDB へデータをコピーして日次シミュレーションを実行
    - コピー対象テーブルのフィルタリング（prices_daily, features, ai_scores, market_regime, market_calendar 等）
    - シミュレーションループの主要ステップ:
      1. 前日シグナルを当日始値で約定
      2. positions テーブルへ書き戻し（generate_signals の SELL 判定に利用）
      3. 終値で時価評価・スナップショット記録
      4. generate_signals を用いて当日分のシグナル生成
      5. ポジションサイジングにより翌日発注リストを組み立て
    - run_backtest は BacktestResult(history, trades, metrics) を返す

- パッケージのエクスポート
  - backtest, research, strategy などの主要 API を __all__ を通じて公開

### 変更 (Changed)

- （初回リリースのため該当なし）

### 修正 (Fixed)

- （初回リリースのため該当なし）

### 既知の制限 / 未実装 (Known limitations / Unimplemented)

- トレーリングストップや時間決済（保有日数での決済）は未実装（signal_generator に注釈あり）。実装には positions テーブルへの peak_price / entry_date の保存が必要。
- research モジュールは外部のデータ処理ライブラリ（pandas 等）には依存しない実装（標準ライブラリ + DuckDB を使用）。
- signals / positions / features 等の DB スキーマを前提としている。実行前にスキーマの初期化（data.schema.init_schema 等）が必要。
- execution 層（実際の発注 API への接続）は本リリースでは含まれていない（execution パッケージは名前のみエクスポートされる構成）。

### マイグレーション / 注意事項 (Migration / Notes)

- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 任意/デフォルトあり: KABUSYS_ENV（default=development）, LOG_LEVEL（default=INFO）, DUCKDB_PATH, SQLITE_PATH
- .env の自動ロードはプロジェクトルートの検出に依存するため、配布後に自動ロードを期待する場合は .git または pyproject.toml を含めるか、KABUSYS_DISABLE_AUTO_ENV_LOAD を適切に設定してください。
- run_backtest は本番 DB を直接変更しない設計だが、バックテスト用に一時的にテーブルのコピーを行います。必要に応じてバックアップを推奨します。
- ログや警告が多数出力されうる箇所があり（価格欠損や不正入力のスキップ等）、運用時はログレベルと監視を適切に設定してください。

---

（以降のリリースでは、機能追加、実運用接続（execution 層）、トレーリングストップ・時間決済の実装、さらなる性能改善・テストカバレッジ向上などの変更を記載してください。）