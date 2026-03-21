# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
リリース日はコードベースから推測して記載しています。

## [0.1.0] - 2026-03-21

### 追加 (Added)
- パッケージ初期リリース: kabusys - 日本株自動売買システムのコア機能を実装。
  - パッケージメタ情報: __version__ = "0.1.0"。
  - モジュール分割: data, strategy, execution, monitoring を公開（execution は初期空ディレクトリ）。
- 環境変数 / 設定管理（kabusys.config）
  - .env ファイルの自動ロード機能（プロジェクトルート判定: .git または pyproject.toml を探索）。
  - .env と .env.local の優先順位処理、OS 環境変数保護（protected set）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - 複雑な .env パース実装（export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント処理）。
  - Settings クラスで主要設定をプロパティ提供（J-Quants トークン、kabu API、Slack、DB パス、環境・ログレベル検証など）。
- データ取得 / 永続化（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - 固定間隔のレートリミッタ（120 req/min）を実装。
  - 再試行 (指数バックオフ、最大3回) と 401 自動トークンリフレッシュ処理。
  - ページネーション対応の fetch_* 関数（株価、財務、マーケットカレンダー）。
  - DuckDB への冪等保存関数（raw_prices, raw_financials, market_calendar）を実装（ON CONFLICT で更新）。
  - 型安全な変換ユーティリティ (_to_float/_to_int)。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集の初期実装（デフォルトに Yahoo Finance ビジネスカテゴリ）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除、スキーム/ホスト lowercase）。
  - セキュリティ対策: defusedxml を使用して XML 攻撃を緩和、受信サイズ制限(MAX_RESPONSE_BYTES)、SSRF 対策の考慮。
  - 挿入はバルクチャンク処理で実装、INSERT RETURNING を意識した設計。
- リサーチ（kabusys.research）
  - ファクター計算モジュール（factor_research）:
    - momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日MA）を計算。
    - volatility: ATR（20日）、相対 ATR (atr_pct)、20日平均売買代金、volume_ratio を計算。
    - value: PER / ROE を raw_financials と prices_daily から計算。
    - DuckDB のウィンドウ関数を活用した効率的な集計。
  - feature_exploration:
    - 将来リターン計算 (calc_forward_returns)：複数ホライズン（デフォルト 1/5/21 営業日）での将来リターン取得。
    - IC（calc_ic）：スピアマンランク相関（ランク処理・ties の平均ランク対応）。
    - factor_summary：基本統計量（count/mean/std/min/max/median）。
    - rank ユーティリティ（同順位は平均ランク、丸めで tie 検出を安定化）。
  - research パッケージは zscore_normalize を外部（kabusys.data.stats）から再公開している。
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research モジュールで算出した生ファクターを統合・フィルタ・正規化して features テーブルへ保存する build_features を実装。
  - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5億円）。
  - Z スコア正規化（kabusys.data.stats の zscore_normalize を使用）、±3 でクリップ。
  - 日付単位の置換（トランザクション＋バルク挿入）で冪等性を保証。
- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して final_score を算出、BUY/SELL シグナルを生成する generate_signals を実装。
  - コンポーネントスコア群: momentum, value, volatility, liquidity, news（AI）。
  - スコア変換: Z スコアをシグモイドで [0,1] に変換、欠損コンポーネントは中立 0.5 で補完。
  - 重み（デフォルト設定）を受け取り合計が 1 でない場合は再スケール、不正な値はスキップ。
  - Bear レジーム判定（ai_scores の regime_score 平均が負なら Bear、サンプル閾値あり）で BUY を抑制。
  - SELL 条件実装: ストップロス（終値／avg_price -1 < -8%）とスコア低下（final_score < threshold）。
  - signals テーブルへの日付単位置換（トランザクション＋バルク挿入）で冪等性を保証。
- トランザクションとエラーハンドリング
  - features / signals の書き込みは BEGIN/COMMIT を用い、例外時に ROLLBACK を試行。ROLLBACK 失敗時は警告ログ。
- ロギング
  - 各重要処理でのログ出力を実装（info/debug/warning）。

### 変更 (Changed)
- （初回公開）内部設計に関する注釈や設計方針を各モジュールに明記（ルックアヘッドバイアス回避、発注層依存の排除など）。

### 修正 (Fixed)
- N/A（初版として新規実装。実行上での既知バグ修正はなし）

### 既知の制限 / TODO / 注意点 (Known limitations / Notes)
- execution モジュールは初期状態で実装がない（公開名はあるが発注ロジックは未実装）。
- signal_generator の SELL 条件に記載のうち、トレーリングストップ（peak_price に基づく）や時間決済（保有 60 営業日超）は未実装。positions テーブルに peak_price / entry_date 等の追加が必要。
- news_collector の RSS パース処理や外部 HTTP の具体的なネットワーク制御（タイムアウトの詳細、リトライ等）は将来的な強化ポイント。
- data.jquants_client の _request は urllib を使用。より堅牢な HTTP クライアント（例: requests）への移行や非同期化は将来的な改善候補。
- 一部ユーティリティ（zscore_normalize など）は別ファイル (kabusys.data.stats) に依存するため、その動作前提に注意。

### セキュリティ (Security)
- news_collector で defusedxml を採用し、受信サイズ制限と URL 正規化によるトラッキング除去を実装。SSRF や XML 注入に配慮した実装。
- J-Quants クライアントはトークン管理と自動リフレッシュ処理を実装。RATE LIMIT を守るため固定スロットリングを採用。

---

今後のリリースで想定される項目（例）
- execution 層の実装（kabuステーション / API 連携、注文管理）
- モニタリング、Slack 通知実装（settings にトークンとチャネルは既に定義済み）
- 単体テスト・統合テストの追加、CI/CD パイプライン整備
- パフォーマンス最適化（DuckDB クエリ最適化、非同期 I/O、バッチ処理改善）

ご要望があれば、各セクションの文言をより詳細に分解してバージョン履歴を拡張します。