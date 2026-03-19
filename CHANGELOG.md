# Changelog

すべての重要な変更履歴をここに記載します。本ファイルは「Keep a Changelog」に準拠しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

※この CHANGELOG は与えられたコードベースから推測して作成した初期リリースの要約です。

## [Unreleased]


## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システム "KabuSys" の基本モジュール群を実装。

### 追加 (Added)
- パッケージ初期化
  - src/kabusys/__init__.py にてバージョンを "0.1.0" に設定し、公開サブパッケージを定義（data, strategy, execution, monitoring）。

- 環境変数 / 設定管理
  - src/kabusys/config.py
    - .env ファイルまたは OS 環境変数から設定を自動ロード（プロジェクトルート検出: .git / pyproject.toml）。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - export KEY=val 形式やクォート／エスケープ、インラインコメント等を考慮した .env パーサを実装。
    - 上書き制御（override）および OS 環境変数を保護する protected セットを実装。
    - Settings クラスを提供（J-Quants トークン、kabu API、Slack、DB パス、環境種別、ログレベル等のプロパティ）。

- データ収集 / 永続化
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装。
    - 固定間隔レートリミッタ（120 req/min）実装。
    - 指数バックオフによるリトライ（最大 3 回）、429 の Retry-After を考慮。
    - 401 受信時の自動トークンリフレッシュ（1 回の再試行を保障）。
    - ページネーション対応（pagination_key による取得ループ）。
    - DuckDB への保存関数を提供（save_daily_quotes / save_financial_statements / save_market_calendar）。
    - 保存は冪等化（ON CONFLICT DO UPDATE）を採用。
    - 型変換ユーティリティ (_to_float / _to_int) を実装し厳密な変換ポリシーを定義。
  - src/kabusys/data/news_collector.py
    - RSS フィードからニュースを収集するモジュールを実装。
    - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント除去、小文字化）を実装。
    - defusedxml を用いた安全な XML パース、受信サイズ上限（10 MB）、SSRF/非 http(s) スキーム対策等の安全対策を導入。
    - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を確保。
    - raw_news テーブルへのバルク保存（チャンク化）と、news_symbols など銘柄紐付けを想定。

- 研究 (Research) ツール
  - src/kabusys/research/factor_research.py
    - モメンタム／ボラティリティ／バリューのファクター計算関数を実装（calc_momentum / calc_volatility / calc_value）。
    - DuckDB の SQL ウィンドウ関数を活用した効率的な計算を採用。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリ（factor_summary）、ランク付けユーティリティ（rank）を実装。
    - 外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装。
  - src/kabusys/research/__init__.py により主要関数を再エクスポート。

- 戦略 (Strategy)
  - src/kabusys/strategy/feature_engineering.py
    - 研究環境で計算した生ファクターを正規化・合成して features テーブルへ UPSERT する build_features を実装。
    - ユニバースフィルタ（最低株価、20日平均売買代金）や Z スコア正規化（±3 クリップ）を実装し、日付単位での置換（トランザクション + バルク挿入）で冪等性を担保。
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合して final_score を計算し、BUY/SELL シグナルを生成する generate_signals を実装。
    - コンポーネントスコア（momentum / value / volatility / liquidity / news）の計算、重みの補完と正規化、閾値による BUY、Bear レジームでの BUY 抑制、エグジット判定（ストップロス、スコア低下）をサポート。
    - positions / prices_daily テーブル参照により SELL 判定を行い、signals テーブルへ日付単位での置換を行い原子性を保証。
  - src/kabusys/strategy/__init__.py で主要 API を公開（build_features, generate_signals）。

### 変更 (Changed)
- なし（初回リリースのため）。

### 修正 (Fixed)
- なし（初回リリースのため）。

### セキュリティ (Security)
- XML パースには defusedxml を使用し XML-Bomb 等の攻撃対策を実施（news_collector）。
- RSS 取得時に受信サイズ上限を設定しメモリ DoS を軽減（MAX_RESPONSE_BYTES）。
- URL 正規化とスキーム検証で SSRF リスクを低減。
- J-Quants クライアントは 401 に対して安全にトークンを更新する実装（無限ループを防ぐフラグを設置）。

### 注意事項 / 実装上の制約 (Notes)
- ファクター計算・シグナル生成はルックアヘッドバイアスを防ぐ設計になっており、target_date 時点のデータのみを使用する想定。
- 一部のエグジット条件（トレーリングストップ、時間決済など）は positions テーブル側に peak_price / entry_date 等の追加情報が必要であり未実装。
- DuckDB スキーマ（raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals 等）は前提として存在することを想定。
- .env 自動ロードはプロジェクトルートの検出に依存するため、配布後やインストール環境では環境変数を直接設定することが推奨される場合がある。

---

著者注: この CHANGELOG は与えられた現行ソースから機能・仕様を推測して作成したものであり、実際のリリースノートと差異がある可能性があります。必要であれば各項目をより詳細に分割（例: 機能ごとのサブバージョン、既知の問題一覧、後続タスク）して更新します。