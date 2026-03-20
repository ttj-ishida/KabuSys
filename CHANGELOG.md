# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

注: この CHANGELOG はソースコードから実装内容を推測して作成した初回リリース向けのまとめです。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-20

初回リリース。主要機能を含む基本的なアーキテクチャとデータ処理・戦略パイプラインを実装。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期化 / バージョン情報を追加（__version__ = "0.1.0"）。
  - __all__ に data, strategy, execution, monitoring を定義（execution は空パッケージ、monitoring は今後の追加想定）。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルと OS 環境変数から設定を自動ロードする仕組みを実装。
    - プロジェクトルートの検出は .git または pyproject.toml を基準に行うため、CWD に依存しない。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
  - .env の行パーサーは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントなどを考慮。
  - Settings クラスを提供し、必要な環境変数の取得・バリデーションを実装（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）。
  - KABUSYS_ENV と LOG_LEVEL の許容値検証を実装（"development","paper_trading","live" / "DEBUG","INFO","WARNING","ERROR","CRITICAL"）。
  - データベースパス（DUCKDB_PATH, SQLITE_PATH）を Path 型で取り扱うユーティリティを提供。

- データ収集（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - 固定間隔の RateLimiter（120 req/min）を実装。
    - 再試行（指数バックオフ、最大 3 回）・HTTP ステータスに応じたリトライ戦略、429 の Retry-After サポート。
    - 401 発生時はリフレッシュトークンから id_token を自動更新して 1 回リトライ。
    - ページネーション対応のフェッチ（daily_quotes / statements / trading_calendar）。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装し、ON CONFLICT (upsert) による冪等保存を行う。
    - 取得時刻（fetched_at）を UTC ISO8601 で記録（look-ahead バイアスのトレース用）。
    - 型変換ユーティリティ（_to_float / _to_int）を実装し、受信データの堅牢化を図る。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集モジュールを実装。
    - デフォルト RSS ソースを定義（例: Yahoo Finance）。
    - defusedxml を使った安全な XML パース。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES）や SSRF 対策（HTTP/HTTPS チェック等）を想定した実装方針。
    - URL 正規化処理を実装（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）。
    - 記事 ID は正規化 URL の SHA-256 ハッシュ先頭（重複検出と冪等性のため）を採用。
    - DB へはバルク挿入（チャンク化）し、ON CONFLICT DO NOTHING などで冪等性を確保。

- 研究用ファクター計算（kabusys.research）
  - ファクター計算モジュールを実装（factor_research.py）。
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）を計算（200 日 MA のカウントチェック含む）。
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）を計算（true_range の NULL 伝播制御、20 日ウィンドウチェック）。
    - Value（per, roe）を計算（raw_financials の target_date 以前の最新レコードを使用）。
    - DuckDB SQL とウィンドウ関数を活用した実装。
  - 特徴量探索ユーティリティ（feature_exploration.py）を実装。
    - 将来リターン計算（calc_forward_returns）: 指定ホライズンの将来終値リターンを一括取得する SQL 実装。
    - IC（Information Coefficient）計算（calc_ic）: スピアマン順位相関を実装（ties の平均ランク処理含む）。
    - ファクター統計サマリー（factor_summary）とランク関数（rank）を実装。
  - 研究向けエクスポート（research.__init__）を提供。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features を実装。
    - research の calc_momentum / calc_volatility / calc_value を使って原始ファクターを取得。
    - ユニバースフィルタ（最低株価 _MIN_PRICE=300 円、20 日平均売買代金 _MIN_TURNOVER=5e8 円）を適用。
    - 指定カラムに対して Z スコア正規化（zscore_normalize を利用）、±3 でクリップして外れ値影響を抑制。
    - features テーブルへ日付単位で DELETE → INSERT のトランザクション置換（冪等性・原子性を確保）。
    - 欠損・異常値に配慮した実装。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals を実装。
    - features / ai_scores / positions を参照して、各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - シグモイド変換、欠損コンポーネントを中立値 0.5 で補完する方針。
    - デフォルト重みを実装（momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10）。ユーザー指定重みは妥当性チェック後に正規化して適用。
    - Bear レジーム検知（ai_scores の regime_score の平均が負の場合に BUY を抑制）を実装。サンプル数が少ない場合は誤判定を避けるため Bear とみなさない。
    - BUY シグナルは閾値（デフォルト 0.60）以上で生成。SELL シグナルはポジションに対してストップロス（-8%）またはスコア低下で判定。
    - SELL 優先ポリシー（SELL 対象を BUY から除外）とランク再付与を実装。
    - signals テーブルへ日付単位で DELETE → INSERT のトランザクション置換（冪等性・原子性）。
    - 未実装のエグジット（トレーリングストップ、時間決済）はコメントで明確に記載。

- インターフェース整理
  - strategy.__init__ で build_features / generate_signals を公開。

### 変更 (Changed)
- （初回リリースにつき変更履歴なし）

### 修正 (Fixed)
- （初回リリースにつき修正履歴なし）

### セキュリティ (Security)
- ニュースの XML 解析に defusedxml を採用して XML Bomb 等へ対策。
- news_collector で受信サイズ制限（MAX_RESPONSE_BYTES）やトラッキングパラメータ除去、スキーム検査などで一定の入力サニタイズを実装。

### 既知の制約 / TODO
- execution 層（実際の注文発行）や monitoring モジュールは本リリースでは未実装／空（今後追加予定）。
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date 等の拡張が必要で未実装。
- news_collector の詳細な SSRF 防止ロジック（IP フィルタ等）は設計方針として想定されているが、実装の範囲はソースから完全には特定できないため注意。
- 一部ユーティリティ（zscore_normalize 等）は kabusys.data.stats に依存しており、その実装と振る舞いに依存する。

---

開発ドキュメントや設計仕様（StrategyModel.md / DataPlatform.md 等）に沿った設計が多く見られます。実運用前に以下を推奨します:
- 実際の DuckDB スキーマとテーブル（raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar 等）との整合性確認。
- J-Quants API の利用にあたってはトークン・レート制限設定の確認とテスト。
- 自動環境変数ロード（.env）の挙動確認（KABUSYS_DISABLE_AUTO_ENV_LOAD の利用方法含む）。
- ニュース収集時の外部接続に対するセキュリティレビュー。

(以上)