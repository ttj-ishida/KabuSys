# CHANGELOG

すべての変更は Keep a Changelog 様式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システム「KabuSys」の基本機能群を実装しました。主にデータ収集・保存、研究用ファクター計算、特徴量生成、シグナル生成、および設定管理に関する機能を含みます。

### Added
- パッケージ化
  - パッケージエントリポイント `kabusys` を導入。バージョンは `0.1.0`。
  - サブパッケージ公開: data, research, strategy, execution, monitoring（__all__ に設定）。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数の自動読み込み機能を実装（ルート判定は .git / pyproject.toml を探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化するフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env パーサーは export 形式、クォート、エスケープ、インラインコメントの扱いに対応。
  - 必須設定に対する取得ヘルパー `_require` を実装（未設定時は ValueError）。
  - Settings クラスに以下のプロパティを実装:
    - J-Quants: `jquants_refresh_token`（必須）
    - kabuステーション API: `kabu_api_password`, `kabu_api_base_url`（デフォルト: http://localhost:18080/kabusapi）
    - Slack: `slack_bot_token`, `slack_channel_id`（必須）
    - DB パス: `duckdb_path`（デフォルト data/kabusys.duckdb）, `sqlite_path`（デフォルト data/monitoring.db）
    - 環境名検証: `env`（有効値: development, paper_trading, live）
    - ログレベル検証: `log_level`（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - ヘルパー: `is_live`, `is_paper`, `is_dev`

- J-Quants API クライアント (kabusys.data.jquants_client)
  - J-Quants API からの日足・財務データ・マーケットカレンダー取得機能を実装（ページネーション対応）。
  - レート制限遵守のための固定間隔スロットリング `_RateLimiter`（120 req/min を想定）を実装。
  - リトライロジック（指数バックオフ、最大 3 回）：408/429/5xx に対するリトライ処理。
  - 401 Unauthorized を受けた場合のトークン自動リフレッシュを 1 回行う仕組みを実装（無限再帰防止）。
  - ページネーションを考慮した fetch_* 関数群:
    - fetch_daily_quotes
    - fetch_financial_statements
    - fetch_market_calendar
  - DuckDB へ冪等に保存する save_* 関数群（ON CONFLICT DO UPDATE）:
    - save_daily_quotes -> raw_prices
    - save_financial_statements -> raw_financials
    - save_market_calendar -> market_calendar
  - 型変換ユーティリティ `_to_float`, `_to_int`（堅牢な変換／空値処理）

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集用モジュールを実装（デフォルトソースに Yahoo Finance を設定）。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等の対策）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を防止。
    - URL 正規化によりトラッキングパラメータ（utm_ 等）を除去。
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を確保。
    - HTTP/HTTPS 以外のスキームを拒否する方針（SSRF 緩和）。
  - バルク挿入のチャンク処理と INSERT RETURNING による挿入件数把握を想定。

- 研究用ファクター計算 (kabusys.research.factor_research)
  - モメンタム、ボラティリティ、バリューファクターの計算を実装:
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200 日ウィンドウの存在チェックあり）
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（TRUE RANGE の NULL 伝播制御）
    - calc_value: per, roe（raw_financials の target_date 以前の最新レコードを結合）
  - DuckDB を用いた SQL + Python 実装で prices_daily/raw_financials のみ参照する設計（本番 API にアクセスしない）。

- 研究用探索ユーティリティ (kabusys.research.feature_exploration)
  - 将来リターン計算: calc_forward_returns（horizons の検証、1/5/21 日がデフォルト、スキャン範囲最適化）
  - IC（Information Coefficient）計算: calc_ic（スピアマンの ρ、同順位は平均順位で処理、データ不足時は None を返す）
  - ランク変換 util: rank（丸めにより ties 検出の安定化）
  - 統計サマリー: factor_summary（count/mean/std/min/max/median を計算）

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - 研究で算出した生ファクターを統合・正規化して features テーブルへ UPSERT（冪等）する機能を実装。
  - ユニバースフィルタ: 最低株価 300 円、20 日平均売買代金 5 億円（_MIN_PRICE, _MIN_TURNOVER）。
  - 正規化: zscore_normalize を使用、対象カラムを指定して Z スコア化、±3 でクリップ。
  - DB 操作はトランザクション（DELETE + INSERT の置換）で原子性を担保。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合し final_score を計算、BUY/SELL シグナルを生成して signals テーブルへ書き込む（冪等）。
  - デフォルトのスコア重みと閾値:
    - momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10
    - BUY 閾値 default 0.60
  - weights の入力検証: 未知キー・非数値・NaN/Inf・負値を無視し、合計が 1.0 でなければ正規化（フォールバック処理あり）。
  - コンポーネントスコアの計算:
    - モメンタム: sigmoid 正規化平均
    - バリュー: PER に基づく逆数モデル（PER=20 -> 0.5）
    - ボラティリティ: atr_pct の Z スコアを反転して sigmoid
    - 流動性: volume_ratio を sigmoid
    - ニュース: ai_score を sigmoid（未登録は中立補完）
  - Bear レジーム判定: ai_scores の regime_score の平均が負の場合を Bear と判定（判定に必要な最小サンプル数 = 3）。
    - Bear 時は BUY シグナルを抑制。
  - SELL（エグジット）判定:
    - ストップロス: 終値 / avg_price - 1 < -8%（優先）
    - スコア低下: final_score < threshold
    - 保有ポジションの価格取得失敗時は SELL 判定をスキップしログ出力（誤クローズ回避）
    - SELL 優先ポリシー: SELL 対象は BUY から除外しランクを再付与
  - DB 書き込みは日付単位で置換（DELETE + bulk INSERT）して原子性を保証。

### Known limitations / Notes
- 一部のエグジット条件は未実装（実装予定）:
  - トレーリングストップ（直近最高値から -10%）
  - 時間決済（保有 60 営業日超過）  
  これらは positions テーブルに peak_price / entry_date 等の追加情報が必要です。
- バリューファクターの一部（PBR、配当利回り）は現バージョンでは未実装。
- 外部依存:
  - duckdb（データベースクライアント）
  - defusedxml（RSS パースの安全化）
- ニュース収集の実装では SSRF 等の追加検査が想定されているが、運用ルールに応じたネットワーク制限（プロキシ／DNS フィルタなど）も推奨。
- get_id_token は settings.jquants_refresh_token を使用するため、環境変数の設定が必須。
- 一部の SQL（Window 関数など）は DuckDB を前提として記述されています。他の DB での互換性は検証済みではありません。

### Security
- RSS パースに defusedxml を使用し、XML に起因する攻撃を緩和。
- ニュース URL 正規化でトラッキングパラメータを除去し、ID をハッシュ化して冪等性を担保。
- J-Quants クライアントはトークンを扱い、401 時にトークンを自動リフレッシュします。リフレッシュ処理は 1 回のみ行われ無限再帰を防止。

### Fixed
- 初回リリースのため該当無し。

### Deprecated
- 初回リリースのため該当無し。

---
備考: 今後のリリースでは execution 層（発注ロジック）や monitoring（運用監視・Slack 通知）の実装拡充、追加ファクター・リスク管理ロジックの実装を予定しています。必要であれば、この CHANGELOG を元にさらに詳細なリリースノート（モジュール別の使用方法や migration 手順等）を作成します。