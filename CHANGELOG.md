# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングを使用します。

## [0.1.0] - 2026-03-19

初期リリース。日本株自動売買システム "KabuSys" の基本機能を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期導入。バージョンは `0.1.0`。
  - パッケージ公開インターフェースとして `data`, `strategy`, `execution`, `monitoring` をエクスポート。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動で読み込む機能を実装（プロジェクトルートを `.git` または `pyproject.toml` により探索）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能。
  - .env パーサを実装（`export KEY=val`、クォート文字列中のエスケープ、inline コメント処理等に対応）。
  - `Settings` クラスを提供し、J-Quants / kabuステーション / Slack / DB パスなどの設定をプロパティ経由で取得（必須キーは未設定時に例外を発生）。
  - `KABUSYS_ENV` / `LOG_LEVEL` の値検証（許容値チェック）・ユーティリティプロパティ（is_live / is_paper / is_dev）。

- データ取得・保存: J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。
  - レート制限（120 req/min）を守る固定間隔レートリミッタを導入。
  - リトライロジック（指数バックオフ、最大3回、408/429/5xx を対象）を実装。
  - 401 応答時はリフレッシュトークンから id_token を自動更新して 1 回リトライする仕組みを実装。
  - ページネーション対応の fetch API（daily_quotes / financial_statements / market_calendar）。
  - DuckDB への保存関数を実装（raw_prices / raw_financials / market_calendar へ冪等的に保存、ON CONFLICT DO UPDATE）。
  - データ整形ユーティリティ `_to_float` / `_to_int` を実装し、頑健な型変換を提供。
  - 取得時の `fetched_at` を UTC で記録し、Look-ahead バイアスのトレースを可能に。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードからの記事収集機能を実装（デフォルトに Yahoo Finance RSS を追加）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、小文字化、フラグメント除去）。
  - 記事 ID を URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を確保。
  - XML パースに defusedxml を利用して XML Bomb 等の脆弱性に対処。
  - SSRF 対策（HTTP/HTTPS スキームのみ許容等）や受信サイズ上限（10MB）を設けメモリ DoS を緩和。
  - DB へのバルク挿入はチャンク化してまとめてトランザクション実行、INSERT RETURNING 相当の扱いで挿入数を把握。

- リサーチモジュール (src/kabusys/research/)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）を計算する `calc_momentum` を実装。
    - Volatility / Liquidity 指標（atr_20, atr_pct, avg_turnover, volume_ratio）を計算する `calc_volatility` を実装。
    - Value 指標（per, roe）を raw_financials と prices_daily から算出する `calc_value` を実装。
    - 各関数は DuckDB の prices_daily / raw_financials テーブルのみ参照し、結果を (date, code) をキーとした dict リストで返す設計。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターンをまとめて取得する `calc_forward_returns`（複数ホライズン、1/5/21 日がデフォルト）。
    - スピアマンランク相関による IC 計算 `calc_ic`。
    - ファクター列の基本統計量を返す `factor_summary`。
    - 値のランク化を行う `rank`（同順位は平均ランク、丸め処理で ties 検出の安定化）。
  - 研究関連ユーティリティをパッケージレベルでエクスポート。

- 戦略モジュール (src/kabusys/strategy/)
  - 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
    - 研究環境で計算した生ファクターを取得し、ユニバースフィルタ（最低株価・平均売買代金）を適用。
    - 正規化（z-score）と ±3 でのクリップを行う（zscore_normalize を利用）。
    - 日付単位での冪等的な features テーブル置換（トランザクション＋バルク挿入）を実装：`build_features(conn, target_date)`。
  - シグナル生成 (src/kabusys/strategy/signal_generator.py)
    - features と ai_scores を統合し、コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - シグモイド変換・欠損補完・重み合成による最終スコア final_score を生成。
    - デフォルト重みと閾値を提供（デフォルト閾値 0.60）。
    - Bear レジーム判定（AI の regime_score の平均が負の場合）に基づく BUY 抑制。
    - 保有ポジションに対するエグジット判定（ストップロス -8% / スコア低下）を実装。
    - BUY / SELL を signals テーブルへ日付単位で冪等的に書き込む（`generate_signals(conn, target_date, ...)`）。
    - SELL 優先ポリシー（SELL 対象銘柄を BUY から除外、ランクを再付与）。

- API レベルの堅牢性
  - 多くの DB 書き込み処理でトランザクションを用い、エラー時にロールバックする実装を行い原子性を保証。
  - ロギング（logger）を適切な箇所に追加し、警告・情報を出力。

### 変更 (Changed)
- 初リリースのため該当なし。

### 修正 (Fixed)
- 初リリースのため該当なし。

### 非推奨 (Deprecated)
- 初リリースのため該当なし。

### 削除 (Removed)
- 初リリースのため該当なし。

### セキュリティ (Security)
- RSS パーサに defusedxml を採用し、XML 関連攻撃を軽減。
- ニュース収集で SSRF を防ぐためスキーム検証等の対策を実装。
- J-Quants クライアントの HTTP エラー/ネットワークエラー時にリトライ・バックオフを行い、誤った連続リクエストによるアカウント問題を軽減。

## 既知の制約・注意事項
- DuckDB のテーブルスキーマ（prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar, raw_news 等）は事前に作成されていることを前提とします。初期スキーマ作成スクリプトは別途必要です。
- 一部の戦略条件（例: トレーリングストップ、時間決済）には positions テーブル側で peak_price や entry_date 等の追加カラムが必要で、現バージョンでは未実装。
- J-Quants API 利用には有効なリフレッシュトークン（環境変数 JQUANTS_REFRESH_TOKEN）が必要です。
- news_collector の URL 正規化や ID 生成は既知のトラッキングパラメータに基づく処理を行いますが、すべてのケースを保証するものではありません。

もしリリースノートの粒度を変更したい、特定のモジュールごとに詳細を増やしたい、または Unreleased セクションを追加したい場合は指示ください。