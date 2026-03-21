# CHANGELOG

すべての顕著な変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

注意: 以下の履歴は提供されたコードベースの内容から推測して作成したリリースノートです。実際のコミット履歴とは異なる場合があります。

## [Unreleased]

## [0.1.0] - 2026-03-21
初回公開リリース（初期実装）。以下の主要機能・モジュールを実装しました。

### 追加 (Added)
- パッケージ構成
  - kabusys パッケージの初期公開。__version__ = "0.1.0"、__all__ に data / strategy / execution / monitoring を追加。

- 設定管理 (kabusys.config)
  - .env ファイル / 環境変数からの設定読み込み機能を実装。
  - プロジェクトルート自動検出: .git または pyproject.toml を起点に探索し、自動で .env / .env.local を読み込む。
  - 読み込み順序と保護: OS 環境変数を保護する protected オプション、.env.local により上書き可能。
  - .env パーサ実装: export プレフィックス対応、シングル/ダブルクォート・バックスラッシュエスケープ対応、インラインコメント処理。
  - 自動読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD を用意（テスト用途など）。
  - Settings クラス: J-Quants / kabuステーション / Slack / DB パス / 環境モード / ログレベル などのプロパティを提供し、必須環境変数未設定で ValueError を送出。
  - 環境値検証: KABUSYS_ENV / LOG_LEVEL の有効値チェック。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - レート制限対応: 固定間隔スロットリング（120 req/min）を RateLimiter で管理。
  - HTTP リトライロジック: 指数バックオフ、最大 3 回、ステータス 408 / 429 / 5xx に対応。429 の Retry-After を尊重。
  - 401 ハンドリング: トークン自動リフレッシュ（1 回）をサポート。
  - ページネーション対応の fetch_* 関数:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（市場カレンダー）
  - DuckDB への冪等保存関数:
    - save_daily_quotes（raw_prices テーブルへ ON CONFLICT DO UPDATE）
    - save_financial_statements（raw_financials テーブルへ ON CONFLICT DO UPDATE）
    - save_market_calendar（market_calendar テーブルへ ON CONFLICT DO UPDATE）
  - データ型変換ユーティリティ: _to_float / _to_int（堅牢な変換ロジック）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからの記事収集モジュールを実装（デフォルトに Yahoo Finance RSS を設定）。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等の防止）。
    - 最大受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）。
    - URL パターン検査・SSRF リスク回避（HTTP/HTTPS のみ想定）。
  - 記事ID生成: 正規化 URL の SHA-256 ハッシュ（先頭 32 文字）を利用して冪等性を確保。
  - DB 挿入のバッチ処理・チャンク化とトランザクションまとめ挿入（パフォーマンスと一貫性を考慮）。

- リサーチ（研究用）モジュール (kabusys.research)
  - ファクター計算群（research/factor_research.py）:
    - calc_momentum（1M/3M/6M リターン、200日移動平均乖離）
    - calc_volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）
    - calc_value（PER / ROE、raw_financials を参照）
    - DuckDB の prices_daily / raw_financials テーブルのみ参照する設計
  - 特徴量探索（research/feature_exploration.py）:
    - calc_forward_returns（任意ホライズンの将来リターン、デフォルト [1,5,21]）
    - calc_ic（Spearman のランク相関による IC 計算、サンプル不足判定）
    - factor_summary（count/mean/std/min/max/median の統計サマリー）
    - rank（同順位は平均ランクで処理、丸めで ties 検出を安定化）
  - research/__init__.py で主要 API をエクスポート。

- 戦略（strategy）モジュール
  - 特徴量エンジニアリング (strategy/feature_engineering.py)
    - research 側で計算した raw factor をマージ・ユニバースフィルタ適用（株価最低 300 円、20 日平均売買代金 >= 5 億円）。
    - 正規化: 指定カラムを Z スコアで正規化し ±3 でクリップ（外れ値抑制）。
    - features テーブルへ日付単位の置換（DELETE→INSERT をトランザクションで実行、冪等性）。
  - シグナル生成 (strategy/signal_generator.py)
    - features と ai_scores を統合して final_score を計算（コンポーネント: momentum/value/volatility/liquidity/news）。
    - スコア変換ユーティリティ: シグモイド変換、欠損値は中立 0.5 で補完。
    - 重みのマージと正規化（デフォルト重みを定義、ユーザー重みは検証してマージ、合計が 1 に再スケール）。
    - Bear レジーム判定（ai_scores の regime_score 平均 < 0）により BUY を抑制。
    - BUY/SELL シグナル生成と signals テーブルへの日付単位置換（トランザクション＋バルク挿入）。
    - SELL 判定ロジック（ストップロス -8% / final_score が閾値未満）。未実装としてトレーリングストップや時間決済を明記。

- 共通・設計上の配慮
  - ルックアヘッドバイアス対策: target_date 時点のみデータ参照する厳格な扱い。
  - 発注 API / execution 層への直接依存を避けた分離設計（strategy 層は signals テーブルを書くだけ）。
  - DuckDB を用いたデータ処理（SQL + Python の組合せ）。
  - ロギングと警告メッセージを多用して異常系を可視化。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。コード内には欠損データや異常値に対する防御ロジック（価格欠損時の SELL 判定スキップや PK 欠損行のスキップなど）が組み込まれています。

### セキュリティ (Security)
- news_collector: defusedxml の採用、受信バイト数制限、URL 正規化により XML・SSRF・DoS リスクに対処。
- jquants_client: トークンの安全なリフレッシュ（キャッシュ）と適切なエラー/再試行制御により不適切な認証失敗や過負荷による障害を低減。

### 既知の制限 / TODO
- strategy/_generate_sell_signals の一部条件（トレーリングストップや保有日数による時間決済）は未実装。positions テーブルに peak_price / entry_date 等の情報が必要。
- execution パッケージはプレースホルダ（src/kabusys/execution/__init__.py が空）で、実際の発注ロジックは未実装。
- 一部ユーティリティ（例: kabusys.data.stats の zscore_normalize）が別ファイルに存在する想定だが、本スナップショットでは省略。
- AI スコア（ai_scores）の取得・更新フロー、ニュース→銘柄関連付け（news_symbols）の実装詳細は今後追加予定。

---

（以後のリリースでは Unreleased を更新し、変更を逐次移動してください。）