# Changelog

すべての重要な変更をここに記録します。本ファイルは Keep a Changelog の形式に従います。

## [0.1.0] - 2026-03-19

初回リリース — 基本的なデータ収集、研究（ファクター計算）、特徴量生成、シグナル生成のワークフローを実装。

### 追加
- パッケージ基盤
  - kabusys パッケージ初期公開（__version__ = 0.1.0）。モジュール群: data, research, strategy, execution, monitoring（execution はプレースホルダとして存在）。
- 環境設定
  - 環境変数/設定管理モジュール（kabusys.config.Settings）
    - .env/.env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env パース実装（export prefix対応、クォート・エスケープ処理、インラインコメント処理など）。
    - 必須環境変数の検査（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。
    - env/log レベル検証（KABUSYS_ENV は development/paper_trading/live のみ、LOG_LEVEL は標準ログレベルのみ許容）。
    - データベースパス設定（DUCKDB_PATH, SQLITE_PATH）。
- データ収集・保存（kabusys.data）
  - J-Quants API クライアント（jquants_client）
    - API 呼び出しユーティリティ（GET/POST、ページネーション対応）。
    - 固定間隔レートリミッタ（120 req/min）実装。
    - リトライロジック（指数バックオフ、最大試行回数、408/429/5xx の再試行対応）。
    - 401 受信時にリフレッシュトークンで自動トークン更新（1 回のみ）して再試行。
    - ID トークンのモジュールキャッシュ（ページネーション間で共有）。
    - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB への保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（冪等性: ON CONFLICT DO UPDATE）。
    - 入力変換ユーティリティ: _to_float / _to_int（堅牢な型変換処理）。
  - ニュース収集モジュール（news_collector）
    - RSS フィード収集・正規化処理（DEFAULT_RSS_SOURCES に既定ソース）。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト正規化、クエリソート、フラグメント除去）。
    - セキュリティ対策: defusedxml を利用した XML パース、受信バイト上限、HTTP スキームのみ許可、SSRF を意識した設計。
    - バルク挿入のチャンク化・トランザクションまとめ保存、挿入件数の正確取得を想定。
- 研究（research）
  - ファクター計算群（research.factor_research）
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均に基づく乖離）。
    - calc_volatility: 20日 ATR、atr_pct（ATR/close）、avg_turnover、volume_ratio（20日移動平均に基づく）。
    - calc_value: per, roe（raw_financials の最新報告を参照）。
    - 実装上の方針: prices_daily / raw_financials のみ参照、営業日欠損・部分窓に対応するウィンドウ条件。
  - 特徴量探索ユーティリティ（research.feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算（LEAD ベース、データ不足は None）。
    - calc_ic: ファクターと将来リターンとの Spearman（ランク）相関（ties の平均ランク対応、最小サンプル閾値あり）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）。
    - rank: 平均ランクを返すユーティリティ（round(v,12) による安定化）。
- 特徴量エンジニアリング（strategy.feature_engineering）
  - build_features(conn, target_date)
    - research モジュールから取得した生ファクターをマージ、ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5 億円）を適用。
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへ日付単位で置換（DELETE + バルク INSERT をトランザクションで実行し冪等性を担保）。
    - ルックアヘッドバイアス回避のため target_date 時点のデータのみ使用。
- シグナル生成（strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None)
    - features と ai_scores を統合して各銘柄の component スコア（momentum/value/volatility/liquidity/news）を計算。
    - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完。
    - final_score を重み付き合算（デフォルト重量を備え、ユーザ指定は検証・リスケーリング）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値以上で BUY を抑制）。
    - BUY シグナル生成（閾値超過）およびエグジット（SELL）判定:
      - ストップロス（終値が avg_price 比で -8% 以下）
      - スコア低下（final_score < threshold）
    - SELL 優先ポリシー（SELL 対象は BUY から除外）、signals テーブルへ日付単位置換（トランザクションで冪等）。
    - weights の無効値チェック（不正なキー・負値・NaN/Inf を無視）。
  - 補助ユーティリティ: 複数のスコア計算関数、Bear 判定ロジック、シグナル入出力のトランザクション処理。
- パフォーマンス・運用上の配慮
  - DuckDB を主たるデータストアとして想定し、SQL を駆使してウィンドウ集計／LEAD/LAG を利用。
  - 取得時刻（fetched_at）を UTC ISO 形式で保存し、Look-ahead バイアスのトレースを可能にする設計思想。

### 既知の制限 / TODO
- シグナルの一部エグジット条件は未実装（注記あり）
  - トレーリングストップ（直近最高値から -10%）および時間決済（保有 60 営業日超過）は未実装。positions テーブルに peak_price / entry_date が必要。
- news_collector の完全な RSS パース・記事抽出処理の詳細（タグ解析・記事→銘柄紐付けロジック）は拡張余地あり。
- execution 層（発注 API との連携）、monitoring 周りは今回のリリースでは最小限。実際の発注ロジックは別途実装が必要。
- 外部依存について: research モジュールは標準ライブラリ + duckdb のみで設計されているが、運用で pandas 等の導入を検討可能。

### セキュリティ / 安全対策
- J-Quants クライアント
  - RateLimiter によるレート制御、リトライでの Retry-After 尊重、401 時の安全なトークン再取得。
  - API レスポンスの JSON デコード失敗時は明確なエラーを返す。
- ニュース収集
  - defusedxml による XML パース（XML Bomb 等の防止）。
  - URL 正規化・トラッキング除去、HTTP/HTTPS スキーム制限、受信サイズ上限で SSRF/DoS のリスク軽減。
- 環境変数管理
  - OS 環境変数を保護する protected ロジック（.env ロード時に既存変数を不用意に上書きしない）。
  - 自動ロード停止フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を提供しテスト時の安全性を確保。

### ドキュメント注記
- ソース内に関数・モジュールごとの docstring と設計方針を多く含めており、research/ と StrategyModel.md / DataPlatform.md 等の外部仕様に従うことを前提としている（これらの仕様文書は別途管理される想定）。
- ロギングが各処理に組み込まれており、運用時のトラブルシュートが可能。

---
今後のリリースでは execution（実取引）統合、monitoring/アラート、ニュース→銘柄マッチングの強化、バックテストツールの追加、性能改善（大規模データでの DuckDB 最適化）等を予定しています。