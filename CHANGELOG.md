# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従っています。  
リリース履歴は日付順（降順）に記載しています。

注意: コードベースから推測してまとめています。実装コメントや docstring に基づく設計上の意図や既知の制約も併記しています。

## [Unreleased]

## [0.1.0] - 2026-03-20
初回公開リリース。

### Added
- パッケージ基盤
  - パッケージルート: `kabusys`、バージョン `0.1.0` を設定。
  - パッケージ公開 API: `data`, `strategy`, `execution`, `monitoring` を __all__ に定義。

- 設定・環境管理 (`kabusys.config`)
  - .env ファイルおよび環境変数からの設定自動ロード機能を実装。
  - プロジェクトルート検出 (`_find_project_root`)：.git または pyproject.toml を起点として探索するため CWD に依存しない。
  - .env パーサー (`_parse_env_line`)：
    - `export KEY=val` 形式に対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理。
    - コメント処理（クォート外の # を条件付きでコメントとして扱う）。
  - .env 読み込み (`_load_env_file`)：
    - override / protected（OS 環境変数保護）オプションを提供。
    - 読み込み失敗時は警告を発行。
  - 自動ロード制御: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - `Settings` クラスで各種必須値やデフォルト値をプロパティ提供:
    - J-Quants / kabu API / Slack / DB パス（DuckDB/SQLite）
    - 環境 (`KABUSYS_ENV`) とログレベル (`LOG_LEVEL`) の検証、利便性プロパティ (`is_live`, `is_paper`, `is_dev`)。

- データ収集・永続化 (`kabusys.data`)
  - J-Quants API クライアント (`jquants_client`) を実装。
    - 固定間隔スロットリングによるレート制御（120 req/min）を実装する `_RateLimiter`。
    - 再試行ロジック（指数バックオフ、最大3回）とステータスコードハンドリング（408/429/5xx）。
    - 401 を検知した場合のリフレッシュトークンによる自動トークン更新＋1回リトライ。
    - ページネーション対応の取得関数:
      - `fetch_daily_quotes`
      - `fetch_financial_statements`
      - `fetch_market_calendar`
    - DuckDB への保存関数（冪等）:
      - `save_daily_quotes` (`raw_prices` へ ON CONFLICT DO UPDATE)
      - `save_financial_statements` (`raw_financials`)
      - `save_market_calendar` (`market_calendar`)
    - データ整形ユーティリティ: `_to_float`, `_to_int`（不正値に寛容な変換）
    - モジュールレベルの ID トークンキャッシュ（ページネーション間で共有）
    - fetched_at を UTC ISO8601 で記録し、look-ahead バイアスを追跡可能に

  - ニュース収集モジュール (`news_collector`)
    - RSS フィードの収集と raw_news への冪等保存（ON CONFLICT DO NOTHING 想定）。
    - 記事 ID は URL 正規化後の SHA-256（先頭 32 文字）で生成して冪等性を確保。
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ（utm_* など）除去、フラグメント削除、クエリソート。
    - セキュリティ対策:
      - defusedxml を利用して XML 関連攻撃（XML Bomb 等）を防ぐ。
      - 受信最大バイト数制限（10 MB）でメモリ DoS を緩和。
      - HTTP/HTTPS 以外のスキーム除外等 SSRF 対策の方針を記述。
    - バルク insert のチャンク化（デフォルト 1000 件）によるパフォーマンス配慮。
    - デフォルト RSS ソースを含む（例: Yahoo Finance business RSS）。

- 研究（Research）モジュール (`kabusys.research`)
  - ファクター計算・探索ユーティリティを実装／公開:
    - `factor_research`:
      - `calc_momentum`（mom_1m/mom_3m/mom_6m、ma200_dev）
      - `calc_volatility`（atr_20、atr_pct、avg_turnover、volume_ratio）
      - `calc_value`（per、roe。raw_financials から最新財務を参照）
    - `feature_exploration`:
      - `calc_forward_returns`（複数ホライズンに対応、デフォルト [1,5,21]）
      - `calc_ic`（Spearman ランク相関による IC 計算）
      - `factor_summary`（count/mean/std/min/max/median）
      - `rank`（同順位は平均ランク）
    - これらを research.__init__ でエクスポート。
  - 設計方針として DuckDB と標準ライブラリのみを用いること、ルックアヘッドバイアス防止を明記。

- 戦略（Strategy）モジュール (`kabusys.strategy`)
  - 特徴量エンジニアリング (`feature_engineering.build_features`)
    - research 側で算出した raw factor を取り込み、ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 指定カラムを Z スコア正規化（zscore_normalize を使用）、±3 でクリップ。
    - features テーブルへ日付単位で置換（トランザクション + バルク挿入）し冪等性を担保。
    - 価格参照は target_date 以前の最新価格を使用（休場日等の欠損に対応）。
  - シグナル生成 (`signal_generator.generate_signals`)
    - features と ai_scores を統合し、複数のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - デフォルト重みと閾値（default weights, threshold=0.60）を実装。ユーザー重みを検証・補正し合計を 1.0 に再スケール。
    - AI レジームスコアの平均から Bear レジームを判定し、Bear 時は BUY を抑制。
    - BUY はスコア閾値超過銘柄へ付与、SELL は保有ポジションに対するストップロス（-8%）やスコア低下で判定。
    - SELL 優先ポリシー（SELL 対象は BUY から除外）と、signals テーブルへの日付単位置換（トランザクション）による冪等性。
    - いくつかのエグジット条件（トレーリングストップ、時間決済）は未実装で、positions テーブルの追加情報が必要である旨をドキュメントに明記。

### Security
- ニュース収集: defusedxml の使用、受信サイズ制限、トラッキングパラメータ除去、URL 正規化等で入力の信頼性を向上。
- J-Quants クライアント: 401 リフレッシュ処理やリトライポリシーで誤った認証状態や一時的な障害に対処。

### Performance / Reliability
- DuckDB 側の挿入処理は executemany / ON CONFLICT を多用し冪等性と効率を両立。
- ニュースのバルク INSERT をチャンク化して SQL 長やパラメータ数の上限を回避。
- API レート制御を中央の RateLimiter で統一実装。

### Documentation / Design notes
- 各モジュールに詳細な docstring を付与し、設計方針、アルゴリズム、既知の未実装点（例: トレーリングストップ）や注意点を明記。
- ルックアヘッドバイアス防止を通底的な設計目標として繰り返し記載。

### Known limitations / Notes
- monitoring / execution の公開はパッケージに含まれるが、今回のコードスニペットでは実装が見られない（execution パッケージは空）。
- 一部のエグジット条件は未実装（コメントで明示）。
- news_collector の RSS 取得時の HTTP レスポンス処理の詳細（gzip 解凍や受信バイト厳密制限の実装箇所の続き）はこのスニペットで途切れているため、実装の完全性はコード全体で要確認。

---

（今後のリリースではバグ修正、テスト追加、execution / monitoring 層の実装、外部向けの CLI / サービス起動方法などを記録してください。）