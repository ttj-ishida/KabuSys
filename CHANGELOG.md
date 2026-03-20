# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠します。

## [0.1.0] - 2026-03-20

初回リリース。日本株自動売買システム「KabuSys」のコア機能を追加しました。
主要な設計方針として、DuckDB を用いたデータ処理、ルックアヘッドバイアス回避、発注（execution）層への直接依存排除、安全性・冗長性を考慮した実装を行っています。

### 追加 (Added)
- パッケージ初期化
  - pakage エントリポイントを追加（kabusys.__init__、バージョン 0.1.0、公開 API の __all__ を設定）。

- 設定・環境変数管理 (src/kabusys/config.py)
  - Settings クラスを導入し、環境変数からアプリ設定を取得するプロパティを提供（J-Quants / kabuステーション / Slack / DB パス / 環境 / ログレベル 等）。
  - .env 自動ロード機能を追加（読み込み優先順位: OS 環境 > .env.local > .env）。プロジェクトルートは .git または pyproject.toml で探索して決定するため CWD に依存しない。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト目的）。
  - .env パーサの強化:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のエスケープ処理をサポート
    - インラインコメントの扱い（クォート無しの場合は「直前が空白/タブの # をコメントとみなす」）を実装
    - 読み込み時の protected（OS 環境変数）保護と override の制御を実装
  - 環境変数の必須チェック（未設定時は ValueError）と env/log_level のバリデーションを実装。

- データ取得・永続化 (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。
    - 固定間隔のレートリミッタ（120 req/min）を実装しレート制限を厳守。
    - リトライロジック（指数バックオフ、最大3回）を実装。408/429/5xx を再試行対象とする。
    - 401 受信時にリフレッシュトークンで ID トークンを自動更新して 1 回だけ再試行する仕組みを実装（無限再帰回避）。
    - ページネーション対応とページネーションキーの重複防止。
    - fetch_* 系 API: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を追加。
    - DuckDB への保存関数を追加（save_daily_quotes / save_financial_statements / save_market_calendar）。ON CONFLICT による冪等保存を行う。
    - データ整形ユーティリティ _to_float / _to_int を追加（安全な型変換を実施）。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードからニュースを収集して raw_news に保存するモジュールを追加。
  - 設計上の安全対策を実装（受信上限バイト数、defusedxml による XML パース、安全な URL 正規化・トラッキングパラメータ除去、記事 ID を正規化 URL の SHA-256 ハッシュ（先頭32文字）で生成して冪等性を担保）。
  - INSERT をチャンク化して大量挿入時の SQL 制限を回避する仕組みを実装。

- 研究用ファクター計算・探索 (src/kabusys/research/*.py)
  - factor_research モジュールを追加:
    - calc_momentum: 1M/3M/6M リターンと 200 日移動平均乖離を計算。
    - calc_volatility: 20 日 ATR / 相対 ATR (atr_pct) / 20 日平均売買代金 / 出来高比率を計算。
    - calc_value: raw_financials の最新財務データと株価を組み合わせて PER / ROE を計算。
    - 各関数は prices_daily / raw_financials のみ参照し、外部 API に依存しない設計。
  - feature_exploration モジュールを追加:
    - calc_forward_returns: 指定日からの将来リターン（デフォルト 1/5/21 営業日）を一括取得する関数を提供。
    - calc_ic: スピアマンのランク相関（IC）を計算する関数を提供（有効サンプルが 3 件未満なら None を返す）。
    - factor_summary: カラムごとの count/mean/std/min/max/median を計算する統計サマリを提供。
    - rank: 同順位の平均ランクを返すランク変換ユーティリティを提供。
  - research パッケージ __all__ で主要ユーティリティを公開。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - build_features(conn, target_date) を実装:
    - research モジュール（calc_momentum / calc_volatility / calc_value）から生ファクターを取得してマージ。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定列を Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップして外れ値の影響を抑制。
    - features テーブルへ日付単位で置換（DELETE→INSERT をトランザクションでまとめ、冪等性と原子性を確保）。
    - ルックアヘッドバイアスを防ぐため target_date 以前の最新価格のみをユニバース判定に使用。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装:
    - features / ai_scores / positions を参照して各銘柄のコンポーネントスコアを計算（momentum/value/volatility/liquidity/news）。
    - コンポーネントスコア計算:
      - momentum: momentum_20/momentum_60/ma200_dev をシグモイド変換して平均化
      - value: PER を 20 を基準に 1/(1 + per/20) で算出（per<=0/欠損は None）
      - volatility: atr_pct の Z スコアを反転してシグモイド変換
      - liquidity: volume_ratio をシグモイド変換
      - news: ai_scores の ai_score をシグモイド変換（未登録は中立扱い）
    - weights のバリデーションと正規化（未知キーは無視、負値/非数は警告、合計が 1 になるよう再スケール）。
    - Bear レジーム判定: ai_scores の regime_score 平均が負であれば BUY シグナルを抑制（サンプル数閾値あり）。
    - BUY シグナルは final_score >= threshold の銘柄（Bear で抑制）。
    - SELL シグナル（エグジット判定）:
      - ストップロス（終値 / avg_price - 1 <= -8%）
      - final_score が閾値未満（score_drop）
      - SELL は BUY より優先される（SELL 対象は BUY から除外しランクを再付与）
    - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入、冪等）。
    - エントリ時の欠損（features に存在しない保有銘柄）は final_score=0 とみなして SELL 判定する等、安全策を実装。

### 修正・改善 (Changed)
- 全体設計の注記・ドキュメント的改善
  - 各モジュールに設計方針・処理フローを詳細にドキュメント化（docstring）。
  - ルックアヘッドバイアス防止や発注層への依存排除等の設計方針を統一して明示。

- DB 操作の堅牢化
  - features/signals/raw_* 等の挿入処理を ON CONFLICT/DELETE→INSERT パターンで冪等化し、トランザクションで原子性を担保。
  - bulk insert を使用しパフォーマンスを改善。

- エラー・ログの扱い
  - 重要箇所での警告ログ出力を追加（例: .env 読み込み失敗、PK 欠損での行スキップ、HTTP retry 情報、価格欠損での SELL 判定スキップ等）。

### セキュリティ (Security)
- news_collector で defusedxml を用いた安全な XML パースを採用し、XML 関連の攻撃を軽減。
- ニュース URL の正規化とトラッキングパラメータ除去を実装し、記事 ID の生成を安定化。
- J-Quants クライアントはタイムアウト・例外処理・リトライを実装し、外部呼び出しの失敗に対して堅牢に動作するように設計。

### 既知の制約・今後の対応予定 (Known limitations / TODO)
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装（positions テーブルに peak_price / entry_date 等の情報が必要）。
- news_collector の SSRF / IP 検査等の追加保護は設計上言及しているが、現状の公開コードでどこまで実装済みかは要確認（ドキュメント化済）。
- UI / execution（実際の発注処理）層は本リリースでは含まれていない。execution パッケージの実装は別途。

---

今後のバージョンアップでは、execution 層統合、追加のリスク管理（トレーリングストップ・時間決済）、モジュール間の統合テスト増強、及び運用監視（monitoring）機能の拡充を予定しています。