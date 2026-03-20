# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に従って記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [0.1.0] - 2026-03-20

初期リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。主な追加点は以下のとおりです。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化: kabusys.__init__ にバージョン情報と公開モジュールを定義。
- 環境設定 / 設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能（優先度: OS > .env.local > .env）。プロジェクトルート判定は .git または pyproject.toml を利用。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途）。
  - .env パーサーの改良: export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱いなど。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / 環境種別 / ログレベルなどの取得と検証を実装。
  - 必須環境変数未設定時は ValueError を発生させる _require 実装。
- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。主な機能:
    - rate limiting（120 req/min 固定間隔スロットリング）による呼び出し制御。
    - 再試行ロジック（指数バックオフ、最大3回）と 408/429/5xx のハンドリング。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュ共有。
    - ページネーション対応（pagination_key のサポート）。
  - データ保存関数（DuckDB 向け、冪等性を確保する ON CONFLICT を使用）:
    - save_daily_quotes（raw_prices）
    - save_financial_statements（raw_financials）
    - save_market_calendar（market_calendar）
  - 型変換ユーティリティ _to_float / _to_int 実装（安全な変換と欠損値処理）。
- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからのニュース収集基盤を実装（既定ソースに Yahoo Finance を登録）。
  - セキュリティ対策: defusedxml による XML パース、受信バイト上限（10MB）、HTTP スキームの検証などの方針を採用。
  - URL 正規化機能（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）を実装。
  - DB への冪等保存とバルク挿入チャンク化（パフォーマンスと SQL パラメータ上限対策）。
- リサーチ / ファクター計算 (kabusys.research)
  - ファクター計算: calc_momentum / calc_volatility / calc_value を実装（prices_daily / raw_financials に対して SQL ウィンドウ集計を利用）。
    - Momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日分のデータ不足は None）。
    - Volatility: atr_20, atr_pct, avg_turnover, volume_ratio（ATR の NULL 伝播を考慮）。
    - Value: per, roe（target_date 以前の最新財務レコードを使用）。
  - 解析ユーティリティ:
    - calc_forward_returns（複数ホライズンの将来リターンを一度のクエリで取得）
    - calc_ic（Spearman のランク相関による IC 計算）
    - factor_summary（count/mean/std/min/max/median）
    - rank（同順位は平均ランク）
  - 外部依存を持たない（pandas 等非依存）実装。
- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features 実装:
    - research の生ファクターを取得してマージ。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）し ±3 でクリップ。
    - 日付単位で features テーブルへ置換（DELETE + INSERT、トランザクションで原子性確保）。
- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals 実装:
    - features と ai_scores を組み合わせて各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - シグモイド変換、欠損値の中立補完（0.5）、重みの正規化（入力 weights のバリデーションとリスケーリング）を実装。
    - Bear レジーム判定（ai_scores の regime_score の平均が負で、十分なサンプル数がある場合に BUY を抑制）。
    - BUY（閾値デフォルト 0.60）・SELL（ストップロス -8% / スコア低下）を生成し、signals テーブルへ日付単位で置換（冪等）。
    - SELL 優先ポリシー（SELL 対象は BUY から除外しランク付けを再実施）。
- 共通設計 / 実装上の配慮
  - DuckDB を使った SQL + Python の組み合わせで高性能に集計・ウィンドウ計算を実現。
  - 各日付単位の書き換え処理はトランザクション＋バルク挿入で原子性を確保。
  - ロギングを各所に配置し、処理状況・警告・エラーをトレース可能に。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- RSS パーサに defusedxml を採用して XML 関連攻撃を軽減。
- news_collector では受信サイズ上限、トラッキングパラメータ除去、スキーム検証などで SSRF / DoS リスクを低減。
- J-Quants クライアントでのトークン管理はモジュールキャッシュによりトークン再利用・最小限の露出を目指す。401 に対しては最小限の自動再取得を行う。

### 既知の制限・注意点 (Known issues / Notes)
- signal_generator の一部のエグジット条件（トレーリングストップ、保有日数による時間決済）は positions テーブルに peak_price / entry_date 等の情報が整備されていないため未実装。
- news_collector の記事ID生成や銘柄紐付け（news_symbols）等の詳細実装は想定仕様として記載されているが、サンプルコード全体に含まれる処理の一部は今後の実装を予定。
- DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, features, ai_scores, positions, signals など）は本リリースで想定されているが、実稼働前にスキーマ整備・マイグレーションが必要。
- calc_forward_returns の horizons は営業日ベース（連続レコード数）であり、最大 252 日まで制限。
- .env パースは多くのケースに対応していますが、極端なエッジケースで解釈差が出る可能性があります。必要に応じてテストを追加してください。

### マイグレーション / 運用メモ (Migration / Operational notes)
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 自動環境ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定するか、運用スクリプトで制御してください。
- J-Quants API 呼び出しはレート制限が入っているため、バルク取得時は時間的余裕を持って実行することを推奨します。
- DuckDB へデータ保存する際、既存の OS 環境変数は .env による上書きから保護されます（config 内で protected set を扱っています）。

--  
今後のリリース予定: トレーリングストップ等のエグジット条件追加、ニュース→銘柄マッピングの拡充、テストカバレッジと CI の整備。