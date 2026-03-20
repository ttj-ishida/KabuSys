# CHANGELOG

すべての注目すべき変更履歴をここに記録します。本ファイルは Keep a Changelog の形式に準拠します。  
バージョン番号は semver に従います。

## [0.1.0] - 2026-03-20

### 追加 (Added)
- パッケージ初期リリース: kabusys - 日本株自動売買システムのコアモジュール群を提供。
  - src/kabusys/__init__.py
    - パッケージメタ情報（__version__ = "0.1.0"）と公開サブパッケージ一覧を定義 (data, strategy, execution, monitoring)。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動ロード機構:
    - プロジェクトルートを .git または pyproject.toml から探索して `.env` / `.env.local` を自動読み込み。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化。
    - OS 環境変数は protected として上書きを防止。
  - .env の行解析に対応:
    - export KEY=val 形式、シングルクォート／ダブルクォート内のエスケープ、インラインコメント処理等に対応。
  - 必須値取得用 _require() を提供（未設定時は ValueError を送出）。
  - Settings で主要設定をプロパティとして公開（例: jquants_refresh_token, kabu_api_password, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level, is_live 等）。
  - KABUSYS_ENV と LOG_LEVEL のバリデーションを実装。

- データ取得・保存モジュール (src/kabusys/data)
  - J-Quants API クライアント (src/kabusys/data/jquants_client.py)
    - レート制限 (120 req/min) を守る固定間隔スロットリング実装（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx をリトライ対象）。
    - 401 受信時は ID トークンを自動リフレッシュして1回リトライ。
    - ページネーション対応の fetch_* 関数:
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - DuckDB へ冪等に保存する関数（ON CONFLICT DO UPDATE）:
      - save_daily_quotes -> raw_prices
      - save_financial_statements -> raw_financials
      - save_market_calendar -> market_calendar
    - データ整形ユーティリティ: _to_float / _to_int、UTC fetched_at の付与。
  - ニュース収集モジュール (src/kabusys/data/news_collector.py)
    - RSS フィードから記事を収集・正規化して raw_news へ保存する処理基盤を実装。
    - セキュリティ対策:
      - defusedxml を用いた XML 解析（XML Bomb 等対策）。
      - 受信サイズ上限 (MAX_RESPONSE_BYTES = 10MB)。
      - URL 正規化でトラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去。
      - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
      - SSRF や不正 URL を避ける設計（HTTP/HTTPS 想定）。
    - バルク INSERT のチャンク処理や DB トランザクションを考慮。

- リサーチ用モジュール (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）計算関数 calc_momentum。
    - Volatility / Liquidity（atr_20, atr_pct, avg_turnover, volume_ratio）計算関数 calc_volatility。
    - Value（per, roe）計算関数 calc_value（raw_financials と prices_daily を組み合わせて計算）。
    - DuckDB のウィンドウ関数を利用した効率的な実装。
  - 特徴量探索・評価 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、範囲制限と性能配慮）。
    - IC（スピアマンランク相関）計算 calc_ic と rank ユーティリティ。
    - factor_summary による基本統計量集計（count/mean/std/min/max/median）。
    - pandas 等に依存せず標準ライブラリ + DuckDB で実装。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - build_features(conn, target_date):
    - research モジュールの calc_momentum / calc_volatility / calc_value を呼び出し生ファクターを統合。
    - ユニバースフィルタ（最低株価 _MIN_PRICE=300 円、20日平均売買代金 _MIN_TURNOVER=5e8）を適用。
    - 指定ファクターを z スコア正規化（kabusys.data.stats.zscore_normalize を使用）し ±3 でクリップ。
    - date 単位で features テーブルへ日付単位の置換（DELETE + INSERT）を行い冪等性と原子性を確保（トランザクション利用）。
    - 保存対象カラム: momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev など。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - generate_signals(conn, target_date, threshold=0.60, weights=None)
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - デフォルト重みを定義（momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10）。ユーザー重みは妥当性チェック後に正規化して使用。
    - コンポーネントの欠損は中立値 0.5 で補完。
    - AI の regime_score を用いて市場レジームが Bear か判定（サンプル閾値あり）。Bear 時は BUY シグナルを抑制。
    - BUY シグナル閾値のデフォルトは 0.60。
    - SELL（エグジット）判定を実装:
      - ストップロス: pnl_rate <= -0.08（-8%）
      - final_score が threshold 未満
      - 保有銘柄の価格欠損時は SELL 判定をスキップ（誤クローズ防止）。
    - SELL 優先ポリシー: SELL 対象は BUY から除外し、BUY のランクを再付与。
    - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入）。

### 変更 (Changed)
- （初回リリースにつき該当なし）

### 修正 (Fixed)
- （初回リリースにつき該当なし）

### 非推奨 (Deprecated)
- （初回リリースにつき該当なし）

### 削除 (Removed)
- （初回リリースにつき該当なし）

### セキュリティ (Security)
- RSS パーサーで defusedxml を採用、受信サイズ制限・URL 正規化等を実施し外部入力に対する防御を導入。
- J-Quants クライアントはトークンの自動リフレッシュとリトライ制御により認証/ネットワーク障害の堅牢性を向上。

---

## 既知の制限・注意事項
- feature_engineering / signal_generator / research モジュールは DuckDB のスキーマ（raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar 等）を前提とします。スキーマ定義はリポジトリ外または別スクリプトで用意する必要があります。
- signal_generator のエグジット条件の一部（トレーリングストップや時間決済）は未実装で、positions テーブルに peak_price / entry_date が必要になる想定です（README/設計書参照）。
- calc_forward_returns の horizons は営業日ベース（レコード数）で扱われ、最大252日までを想定。
- news_collector の記事 ID は正規化 URL のハッシュに依存するため、URL 正規化ルールを変えると既存記事との重複判定が変わります。
- J-Quants クライアントは外部 API の挙動（レスポンス形式・ステータス・RateLimit ヘッダ）に依存します。環境に応じた設定（settings.jquants_refresh_token 等）の準備が必要です。
- .env ローダーはプロジェクトルートの検出に __file__ の親ディレクトリを用いるため、パッケージ配布後も期待どおりに動作しますが、特殊な配置やパッケージインストール環境では自動ロードを無効化して手動で環境変数を注入することを推奨します。

---

今後の予定（例）
- 売買ルール拡張: トレーリングストップ、時間決済、ポジションサイズ算出ロジックの追加
- モニタリング/実行層: execution, monitoring サブパッケージの具体実装
- テスト: 各ユニットのカバレッジ強化、外部 API モックの追加

--- 

この CHANGELOG はソースコードの注釈・設計コメントから推測して作成しました。実際の変更履歴やリリースノートとして利用する場合は差分やコミット履歴に基づいて調整してください。