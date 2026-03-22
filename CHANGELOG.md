# Changelog

すべての変更は Keep a Changelog の規約に従って記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

すべての変更点は、コードベースから推測して記載しています（実際のコミット履歴ではありません）。

## [Unreleased]

## [0.1.0] - 2026-03-22

初回リリース。日本株自動売買システム「KabuSys」のコア機能を提供します。以下の主要機能と設計方針を実装しています。

### 追加 (Added)
- パッケージ基礎
  - 基本メタ情報を `src/kabusys/__init__.py` に追加（バージョン "0.1.0"、公開モジュール一覧）。
- 環境設定管理 (`kabusys.config`)
  - .env ファイル自動読み込み（プロジェクトルートを .git / pyproject.toml から特定）。
  - .env と .env.local の読み込み順序を実装（OS環境変数を保護しつつ .env.local で上書き可能）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト向け）。
  - .env パーサ: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
  - 環境値検証用の Settings クラスを提供（必須キー取得のための _require、env/log_level の値検証、DB パスの Path 返却等）。
  - サポートする環境: development / paper_trading / live。ログレベルの許容値チェック。
- 戦略関連 (`kabusys.strategy`)
  - 特徴量エンジニアリング: build_features(conn, target_date)
    - research モジュール（calc_momentum / calc_volatility / calc_value）から生ファクターを取得、株価・流動性でユニバースフィルタを適用。
    - 指定列を Z スコア正規化し ±3 でクリップし、features テーブルへ日付単位での置換（冪等）を実装。
    - 欠損や外れ値に対する安全な取り扱い、トランザクションによる原子性確保、ROLLBACK の失敗ログを実装。
  - シグナル生成: generate_signals(conn, target_date, threshold, weights)
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算。
    - シグモイド変換や欠損時の中立補完（0.5）を採用し、重み付き合算で final_score を算出。
    - Bear レジーム判定（AI の regime_score の平均が負の場合、最小サンプル数条件あり）により BUY を抑制。
    - BUY/SELL シグナルを生成し、signals テーブルへ日付単位での置換（冪等）。SELL 優先のポリシーを採用。
    - weights の入力は検証・正規化され、未知キーや不正値は無視。合計が 1.0 でない場合は再スケール。
    - エグジット判定（stop_loss, score_drop）を実装。価格欠損時の慎重な挙動（判定スキップ）を保持。
- 研究用ユーティリティ (`kabusys.research`)
  - ファクター計算（factor_research）
    - calc_momentum / calc_volatility / calc_value を実装（prices_daily / raw_financials のみ参照）。
    - 各関数は (date, code) ベースの dict リストを返す設計。営業日ベースの窓幅を使用、データ不足時は None を返す。
    - ATR / MA200 /各種モメンタム（1m/3m/6m） / 平均売買代金 / 出来高比率 / PER などを算出。
  - 特徴量探索（feature_exploration）
    - calc_forward_returns(conn, target_date, horizons): 複数ホライズンの将来リターンを一括クエリで取得。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）計算を実装。サンプル不足時は None。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する統計サマリー。
    - rank(values): 平均ランク（ties は平均ランクで処理）。丸めによる tie 検出の安定化を実装（round(..., 12)）。
  - research パッケージの __all__ を整備。
- データ処理ユーティリティ参照
  - zscore_normalize を用いることで特徴量の標準化処理を分離（kabusys.data.stats に依存）。
- バックテストフレームワーク (`kabusys.backtest`)
  - シミュレータ（simulator）
    - PortfolioSimulator: キャッシュ・保有・平均取得単価の管理、BUY/SELL の擬似約定ロジック（始値、スリッページ、手数料モデル）、全量クローズ戦略。
    - TradeRecord / DailySnapshot のデータクラスを定義。
    - mark_to_market により終値で時価評価し DailySnapshot を記録（欠損終値は 0 として WARNING ログ）。
  - メトリクス計算（metrics）
    - CAGR, Sharpe Ratio（無リスク=0）, Max Drawdown, Win Rate, Payoff Ratio, 総トレード数 を計算する BacktestMetrics を実装。
    - 各内部関数は境界条件（データ不足、0除算等）に対する安全な戻り値を用意。
  - エンジン（engine）
    - run_backtest(conn, start_date, end_date, ...): 本番 DB からインメモリ DuckDB へデータをコピーして日次ループでシミュレーションを実行。
    - コピー対象テーブルのフィルタリング（date 範囲）や market_calendar の全件コピー。コピー失敗時は警告ログでスキップ。
    - 日次処理の流れを実装:
      1. 前日シグナルを当日の始値で約定（simulator.execute_orders）
      2. simulator の保有状態を positions テーブルに書き戻し（generate_signals の SELL 判定用）
      3. 終値で時価評価・スナップショット記録
      4. generate_signals を呼出して当日のシグナルを生成
      5. signal を基にポジションサイジングして翌日発注リストを構築
    - DB のコピーは init_schema(":memory:") を使用してインメモリ環境を準備。
- 公開 API の整理
  - 各サブパッケージで必要な関数・クラスを __all__ で公開（backtest, research, strategy 等）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- DB 書き込みで例外発生時に ROLLBACK を試み、ROLLBACK 自体の失敗を警告ログに出す（トランザクション安全性の向上）。
- 多くの場所で欠損データや非有限値（NaN/Inf）を検出して安全にスキップするように実装（ロバストネス向上）。

### 非推奨 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- 環境変数自動ロード時に既存の OS 環境変数を protected として上書きされないよう保護。
- 必須トークン・鍵類は Settings._require で未設定時に明確な ValueError を投げる（早期失敗）。

---

注記（設計方針・挙動の要約）
- ルックアヘッドバイアス回避: 各処理は target_date 時点までのデータのみを参照するよう設計されています。
- 冪等性: features / signals / positions への日付単位の置換（DELETE→INSERT）により再実行しても整合性を保てるようになっています。
- 外部依存: prices_daily / raw_financials / ai_scores / market_calendar 等のテーブルを前提とし、発注 API 等の外部サービスには直接依存しない設計です（実運用では execution 層との連携が別途必要）。
- ロギング: 不整合や欠損時は WARNING/INFO/DEBUG で記録し、後続処理を続行することで堅牢性を高めています。

もし、変更点の粒度（例えばモジュール別のより詳細な差分や想定される既知の制約・既知の未実装項目）をさらに詳述したい場合は、対象モジュールを指定していただければ追記します。