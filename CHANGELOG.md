# Changelog

すべての注目すべき変更はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用します。

## [Unreleased]

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システムのコア機能（データ取得・保存、ファクター計算、特徴量生成、シグナル生成、研究用ユーティリティ）を実装。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化とバージョン定義を追加（kabusys __version__ = 0.1.0）。
  - モジュール群を public API としてエクスポート（data, strategy, execution, monitoring）。

- 環境設定管理 (kabusys.config)
  - .env と .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする仕組みを実装。
  - 読み込み順序: OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用）。
  - .env の行パーサを実装。export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント（条件付き）などを考慮して堅牢にパース。
  - 環境変数必須チェック用 _require() と Settings クラスを実装。J-Quants / kabu / Slack / DB パス / システム設定などのプロパティを提供。
  - KABUSYS_ENV / LOG_LEVEL の検証（有効な値セットをチェック）と便利なフラグ (is_live/is_paper/is_dev)。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。主な機能:
    - レート制限 (120 req/min) の固定間隔スロットリング実装（RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大3回、408/429/5xx を対象）。
    - 401 受信時のトークン自動リフレッシュ（1 回のみ）と ID トークンキャッシュ。
    - ページネーション対応のデータ取得（daily_quotes、statements、trading_calendar）。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT を用いた冪等保存。
    - データ型変換ユーティリティ (_to_float / _to_int) を実装し不正値を安全に扱う。
    - fetched_at を UTC ISO8601 で記録し、Look-ahead バイアスのトレースを可能に。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集基盤を実装（デフォルトに Yahoo Finance を設定）。
  - セキュリティ対策: defusedxml を利用した XML パース、防御的 URL 検査（HTTP/HTTPS のみ）、受信サイズ制限（10MB）等を実装。
  - URL 正規化 (utm_* 等トラッキングパラメータ削除、クエリソート、フラグメント除去) と記事 ID の一意化（ハッシュ化）方針を導入。
  - テキスト前処理・チャンクバルク挿入・INSERT 扱いの冪等性を考慮した実装。

- 研究用ファクター計算 (kabusys.research.factor_research)
  - モメンタム（calc_momentum）
    - 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を計算。
    - データ不足時の扱い（十分なウィンドウがない場合は None）。
  - ボラティリティ / 流動性（calc_volatility）
    - ATR（20 日）、相対 ATR (atr_pct)、20 日平均売買代金、出来高比 (volume_ratio) を計算。
    - true_range の NULL 伝播制御（high/low/prev_close が NULL の場合は true_range を NULL にする）。
  - バリュー（calc_value）
    - raw_financials から target_date 以前の最新財務データを取得し PER / ROE を計算。
    - 財務データが欠損・EPS が 0 の場合の安全な処理。
  - DuckDB に対する効率的な SQL 実装（スキャン範囲の限定、ウィンドウ関数利用）を採用。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date) を実装:
    - research モジュールから取得した生ファクターを統合し、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
    - 指定カラムの Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）と ±3 クリップ。
    - 日付単位で features テーブルへ置換（DELETE + bulk INSERT）し冪等性・原子性を保証（トランザクション）。
    - ルックアヘッドバイアス対策として target_date 時点のデータのみを使用する設計方針を明示。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold=0.6, weights=None) を実装:
    - features と ai_scores を統合し、コンポーネントスコア（momentum / value / volatility / liquidity / news）を算出。
    - sigmoid 変換・欠損補完（None を中立 0.5 で補完）を行い final_score を計算。
    - ユーザ指定 weights を検証・フォールバックし合計が 1.0 になるよう再スケール。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合。ただしサンプル数閾値あり）により BUY 抑制が可能。
    - BUY 判定（閾値以上）、SELL 判定（ストップロス / スコア低下）を実装し、signals テーブルへ日付単位の置換で保存（トランザクション）。
    - 保有ポジションのエグジット判定は positions / prices_daily を参照し、価格欠損時に安全にスキップ。
    - 未実装のエグジット条件（トレーリングストップ・時間決済）はコメントで明記。

- 研究用探索ユーティリティ (kabusys.research.feature_exploration)
  - calc_forward_returns(conn, target_date, horizons=[1,5,21]) を実装。LEAD ウィンドウを用いた将来リターン取得。
  - calc_ic(factor_records, forward_records, factor_col, return_col) を実装。Spearman のランク相関（ties を平均ランクで扱う）を算出し、サンプル不足時は None を返却。
  - rank(values) 実装。浮動小数点の丸め誤差対策として round(..., 12) を使い同順位を平均ランク化。
  - factor_summary(records, columns) により count/mean/std/min/max/median を算出。

### 変更 (Changed)
- 初版のため該当なし。

### 修正 (Fixed)
- 初版のため該当なし。

### セキュリティ (Security)
- news_collector で defusedxml を使用し XML パーシング攻撃を軽減。
- URL 正規化とスキーム制限により SSRF リスクを低減。
- news_collector の受信バイト上限を設け、メモリ DoS の可能性を低減。

### 内部 (Internals)
- DuckDB を中心としたデータ設計により、クエリは prices_daily / raw_prices / raw_financials / features / ai_scores / positions / signals / market_calendar などのテーブルを参照する設計を想定。
- ルックアヘッドバイアス防止のため、各所で「target_date 以前の最新データのみ参照する」方針を徹底。
- ほとんどの DB 書き込みはトランザクション + バルク挿入により原子性・冪等性を確保。
- 外部依存を極力排し標準ライブラリ中心で実装（ただし XML 安全化のため defusedxml を利用）。

### 既知の制限・今後の課題
- positions テーブルに peak_price / entry_date 等の情報が存在しないため、トレーリングストップや時間決済（保有日数ベース）の実装は未完了。
- 一部の機能（execution / monitoring）モジュールの実装はパッケージ構造として存在するが、具体的な発注連携ロジックは含まれていない。
- AI スコア（ai_scores）の生成・更新は本リリースでの責務外。外部プロセスで ai_scores を投入する想定。
- news_collector の DB 保存や記事→銘柄紐付けロジックの詳細（news_symbols 等）は運用で拡張予定。

---

（注）リリースノートはコードベースから推測して作成しています。実際の運用やドキュメントと差異がある可能性があります。必要であれば各機能ごとにより詳細な CHANGELOG エントリやマイグレーション手順を追記します。