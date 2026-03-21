# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-21

初回公開リリース。日本株自動売買システム「KabuSys」の基礎モジュール群を追加しました。主な追加機能・実装は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージの公開APIとして data, strategy, execution, monitoring をエクスポート。

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local / OS環境変数からの設定読み込みを実装（自動ロード機能）。
  - プロジェクトルート検出: .git または pyproject.toml を起点に自動でルートを特定。
  - .env ファイルパーサを実装:
    - 空行・コメント（先頭の#）を無視。
    - export KEY=val 形式に対応。
    - シングル/ダブルクォートされた値をバックスラッシュエスケープを考慮して適切にパース。
    - 非クォート値のインラインコメント判定（# の前に空白がある場合のみコメントとみなす）。
  - .env/.env.local の読み込み優先度: OS 環境変数 > .env.local (> .env)。
  - .env 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを実装し、主要設定値をプロパティで提供（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DBパス等）。
  - 環境変数検証:
    - KABUSYS_ENV は "development" / "paper_trading" / "live" のみ許容。
    - LOG_LEVEL は "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL" のみ許容。
  - デフォルトの DB パス: duckdb -> data/kabusys.duckdb、sqlite -> data/monitoring.db。

- データ取得/永続化: J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装（取得・保存ユーティリティ）。
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
  - リトライロジック: 指数バックオフ、最大 3 回、対象ステータス 408/429/5xx。
  - 401 応答時はトークンを自動リフレッシュして 1 回リトライ（無限再帰防止）。
  - JSON デコードエラーハンドリング/詳細な例外メッセージ。
  - ページネーション対応の fetch_* 関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を実装。
  - DuckDB への保存関数:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。
    - fetched_at を UTC (Z) で記録。
    - PK 欠損行はスキップしログ警告を出力。
    - ON CONFLICT DO UPDATE を使った冪等保存。
  - HTTP レスポンスの Retry-After ヘッダを尊重する挙動（429）。
  - 型変換ユーティリティ: _to_float / _to_int（不正な文字列を安全に None に変換）。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集し raw_news へ保存する基盤を実装。
  - 安全対策:
    - defusedxml を利用した XML パース（XML Bomb 等への対策）。
    - 受信バイト数上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を軽減。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリパラメータのソート）。
    - トラッキングパラメータの除去リストを定義（utm_*, fbclid, gclid, ref_, _ga 等）。
  - バルク挿入のチャンク化（_INSERT_CHUNK_SIZE）による SQL 長制限への配慮。
  - デフォルト RSS ソースを設定（例: Yahoo Finance）。

- 研究モジュール (src/kabusys/research/)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、atr_pct、20日平均売買代金、出来高比率を計算。
    - calc_value: PER（株価/EPS）、ROE を raw_financials と prices_daily から計算。
    - 各関数は prices_daily / raw_financials のみ参照し、(date, code) キーの dict リストを返す。
  - feature_exploration:
    - calc_forward_returns: LEAD を用いた将来リターン計算（デフォルト horizons = [1,5,21]）。horizons 引数のバリデーション（1..252）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。サンプル数が 3 未満なら None を返す。
    - rank: 同順位は平均ランクで処理し、丸め誤差対策として round(..., 12) を使用。
    - factor_summary: 各ファクター列について count/mean/std/min/max/median を計算。

- 戦略モジュール (src/kabusys/strategy/)
  - 特徴量作成 (feature_engineering.build_features)
    - research の calc_momentum/calc_volatility/calc_value を組み合わせて features を生成。
    - ユニバースフィルタ: 最低株価 300 円、20日平均売買代金 5 億円を実装。
    - 正規化: 指定カラム群を Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップ。
    - DuckDB に対して日付単位で削除→バルク挿入のトランザクション置換（冪等性、原子性保証）。
  - シグナル生成 (signal_generator.generate_signals)
    - features と ai_scores を組み合わせ、複数コンポーネント（momentum, value, volatility, liquidity, news）を重み付き合算して final_score を算出。
    - デフォルト重みを定義（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。ユーザ渡しの weights は検証・補完・再スケールされる。
    - コンポーネント計算:
      - momentum: sigmoid 変換した momentum_20/60 と ma200_dev の平均。
      - value: PER を 20 を基準に 1/(1+per/20) でスコア化（PER が不正なら None）。
      - volatility: atr_pct の Z スコアを反転して sigmoid。
      - liquidity: volume_ratio を sigmoid。
      - news: ai_score を sigmoid（未登録は中立補完）。
    - 欠損コンポーネントは中立値 0.5 で補完（欠損銘柄が不当に不利にならない措置）。
    - Bear レジーム判定: ai_scores の regime_score 平均が負なら Bear と判定（サンプル数閾値あり）。
      - Bear レジーム時は BUY シグナルを抑制。
    - BUY シグナル: final_score が閾値（デフォルト 0.60）を超えた銘柄を上位ランクで選出（Bear なら抑制）。
    - SELL シグナル（エグジット判定）:
      - ストップロス: 現在株価 / avg_price - 1 <= -8% の場合 SELL。
      - スコア低下: final_score が閾値未満の場合 SELL。
      - 価格が取得できない保有銘柄は SELL 判定をスキップして警告ログを出力（誤クローズ防止）。
      - features に存在しない保有銘柄は final_score = 0.0 として SELL 扱い（警告ログ）。
    - BUY/SELL の signals テーブルへの保存は日付単位で削除→挿入するトランザクション置換（冪等性、原子性）。
    - ログ出力により生成数や警告を通知。

### 変更 (Changed)
- （初回リリースのため既存の変更はなし）

### 修正 (Fixed)
- （初回リリースのため既存の修正はなし）

### セキュリティ (Security)
- news_collector で defusedxml を使用して XML の安全なパースを行うなど、外部入力に対する防御を強化。
- news_collector における受信サイズ上限・URL 正規化で SSRF/トラッキング漏洩リスクを低減。

### 既知の制限 / 未実装項目
- signal_generator のエグジット条件として設計にあるもののうち、トレーリングストップ（peak_price）が positions テーブルに未実装のため未実装。
- research モジュールは外部ライブラリ（pandas 等）に依存しない純粋 Python/SQL 実装であり、大量データでの最適化は今後の改善点。
- news_collector の記事ID生成やニュース→銘柄紐付け（news_symbols）などの詳細実装はドキュメントに言及があるが、実装済み/未実装の差異はコードベースの該当箇所に依存（本リリースでは URL 正規化等の基盤を提供）。

---

今後のリリースではテストカバレッジの拡充、モジュール間の統合テスト、実運用向けの監視/メトリクス・execution 層の実装・安全なシークレット管理強化などを予定しています。