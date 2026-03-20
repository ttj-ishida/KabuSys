# CHANGELOG

すべての重要な変更点はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

全般方針:
- 可能な限り破壊的変更を避け、DuckDB を中心とした冪等（idempotent）なデータ保存を採用しています。
- ルックアヘッドバイアス防止、データ取得時刻（UTC）記録、外部入力の安全化（XML／URL の検証）などに配慮しています。

## [0.1.0] - 2026-03-20

初回リリース。本パッケージは日本株自動売買システム（KabuSys）の基礎モジュール群を提供します。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは 0.1.0。公開 API として data / strategy / execution / monitoring を想定（execution は空の __init__ を含む）。
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定値を自動的に読み込む機能を実装。
  - 自動ロード優先順位: OS 環境変数 > .env.local > .env。
  - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索するため、CWD に依存しない。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト等で使用）。
  - 必須環境変数取得時に未設定であれば ValueError を送出するヘルパーを提供。
  - デフォルト値:
    - KABU_API_BASE_URL: "http://localhost:18080/kabusapi"
    - DUCKDB_PATH: "data/kabusys.duckdb"
    - SQLITE_PATH: "data/monitoring.db"
    - KABUSYS_ENV: "development"（有効値: development / paper_trading / live）
    - LOG_LEVEL: "INFO"（有効値: DEBUG / INFO / WARNING / ERROR / CRITICAL）
  - 必須環境変数の明示: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- データ取得・保存 (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。
    - レート制限（120 req/min）を守る固定間隔スロットリング（RateLimiter）。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - HTTP リトライ（指数バックオフ、最大 3 回）。再試行対象は 408/429 と 5xx、ネットワークエラー等。
    - 401 を受け取った場合は ID トークンを自動リフレッシュして 1 回リトライ（無限再帰を防ぐ設計）。
    - モジュールレベルで ID トークンをキャッシュしページネーション間で共有。
    - 取得時刻を UTC ISO 形式で記録（fetched_at）。ルックアヘッドバイアスのトレースを容易に。
  - DuckDB への保存関数を提供（save_daily_quotes / save_financial_statements / save_market_calendar）。
    - 保存は冪等（ON CONFLICT DO UPDATE / DO NOTHING）で実装。
    - PK 欠損行はスキップし、スキップ数をログ出力。
    - 型変換ユーティリティ _to_float / _to_int を提供（不正値は None に変換）。
- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集して raw_news に保存する基礎を追加。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去、小文字化）を実装し、記事ID を正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成して冪等性を確保。
  - defusedxml を利用して XML Bomb 等の攻撃を防止。
  - HTTP レスポンスの最大受信バイト数を制限（デフォルト 10 MB）してメモリ DoS を防ぐ。
  - HTTP スキームの検査等により SSRF 危険性に配慮。
  - バルク INSERT のチャンク処理でパラメータ数制限に対応し、INSERT RETURNING により実際に追加された件数を報告。
  - デフォルト RSS ソースに Yahoo Finance のビジネス RSS を追加。
- 研究（research）モジュール
  - factor_research.py: prices_daily / raw_financials を参照して各種ファクターを計算する関数を実装。
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日移動平均乖離）を計算。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、volume_ratio を計算。true_range の NULL 伝播を制御してカウント精度を保つ。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算。EPS が 0 または欠損の場合は per を None にする。
  - feature_exploration.py:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）で将来リターンを計算。ホライズンは営業日ベースでチェックし、範囲をまとめて 1 クエリで取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコード < 3 なら None）。
    - factor_summary: 各ファクター列の基本統計（count/mean/std/min/max/median）を計算。
    - rank: 同順位は平均ランクを採用するランク変換ユーティリティ（round(..., 12) を用いた tie の安定化）。
  - research パッケージ __init__ で主要関数を公開。
- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - build_features を実装。
    - research モジュールの calc_momentum / calc_volatility / calc_value を用いて生ファクターを取得。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップして外れ値の影響を抑制。
    - features テーブルへ日付単位で置換（トランザクション + バルク挿入で原子性を保証）。冪等性を重視。
- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - generate_signals を実装。
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を算出。
    - final_score を重み付き合算（デフォルト重みは momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10）。
    - weights の妥当性検証と合計が 1.0 でない場合の再スケール機能を実装。無効なキーや値は警告して無視。
    - Bear レジーム判定: ai_scores の regime_score 平均が負のとき（ただしサンプル数が閾値未満なら Bear 判定しない）BUY を抑制。
    - BUY シグナル閾値はデフォルト 0.60。SELL シグナル（エグジット）条件としてストップロス（-8%）とスコア低下を実装。SELL は BUY より優先して排除。
    - signals テーブルへ日付単位で置換（トランザクション + バルク挿入で原子性を保証）。
- ログとエラーハンドリング
  - 主要処理で情報・警告・デバッグログを適切に出力するよう設計（logger 使用）。

### 改善 (Changed)
- データ処理・集計は基本的に SQL（DuckDB）で行い、必要な集計ウィンドウは SQL 側で完結させることでパフォーマンスと一貫性を向上。
- NULL 値伝播やカウント条件（ATR / MA の十分なデータ点数チェック）に注意して計算精度を改善。

### 修正 (Fixed)
- （初版のため暫定）価格や財務値が欠損する場合は計算を None とするなど安全に動作する設計を反映。

### セキュリティ (Security)
- RSS パースに defusedxml を使用して XML による攻撃を緩和。
- ニュースの URL 正規化／検査によりトラッキングパラメータ除去・SSRF のリスク低減。
- J-Quants のトークンはキャッシュ制御しつつ、401 発生時は自動で安全にリフレッシュするが、無限ループを起こさない設計を採用。

### 既知の制限・未実装 (Known issues / TODO)
- signal_generator のエグジット条件でトレーリングストップ（peak_price に基づく）や時間決済（保有 60 営業日超）は未実装（positions テーブルに peak_price / entry_date が必要）。
- data.stats.zscore_normalize の実装詳細は別モジュール（現状 import で利用）で提供される前提。
- execution（発注層）は本バージョンで未実装（プレースホルダ存在）。
- 一部の外部 API や DB スキーマ（テーブル定義）はこのリリースに含まれておらず、導入時にスキーマ準備が必要。

### マイグレーションノート (Migration notes)
- 環境変数を正しく設定すること:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 任意・デフォルト値あり: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL
- テスト環境等で自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

今後の予定（短期ロードマップ案）
- execution 層の実装（kabuステーション API 経由の発注・約定管理）。
- signal_generator の追加エグジットルール（トレーリングストップ、保有期間による決済）。
- モニタリング / Slack 通知機能の実装（slack_bot_token を用いた通知）。
- 単体テストと CI/CD パイプラインの整備。

（以上）