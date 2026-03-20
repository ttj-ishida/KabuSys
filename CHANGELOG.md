# Changelog

全ての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

現在のバージョン: 0.1.0

## [Unreleased]
- なし（初期リリースのみ）

## [0.1.0] - 2026-03-20
初期リリース。日本株自動売買システム "KabuSys" のコア機能を提供します。以下の主要機能・設計方針・既知の制約を含みます。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化（kabusys.__version__ = 0.1.0、公開 API: data / strategy / execution / monitoring）。
- 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数の読み込み機能（プロジェクトルートを .git または pyproject.toml で探索）。
  - .env パーサ（コメント、export プレフィックス、クォート、エスケープ対応）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須環境変数チェック（_require）。
  - settings オブジェクト（J-Quants/ kabu API / Slack / DB パス / 環境判定 / ログレベル等）。

- データ取得・保存（src/kabusys/data）
  - J-Quants API クライアント（jquants_client.py）
    - 固定間隔スロットリングによるレート制御（120 req/min）。
    - 再試行（指数バックオフ、最大3回）、408/429/5xx の取り扱い、429 の Retry-After 優先。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュ。
    - ページネーション対応（pagination_key を用いた継続取得）。
    - fetch_* 系関数: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
    - DuckDB への冪等保存関数: save_daily_quotes / save_financial_statements / save_market_calendar（ON CONFLICT による更新）。
    - 型変換ユーティリティ (_to_float, _to_int)。
    - 取得時刻（fetched_at）を UTC で記録して look-ahead bias 記録を可能に。
  - ニュース収集（news_collector.py）
    - RSS フィード取得と前処理（URL 正規化、トラッキングパラメータ除去、テキスト正規化）。
    - defusedxml を用いた XML パースで XML 攻撃軽減。
    - SSRF 防止、受信サイズ上限（MAX_RESPONSE_BYTES）によるメモリDoS 対策。
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
    - raw_news / news_symbols 等へのバルク挿入を想定（チャンク化）。

- 研究用モジュール（src/kabusys/research）
  - ファクター計算（factor_research.py）
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均の乖離）を DuckDB 上で計算。
    - calc_volatility: 20日 ATR（atr_20 / atr_pct）、avg_turnover、volume_ratio を計算（true_range の NULL 伝播を制御）。
    - calc_value: raw_financials と prices_daily を組み合わせた per / roe の計算（target_date 以前の最新財務データを結合）。
    - DuckDB のウィンドウ関数と効率的なスキャン範囲指定を利用。
  - 特徴量探索（feature_exploration.py）
    - calc_forward_returns: 指定ホライズン（デフォルト 1/5/21 営業日）の将来リターン計算（LEAD を利用）。
    - calc_ic: スピアマンランク相関（Information Coefficient）計算（同位ランクは平均ランクで処理）。
    - rank / factor_summary: ランク付けと基本統計量（count/mean/std/min/max/median）を算出。
  - research パッケージの公開 API を整備（calc_momentum 等を再エクスポート）。

- 戦略関連（src/kabusys/strategy）
  - 特徴量エンジニアリング（feature_engineering.py）
    - research モジュールの生ファクターを取得し、ユニバースフィルタ（最低株価、最低平均売買代金）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへの日付単位の置換（トランザクション＋一括挿入で冪等性を保証）。
  - シグナル生成（signal_generator.py）
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - 統合重み（デフォルト）に基づく final_score の計算、閾値超えで BUY シグナル生成。
    - Bear レジーム検知（ai_scores の regime_score の集計平均が負 → BUY 抑制）。
    - 保有ポジションのエグジット判定（ストップロス、スコア低下）により SELL シグナル生成。
    - signals テーブルへ日付単位の置換（冪等）。
    - weights の入力検証・正規化（不正値は無視、合計が 1 でない場合は再スケール）。

- ロギング/設計上の配慮
  - 各処理で適切なログ出力（info/warning/debug）を実装。
  - ルックアヘッドバイアス回避方針を明示（target_date 時点までのデータのみを使用）。
  - 本番発注層（execution）への直接依存は持たない設計。

### 変更 (Changed)
- 該当なし（初回リリース）

### 修正 (Fixed)
- 該当なし（初回リリース）

### 削除 (Removed)
- 該当なし（初回リリース）

### セキュリティ (Security)
- news_collector: defusedxml の使用、受信サイズ制限、HTTP スキーム検証などを実装し、XML Bomb / SSRF / メモリ DoS のリスクを低減。
- jquants_client: レートリミットと再試行制御により API 乱用や過負荷による失敗に対処。

### 既知の制約・TODO / 注意事項
- エグジット条件の未実装事項:
  - トレーリングストップ（直近最高値に基づく）や時間決済（保有日数による強制決済）は未実装（コード内コメントで明示）。
  - これらは positions テーブルに peak_price / entry_date 等の情報を追加する必要がある。
- feature_engineering は zscore_normalize を外部（kabusys.data.stats）に依存しているので、その実装が必要（本リポジトリ外の未提示ファイルがある可能性あり）。
- news_collector の実装は RSS パース以降の保存・銘柄紐付け処理が想定されているが、実際の DB スキーマや呼び出し側処理と合わせての検証が必要。
- jquants_client の HTTP 実行は urllib を使用。プロキシや認証まわりは環境に依存するため運用時の確認が必要。
- .env 自動読み込みはプロジェクトルート検出に依存。配布後やインストール環境での挙動に注意（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。

---

貢献・バグ報告・改善提案は issue を通じてお願いします。