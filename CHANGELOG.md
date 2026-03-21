# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このリポジトリはセマンティックバージョニングを採用しています。

## [0.1.0] - 2026-03-21

初回リリース。日本株アルゴリズム売買システム「KabuSys」の基盤機能を実装しました。

### 追加 (Added)
- パッケージ初期化
  - src/kabusys/__init__.py にてバージョン (0.1.0) および公開モジュール一覧を定義。

- 設定/環境変数管理
  - src/kabusys/config.py
    - .env/.env.local をプロジェクトルートから自動読み込み（.git または pyproject.toml をルート判定）。
    - エントリ行のパース機能を実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - Settings クラスを追加し、J-Quants / kabuステーション / Slack / DB パス / システム環境 (env, log_level) をプロパティ経由で取得・検証。
    - env や log_level の値検証（許容値以外は ValueError）。

- データ取得・保存（J-Quants）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装（株価日足、財務データ、マーケットカレンダー取得）。
    - 固定間隔レートリミッタ（120 req/min）を実装。
    - リトライ（指数バックオフ、最大3回）、HTTP 429 の Retry-After 利用、ネットワーク例外に対するリトライ処理。
    - 401 を検知した場合のリフレッシュトークンによる自動トークン更新（1 回のみ）と再試行。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装し、ON CONFLICT を用いた冪等保存を実現。
    - 型変換ユーティリティ (_to_float, _to_int) を実装し、不正値を安全に None に変換。

- ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィードを取得して raw_news に保存する機能の骨子を実装。
    - 記事ID生成に URL 正規化＋SHA-256 使用、トラッキングパラメータ除去。
    - defusedxml を用いた安全な XML 解析、受信サイズ制限、SSRF 回避に関する考慮点。
    - バルク挿入チャンク化による DB 負荷軽減。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py
    - モメンタム (calc_momentum)：1M/3M/6M リターン、MA200 乖離率の計算。
    - ボラティリティ/流動性 (calc_volatility)：20日 ATR、相対ATR (atr_pct)、平均売買代金、volume_ratio の算出。
    - バリュー (calc_value)：raw_financials から最新財務を取得し PER/ROE を計算。
    - DuckDB の SQL ウィンドウ関数を使った効率的な実装とデータ欠損時の安全対策。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 (calc_forward_returns)：指定ホライズンの将来リターン（デフォルト [1,5,21]）。
    - IC（スピアマンランク相関）計算 (calc_ic)、rank、factor_summary（count/mean/std/min/max/median）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで統計処理を実装。

  - src/kabusys/research/__init__.py に公開 API を設定。

- 特徴量エンジニアリング / 戦略
  - src/kabusys/strategy/feature_engineering.py
    - build_features を実装。
      - research の calc_momentum / calc_volatility / calc_value を呼び出して生ファクターを取得。
      - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用。
      - 数値ファクターの Z スコア正規化（外部 zscore_normalize を利用）および ±3 でクリップ。
      - DuckDB の features テーブルへ日付単位で置換（トランザクション + バルク挿入）し冪等性を担保。
      - トランザクション失敗時のロールバックと警告ログ。

  - src/kabusys/strategy/signal_generator.py
    - generate_signals を実装。
      - features, ai_scores, positions テーブルを参照して銘柄ごとのコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
      - シグモイド変換、欠損値は中立値 0.5 で補完。
      - デフォルト重みを定義し、外部から渡された weights の検証・補完・再スケーリング処理を実装。
      - Bear レジーム判定（ai_scores の regime_score 平均が負で十分なサンプル数がある場合）により BUY シグナルを抑制。
      - BUY（閾値 0.60）および SELL（ストップロス -8%、スコア低下）の判定ロジックを実装。
      - SELL 優先ポリシー（SELL 対象は BUY から除外）、signals テーブルへの日付単位置換（トランザクション）で冪等性を担保。

- パッケージ公開
  - src/kabusys/strategy/__init__.py で build_features と generate_signals をエクスポート。

### 変更 (Changed)
- なし（初回リリースのため該当なし）。

### 修正 (Fixed)
- なし（初回リリースのため該当なし）。

### セキュリティ (Security)
- XML パースに defusedxml を使用して XML Bomb 等の攻撃を防止（news_collector）。
- RSS URL 正規化とトラッキングパラメータ除去により ID 再生成時の冪等性と不要な外部参照を抑制。
- news_collector で受信バイト数上限を設け、メモリ DoS を緩和。
- news_collector 内での URL スキーム/ホストチェックや受信先制限により SSRF/不正リダイレクトリスクに配慮（実装方針の明記）。

### 既知の制限 / TODO
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装で、positions テーブルに peak_price / entry_date が必要（注記あり）。
- news_collector の RSS フィード取得中のネットワークリスク回避・タイムアウト等の詳細設定は必要に応じて拡張可能。
- DB スキーマ（テーブル定義）はこのリリースに含まれていないため、運用前に適切なスキーマを作成する必要あり。
- 単体テストの実装は別途実施予定（自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をテスト補助として利用可能）。

---

今後のリリースでは、実運用に向けた次の項目を予定しています（優先度順、例）:
- execution 層（発注ロジック）と監視（monitoring）モジュールの実装
- テストカバレッジ強化・CI 統合
- news_collector の URL エンティティ抽出と銘柄マッチングロジック強化
- パフォーマンス改善（大量データ処理時のメモリ/SQL 最適化）

もし追加で CHANGELOG に含めたい詳細（例えば各ファイルのより細かい実装差分や設計決定理由）があれば教えてください。必要に応じてセクションを分割・追記します。