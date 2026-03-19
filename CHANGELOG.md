# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に従い、セマンティックバージョニングを採用します。

最新: [0.1.0] - 2026-03-19

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システム "KabuSys" のコアライブラリを公開します。主な機能・設計方針・注意点を以下にまとめます。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化とバージョン管理（kabusys.__init__）。
  - __all__ に data, strategy, execution, monitoring を公開。

- 環境設定 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートを .git / pyproject.toml で検出）。
  - 読み込み優先順: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ実装: export プレフィックス対応、シングル/ダブルクォート対応、インラインコメント処理、エスケープ処理。
  - Settings クラス: 必須環境変数の検証（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）、デフォルト値の提供（KABU_API_BASE_URL, データベースパス等）、env/log_level の妥当性チェック、is_live/is_paper/is_dev 補助プロパティ。

- データ取得・永続化 (src/kabusys/data)
  - J-Quants API クライアント (jquants_client.py)
    - 固定間隔スロットリングによるレート制御（120 req/min）。
    - リトライ（指数バックオフ、最大3回）、HTTP 408/429/5xx に対応。
    - 401 受信時はリフレッシュトークンを使って id_token を自動更新して再試行（無限ループ防止）。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）: ON CONFLICT を利用し重複を上書き。
    - 値変換ユーティリティ (_to_float, _to_int) により不正データ耐性を確保。
    - fetched_at を UTC で記録し、Look-ahead Bias の追跡を可能に。

  - ニュース収集モジュール (news_collector.py)
    - RSS フィード取得、記事の前処理、raw_news への冪等保存フローを実装。
    - URL 正規化: トラッキングパラメータ (utm_*, fbclid 等) の除去、クエリソート、スキーム/ホストの小文字化、フラグメント削除。
    - 記事IDは正規化 URL の SHA-256（先頭32文字）等を利用して冪等性を担保。
    - defusedxml で XML 攻撃対策、受信サイズ上限（10MB）、SSRF/不正スキーム検査、バルク INSERT チャンク化などの堅牢化。
    - デフォルト RSS ソースとして Yahoo Finance を登録。

- リサーチ機能 (src/kabusys/research)
  - ファクター計算 (factor_research.py)
    - Momentum（mom_1m/mom_3m/mom_6m、MA200乖離）、Volatility（ATR20、atr_pct、avg_turnover、volume_ratio）、Value（per、roe）など主要ファクター計算を実装。
    - DuckDB SQL を用いた効率的なウィンドウ集計（LAG, AVG OVER 等）。
    - データ不足時は None を返す（安全な欠損扱い）。
  - 特徴量探索 (feature_exploration.py)
    - 将来リターン計算（複数ホライズン対応、デフォルト [1,5,21] 営業日）。
    - IC（Spearman ランク相関）計算、ランク化ユーティリティ（同順位は平均ランク）。
    - ファクターの統計サマリー（count/mean/std/min/max/median）。
  - 研究用ユーティリティをパッケージ公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - research の生ファクターを統合して features テーブル向け特徴量を生成する build_features を実装。
  - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
  - 指定列を Z スコア正規化し ±3 でクリップ（外れ値抑制）。
  - target_date 単位で日付の置換（削除→挿入）を行い冪等性と原子性を確保（BEGIN/COMMIT/ROLLBACK）。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - features と ai_scores を統合して final_score を計算し、BUY/SELL シグナルを生成する generate_signals を実装。
  - コンポーネントスコア: momentum/value/volatility/liquidity/news を計算。
  - デフォルト重みと閾値（デフォルト閾値 0.60、重みは momentum 0.40 等）を実装。ユーザー指定重みは検証・正規化。
  - AI レジームスコア集計による Bear 判定（サンプル数閾値あり）。Bear 時は BUY を抑制。
  - エグジット条件（ストップロス -8%、final_score が閾値未満）による SELL シグナル生成。
  - positions テーブルと prices_daily を参照して SELL 判定を行い、SELL 優先で BUY を排除。
  - signals テーブルへ日付単位での置換保存（トランザクション付き）。

### 変更 (Changed)
- 初回リリースのため履歴無し。コードは設計ドキュメント（StrategyModel.md, DataPlatform.md 等）に沿って実装。

### 修正 (Fixed)
- 初版リリースに含まれる既知の実装上の防御（欠損データスキップ、JSON デコードエラー検出、PK 欠損行のスキップ等）を反映。

### 既知の制限 / 未実装 (Known limitations)
- signal_generator のエグジット論理について未実装の項目:
  - トレーリングストップ（peak_price の追跡が positions テーブルに未対応）
  - 時間決済（保有 60 営業日超過の自動クローズ）
  これらは positions テーブルに peak_price / entry_date 等の拡張が必要。
- news_collector の記事 ID は設計通り SHA-256 を用いるが、実運用での重複判定やマッチング改善は今後の課題。
- research モジュールは DuckDB の prices_daily / raw_financials テーブルを前提としており、外部依存のデータ整備が必要。
- execution パッケージは初期状態（空の __init__）で、実際の発注連携ロジックは含まれない。

### セキュリティ (Security)
- RSS パーシングに defusedxml を利用（XML Bomb など対策）。
- news_collector で受信サイズ制限・URL 正規化・SSRF 回避処理を実装。
- J-Quants クライアントはトークン管理・自動リフレッシュ・リトライ制御で安定性を重視。

### マイグレーション / データベース注意事項
- 期待される DuckDB / SQLite テーブル（名称と想定カラム）:
  - raw_prices (date, code, open, high, low, close, volume, turnover, fetched_at)
  - raw_financials (code, report_date, period_type, eps, roe, fetched_at, ...)
  - prices_daily (date, code, close, high, low, volume, turnover, ...)
  - features (date, code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev, created_at)
  - ai_scores (date, code, ai_score, regime_score)
  - positions (date, code, position_size, avg_price, ...)
  - signals (date, code, side, score, signal_rank)
  - market_calendar (date, is_trading_day, is_half_day, is_sq_day, holiday_name)
- save_* 系関数は ON CONFLICT を用いるため、適切な PK/UNIQUE 制約をスキーマに設定しておく必要があります。

### ドキュメント / 設定
- .env.example を参考に必須環境変数を設定してください（JQUANTS_REFRESH_TOKEN 等）。Settings._require は未設定時に ValueError を投げます。
- ログレベルは LOG_LEVEL 環境変数で設定（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

---

今後の改善予定（次期リリース候補）
- execution 層の発注ロジック統合（kabu API 連携）。
- positions スキーマ拡張（peak_price, entry_date）とトレーリングストップ・時間決済の実装。
- ニュースと銘柄のマッチング精度向上、自然言語処理基盤の導入。
- 単体テスト・統合テストの充実、CI パイプラインの整備。

----- 
（注）この CHANGELOG はソースコードから推測して作成しています。実際のリリースノートとして利用する場合は、変更点や日付等をプロジェクト実情に合わせて適宜調整してください。