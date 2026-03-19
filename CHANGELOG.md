# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

現在のリリース
- [0.1.0] - 2026-03-19

## [0.1.0] - 2026-03-19
初回公開リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基礎
  - src/kabusys/__init__.py によるパッケージ化とバージョン管理（__version__ = "0.1.0"）。
  - 公開 API: kabusys.data / kabusys.strategy / kabusys.execution / kabusys.monitoring を __all__ に定義。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルと環境変数の優先順位を扱う Settings クラスを実装。
  - 自動 .env ロード:
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を自動読み込み（CWD 非依存）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - .env.local は .env を上書き（ただし既存 OS 環境変数は保護）。
  - .env 行パーサを実装（コメント行・export プレフィックス・クォート/エスケープ・インラインコメント処理などをサポート）。
  - 必須環境変数取得用の _require() とバリデーション:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等をプロパティで取得。
    - KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL 値検証を実装。
  - デフォルト DB パス（DuckDB / SQLite）を設定。

- データ取得・保存 (src/kabusys/data/)
  - J-Quants クライアント (src/kabusys/data/jquants_client.py)
    - API 通信ラッパーを実装。リクエストの共通処理、JSON デコード、ページネーション対応を提供。
    - レート制限対応: 固定間隔スロットリング（120 req/min）での制御クラスを実装。
    - 再試行ロジック: 指数バックオフ、最大3回、408/429/5xx に対するリトライ処理。
    - 401 Unauthorized 受信時にリフレッシュトークンで自動的にトークン再取得して1回リトライ。
    - ID トークンのモジュール内キャッシュ（ページネーション間で共有）を実装。
    - 高レベル API: get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar() を実装。
    - DuckDB への保存ユーティリティ: save_daily_quotes(), save_financial_statements(), save_market_calendar() を実装。いずれも冪等化（ON CONFLICT DO UPDATE）をサポートし、fetched_at を UTC で記録。
    - 型変換ユーティリティ _to_float() / _to_int() を実装し、不正値を安全に扱う。
  - ニュース収集 (src/kabusys/data/news_collector.py)
    - RSS からの記事収集用モジュールを実装（RSS フィード取得、テキスト前処理、冪等保存、記事ID生成方針等）。
    - セキュリティ対策: defusedxml を利用して XML 攻撃を防止、受信サイズ上限（10MB）を設定、HTTP/HTTPS のみ許可などを想定。
    - URL 正規化: トラッキングパラメータ除去（utm_* 等）、スキーム/ホスト小文字化、クエリソート、フラグメント除去を実装。
    - デフォルト RSS ソースとして Yahoo Finance を登録。

- 研究用ファクター計算 (src/kabusys/research/)
  - factor_research.py
    - モメンタム計算 (calc_momentum): 1M/3M/6M リターン、200日移動平均乖離率を DuckDB の SQL ウィンドウ関数で実装。
    - ボラティリティ/流動性計算 (calc_volatility): 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を実装。True Range の NULL 伝搬制御を含む。
    - バリュー計算 (calc_value): raw_financials から最新財務データを取り出して PER / ROE を計算（EPS が 0 もしくは欠損なら PER は None）。
    - いずれも prices_daily / raw_financials のみを参照し、本番 API には依存しない設計。
  - feature_exploration.py
    - 将来リターン計算 (calc_forward_returns): 複数ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD ウィンドウ関数で一括取得。
    - IC（Information Coefficient）計算 (calc_ic): factor と将来リターンのスピアマンランク相関を計算。サンプル不足時は None を返す。
    - ランク変換ユーティリティ (rank): 同順位は平均ランクを割り当てる処理を実装（丸め対策含む）。
    - 統計サマリー (factor_summary): count/mean/std/min/max/median を計算。
  - research パッケージから上記関数群をエクスポート。

- 特徴量作成とシグナル生成 (src/kabusys/strategy/)
  - 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
    - research モジュールの生ファクターを取り込み、ユニバースフィルタ・Z スコア正規化（zscore_normalize を使用）・±3 クリップを行い features テーブルへ UPSERT（日付単位の置換で冪等化）する build_features(conn, target_date) を実装。
    - ユニバースフィルタ: 価格 >= 300 円、20日平均売買代金 >= 5 億円でフィルタリング。
    - 処理は target_date 時点のデータのみ参照してルックアヘッドバイアスを防止。
  - シグナル生成 (src/kabusys/strategy/signal_generator.py)
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）および final_score を算出する generate_signals(conn, target_date, threshold, weights) を実装。
    - デフォルト重み: momentum=0.40, value=0.20, volatility=0.15, liquidity=0.15, news=0.10。閾値デフォルトは 0.60。
    - コンポーネント計算:
      - momentum: momentum_20 / momentum_60 / ma200_dev のシグモイド平均。
      - value: PER を 1/(1+PER/20) でスケール。
      - volatility: atr_pct の Z スコアを反転してシグモイド変換。
      - liquidity: 出来高比率にシグモイド。
      - news: ai_score をシグモイド（未登録は中立）。
    - Bear レジーム判定: ai_scores の regime_score の平均が負（かつサンプル数 >= 3）で Bear と判定し BUY を抑制。
    - SELL（エグジット）判定: ストップロス（現在価格が avg_price より -8% 以下）および final_score が閾値未満の場合に SELL。価格欠損時は SELL 判定をスキップ（誤クローズ防止）。
    - signals テーブルへの日付単位置換（トランザクション＋バルク挿入）で冪等化。

- データ統計ユーティリティ (src/kabusys/data/stats.py はエクスポート参照あり)
  - zscore_normalize を研究／戦略フローで利用（正規化処理の一元化）。

### 変更 (Changed)
- （初版のためなし）

### 修正 (Fixed)
- （初版のためなし）

### セキュリティ & 信頼性
- ネットワーク/外部データ取得時の堅牢性を重視:
  - J-Quants クライアントにレート制限・リトライ・トークン自動更新を実装。
  - RSS 取り込みに defusedxml を採用し XML ベースの攻撃を防止、受信サイズ制限や URL 正規化で SSRF／トラッキングを抑止。
- DB 操作は可能な限り冪等 (ON CONFLICT) とトランザクションで原子性を確保。

### 既知の制約・未実装点
- strategy のいくつかのエグジット条件（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date などの追加情報が必要であり未実装。
- news_collector の RSS パース・記事→銘柄マッチングの詳細実装（例: news_symbols への紐付け）は引き続き実装が必要。
- execution / monitoring モジュールはパッケージに含まれているエクスポート対象があるが、本リリースでの実装は限定的／未実装の可能性あり（コードベース内での公開のみ）。

---

今後の計画（例）
- execution 層の実装（kabuステーション API 統合、注文送信ロジック）
- モニタリング・アラート（Slack 連携を含む）の完成
- news_collector の記事→銘柄マッピング強化、NLP によるニューススコアリングの実装
- 単体テストの整備と CI/CD の導入

--- 

（注）この CHANGELOG は提供されたコードベースから推測して作成しています。実際のリリースノート作成時は差分履歴（コミットログ）と合わせて検証してください。